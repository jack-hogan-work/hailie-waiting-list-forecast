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
        direction = "increase" if change_pct > 0.05 else "decrease" if change_pct < -0.05 else "broadly flat"
        change_phrase = (
            f"an increase of {fmt_pct(change_pct)}"
            if direction == "increase"
            else f"a decrease of {fmt_pct(change_pct)}"
            if direction == "decrease"
            else f"broadly unchanged ({fmt_pct(change_pct)})"
        )
        selection = selection_by_code[code]
        options.append(f'<option value="{html.escape(code)}">{html.escape(name)}</option>')
        comparison_rows.append(
            [
                html.escape(name),
                fmt(latest),
                fmt(point_2028),
                f"{html.escape(direction)} ({fmt_pct(change_pct)})",
                html.escape(selection["primary_model_label"]),
            ]
        )
        forecast_table = table(
            ["Year", "Point forecast", "80% interval", "95% interval"],
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
              {fmt(point_2028)}, {html.escape(change_phrase)}. The selected short-horizon
              model is {html.escape(selection["primary_model_label"])}; the separately selected five-year
              extension model is {html.escape(selection["extension_model_label"])}.</p>
              {forecast_table}
            </section>'''
        )

    comparison_rows.sort(key=lambda row: float(row[2].replace(",", "")), reverse=True)
    comparison_table = table(
        ["Region", "2025 observed", "2028 forecast", "Direction", "Selected model"],
        comparison_rows,
        "Regional 2025 observations and final 2028 short-horizon forecasts",
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
        ["Year", "Point forecast", "80% interval", "95% interval", "Selected model"],
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
        ["Year", "Point forecast", "80% interval", "95% interval"],
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

    model_order = ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]

    def sensitivity_selection(records: list[dict[str, str]]) -> tuple[str, float, str, float, int, int]:
        metric = {(row["model"], int(row["horizon_years"])): float(row["mae_households"]) for row in records}
        names = {row["model"]: row["model_label"] for row in records}
        primary_scores = {model: sum(metric[(model, horizon)] for horizon in [1, 2, 3]) / 3 for model in model_order}
        extension_scores = {model: metric[(model, 5)] for model in model_order}
        primary = min(model_order, key=lambda model: (primary_scores[model], model_order.index(model)))
        extension = min(model_order, key=lambda model: (extension_scores[model], model_order.index(model)))
        first = next(row for row in records if row["model"] == primary and row["horizon_years"] == "1")
        fifth = next(row for row in records if row["model"] == extension and row["horizon_years"] == "5")
        return names[primary], primary_scores[primary], names[extension], extension_scores[extension], int(first["forecast_origins"]), int(fifth["forecast_origins"])

    sensitivity_groups = {
        "1987 (full, pre-specified)": national_metrics,
        "1998 (first trough onward)": [row for row in history_sensitivity if row["history_start_year"] == "1998"],
        "2005 (stronger-validation era)": [row for row in history_sensitivity if row["history_start_year"] == "2005"],
    }
    sensitivity_table = table(
        ["History window", "Y1–Y3 winner", "Mean MAE", "Y5 winner", "Y5 MAE", "Y1 / Y5 origins"],
        [
            [html.escape(label), html.escape(result[0]), fmt(result[1]), html.escape(result[2]), fmt(result[3]), f"{result[4]} / {result[5]}"]
            for label, result in ((label, sensitivity_selection(records)) for label, records in sensitivity_groups.items())
        ],
        "Sensitivity of national model selection to the amount of history used",
        row_headers=True,
    )

    jose_table = table(
        ["José’s question or concern", "Action and evidence", "Closure"],
        [
            ["Provenance and processing integrity", "Raw Table 600 is retained; scripted extraction and validation reconcile all nine regions to England for all 39 years.", '<span class="status closed">Closed</span>'],
            ["Meaning of [x], [z], blanks, zeroes and imputations", "Publisher markers were audited: 45 MHCLG replacements, 1,421 [z], 2 [x] and 8 genuine zeroes. No new values were imputed by this project.", '<span class="status closed">Closed</span>'],
            ["Independent check", "Six London periods were checked against LG Inform and all six matched after documenting year-label alignment.", '<span class="status closed">Closed</span>'],
            ["Objective and forecast horizon", "The target is the annual England household count, with a primary three-year forecast and a separately selected five-year extension.", '<span class="status closed">Closed</span>'],
            ["Out-of-sample evaluation and leakage", "Expanding-window rolling-origin backtests use only information available at each origin; horizons 1, 2, 3 and 5 are assessed separately.", '<span class="status closed">Closed</span>'],
            ["How the model was chosen", "Seven models were compared. MAE is the primary metric; RMSE, MAPE and bias are diagnostics. Parsimony resolves materially tied performance.", '<span class="status closed">Closed</span>'],
            ["Different three- and five-year models", "The overlapping forecasts are compared directly above. Their 2028 difference is about 19,374 households (1.4%), small relative to the empirical intervals.", '<span class="status closed">Closed</span>'],
            ["Prediction uncertainty", "Every primary forecast includes empirical 80% and 95% intervals derived from historical out-of-sample errors; source-data uncertainty is discussed separately.", '<span class="status closed">Closed</span>'],
            ["Table 602 and other predictors", "They were not merged into the final model: flow and contextual measures require timing, alignment and leakage tests before use, and no out-of-sample gain was demonstrated.", '<span class="status scoped">Scoped out</span>'],
            ["Changing local-authority geography", "Local-authority forecasts were excluded because a continuous current-boundary series was not validated. National and nine-region series are used instead.", '<span class="status scoped">Scoped out</span>'],
            ["Sensitivity to history and policy breaks", "The model comparison was repeated from 1998 and 2005. The near-term winner changes, while naive remains the five-year winner. This supports cautious interpretation; a causal policy-break analysis was not attempted.", '<span class="status closed">Tested</span>'],
        ],
        "Supervisor concern-to-evidence closure matrix",
        row_headers=True,
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
        "__NATIONAL_METRICS_TABLE__": national_metrics_table,
        "__SENSITIVITY_TABLE__": sensitivity_table,
        "__JOSE_TABLE__": jose_table,
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
    a{color:#005a85;text-decoration-thickness:.1em;text-underline-offset:.15em} a:focus-visible,button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #f2a900;outline-offset:3px}
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
  <p class="eyebrow">HAILIE · Final analytical submission</p>
  <h1>England social housing waiting-list forecast</h1>
  <p class="lead">A decision-focused forecast for 2026–2028, a cautious extension to 2030, and the full evidence behind the data, model selection and uncertainty.</p>
  <p class="meta">Source: MHCLG Live Table 600 · Observations: 1987–2025 · Final report generated __GENERATED_DATE__</p>
</header>
<nav aria-label="Report sections"><ul><li><a href="#answer">Answer</a></li><li><a href="#regions">Regions</a></li><li><a href="#data">Data</a></li><li><a href="#models">Models</a></li><li><a href="#jose">José closure</a></li><li><a href="#reproduce">Reproduce</a></li></ul></nav>
<main id="main">
<section id="answer">
  <h2>1. Executive answer</h2>
  <p class="question">What is the likely direction of social housing waiting lists in England and its regions over the next three to five years, and how uncertain is that outlook?</p>
  <div class="answer"><strong>The final national model suggests a modest near-term increase, not a sharp change.</strong> England rises from __LATEST__ observed households in 2025 to __FORECAST_2028__ in 2028 (__CHANGE_2028__). The 2028 80% empirical interval is __PI80_2028__, so materially lower and higher outcomes remain plausible.</div>
  <div class="cards"><div class="card"><span class="value">__LATEST__</span><span class="label">Observed in 2025</span></div><div class="card"><span class="value">__FORECAST_2028__</span><span class="label">Primary forecast for 2028</span></div><div class="card"><span class="value">__CHANGE_2028__</span><span class="label">Forecast change, 2025–2028</span></div><div class="card"><span class="value">Damped Holt</span><span class="label">Selected using mean Y1–Y3 MAE</span></div></div>
  __NATIONAL_TABLE__
  <p class="caution"><strong>Interpretation:</strong> the point forecast is a central estimate, not a target or guarantee. The widening intervals are a result: historical forecasting errors increase with horizon. Administrative changes, policy and future economic conditions may create uncertainty beyond these model-error intervals.</p>
  <figure><img src="data:image/png;base64,__NATIONAL_TREND_IMAGE__" alt=""><figcaption><strong>Historical context.</strong> England’s series is cyclical rather than a stable upward trend: it fell through the 1990s, rose to a 2012 peak, fell again, and has increased since 2020. This is why extrapolating a straight trend performed poorly.</figcaption></figure>
</section>
<section id="regions">
  <h2>2. Regional outlook</h2>
  <p>The nine regions were modelled independently after the national pipeline was finalised. Different models can therefore be selected where regional backtests provide different evidence. Regional forecasts are not forced to sum to the separately modelled England forecast.</p>
  __REGIONAL_COMPARISON__
  <div class="region-picker"><label for="region-select">Inspect one region</label><select id="region-select"><option value="">Choose a region</option>__REGION_OPTIONS__</select></div>
  <div id="region-details" aria-live="polite">__REGION_PANELS__</div>
  <figure><img src="data:image/png;base64,__REGIONAL_TREND_IMAGE__" alt=""><figcaption><strong>Historical regional context.</strong> All regions share the broad national cycle, but their levels and volatility differ. The final region selector and table therefore show each region’s own selected model and uncertainty rather than applying one national model everywhere.</figcaption></figure>
</section>
<section id="data"><h2>3. Data provenance and quality</h2>
  <p>The source is MHCLG Live Table 600, retained in the repository. The reproducible preparation pipeline creates a long-format dataset covering England and nine regions for 1987–2025. The nine regional totals reconcile exactly to England in every one of the 39 years.</p>
  <ul><li>390 regional records and 14,664 local-authority records were checked.</li><li>MHCLG supplied 45 replacement values; 1,421 <code>[z]</code> markers, 2 <code>[x]</code> markers and 8 genuine zeroes were audited.</li><li>This project introduced no new numerical imputations.</li><li>Six London periods were independently checked against LG Inform; all six matched after year-label alignment.</li></ul>
  <p class="caution"><strong>What the measure means:</strong> Table 600 counts households on local-authority housing registers. These registers are the available administrative measure of social housing waiting-list demand, but they do not include every separate housing-association waiting list and are not a complete measure of housing need. Changes can reflect register administration as well as changes in demand.</p>
</section>
<section id="models"><h2>4. Forecasting choices and evidence</h2>
  <p>Seven transparent candidates were evaluated: naive, drift, linear trend, simple exponential smoothing, Holt linear trend, damped Holt trend and a deliberately restricted ARIMA search. Annual data have no within-year seasonal frequency, so seasonal models were not used.</p>
  <p><strong>Evaluation:</strong> expanding-window rolling-origin backtesting. The first origin is 1996 after ten observations. There are 29 one-year, 28 two-year, 27 three-year and 25 five-year forecast origins. At each origin the model sees only data available at that time.</p>
  <p><strong>Selection:</strong> MAE is primary because it reports typical error directly in households. RMSE, MAPE and bias are supporting diagnostics. The primary model minimises mean Y1–Y3 MAE; the extension uses Y5 MAE, with the simpler model preferred where performance is effectively tied.</p>
  __NATIONAL_METRICS_TABLE__
  __SELECTION_TABLE__
  <h3>Why the three- and five-year forecasts differ</h3><p>Damped Holt is most consistent across Y1–Y3, while naive is hardest to beat at Y5. This is a horizon-specific decision rather than a contradiction:</p>
  __OVERLAP_TABLE__
  <p>The overlapping difference remains small relative to forecast uncertainty. The five-year extension is therefore retained as a cautious planning benchmark:</p>
  __EXTENSION_TABLE__
  <h3>History-window sensitivity</h3><p>The comparison was repeated after excluding the earliest observations. The primary winner changes from damped Holt on the pre-specified full history to naive from 1998 and ARIMA from 2005; the five-year naive winner is stable. MAE levels are not directly comparable because the later windows contain fewer and different forecast origins. The changing near-term winner reinforces the decision to present a modest direction signal with wide uncertainty rather than treat one model name as permanent.</p>
  __SENSITIVITY_TABLE__
  <details><summary>Decision record</summary><ol class="decision-list"><li><strong>Use published England and complete regional aggregates:</strong> chosen for continuity and validation; local-authority forecasts were excluded because changing boundaries were not reconciled into continuous current-geography series.</li><li><strong>Use annual univariate benchmarks:</strong> they match the frequency and sample size. Table 602, deprivation, unemployment and other predictors were not added without a leakage-safe alignment and demonstrated out-of-sample gain.</li><li><strong>Use rolling-origin evaluation:</strong> a single holdout would provide too little evidence from 39 annual observations.</li><li><strong>Use MAE as primary:</strong> it is understandable in household units and less dominated by a few large errors than RMSE.</li><li><strong>Use empirical intervals:</strong> they reflect errors actually observed out of sample and avoid overstating parametric certainty.</li><li><strong>Keep the report executive-first:</strong> headline direction and uncertainty appear before technical detail, while the evidence remains in the same auditable artifact.</li></ol></details>
</section>
<section id="limitations"><h2>5. Limitations</h2><ul><li>Counts reflect register rules and administrative cleanses as well as housing need.</li><li>The models contain no policy, supply, labour-market or macroeconomic predictors.</li><li>Annual sample sizes are small; longer-horizon rolling origins overlap and are not independent trials.</li><li>Prediction intervals describe historical model error, not every uncertainty in source reporting or future structural change.</li><li>The history-window sensitivity check changes the near-term winning model. It is a robustness diagnostic, not a formal causal analysis of individual policy breaks.</li><li>Regional forecasts are independently modelled and are not constrained to reconcile to the national point forecast.</li></ul></section>
<section id="jose"><h2>6. José’s concerns: closure and remaining limits</h2><p>This table distinguishes completed evidence from deliberate exclusions and unresolved limitations. “Scoped out” does not mean the issue is unimportant; it records why it was not represented as completed work.</p>__JOSE_TABLE__</section>
<section id="design"><h2>7. Report design and review approach</h2><p>The report applies Tom Stephenson’s advice by starting with one real user question, keeping the first screen focused, supporting decision-maker, regional and technical-review scenarios, and moving dense evidence below the answer. It uses semantic headings, keyboard-operable controls, visible focus, text labels that do not depend on colour, scoped tables, text summaries for charts, responsive layout and print styling.</p><p>External testing by Tom or Myles is not claimed as completed. Their review can be recorded after this first complete version is shared; the analytical submission does not depend on unperformed testing.</p></section>
<section id="reproduce"><h2>8. Reproducing the submission</h2><p>Run from the repository root using Python 3.9 or later:</p><pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python scripts/generate_final_outputs.py
python3 scripts/build_report.py
python3 scripts/validate_final_submission.py</code></pre><p>The authoritative machine-readable outputs are under <code>outputs/final/</code>. Earlier exploratory scripts, results and reports are retained only under <code>archive/forecasting_phase/</code>.</p></section>
</main>
<footer class="footer"><p>HAILIE social housing waiting-list forecast · final analytical submission · generated __GENERATED_DATE__</p></footer>
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
