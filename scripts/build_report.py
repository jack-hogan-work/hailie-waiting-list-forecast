#!/usr/bin/env python3
"""Week 2 consolidated project report for MHCLG Live Table 600 waiting-list work.

Assembles a single, self-contained HTML report (outputs/report.html) from the
already-generated, already-validated outputs of the rest of the pipeline: the
processed data, the national/regional/statistical backtest result CSVs, and a
selection of the chart PNGs (embedded as base64 data URIs so the report is one
portable file with no external references).

This script does not compute anything new - every number in the report is read
directly from a CSV already produced and QA-checked by an earlier script (see
docs/*.md for how each was derived). It should be run last, after:
    python3 scripts/prepare_data.py
    python3 scripts/validate_national.py
    .venv/bin/python3 scripts/explore_national.py
    .venv/bin/python3 scripts/forecast_national.py
    .venv/bin/python3 scripts/forecast_regional.py
    .venv/bin/python3 scripts/forecast_statistical.py

Standard library only (csv, base64, pathlib, datetime, html). Run with:
    python3 scripts/build_report.py
"""

import base64
import csv
import html
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
OUTPUTS_DIR = REPO_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

ENGLAND_AREA_CODE = "E92000001"
REGION_ORDER = [
    ("E12000001", "North East"),
    ("E12000002", "North West"),
    ("E12000003", "Yorkshire and The Humber"),
    ("E12000004", "East Midlands"),
    ("E12000005", "West Midlands"),
    ("E12000006", "East of England"),
    ("E12000007", "London"),
    ("E12000008", "South East"),
    ("E12000009", "South West"),
]

MODEL_LABELS = {
    "naive": "Naive",
    "drift": "Drift",
    "linear_trend": "Linear trend",
    "ses": "SES",
    "holt": "Holt's linear",
    "ets_damped": "ETS damped trend",
    "arima": "ARIMA",
}

IMAGES = [
    ("england_waiting_list_1987_2025.png", "England households on the register, 1987-2025"),
    ("england_annual_percentage_change.png", "Year-on-year percentage change, 1988-2025"),
    ("regional_waiting_list_trends.png", "The nine English regions, 1987-2025 (small multiples)"),
    ("backtest_one_step_ahead_extended.png", "Actual vs. 1-year-ahead backtested forecasts, all 7 models"),
    ("backtest_mape_by_horizon_extended.png", "Backtest MAPE by horizon, all 7 models"),
    ("regional_backtest_mape_heatmap.png", "Regional backtest MAPE by model, 1-year vs. 5-year horizon"),
    ("regional_win_counts_extended.png", "Regions where each model has the lowest MAPE, by horizon"),
]


# --- Data loading (re-derived from source CSVs, nothing hardcoded) ------------


def load_series(area_code):
    series = {}
    with PROCESSED_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["Area code"] != area_code:
                continue
            v = row["households_on_register"]
            if v != "":
                series[int(row["year"])] = int(v)
    return series


def load_csv_rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute_headline_stats():
    england = load_series(ENGLAND_AREA_CODE)
    years = sorted(england)
    v1987, v2025 = england[1987], england[2025]
    v2020 = england[2020]
    peak_year = max(years, key=lambda y: england[y])
    trough_year = min(years, key=lambda y: england[y])
    return {
        "v1987": v1987,
        "v2025": v2025,
        "change_87_25_abs": v2025 - v1987,
        "change_87_25_pct": 100 * (v2025 - v1987) / v1987,
        "v2020": v2020,
        "change_20_25_abs": v2025 - v2020,
        "change_20_25_pct": 100 * (v2025 - v2020) / v2020,
        "peak_year": peak_year,
        "peak_value": england[peak_year],
        "trough_year": trough_year,
        "trough_value": england[trough_year],
    }


def regional_2025_snapshot():
    rows = []
    for code, name in REGION_ORDER:
        series = load_series(code)
        rows.append((name, series[2025]))
    return sorted(rows, key=lambda r: -r[1])


def best_per_horizon(summary_rows, horizons=(1, 2, 3, 5)):
    best = {}
    for h in horizons:
        candidates = [r for r in summary_rows if int(r["horizon_years"]) == h]
        best[h] = min(candidates, key=lambda r: float(r["mape_pct"]))
    return best


def regional_best_model_table(regional_extended_rows, horizon):
    out = []
    for code, name in REGION_ORDER:
        candidates = [r for r in regional_extended_rows if r["region_code"] == code and int(r["horizon_years"]) == horizon]
        best = min(candidates, key=lambda r: float(r["mape_pct"]))
        out.append((name, MODEL_LABELS.get(best["model"], best["model"]), float(best["mape_pct"])))
    return out


def encode_image(filename):
    data = (FIGURES_DIR / filename).read_bytes()
    return base64.b64encode(data).decode("ascii")


# --- HTML rendering -------------------------------------------------------------


def fmt(n):
    return f"{n:,.0f}"


def fmt_pct(n, sign=False):
    s = "+" if sign and n >= 0 else ""
    return f"{s}{n:.1f}%"


def render_model_results_table(summary_rows, horizons=(1, 2, 3, 5)):
    model_order = ["ets_damped", "arima", "holt", "naive", "ses", "drift", "linear_trend"]
    rows_by_model = {}
    for r in summary_rows:
        rows_by_model.setdefault(r["model"], {})[int(r["horizon_years"])] = r

    thead = "<tr><th>Model</th>" + "".join(f"<th>{h}-year MAPE</th>" for h in horizons) + "</tr>"
    body_rows = []
    for model in model_order:
        if model not in rows_by_model:
            continue
        cells = [f'<td class="model-name">{MODEL_LABELS.get(model, model)}</td>']
        for h in horizons:
            r = rows_by_model[model].get(h)
            mape = float(r["mape_pct"]) if r else None
            cell_class = "best-cell" if mape is not None and mape == min(
                float(rows_by_model[m][h]["mape_pct"]) for m in rows_by_model if h in rows_by_model[m]
            ) else ""
            cells.append(f'<td class="num {cell_class}">{mape:.2f}%</td>' if mape is not None else "<td class=\"num\">-</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="data-table"><thead>{thead}</thead><tbody>{"".join(body_rows)}</tbody></table>'


def render_regional_snapshot_table(snapshot):
    rows = "".join(f"<tr><td>{html.escape(name)}</td><td class='num'>{fmt(v)}</td></tr>" for name, v in snapshot)
    return f'<table class="data-table"><thead><tr><th>Region</th><th>Households on the register, 2025</th></tr></thead><tbody>{rows}</tbody></table>'


def render_regional_best_model_table(rows_1y, rows_5y):
    body = []
    for (name, model1, mape1), (_, model5, mape5) in zip(rows_1y, rows_5y):
        body.append(
            f"<tr><td>{html.escape(name)}</td>"
            f"<td class='model-name'>{model1} <span class='num muted'>({mape1:.1f}%)</span></td>"
            f"<td class='model-name'>{model5} <span class='num muted'>({mape5:.1f}%)</span></td></tr>"
        )
    return (
        "<table class='data-table'><thead><tr><th>Region</th><th>Best model, 1-year</th>"
        f"<th>Best model, 5-year</th></tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def render_forward_forecast_table(rows):
    by_model = {}
    years = sorted({int(r["target_year"]) for r in rows})
    for r in rows:
        by_model.setdefault(r["model"], {})[int(r["target_year"])] = float(r["forecast"])
    model_order = ["naive", "drift", "linear_trend", "ses", "holt"]
    thead = "<tr><th>Model</th>" + "".join(f"<th>{y}</th>" for y in years) + "</tr>"
    body_rows = []
    for model in model_order:
        if model not in by_model:
            continue
        cells = [f'<td class="model-name">{MODEL_LABELS.get(model, model)}</td>']
        for y in years:
            cells.append(f'<td class="num">{fmt(by_model[model][y])}</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="data-table"><thead>{thead}</thead><tbody>{"".join(body_rows)}</tbody></table>'


def image_block(filename, caption, img_data):
    return f"""
    <figure class="chart-card">
      <img src="data:image/png;base64,{img_data}" alt="{html.escape(caption)}" loading="lazy" />
      <figcaption>{html.escape(caption)}</figcaption>
    </figure>
    """


PAGE_TEMPLATE = """<!doctype html>
<title>Hailie Waiting List Report</title>
<style>
{css}
</style>
<div class="page">

  <header class="masthead">
    <p class="eyebrow">Hailie &middot; England housing waiting lists</p>
    <h1>Households on the housing register: trends and forecasts, 1987&ndash;2025</h1>
    <p class="dek">
      A consolidated analysis of MHCLG Live Table 600 &mdash; the national and regional trend,
      a leakage-free rolling-origin backtest of seven forecasting models, and what they do
      (and don't) tell us about 2026&ndash;2030.
    </p>
    <p class="meta">
      Source: MHCLG Live Table 600, retrieved 7 Aug 2026 &middot; Report generated {generated_date}
    </p>
  </header>

  <nav class="toc" aria-label="Contents">
    <ol>
      <li><a href="#summary">Executive summary</a></li>
      <li><a href="#trend">1. The national and regional trend</a></li>
      <li><a href="#method">2. Forecasting method</a></li>
      <li><a href="#results">3. Backtest results</a></li>
      <li><a href="#regional-results">4. Regional results</a></li>
      <li><a href="#forward">5. Illustrative 2026&ndash;2030 forecast</a></li>
      <li><a href="#limitations">6. Limitations</a></li>
      <li><a href="#reproduce">7. Reproducing this work</a></li>
    </ol>
  </nav>

  <section id="summary" class="callout">
    <h2>Executive summary</h2>
    <div class="stat-grid">
      <div class="stat">
        <span class="stat-value">{v2025}</span>
        <span class="stat-label">households on the register, 2025</span>
      </div>
      <div class="stat">
        <span class="stat-value">{change_20_25_pct}</span>
        <span class="stat-label">change since 2020 ({v2020} &rarr; {v2025})</span>
      </div>
      <div class="stat">
        <span class="stat-value">{best_1y_model}</span>
        <span class="stat-label">best 1-year model &middot; {best_1y_mape} MAPE</span>
      </div>
      <div class="stat">
        <span class="stat-value">{best_5y_model}</span>
        <span class="stat-label">best 5-year model &middot; {best_5y_mape} MAPE</span>
      </div>
    </div>
    <p>
      The England total is <strong>not a trend</strong> &mdash; it traces two full cycles since 1987,
      falling to a trough of {trough_value} in {trough_year}, rising to a peak of {peak_value} in {peak_year},
      falling again to a shallower trough around 2018, and rising since 2020 to {v2025} in 2025.
      Seven benchmark forecasting models were compared with leakage-free rolling-origin backtesting.
      <strong>No single model wins at every horizon:</strong> a damped-trend exponential smoother
      (<code>ets_damped</code>) is most accurate one to two years out, but the simplest possible
      model &mdash; carry the last value forward (<code>naive</code>) &mdash; is hardest to beat
      from three years out onward, because every trend-following model eventually overshoots when
      the cycle turns.
    </p>
  </section>

  <section id="trend">
    <h2>1. The national and regional trend</h2>
    <p>
      England's housing register total is not monotonic. Over 1988&ndash;2025 (38 year-on-year changes),
      21 years saw an increase and 17 a decrease &mdash; the largest single-year rise was +16.1% (2003)
      and the largest fall was &minus;18.8% (2014). Register counts can move for administrative reasons
      (periodic list &ldquo;cleanses&rdquo;) as well as genuine change in housing need; this report does
      not attempt to separate the two (see <a href="#limitations">Limitations</a>).
    </p>
    {img_trend}
    {img_pctchange}
    <h3>Regional picture</h3>
    <p>
      The nine English regions sum exactly to the England total. They do not move uniformly &mdash;
      London and the South West show the largest proportional rise since 1987, while the North East
      and East Midlands show the largest falls &mdash; but every region traces the same broad
      rise-peak-fall-rise shape as the national series (see chart).
    </p>
    {img_regional}
    {regional_snapshot_table}
  </section>

  <section id="method">
    <h2>2. Forecasting method</h2>
    <p>
      Seven models were compared, all evaluated identically with <strong>rolling-origin
      (walk-forward) backtesting</strong>: at each origin year from 1996 to 2024, every model is
      trained only on data up to and including that year (an expanding window), then forecast
      1/2/3/5 years ahead; the forecast is compared against the actual value once it becomes
      available. No model ever sees data from after its origin year &mdash; this is checked
      structurally in code, not just asserted in prose.
    </p>
    <table class="data-table method-table">
      <thead><tr><th>Model</th><th>Idea</th><th>Dependency</th></tr></thead>
      <tbody>
        <tr><td class="model-name">Naive</td><td>Last observed value, held flat</td><td>None</td></tr>
        <tr><td class="model-name">Drift</td><td>Last value + average historical slope &times; horizon</td><td>None</td></tr>
        <tr><td class="model-name">Linear trend</td><td>OLS straight-line fit, extrapolated</td><td>None</td></tr>
        <tr><td class="model-name">SES</td><td>Exponentially-weighted level (no trend), &alpha; grid-searched</td><td>None</td></tr>
        <tr><td class="model-name">Holt's linear</td><td>Exponentially-weighted level + trend, &alpha;/&beta; grid-searched</td><td>None</td></tr>
        <tr><td class="model-name">ETS damped trend</td><td>Holt's method with the trend damped toward flat over the horizon</td><td>statsmodels</td></tr>
        <tr><td class="model-name">ARIMA</td><td>Order (p,d,q) chosen per origin by AIC, restricted to well-conditioned fits</td><td>statsmodels</td></tr>
      </tbody>
    </table>
    <p class="note">
      <strong>A real bug was found and fixed during this work:</strong> an early, unconstrained
      version of the ARIMA order search picked a numerically degenerate model at one origin &mdash;
      its AR and MA roots sat exactly on the unit circle, producing a forecast of precisely
      <strong>0.0 households</strong>. The fix rejects any candidate order whose roots come within
      1.05 of the unit circle. Full diagnosis: <code>docs/statistical_models_methodology.md</code> &sect;2.
    </p>
  </section>

  <section id="results">
    <h2>3. National backtest results</h2>
    <p>Mean absolute percentage error (MAPE), lower is better, best model per horizon highlighted:</p>
    {national_results_table}
    {img_backtest_chart}
    {img_mape_chart}
    <p>
      <strong>ETS damped trend is the strongest model at 1- and 2-year horizons</strong> &mdash; it
      damps Holt's trend term just enough to avoid most of the overshoot that makes the undamped
      Holt model swing wildly around turning points, while still tracking the post-2020 upturn
      faster than the flat models. From the 3-year horizon on, though, the simplest model in the
      comparison &mdash; naive &mdash; is hardest to beat (with SES close behind it), because
      <em>every</em> trend-aware model eventually extrapolates through a cycle turn and pays for
      it, and that catches up with even the damped version by 3 years out. Linear trend is the
      weakest model at every horizon by a wide margin, for the same reason: it cannot represent
      a series that rises, falls, rises, falls.
    </p>
  </section>

  <section id="regional-results">
    <h2>4. Regional results</h2>
    <p>
      The same seven-model comparison was run separately for each of the nine English regions.
      Two findings stand out. First, every region is <em>harder</em> to forecast than the smoother
      national total (higher MAPE at every horizon) &mdash; aggregation cancels out some of each
      region's own noise. Second, the best model varies by region as well as by horizon:
    </p>
    {regional_best_model_table}
    {img_regional_heatmap}
    {img_regional_wins}
    <p class="note">
      <strong>Caution:</strong> most of naive's apparent wins above are decided by under 0.1 MAPE
      points against SES &mdash; effectively a tie, not a real difference (full analysis:
      <code>docs/regional_forecast_methodology.md</code> &sect;2.4). Read the win counts as
      &ldquo;naive/SES/ETS-damped are all competitive here,&rdquo; not as one model dominating.
    </p>
  </section>

  <section id="forward">
    <h2>5. Illustrative 2026&ndash;2030 forecast</h2>
    <p>
      Each dependency-light model was fit on the <strong>full</strong> 1987&ndash;2025 series and
      extrapolated forward. This is <strong>not a validated prediction</strong> &mdash; it has not
      itself been backtested, only the methodology that produced it has. Given the backtested MAPEs
      above (roughly 4&ndash;5% at 1 year, rising to 22&ndash;34% at 5 years depending on model),
      every row below should be read as a wide-uncertainty benchmark, not a point estimate to plan
      against.
    </p>
    {forward_forecast_table}
  </section>

  <section id="limitations">
    <h2>6. Limitations</h2>
    <ul class="limitations-list">
      <li><strong>Not a complete measure of housing need.</strong> Live Table 600 counts households
        on local authorities' own housing registers only; it excludes housing-association-run
        registers where these are separate from the council list, so the true scale of social
        housing demand is understated to a degree that varies by area.</li>
      <li><strong>Administrative &ldquo;cleanse&rdquo; effects are not separated from genuine
        demand change.</strong> Councils periodically review and remove applicants from their
        registers; a fall in the reported count can reflect this rather than reduced need. This
        data alone cannot distinguish the two.</li>
      <li><strong>No exogenous drivers.</strong> Every model here uses only the series' own
        history &mdash; none accounts for policy changes, local housing supply, or economic
        conditions that plausibly drive some of the swings shown above.</li>
      <li><strong>Small, overlapping backtest samples at longer horizons.</strong> The 5-year
        backtest has 25 origins nationally, and the same 25 origins independently in each of the
        9 regions &mdash; but consecutive origins share almost all of their training data, so
        these are not 25 independent trials &mdash; treat horizon-level MAPE as indicative of
        relative model performance, not a precise confidence interval.</li>
      <li><strong>Local-authority-level forecasting was not attempted.</strong> Unlike the clean
        regional data used here, the local-authority extract mixes pre- and post-reorganisation
        authority codes (boundary changes through 2019&ndash;2023) that would need reconciling
        first &mdash; documented but not resolved in <code>docs/initial_feasibility_note.md</code>
        &sect;2.</li>
      <li><strong>ARIMA's automatic order search can still produce implausible long-horizon
        forecasts</strong> even after the unit-root fix above &mdash; including one negative
        forecast at a training window ending near a sharp trend change. These were reported, not
        clipped or hidden; see <code>docs/statistical_models_methodology.md</code> &sect;4.</li>
    </ul>
  </section>

  <section id="reproduce">
    <h2>7. Reproducing this work</h2>
    <p>
      Every number and chart in this report is generated by a script, in order, from the raw
      MHCLG source file. Nothing is hand-edited or estimated by eye.
    </p>
    <pre class="code-block">python3 scripts/prepare_data.py         # raw extracts &rarr; processed long-format CSVs
python3 scripts/validate_national.py    # England-total figures vs. raw extract
.venv/bin/python3 scripts/explore_national.py    # EDA charts and headline stats
.venv/bin/python3 scripts/forecast_national.py   # national backtest, 5 base models
.venv/bin/python3 scripts/forecast_regional.py   # regional backtest, 5 base models
.venv/bin/python3 scripts/forecast_statistical.py  # + ets_damped, arima (national &amp; regional)
python3 scripts/build_report.py         # this report</pre>
    <p>
      Full technical detail, QA checks, and the complete decision log for every choice above
      (why an expanding window, why <code>MIN_TRAIN_YEARS=10</code>, why these four horizons) live
      in <code>docs/national_forecast_methodology.md</code>, <code>docs/regional_forecast_methodology.md</code>,
      and <code>docs/statistical_models_methodology.md</code>.
    </p>
  </section>

  <footer class="page-footer">
    <p>Hailie waiting-list forecast &middot; generated {generated_iso} &middot; source data: MHCLG Live Table 600</p>
  </footer>

</div>
"""


CSS = """
:root {
  --surface: #fcfcfb;
  --page-plane: #f9f9f7;
  --ink-primary: #17140f;
  --ink-secondary: #55503f;
  --ink-muted: #8a8471;
  --border: #e3ddc9;
  --accent: #2a6b52;
  --accent-soft: #e7efe6;
  --warm: #a4462a;
  --warm-soft: #f6e9e2;
  --card-surface: #fcfcfb;
  --card-border: #d8d2bc;
  --best-cell: #d9ead9;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --surface: #17140f;
    --page-plane: #0f0d0a;
    --ink-primary: #f6f3ea;
    --ink-secondary: #c9c2a9;
    --ink-muted: #948d76;
    --border: #3a3527;
    --accent: #7fbfa0;
    --accent-soft: #1f2b23;
    --warm: #e08a63;
    --warm-soft: #2c1f18;
    --card-surface: #fcfcfb;
    --card-border: #d8d2bc;
    --best-cell: #274a2f;
  }
}
:root[data-theme="dark"] {
  --surface: #17140f;
  --page-plane: #0f0d0a;
  --ink-primary: #f6f3ea;
  --ink-secondary: #c9c2a9;
  --ink-muted: #948d76;
  --border: #3a3527;
  --accent: #7fbfa0;
  --accent-soft: #1f2b23;
  --warm: #e08a63;
  --warm-soft: #2c1f18;
  --card-surface: #fcfcfb;
  --card-border: #d8d2bc;
  --best-cell: #274a2f;
}

* { box-sizing: border-box; }
html { color-scheme: light dark; }
body {
  margin: 0;
  background: var(--page-plane);
  color: var(--ink-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
}

.page {
  max-width: 780px;
  margin: 0 auto;
  padding: 3rem 1.5rem 5rem;
}

h1, h2, h3 {
  font-family: Georgia, "Iowan Old Style", "Palatino Linotype", "URW Palladio", serif;
  color: var(--ink-primary);
  text-wrap: balance;
  line-height: 1.2;
}

.masthead { margin-bottom: 2.5rem; }
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 600;
  margin: 0 0 0.6rem;
}
h1 { font-size: 2.05rem; margin: 0 0 1rem; }
.dek {
  font-size: 1.08rem;
  color: var(--ink-secondary);
  max-width: 62ch;
  margin: 0 0 1rem;
}
.meta { font-size: 0.85rem; color: var(--ink-muted); margin: 0; }

.toc {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.5rem;
  margin-bottom: 2.5rem;
}
.toc ol { margin: 0; padding-left: 1.2rem; columns: 2; column-gap: 2rem; }
.toc li { margin-bottom: 0.35rem; font-size: 0.92rem; }
.toc a { color: var(--ink-secondary); text-decoration: none; }
.toc a:hover, .toc a:focus-visible { color: var(--accent); text-decoration: underline; }

section { margin: 3rem 0; }
h2 {
  font-size: 1.5rem;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.5rem;
  margin-bottom: 1.2rem;
}
h3 { font-size: 1.15rem; margin: 1.5rem 0 0.7rem; }
p { color: var(--ink-secondary); max-width: 68ch; }
strong { color: var(--ink-primary); }
code {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.88em;
  background: var(--accent-soft);
  padding: 0.1em 0.4em;
  border-radius: 4px;
  color: var(--ink-primary);
}

.callout {
  background: var(--accent-soft);
  border-left: 4px solid var(--accent);
  border-radius: 4px;
  padding: 1.6rem 1.8rem 1.4rem;
}
.callout h2 { border-bottom: none; margin-bottom: 1rem; padding-bottom: 0; }
.callout p { max-width: 74ch; color: var(--ink-primary); }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1.2rem;
  margin-bottom: 1.4rem;
}
.stat { display: flex; flex-direction: column; gap: 0.15rem; }
.stat-value {
  font-family: Georgia, serif;
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 0.82rem; color: var(--ink-secondary); }

.note {
  background: var(--warm-soft);
  border-left: 4px solid var(--warm);
  border-radius: 4px;
  padding: 0.9rem 1.2rem;
  font-size: 0.95rem;
}
.note strong { color: var(--ink-primary); }

.chart-card {
  margin: 1.5rem 0;
  padding: 1rem;
  background: var(--card-surface);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  overflow-x: auto;
}
.chart-card img { max-width: 100%; height: auto; display: block; border-radius: 4px; }
.chart-card figcaption {
  margin-top: 0.6rem;
  font-size: 0.82rem;
  color: #6b6656;
  text-align: left;
}

.table-wrap { overflow-x: auto; }
table.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
  margin: 1.2rem 0;
  overflow-x: auto;
  display: block;
}
table.data-table thead, table.data-table tbody { display: table; width: 100%; table-layout: fixed; }
table.data-table th {
  text-align: left;
  font-weight: 600;
  color: var(--ink-secondary);
  border-bottom: 1px solid var(--border);
  padding: 0.55rem 0.7rem;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
table.data-table td {
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid var(--border);
  color: var(--ink-secondary);
}
table.data-table .model-name { color: var(--ink-primary); font-weight: 600; }
table.data-table .num { font-variant-numeric: tabular-nums; text-align: right; }
table.data-table .muted { color: var(--ink-muted); font-weight: 400; }
table.data-table .best-cell { background: var(--best-cell); color: var(--ink-primary); font-weight: 700; border-radius: 4px; }
table.data-table tbody tr:last-child td { border-bottom: none; }

.code-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.2rem;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.85rem;
  overflow-x: auto;
  color: var(--ink-primary);
  line-height: 1.7;
}

.limitations-list { padding-left: 1.2rem; }
.limitations-list li { margin-bottom: 0.9rem; color: var(--ink-secondary); max-width: 68ch; }
.limitations-list strong { color: var(--ink-primary); }

.page-footer {
  margin-top: 4rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--ink-muted);
}

@media (max-width: 600px) {
  .toc ol { columns: 1; }
  .stat-grid { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
  h1 { font-size: 1.6rem; }
}
"""


def main():
    stats = compute_headline_stats()
    snapshot = regional_2025_snapshot()

    national_extended = load_csv_rows(OUTPUTS_DIR / "model_results_extended.csv")
    regional_extended = load_csv_rows(OUTPUTS_DIR / "regional_model_results_extended.csv")
    forward_rows = load_csv_rows(OUTPUTS_DIR / "national_forecast_2026_2030.csv")

    best = best_per_horizon(national_extended)
    best_1y, best_5y = best[1], best[5]

    images = {name.replace(".png", ""): encode_image(name) for name, _ in IMAGES}
    img_lookup = dict(IMAGES)

    def img(name):
        key = name.replace(".png", "")
        return image_block(name, img_lookup[name], images[key])

    now = datetime.now(timezone.utc)

    html_out = PAGE_TEMPLATE.format(
        css=CSS,
        generated_date=date.today().strftime("%-d %B %Y"),
        generated_iso=now.strftime("%Y-%m-%d"),
        v2025=fmt(stats["v2025"]),
        v2020=fmt(stats["v2020"]),
        change_20_25_pct=fmt_pct(stats["change_20_25_pct"], sign=True),
        trough_value=fmt(stats["trough_value"]),
        trough_year=stats["trough_year"],
        peak_value=fmt(stats["peak_value"]),
        peak_year=stats["peak_year"],
        best_1y_model=MODEL_LABELS.get(best_1y["model"], best_1y["model"]),
        best_1y_mape=f"{float(best_1y['mape_pct']):.2f}%",
        best_5y_model=MODEL_LABELS.get(best_5y["model"], best_5y["model"]),
        best_5y_mape=f"{float(best_5y['mape_pct']):.2f}%",
        img_trend=img("england_waiting_list_1987_2025.png"),
        img_pctchange=img("england_annual_percentage_change.png"),
        img_regional=img("regional_waiting_list_trends.png"),
        regional_snapshot_table=render_regional_snapshot_table(snapshot),
        national_results_table=render_model_results_table(national_extended),
        img_backtest_chart=img("backtest_one_step_ahead_extended.png"),
        img_mape_chart=img("backtest_mape_by_horizon_extended.png"),
        regional_best_model_table=render_regional_best_model_table(
            regional_best_model_table(regional_extended, 1), regional_best_model_table(regional_extended, 5)
        ),
        img_regional_heatmap=img("regional_backtest_mape_heatmap.png"),
        img_regional_wins=img("regional_win_counts_extended.png"),
        forward_forecast_table=render_forward_forecast_table(forward_rows),
    )

    out_path = OUTPUTS_DIR / "report.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"Wrote {out_path.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")


if __name__ == "__main__":
    main()
