#!/usr/bin/env python3
"""Build the canonical self-contained HAILIE final report.

The report consumes only the authoritative files in ``outputs/final``.  Run
``scripts/generate_final_outputs.py`` first; archived exploratory outputs are
never read by this script.
"""

from __future__ import annotations

import base64
import csv
import html
import json
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
FINAL_DIR = REPO_ROOT / "outputs" / "final"
FIGURES_DIR = REPO_ROOT / "outputs" / "figures"
REPORT_PATH = REPO_ROOT / "outputs" / "HAILIE_final_report.html"
ENGLAND_CODE = "E92000001"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def load_observations() -> dict[str, dict]:
    series: dict[str, dict] = {}
    for row in load_csv(DATA_PATH):
        code = row["Area code"]
        series.setdefault(code, {"name": row["Region"], "values": {}})
        if row["households_on_register"]:
            series[code]["values"][int(row["year"])] = int(row["households_on_register"])
    return series


def fmt(value: float | str) -> str:
    return f"{float(value):,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value:+.1f}%"


def image_data(filename: str) -> str:
    return base64.b64encode((FIGURES_DIR / filename).read_bytes()).decode("ascii")


def table(headers: list[str], rows: list[list[str]], caption: str, row_headers: bool = False) -> str:
    header_html = "".join(f'<th scope="col">{html.escape(header)}</th>' for header in headers)
    body = []
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            tag = "th" if row_headers and index == 0 else "td"
            scope = ' scope="row"' if tag == "th" else ""
            cells.append(f"<{tag}{scope}>{value}</{tag}>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-wrap"><table><caption>'
        + html.escape(caption)
        + "</caption><thead><tr>"
        + header_html
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def build_region_panels(
    observations: dict[str, dict],
    regional_forecasts: list[dict[str, str]],
    selections: list[dict[str, str]],
) -> tuple[str, str, str]:
    selection_by_code = {row["area_code"]: row for row in selections}
    forecasts_by_code: dict[str, list[dict[str, str]]] = {}
    for row in regional_forecasts:
        forecasts_by_code.setdefault(row["area_code"], []).append(row)

    options = []
    panels = []
    comparison_rows = []
    for code in sorted(forecasts_by_code, key=lambda value: observations[value]["name"]):
        name = observations[code]["name"]
        latest = observations[code]["values"][2025]
        forecast_rows = sorted(forecasts_by_code[code], key=lambda row: int(row["forecast_year"]))
        final_row = forecast_rows[-1]
        point_2028 = float(final_row["point_forecast"])
        change_pct = 100 * (point_2028 - latest) / latest
        selection = selection_by_code[code]
        range_2028 = f'{fmt(final_row["lower_80"])}–{fmt(final_row["upper_80"])}'
        if selection["primary_model"] == "naive":
            interpretation = (
                "The central estimate repeats the 2025 observation because backtesting selected "
                "the naive carry-forward model. This is a property of the model, not evidence that "
                "the register count will remain unchanged."
            )
        else:
            interpretation = (
                f"The selected model gives a central change of {fmt_pct(change_pct)} from 2025. "
                "The regional backtest does not support treating that point estimate as a strong "
                "directional call."
            )
        options.append(f'<option value="{html.escape(code)}">{html.escape(name)}</option>')
        comparison_rows.append(
            [
                html.escape(name),
                html.escape(selection["primary_model_label"]),
                fmt(latest),
                fmt(point_2028),
                range_2028,
            ]
        )
        forecast_table = table(
            ["Year", "Point forecast", "80% interval", "95% diagnostic range"],
            [
                [
                    row["forecast_year"],
                    fmt(row["point_forecast"]),
                    f'{fmt(row["lower_80"])}–{fmt(row["upper_80"])}',
                    f'{fmt(row["lower_95"])}–{fmt(row["upper_95"])}',
                ]
                for row in forecast_rows
            ],
            f"{name}: final 2026–2028 forecast and empirical prediction intervals",
        )
        panels.append(
            f'''<section class="region-panel" id="region-{html.escape(code)}" hidden>
              <h3>{html.escape(name)}</h3>
              <p><strong>2025 observed:</strong> {fmt(latest)} households. <strong>2028 forecast:</strong>
              {fmt(point_2028)} with an 80% range of {range_2028}. The selected short-horizon
              model is {html.escape(selection["primary_model_label"])}. {html.escape(interpretation)}
              The separately selected five-year extension model is
              {html.escape(selection["extension_model_label"])}.</p>
              {forecast_table}
            </section>'''
        )

    comparison_rows.sort(key=lambda row: float(row[3].replace(",", "")), reverse=True)
    comparison_table = table(
        ["Region", "Selected model", "2025 observed", "2028 central", "2028 80% range"],
        comparison_rows,
        "Regional 2025 observations, selected models and 2028 forecasts with 80% ranges",
        row_headers=True,
    )
    return "".join(options), "".join(panels), comparison_table


def main() -> None:
    required = [
        "national_model_metrics.csv",
        "national_model_selection.csv",
        "national_forecast_2026_2028.csv",
        "national_extension_2026_2030.csv",
        "national_history_sensitivity.csv",
        "regional_model_metrics.csv",
        "regional_model_selection.csv",
        "regional_forecast_2026_2028.csv",
        "regional_extension_2026_2030.csv",
    ]
    missing = [name for name in required if not (FINAL_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing final outputs: " + ", ".join(missing) + ". Run scripts/generate_final_outputs.py first."
        )

    observations = load_observations()
    national_forecasts = load_csv(FINAL_DIR / "national_forecast_2026_2028.csv")
    national_extension = load_csv(FINAL_DIR / "national_extension_2026_2030.csv")
    national_metrics = load_csv(FINAL_DIR / "national_model_metrics.csv")
    history_sensitivity = load_csv(FINAL_DIR / "national_history_sensitivity.csv")
    regional_forecasts = load_csv(FINAL_DIR / "regional_forecast_2026_2028.csv")
    regional_selections = load_csv(FINAL_DIR / "regional_model_selection.csv")

    england = observations[ENGLAND_CODE]["values"]
    latest = england[2025]
    national_2028 = next(row for row in national_forecasts if row["forecast_year"] == "2028")
    national_change = 100 * (float(national_2028["point_forecast"]) - latest) / latest

    national_table = table(
        ["Year", "Point forecast", "80% interval", "95% diagnostic range", "Selected model"],
        [
            [
                row["forecast_year"],
                fmt(row["point_forecast"]),
                f'{fmt(row["lower_80"])}–{fmt(row["upper_80"])}',
                f'{fmt(row["lower_95"])}–{fmt(row["upper_95"])}',
                html.escape(row["selected_model_label"]),
            ]
            for row in national_forecasts
        ],
        "Final England forecast for 2026–2028",
    )

    extension_by_year = {row["forecast_year"]: row for row in national_extension}
    overlap_table = table(
        ["Year", "Primary damped-trend forecast", "Naive five-year extension", "Difference"],
        [
            [
                row["forecast_year"],
                fmt(row["point_forecast"]),
                fmt(extension_by_year[row["forecast_year"]]["point_forecast"]),
                fmt(float(row["point_forecast"]) - float(extension_by_year[row["forecast_year"]]["point_forecast"])),
            ]
            for row in national_forecasts
        ],
        "Direct comparison of overlapping 2026–2028 forecasts",
    )

    extension_table = table(
        ["Year", "Point forecast", "80% interval", "95% diagnostic range"],
        [
            [
                row["forecast_year"],
                fmt(row["point_forecast"]),
                f'{fmt(row["lower_80"])}–{fmt(row["upper_80"])}',
                f'{fmt(row["lower_95"])}–{fmt(row["upper_95"])}',
            ]
            for row in national_extension
        ],
        "England five-year naive extension, 2026–2030",
    )

    region_options, region_panels, regional_comparison = build_region_panels(
        observations, regional_forecasts, regional_selections
    )

    selection_table = table(
        ["Region", "2026–2028 model", "Mean Y1–Y3 MAE", "2026–2030 model", "Y5 MAE"],
        [
            [
                html.escape(row["region"]),
                html.escape(row["primary_model_label"]),
                fmt(row["mean_y1_y3_mae_households"]),
                html.escape(row["extension_model_label"]),
                fmt(row["y5_mae_households"]),
            ]
            for row in regional_selections
        ],
        "Final regional model selections using MAE",
        row_headers=True,
    )

    metrics_by_model: dict[str, dict[int, str]] = {}
    labels = {}
    for row in national_metrics:
        metrics_by_model.setdefault(row["model"], {})[int(row["horizon_years"])] = fmt(row["mae_households"])
        labels[row["model"]] = row["model_label"]
    national_metrics_table = table(
        ["Model", "Y1 MAE", "Y2 MAE", "Y3 MAE", "Y5 MAE"],
        [
            [html.escape(labels[model])] + [metrics_by_model[model][horizon] for horizon in [1, 2, 3, 5]]
            for model in ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]
        ],
        "National rolling-origin model performance; MAE in households (lower is better)",
        row_headers=True,
    )
    national_model_note = (
        "Model note: although seven candidate labels are evaluated, the restricted ARIMA search selects "
        "(0,1,0) here and SES converges to alpha approximately 1, so both reproduce the naive carry-forward "
        "forecast on this series. These are effectively equivalent baselines, not independent corroboration."
    )

    model_order = ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]

    def sensitivity_selection(
        records: list[dict[str, str]],
    ) -> tuple[str, float, str, float, int, int, float, int, float]:
        metric = {(row["model"], int(row["horizon_years"])): float(row["mae_households"]) for row in records}
        names = {row["model"]: row["model_label"] for row in records}
        primary_scores = {model: sum(metric[(model, horizon)] for horizon in [1, 2, 3]) / 3 for model in model_order}
        extension_scores = {model: metric[(model, 5)] for model in model_order}
        primary_ranking = sorted(model_order, key=lambda model: (primary_scores[model], model_order.index(model)))
        primary = primary_ranking[0]
        extension = min(model_order, key=lambda model: (extension_scores[model], model_order.index(model)))
        first = next(row for row in records if row["model"] == primary and row["horizon_years"] == "1")
        fifth = next(row for row in records if row["model"] == extension and row["horizon_years"] == "5")
        return (
            names[primary],
            primary_scores[primary],
            names[extension],
            extension_scores[extension],
            int(first["forecast_origins"]),
            int(fifth["forecast_origins"]),
            primary_scores["damped_trend"],
            primary_ranking.index("damped_trend") + 1,
            primary_scores["naive"],
        )

    sensitivity_groups = {
        "1987 (full, pre-specified)": national_metrics,
        "1998 (first trough onward)": [row for row in history_sensitivity if row["history_start_year"] == "1998"],
        "2005 (stronger-validation era)": [row for row in history_sensitivity if row["history_start_year"] == "2005"],
    }
    sensitivity_results = {
        label: sensitivity_selection(records) for label, records in sensitivity_groups.items()
    }
    sensitivity_table = table(
        [
            "History window",
            "Y1–Y3 winner",
            "Winner mean MAE",
            "Damped-Holt mean MAE",
            "Damped-Holt rank",
            "Naive mean MAE",
            "Y5 winner",
            "Y5 MAE",
            "Y1 / Y5 origins",
        ],
        [
            [
                html.escape(label),
                html.escape(result[0]),
                fmt(result[1]),
                fmt(result[6]),
                f"{result[7]} of {len(model_order)}",
                fmt(result[8]),
                html.escape(result[2]),
                fmt(result[3]),
                f"{result[4]} / {result[5]}",
            ]
            for label, result in sensitivity_results.items()
        ],
        "Sensitivity of national model selection to the amount of history used",
        row_headers=True,
    )
    sensitivity_1998 = sensitivity_results["1998 (first trough onward)"]
    sensitivity_2005 = sensitivity_results["2005 (stronger-validation era)"]
    sensitivity_summary = (
        "Naive has lower mean Y1–Y3 MAE than damped Holt in both later-history windows. "
        f"For 1998–2025, damped Holt records {fmt(sensitivity_1998[6])} and ranks "
        f"{sensitivity_1998[7]} of {len(model_order)}, compared with {fmt(sensitivity_1998[8])} "
        f"for naive. For 2005–2025, damped Holt records {fmt(sensitivity_2005[6])} and ranks "
        f"{sensitivity_2005[7]} of {len(model_order)}, compared with {fmt(sensitivity_2005[8])} "
        "for naive."
    )

    html_out = TEMPLATE
    replacements = {
        "__GENERATED_DATE__": date.today().strftime("%-d %B %Y"),
        "__LATEST__": fmt(latest),
        "__FORECAST_2028__": fmt(national_2028["point_forecast"]),
        "__CHANGE_2028__": fmt_pct(national_change),
        "__PI80_2028__": f'{fmt(national_2028["lower_80"])}–{fmt(national_2028["upper_80"])}',
        "__NATIONAL_TABLE__": national_table,
        "__OVERLAP_TABLE__": overlap_table,
        "__EXTENSION_TABLE__": extension_table,
        "__REGION_OPTIONS__": region_options,
        "__REGION_PANELS__": region_panels,
        "__REGIONAL_COMPARISON__": regional_comparison,
        "__SELECTION_TABLE__": selection_table,
        "__NATIONAL_METRICS_TABLE__": national_metrics_table + f'<p class="small">{html.escape(national_model_note)}</p>',
        "__SENSITIVITY_TABLE__": sensitivity_table,
        "__SENSITIVITY_SUMMARY__": sensitivity_summary,
        "__NATIONAL_TREND_IMAGE__": image_data("england_waiting_list_1987_2025.png"),
        "__REGIONAL_TREND_IMAGE__": image_data("regional_waiting_list_trends.png"),
        "__REGION_DATA_JSON__": json.dumps([row["area_code"] for row in regional_selections]),
    }
    for marker, value in replacements.items():
        html_out = html_out.replace(marker, value)
    if "__" in html_out:
        raise AssertionError("An unreplaced report template marker remains")
    REPORT_PATH.write_text(html_out, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HAILIE social housing waiting-list forecast — final report</title>
  <style>
    :root{--navy:#17324d;--blue:#245b78;--teal:#19706f;--ink:#16232e;--muted:#4f5f6c;--line:#ccd6dc;--soft:#edf3f5;--paper:#fff;--warn:#7a4b00;--warn-bg:#fff4d8;--ok:#155b3b;--ok-bg:#e5f4ec}
    *{box-sizing:border-box} html{scroll-behavior:smooth} body{margin:0;background:#f3f6f7;color:var(--ink);font:16px/1.58 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    a{color:#005a85;text-decoration-thickness:.1em;text-underline-offset:.15em} a:focus-visible,button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #9a6a00;outline-offset:3px}
    .skip{position:absolute;left:-9999px;top:0}.skip:focus{left:1rem;top:1rem;background:#fff;padding:.7rem;z-index:10}
    .page{max-width:1080px;margin:auto;background:var(--paper);min-height:100vh;box-shadow:0 0 30px #21313c1a}.hero{padding:3.5rem clamp(1.2rem,5vw,4rem);background:var(--navy);color:#fff}.hero *{color:#fff}.eyebrow{text-transform:uppercase;letter-spacing:.09em;font-weight:700;font-size:.82rem}.hero h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.06;max-width:17ch;margin:.4rem 0 1rem}.hero .lead{max-width:70ch;font-size:1.15rem}.meta{opacity:.86;font-size:.9rem}
    nav{padding:1rem clamp(1.2rem,5vw,4rem);border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:2}nav ul{display:flex;gap:1rem 1.4rem;flex-wrap:wrap;list-style:none;margin:0;padding:0}nav a{font-weight:650;text-decoration:none}
    main{padding:0 clamp(1.2rem,5vw,4rem) 4rem}section{scroll-margin-top:5rem;margin:3.2rem 0}h2{font-size:1.75rem;line-height:1.2;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:.55rem}h3{color:var(--navy)}p,li{max-width:76ch}.question{font-size:1.28rem;font-weight:650;color:var(--navy)}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem;margin:1.4rem 0}.card{border:1px solid var(--line);border-radius:.55rem;padding:1.1rem;background:var(--soft)}.value{display:block;font-size:1.65rem;font-weight:750;color:var(--navy)}.label{font-size:.9rem;color:var(--muted)}
    .answer{border-left:5px solid var(--teal);background:#eaf6f5;padding:1.1rem 1.3rem}.caution{border-left:5px solid #bd7a00;background:var(--warn-bg);padding:1rem 1.2rem}.small{font-size:.91rem;color:var(--muted)}
    .table-wrap{overflow:auto;margin:1.3rem 0}table{width:100%;border-collapse:collapse;font-size:.92rem}caption{text-align:left;font-weight:700;color:var(--navy);margin-bottom:.55rem}th,td{padding:.65rem .7rem;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}th:first-child,td:first-child{text-align:left}thead th{background:var(--navy);color:#fff;white-space:nowrap}tbody th{color:var(--navy)}tbody tr:nth-child(even){background:#f7f9fa}
    figure{margin:1.5rem 0;border:1px solid var(--line);padding:1rem;border-radius:.5rem}figure img{width:100%;height:auto;display:block}figcaption{font-size:.92rem;color:var(--muted);margin-top:.7rem}
    label{font-weight:700;display:block;margin:.8rem 0 .35rem}select{font:inherit;min-height:44px;max-width:100%;padding:.55rem .7rem;border:2px solid var(--blue);border-radius:.35rem;background:#fff;color:var(--ink)}.region-panel{border:1px solid var(--line);border-radius:.5rem;padding:1rem 1.2rem;margin-top:1rem}
    details{border:1px solid var(--line);border-radius:.45rem;margin:.8rem 0;padding:.8rem 1rem}summary{font-weight:700;color:var(--navy);cursor:pointer}.status{font-weight:700;white-space:nowrap}.closed{color:var(--ok)}.scoped,.limitation{color:var(--warn)}code{background:var(--soft);padding:.1rem .3rem;border-radius:.2rem}.decision-list li{margin:.75rem 0}.footer{padding:1.5rem clamp(1.2rem,5vw,4rem);background:var(--navy);color:#fff}.footer p{color:#fff}
    @media(max-width:650px){nav{position:static}.hero{padding-top:2.2rem}th,td{padding:.55rem;font-size:.84rem}}
    @media print{body{background:#fff;font-size:10.5pt}.page{box-shadow:none;max-width:none}nav,.skip,.region-picker{display:none}.hero{padding:1.5rem;background:#fff;color:#000;border-bottom:3px solid #17324d}.hero *{color:#000}.region-panel[hidden]{display:block}.region-panel{break-inside:avoid}section{margin:1.5rem 0}details{display:block}details>summary{display:none}.table-wrap{overflow:visible}a{color:#000;text-decoration:none}}
  </style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<div class="page">
<header class="hero">
  <p class="eyebrow">HAILIE · Evidence report</p>
  <h1>England social housing waiting-list forecast</h1>
  <p class="lead">A decision-focused forecast for 2026–2028, a cautious extension to 2030, and the full evidence behind the data, model selection and uncertainty.</p>
  <p><a href="HAILIE_dashboard.html">Open the interactive forecast dashboard</a></p>
  <p class="meta">Source: MHCLG Live Table 600 · Observations: 1987–2025 · Build generated __GENERATED_DATE__</p>
</header>
<nav aria-label="Report sections"><ul><li><a href="#answer">Answer</a></li><li><a href="#regions">Regions</a></li><li><a href="#data">Data</a></li><li><a href="#models">Models</a></li><li><a href="#limitations">Limitations</a></li><li><a href="#reproduce">Reproduce</a></li></ul></nav>
<main id="main">
<section id="answer">
  <h2>1. Executive answer</h2>
  <p class="question">What is the likely direction of social housing waiting lists in England and its regions over the next three to five years, and how uncertain is that outlook?</p>
  <div class="answer"><strong>The evidence does not identify a robust national increase or decrease over the next three years.</strong> The damped-Holt model selected on the full 1987–2025 history gives a central estimate of __FORECAST_2028__ in 2028 (__CHANGE_2028__ from __LATEST__ in 2025), but naive performs better in both later-history sensitivity windows, especially 2005–2025. The 2028 80% empirical interval is __PI80_2028__, so materially lower and higher outcomes remain plausible.</div>
  <div class="cards"><div class="card"><span class="value">__LATEST__</span><span class="label">Observed in 2025</span></div><div class="card"><span class="value">__FORECAST_2028__</span><span class="label">Full-history central estimate for 2028</span></div><div class="card"><span class="value">__CHANGE_2028__</span><span class="label">Full-history estimate, 2025–2028</span></div><div class="card"><span class="value">Damped Holt</span><span class="label">Selected on the full history</span></div></div>
  __NATIONAL_TABLE__
  <p class="caution"><strong>95% diagnostic-range warning:</strong> the dashboard and public briefing show only the 80% empirical range. The 95% figures are retained in this technical report for transparency, but the three-year backtest has only 27 errors. Each 95% tail is therefore interpolated from the first and second most extreme observations, including periods associated with choice-based lettings around 2003 and qualification changes following the Localism Act 2011. These bounds are diagnostic historical ranges, not stable 95% probability limits for the next three years.</p>
  <p class="caution"><strong>Interpretation:</strong> the point forecast is a central estimate, not a target or guarantee. Historical forecasting errors increase with horizon. Administrative changes, policy and future economic conditions may create uncertainty beyond either empirical range.</p>
  <figure><img src="data:image/png;base64,__NATIONAL_TREND_IMAGE__" alt="Line chart of England households on local-authority housing registers from 1987 to 2025: the series falls through the 1990s, rises to a peak around 2012, falls again, and increases after 2020."><figcaption><strong>Historical context.</strong> England’s series is cyclical rather than a stable upward trend: it fell through the 1990s, rose to a 2012 peak, fell again, and has increased since 2020. This is why extrapolating a straight trend performed poorly.</figcaption></figure>
</section>
<section id="regions">
  <h2>2. Regional outlook</h2>
  <p><strong>The regional backtests do not support a strong directional call.</strong> Six of nine regions use a naive model that carries the 2025 observation forward, so their repeated 2028 central estimates are properties of the selected models rather than evidence that waiting lists will remain unchanged. Every 2028 central estimate is therefore shown with its selected model and 80% range. The regions were modelled independently and are not forced to sum to the separately modelled England forecast.</p>
  __REGIONAL_COMPARISON__
  <div class="region-picker"><label for="region-select">Inspect one region</label><select id="region-select"><option value="">Choose a region</option>__REGION_OPTIONS__</select></div>
  <div id="region-details" aria-live="polite">__REGION_PANELS__</div>
  <p class="small"><strong>Known regional comparability breaks:</strong> Telford &amp; Wrekin stopped operating a housing register from 31 March 2021, affecting West Midlands and England totals; Epping Forest changed its treatment of transfer applicants from 2022–23, affecting the East of England series. These breaks are disclosed here without re-modelling.</p>
  <figure><img src="data:image/png;base64,__REGIONAL_TREND_IMAGE__" alt="Small-multiple line charts for nine English regions from 1987 to 2025, showing different levels and volatility while sharing broad national turning points."><figcaption><strong>Historical regional context.</strong> All regions share the broad national cycle, but their levels and volatility differ. The region selector and comparison table show each region’s selected model and 80% range so that naive carry-forwards are not presented as evidence of stability.</figcaption></figure>
</section>
<section id="data"><h2>3. Data provenance and quality</h2>
  <p>The source is MHCLG Live Table 600, retained in the repository. The reproducible preparation pipeline creates a long-format dataset covering England and nine regions for 1987–2025. The nine regional totals reconcile exactly to England in every one of the 39 years.</p>
  <ul><li>390 regional records and 14,664 local-authority records were checked.</li><li>MHCLG supplied 45 replacement values; 1,421 <code>[z]</code> markers, 2 <code>[x]</code> markers and 8 genuine zeroes were audited.</li><li>This project introduced no new numerical imputations.</li><li>Six London periods were independently checked against LG Inform; all six matched after year-label alignment.</li></ul>
  <p class="caution"><strong>What the measure means:</strong> Table 600 counts households on local-authority housing registers. Separate housing-association waiting lists are not included; applicants can appear on more than one authority register, and the publisher says periodic reviews and duplicate listings mean the total is likely to overstate households still requiring social housing at any one time. These registers are therefore not a complete measure of housing need. Changes can reflect register administration as well as changes in demand.</p>
  <p class="small"><strong>Reference dates:</strong> the source reference date is 1 April up to 2018 and 31 March from 2019 onward. Data were retrieved 7 August 2026.</p>
</section>
<section id="models"><h2>4. Forecasting choices and evidence</h2>
  <p>Seven transparent candidates were evaluated: naive, drift, linear trend, simple exponential smoothing, Holt linear trend, damped Holt trend and a deliberately restricted ARIMA search. Annual data have no within-year seasonal frequency, so seasonal models were not used.</p>
  <p><strong>Evaluation:</strong> expanding-window rolling-origin backtesting. The first origin is 1996 after ten observations. There are 29 one-year, 28 two-year, 27 three-year and 25 five-year forecast origins. At each origin the model sees only data available at that time.</p>
  <p><strong>Selection:</strong> MAE is primary because it reports typical error directly in households. RMSE, MAPE and bias are supporting diagnostics. The primary model minimises mean Y1–Y3 MAE; the extension uses Y5 MAE, with the simpler model preferred where performance is effectively tied. Selection differences are descriptive only: overlapping origins and no formal Diebold–Mariano test mean near-ties should not be treated as statistically significant.</p>
  __NATIONAL_METRICS_TABLE__
  __SELECTION_TABLE__
  <h3>Why the three- and five-year forecasts differ</h3><p>Damped Holt is most consistent across Y1–Y3, while naive is hardest to beat at Y5. This is a horizon-specific decision rather than a contradiction:</p>
  __OVERLAP_TABLE__
  <p>The overlapping difference remains small relative to forecast uncertainty. The five-year extension is therefore retained as a cautious planning benchmark:</p>
  __EXTENSION_TABLE__
  <h3>History-window sensitivity</h3><p>The comparison was repeated after excluding the earliest observations. The primary winner changes from damped Holt on the pre-specified full history to naive from 1998 and ARIMA from 2005; the five-year naive winner is stable. __SENSITIVITY_SUMMARY__ MAE levels are not directly comparable across windows because the later windows contain fewer and different forecast origins. The changing near-term winner means the evidence does not support a robust directional national claim, while the preserved full-history model still supplies the published central estimate.</p>
  __SENSITIVITY_TABLE__
  <details><summary>Method decisions</summary><ol class="decision-list"><li><strong>Use published England and regional aggregates:</strong> these provide complete, validated annual series.</li><li><strong>Use annual univariate models:</strong> these match the frequency and length of the available series.</li><li><strong>Use rolling-origin evaluation:</strong> a single holdout would provide too little evidence from 39 annual observations.</li><li><strong>Use MAE as primary:</strong> it is understandable in household units and less dominated by a few large errors than RMSE.</li><li><strong>Use empirical ranges:</strong> they reflect errors actually observed out of sample. Public surfaces use the more stable 80% range; 95% figures are retained here as small-sample diagnostics.</li></ol></details>
</section>
<section id="limitations"><h2>5. Limitations</h2><ul><li>Counts reflect register rules and administrative cleanses as well as housing need.</li><li>Applicants may appear on more than one authority register, and the publisher says the total likely overstates households still requiring social housing at any one time.</li><li>Separate housing-association waiting lists are not included.</li><li>The forecasts are statistical projections and should not be interpreted as causal estimates.</li><li>Annual sample sizes are small; longer-horizon rolling origins overlap and are not independent trials.</li><li>The 95% diagnostic ranges are highly sensitive to a few extreme historical errors and are not stable 95% probability limits.</li><li>Empirical ranges describe historical model error, not every uncertainty in source reporting or future structural change.</li><li>The history-window sensitivity check changes the near-term winning model, reinforcing the need for cautious interpretation.</li><li>Regional forecasts are independently modelled and are not constrained to reconcile to the national point forecast.</li><li>Regional five-year extension points have no calculated uncertainty bands and should not be used as standalone planning forecasts.</li></ul></section>
<section id="reproduce"><h2>6. Reproducing the analysis</h2><p>Run from the repository root using Python 3.9 or later:</p><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python scripts/generate_final_outputs.py
# Add --check-regression only when comparing a rebuild with the published run.
python3 scripts/build_report.py
python3 scripts/validate_final_submission.py</code></pre><p>The authoritative machine-readable outputs are under <code>outputs/final/</code>. Earlier exploratory scripts, results and reports are retained only under <code>archive/forecasting_phase/</code>.</p></section>
</main>
<footer class="footer"><p>HAILIE social housing waiting-list forecast · evidence report · build generated __GENERATED_DATE__</p></footer>
</div>
<script>
  const regionCodes = __REGION_DATA_JSON__;
  const select = document.getElementById('region-select');
  select.addEventListener('change', () => {
    regionCodes.forEach(code => { document.getElementById('region-' + code).hidden = code !== select.value; });
  });
</script>
</body></html>'''


if __name__ == "__main__":
    main()
