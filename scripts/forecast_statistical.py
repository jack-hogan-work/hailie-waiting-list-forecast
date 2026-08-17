#!/usr/bin/env python3
"""Week 2 statistical-model comparison for MHCLG Live Table 600 (national + regional).

Adds two statsmodels-based models to the five dependency-light benchmarks defined
in scripts/forecast_national.py, then reuses that script's (and
scripts/forecast_regional.py's) unmodified backtest harness, chart functions, and
data loaders to compare all seven models on the same leakage-free rolling-origin
design (expanding window, MIN_TRAIN_YEARS=10, HORIZONS=[1,2,3,5]). Nothing about
the harness itself is reimplemented; run_backtest(), forward_forecast(), and the
two chart functions in forecast_national.py were given an optional
`models=`/`model_colors=`/`model_labels=` parameter (defaulting to the original
five) specifically so this script did not need to duplicate them.

New models (statsmodels; NOT dependency-light - this is why the session asked
before installing statsmodels, see docs/statistical_models_methodology.md):
  - ets_damped: Holt's damped-trend exponential smoothing
                (statsmodels.tsa.holtwinters.ExponentialSmoothing, trend="add",
                damped_trend=True, seasonal=None - annual data has no seasonal
                period to model). Directly targets the long-horizon overshoot
                seen in the plain (undamped) `holt` model.
  - arima     : ARIMA(p,d,q) with the order chosen per origin by an AIC grid
                search (d in {1,2}, p,q in {0,1,2} = 18 combinations) on the
                training window only - no leakage, same principle as the
                alpha/beta grid searches in forecast_national.py.

Run with:
    .venv/bin/python3 scripts/forecast_statistical.py
"""

import math
import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from forecast_national import (
    FORWARD_YEARS,
    HORIZONS,
    MODEL_COLORS,
    MODEL_LABELS,
    MODELS,
    forward_forecast,
    load_england_series,
    make_mape_by_horizon_chart,
    make_one_step_ahead_chart,
    run_backtest,
    summarize,
    write_csv,
)
from forecast_regional import REGION_CODES, REGION_ORDER, load_all_regions

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

ARIMA_D_VALUES = (1, 2)
ARIMA_PQ_VALUES = (0, 1, 2)

TEAL = "#1baf7a"     # ets_damped / categorical slot 3 (aqua)
YELLOW = "#eda100"   # arima / categorical slot 4


# --- New models (statsmodels) --------------------------------------------------


def ets_damped_forecast(train_years, train_values, horizons):
    """Holt's damped-trend exponential smoothing. Same signature as the dependency-
    light models in forecast_national.py so it drops straight into MODELS/run_backtest."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(
            train_values, trend="add", damped_trend=True, seasonal=None, initialization_method="estimated"
        ).fit(optimized=True)
    max_h = max(horizons)
    fc = np.asarray(fit.forecast(max_h))
    return {h: float(fc[h - 1]) for h in horizons}


MIN_ROOT_DISTANCE = 1.05  # AR/MA roots must clear the unit circle by this margin to be accepted


def _is_well_conditioned(fit):
    """Reject candidates whose AR/MA roots sit too close to the unit circle.

    On short training windows (as few as 10 points here), unconstrained AIC search
    can select an over-parameterised order where the AR and MA polynomials nearly
    cancel - both sets of roots collapse onto the unit circle, in-sample fit becomes
    spuriously near-perfect (AIC artificially tiny), and the resulting forecast is
    numerically degenerate (observed directly: an origin=2003 fit during development
    selected ARIMA(2,2,2) with AIC=10 against ~368 for the next best candidate, roots
    at |root|=1.0000000009, and a forecast of exactly 0.0 households for every future
    year - see docs/statistical_models_methodology.md for the full diagnosis). This
    check is the standard safeguard against that failure mode.
    """
    for roots in (fit.arroots, fit.maroots):
        if len(roots) and min(abs(r) for r in roots) < MIN_ROOT_DISTANCE:
            return False
    return True


def arima_forecast(train_years, train_values, horizons):
    """ARIMA with order chosen by in-sample AIC grid search on the training window only,
    restricted to well-conditioned candidates (see _is_well_conditioned)."""
    best_aic, best_fit = float("inf"), None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for d in ARIMA_D_VALUES:
            for p in ARIMA_PQ_VALUES:
                for q in ARIMA_PQ_VALUES:
                    try:
                        fit = ARIMA(train_values, order=(p, d, q)).fit()
                    except Exception:
                        continue
                    if not _is_well_conditioned(fit):
                        continue
                    if fit.aic < best_aic:
                        best_aic, best_fit = fit.aic, fit
        if best_fit is None:
            # ARIMA(0,1,0) = random walk; always converges and is always well-conditioned
            # (no AR/MA roots), used only if the whole grid failed or was rejected.
            best_fit = ARIMA(train_values, order=(0, 1, 0)).fit()
    max_h = max(horizons)
    fc = np.asarray(best_fit.forecast(steps=max_h))
    return {h: float(fc[h - 1]) for h in horizons}


EXTENDED_MODELS = dict(MODELS)
EXTENDED_MODELS["ets_damped"] = ets_damped_forecast
EXTENDED_MODELS["arima"] = arima_forecast

EXTENDED_COLORS = dict(MODEL_COLORS)
EXTENDED_COLORS["ets_damped"] = TEAL
EXTENDED_COLORS["arima"] = YELLOW

EXTENDED_LABELS = dict(MODEL_LABELS)
EXTENDED_LABELS["ets_damped"] = "ETS damped trend"
EXTENDED_LABELS["arima"] = "ARIMA (AIC-selected)"


# --- National ---------------------------------------------------------------


def run_national():
    years, values = load_england_series()
    detail = run_backtest(years, values, models=EXTENDED_MODELS)
    summary = summarize(detail)
    return years, values, detail, summary


# --- Regional -----------------------------------------------------------------


def run_regional_summary_only(regions):
    """Same as forecast_regional.run_all_regions but summary rows only (no detail
    CSV - 9 regions x 109 origin/horizon rows x 7 models would be ~50k rows for a
    result that's only used in aggregate here; see the methodology note)."""
    summary = []
    for code, name in REGION_ORDER:
        r = regions[code]
        r_detail = run_backtest(r["years"], r["values"], models=EXTENDED_MODELS)
        r_summary = summarize(r_detail)
        for row in r_summary:
            row = dict(row)
            row["region_code"] = code
            row["region_name"] = name
            summary.append(row)
    return summary


def regional_forward_forecast(regions, models=None):
    """Forecast 2026-2030 per region, each model fit on that region's full
    1987-2025 series. Applies forward_forecast() from forecast_national.py once
    per region, mirroring run_regional_summary_only()'s per-region loop over the
    same (unmodified) national function."""
    rows = []
    for code, name in REGION_ORDER:
        r = regions[code]
        for row in forward_forecast(r["years"], r["values"], models=models):
            row = dict(row)
            row["region_code"] = code
            row["region_name"] = name
            rows.append(row)
    return rows


def regional_best_per_horizon(regional_summary, region_code, horizons=HORIZONS):
    """Same selection rule as build_report.py's best_per_horizon(), applied to one
    region: the model with the lowest backtested MAPE at each evaluated horizon."""
    best = {}
    for h in horizons:
        candidates = [r for r in regional_summary if r["region_code"] == region_code and r["horizon_years"] == h]
        best[h] = min(candidates, key=lambda r: r["mape_pct"])
    return best


def select_regional_forecast(regional_summary, regional_forward):
    """For each region and each backtested horizon (1/2/3/5-year - never 4-year/2029,
    which HORIZONS never evaluates), pick the forward forecast from the model that
    actually won that region's backtest at that horizon - the forward forecast that
    is consistent with the evaluation results, not a separately-chosen model."""
    origin_year = FORWARD_YEARS[0] - 1  # 2025: last actual year, per FORWARD_YEARS=[2026..2030]
    selected = []
    for code, name in REGION_ORDER:
        best = regional_best_per_horizon(regional_summary, code)
        for h, row in best.items():
            target_year = origin_year + h
            model = row["model"]
            match = [
                fr for fr in regional_forward
                if fr["region_code"] == code and fr["model"] == model and fr["target_year"] == target_year
            ]
            assert len(match) == 1, f"missing/duplicate forward forecast for {name}/{model}/{target_year}"
            selected.append(
                {
                    "region_code": code,
                    "region_name": name,
                    "target_year": target_year,
                    "horizon_years": h,
                    "selected_model": model,
                    "mape_pct_at_selection": row["mape_pct"],
                    "forecast": match[0]["forecast"],
                }
            )
    return selected


def regional_pct_change_2030(regions, selected, regional_forward, models):
    """% change from 2025 actual to 2030, per region: the backtest-selected model's
    point estimate (pct_change), plus the min/max spread across `models`' 2030
    forecasts. The spread matters because naive - flat by construction - is the
    backtest-selected model in 8 of 9 regions at the 5-year horizon (see
    docs/regional_forecast_methodology.md), which makes the selected point estimate
    alone read as 'nothing changes'; the spread across models shows whether that
    flat call is a confident 'no clear trend' or a case where trend-aware models
    still disagree sharply on direction/magnitude even though none of them beat
    naive on the historical backtest.

    Callers should exclude `linear_trend` from `models`: per the backtest results
    (docs/statistical_models_methodology.md, docs/regional_forecast_methodology.md),
    it is the worst-performing model at every horizon in every region, by a wide
    margin - including it here would make its known overshoot dominate the range
    and read as genuine model disagreement rather than one discredited model."""
    out = []
    for code, name in REGION_ORDER:
        actual_2025 = regions[code]["values"][-1]
        row5 = next(s for s in selected if s["region_code"] == code and s["horizon_years"] == 5)
        selected_pct = 100 * (row5["forecast"] - actual_2025) / actual_2025

        model_pcts = []
        for m in models:
            match = [
                r for r in regional_forward
                if r["region_code"] == code and r["model"] == m and r["target_year"] == 2030
            ]
            assert len(match) == 1, f"missing 2030 forecast for {name}/{m}"
            model_pcts.append(100 * (match[0]["forecast"] - actual_2025) / actual_2025)

        out.append(
            {
                "region_code": code,
                "region_name": name,
                "actual_2025": actual_2025,
                "forecast_2030": row5["forecast"],
                "selected_model": row5["selected_model"],
                "pct_change": selected_pct,
                "pct_change_min_across_models": min(model_pcts),
                "pct_change_max_across_models": max(model_pcts),
            }
        )
    return out


def make_regional_win_count_chart(summary):
    import matplotlib.pyplot as plt

    from forecast_national import INK_MUTED, INK_PRIMARY, SOURCE_CAPTION, SURFACE, style_axes

    model_names = list(EXTENDED_MODELS)
    n_models = len(model_names)
    counts = {m: [0] * len(HORIZONS) for m in model_names}

    for hi, h in enumerate(HORIZONS):
        for code, _ in REGION_ORDER:
            region_rows = [s for s in summary if s["region_code"] == code and s["horizon_years"] == h]
            best = min(region_rows, key=lambda s: s["mape_pct"])
            counts[best["model"]][hi] += 1

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=SURFACE)
    style_axes(ax)

    x = list(range(len(HORIZONS)))
    width = 0.8 / n_models
    center = (n_models - 1) / 2
    for i, model_name in enumerate(model_names):
        offsets = [xi + (i - center) * width for xi in x]
        ax.bar(
            offsets,
            counts[model_name],
            width=width,
            color=EXTENDED_COLORS[model_name],
            label=EXTENDED_LABELS[model_name],
            zorder=2,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}-year" for h in HORIZONS])
    ax.set_ylim(0, 9)
    ax.set_yticks(range(0, 10))
    ax.set_title(
        "Regions where each of the 7 models has the lowest MAPE, by horizon (of 9 regions)",
        fontsize=13,
        color=INK_PRIMARY,
        loc="left",
        pad=12,
    )
    ax.set_xlabel("Forecast horizon", fontsize=10, color="#52514e")
    ax.set_ylabel("Number of regions (of 9) where this model wins", fontsize=10, color="#52514e")
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)
    fig.text(
        0.02,
        0.045,
        "Caution: naive/SES/ETS-damped wins are often decided by <0.1 MAPE points - see the methodology note.",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIGURES_DIR / "regional_win_counts_extended.png", dpi=150)
    plt.close(fig)


# Diverging pair (dataviz skill reference palette, light mode): blue = rise, red = fall.
DIVERGING_BLUE = "#2a78d6"
DIVERGING_RED = "#e34948"


def make_regional_change_chart(pct_change_rows):
    """Horizontal range chart, one row per region: a muted gray span from the lowest
    to the highest 2025->2030 % change across the 6 competitive models (naive, drift,
    ses, holt, ets_damped, arima - linear_trend excluded, see regional_pct_change_2030()
    docstring), with a diverging-colored dot marking the backtest-selected model's
    point estimate. A plain bar of the selected value alone would be nearly invisible
    for 8 of 9 regions (naive - flat by construction - is the backtest winner almost
    everywhere at 5 years), so the range is the real signal here: a short span means
    the models agree the 2030 level is close to flat; a wide span (e.g. West Midlands,
    arima vs. holt) means the 'flat' selected point is masking real disagreement about
    direction, not a confident no-change call."""
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib.lines import Line2D

    from forecast_national import BASELINE, INK_MUTED, INK_PRIMARY, INK_SECONDARY, SOURCE_CAPTION, SURFACE, style_axes

    rows_sorted = sorted(pct_change_rows, key=lambda r: r["pct_change"])
    names = [r["region_name"] for r in rows_sorted]
    selected_vals = [r["pct_change"] for r in rows_sorted]
    lo_vals = [r["pct_change_min_across_models"] for r in rows_sorted]
    hi_vals = [r["pct_change_max_across_models"] for r in rows_sorted]

    fig, ax = plt.subplots(figsize=(11, 6.4), facecolor=SURFACE)
    style_axes(ax)
    ax.xaxis.grid(True, color=BASELINE, linewidth=1, zorder=0)
    ax.yaxis.grid(False)

    y = list(range(len(names)))
    for yi, lo, hi in zip(y, lo_vals, hi_vals):
        ax.plot([lo, hi], [yi, yi], color=INK_MUTED, linewidth=3, solid_capstyle="round", zorder=2, alpha=0.5)
    dot_colors = [DIVERGING_BLUE if v >= 0 else DIVERGING_RED for v in selected_vals]
    ax.scatter(selected_vals, y, color=dot_colors, s=55, zorder=3, edgecolor=SURFACE, linewidth=1.2)
    ax.axvline(0, color=INK_PRIMARY, linewidth=1, zorder=1)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9, color=INK_PRIMARY)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
    for yi, v in zip(y, selected_vals):
        ax.text(v, yi + 0.32, f"{v:+.1f}%", va="bottom", ha="center", fontsize=7.5, color=INK_SECONDARY)

    legend_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=7, markerfacecolor=DIVERGING_BLUE,
               markeredgecolor=SURFACE, label="Backtest-selected model (rise)"),
        Line2D([0], [0], marker="o", linestyle="none", markersize=7, markerfacecolor=DIVERGING_RED,
               markeredgecolor=SURFACE, label="Backtest-selected model (fall)"),
        Line2D([0], [0], color=INK_MUTED, linewidth=3, alpha=0.5, label="Range across the 6 competitive models"),
    ]
    ax.legend(handles=legend_handles, frameon=False, fontsize=8.5, loc="lower right")

    ax.set_title(
        "Illustrative 2025→2030 change: selected model vs. 6-model range",
        fontsize=13,
        color=INK_PRIMARY,
        loc="left",
    )
    ax.set_xlabel("% change, 2025 actual to 2030 forecast", fontsize=10, color=INK_SECONDARY)

    fig.subplots_adjust(left=0.18, right=0.96, top=0.90, bottom=0.20)
    fig.text(
        0.18,
        0.075,
        "Dot = model selected by lowest 5-year backtested MAPE per region; range excludes linear_trend (uncompetitive at every horizon/region).",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.text(0.18, 0.03, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.savefig(FIGURES_DIR / "regional_forecast_change_2025_2030.png", dpi=150)
    plt.close(fig)


def make_regional_trajectory_chart(regions, regional_forward, selected):
    """3x3 small multiples, one panel per region: actual history (solid, ink) plus
    the backtest-selected model's 2026-2030 forecast (dashed, that model's own
    established color from EXTENDED_COLORS - same palette used throughout this
    script, not a new per-region hue, so the 9-panel grid never exceeds the
    categorical palette's identity budget)."""
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib.lines import Line2D

    from forecast_national import INK_MUTED, INK_PRIMARY, SOURCE_CAPTION, SURFACE, style_axes

    trajectory_start_year = 2015

    fig, axes = plt.subplots(3, 3, figsize=(12, 10), facecolor=SURFACE, sharex=True)
    used_models = set()

    for ax, (code, name) in zip(axes.flat, REGION_ORDER):
        r = regions[code]
        style_axes(ax)
        hist = [(y, v) for y, v in zip(r["years"], r["values"]) if y >= trajectory_start_year]
        ax.plot([y for y, _ in hist], [v for _, v in hist], color=INK_PRIMARY, linewidth=1.6, zorder=3)

        sel = next(s for s in selected if s["region_code"] == code and s["horizon_years"] == 5)
        model = sel["selected_model"]
        used_models.add(model)
        fc_rows = sorted(
            (fr for fr in regional_forward if fr["region_code"] == code and fr["model"] == model),
            key=lambda fr: fr["target_year"],
        )
        fc_years = [r["years"][-1]] + [fr["target_year"] for fr in fc_rows]
        fc_values = [r["values"][-1]] + [fr["forecast"] for fr in fc_rows]
        ax.plot(
            fc_years, fc_values,
            color=EXTENDED_COLORS[model], linewidth=1.6, linestyle="--",
            marker="o", markersize=3, zorder=3,
        )

        ax.set_title(name, fontsize=10, color=INK_PRIMARY, loc="left")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1000:.0f}k"))
        ax.tick_params(labelsize=7.5)

    legend_handles = [Line2D([0], [0], color=INK_PRIMARY, linewidth=1.6, label="Actual")] + [
        Line2D([0], [0], color=EXTENDED_COLORS[m], linewidth=1.6, linestyle="--", label=f"Forecast: {EXTENDED_LABELS[m]}")
        for m in sorted(used_models)
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.035))
    fig.suptitle(
        f"Regional trajectories: {trajectory_start_year}-2025 actual + 2026-2030 forecast "
        "(backtest-selected model, 5-year horizon)",
        fontsize=13,
        color=INK_PRIMARY,
        x=0.02,
        ha="left",
    )
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    fig.savefig(FIGURES_DIR / "regional_forecast_trajectories_2026_2030.png", dpi=150)
    plt.close(fig)


# --- QA --------------------------------------------------------------------------


def run_qa(national_summary, regional_summary):
    print("\n--- QA: forecast_statistical ---")
    expected_national_rows = len(EXTENDED_MODELS) * len(HORIZONS)
    print(f"National summary rows: {len(national_summary)} (expected {expected_national_rows})")
    assert len(national_summary) == expected_national_rows

    expected_regional_rows = len(EXTENDED_MODELS) * len(HORIZONS) * 9
    print(f"Regional summary rows: {len(regional_summary)} (expected {expected_regional_rows})")
    assert len(regional_summary) == expected_regional_rows

    print("All QA checks passed.")


def run_regional_forward_qa(regional_forward, selected, models=None):
    """QA for the regional forward forecast: missing regions, missing years,
    duplicate rows, non-finite/implausible values, and other pipeline failures -
    reported explicitly rather than silently clipped, per this project's existing
    convention (docs/statistical_models_methodology.md's ARIMA finding)."""
    models = models if models is not None else EXTENDED_MODELS
    print("\n--- QA: regional forward forecast ---")

    regions_present = {row["region_code"] for row in regional_forward}
    print(f"Regions present: {len(regions_present)} (expected {len(REGION_CODES)})")
    assert regions_present == REGION_CODES, (
        f"region mismatch: missing {REGION_CODES - regions_present}, "
        f"unexpected {regions_present - REGION_CODES}"
    )

    seen = set()
    for row in regional_forward:
        key = (row["region_code"], row["model"], row["target_year"])
        assert key not in seen, f"duplicate forward-forecast row: {key}"
        seen.add(key)
        assert row["model"] in models, f"unexpected model in forward forecast: {row}"
        assert row["target_year"] in FORWARD_YEARS, f"unexpected target year: {row}"
        forecast = row["forecast"]
        assert isinstance(forecast, (int, float)) and math.isfinite(forecast), f"non-finite forecast: {row}"

    expected_total = len(REGION_CODES) * len(models) * len(FORWARD_YEARS)
    print(f"Forward-forecast rows: {len(regional_forward)} (expected {expected_total})")
    assert len(regional_forward) == expected_total, f"expected {expected_total} rows, got {len(regional_forward)}"

    for code, name in REGION_ORDER:
        years_seen = {row["target_year"] for row in regional_forward if row["region_code"] == code}
        missing_years = set(FORWARD_YEARS) - years_seen
        assert not missing_years, f"{name}: missing forward years {missing_years}"

    expected_selected = len(REGION_CODES) * len(HORIZONS)
    print(f"Selected-model rows: {len(selected)} (expected {expected_selected})")
    assert len(selected) == expected_selected, f"expected {expected_selected} selected rows, got {len(selected)}"

    negatives = [row for row in regional_forward if row["forecast"] < 0]
    if negatives:
        print(f"WARNING: {len(negatives)} negative forecast value(s) found (reported, not clipped):")
        for row in negatives:
            label = MODEL_LABELS.get(row["model"], row["model"])
            print(f"  {row['region_name']:<28} {label:<24} {row['target_year']} -> {row['forecast']:,.0f}")
    else:
        print("Negative-forecast check: none found.")

    negatives_selected = [row for row in selected if row["forecast"] < 0]
    if negatives_selected:
        print(f"WARNING: {len(negatives_selected)} of the *selected* (headline) forecasts are negative:")
        for row in negatives_selected:
            print(f"  {row['region_name']:<28} {row['selected_model']:<14} {row['target_year']} -> {row['forecast']:,.0f}")

    print("All regional forward-forecast QA checks passed (structural checks); see warnings above for any implausible values.")


# --- Main ------------------------------------------------------------------------


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Running national backtest with 7 models (5 base + ets_damped + arima)...")
    years, values, detail, national_summary = run_national()

    write_csv(
        OUTPUTS_DIR / "backtest_predictions_extended.csv",
        detail,
        [
            "model",
            "origin_year",
            "train_length",
            "horizon",
            "target_year",
            "actual",
            "forecast",
            "error",
            "abs_error",
            "pct_error",
        ],
    )
    write_csv(
        OUTPUTS_DIR / "model_results_extended.csv",
        national_summary,
        ["model", "horizon_years", "n_origins", "first_origin_year", "last_origin_year", "mae", "rmse", "mape_pct", "mean_error_bias"],
    )

    forward = forward_forecast(years, values, models=EXTENDED_MODELS)
    write_csv(
        OUTPUTS_DIR / "national_forecast_2026_2030_extended.csv",
        forward,
        ["model", "target_year", "forecast"],
    )

    make_one_step_ahead_chart(
        detail,
        years,
        values,
        models=EXTENDED_MODELS,
        model_colors=EXTENDED_COLORS,
        model_labels=EXTENDED_LABELS,
        title="England: actual vs. 1-year-ahead forecasts, 7 models (1997-2025)",
        out_path=FIGURES_DIR / "backtest_one_step_ahead_extended.png",
    )
    make_mape_by_horizon_chart(
        national_summary,
        models=EXTENDED_MODELS,
        model_colors=EXTENDED_COLORS,
        model_labels=EXTENDED_LABELS,
        title="England: rolling-origin backtest MAPE by horizon, 7 models",
        out_path=FIGURES_DIR / "backtest_mape_by_horizon_extended.png",
    )

    print("\n--- National model results (7 models) ---")
    print(f"{'model':<14}{'horizon':>8}{'n':>5}{'MAE':>12}{'RMSE':>12}{'MAPE%':>9}{'bias':>12}")
    for s in sorted(national_summary, key=lambda s: (s["horizon_years"], s["model"])):
        print(
            f"{s['model']:<14}{s['horizon_years']:>7}y{s['n_origins']:>5}"
            f"{s['mae']:>12,.0f}{s['rmse']:>12,.0f}{s['mape_pct']:>9.2f}{s['mean_error_bias']:>12,.0f}"
        )

    print("\nRunning regional backtest with 7 models (9 regions)...")
    regions = load_all_regions()
    regional_summary = run_regional_summary_only(regions)

    write_csv(
        OUTPUTS_DIR / "regional_model_results_extended.csv",
        regional_summary,
        [
            "region_code",
            "region_name",
            "model",
            "horizon_years",
            "n_origins",
            "first_origin_year",
            "last_origin_year",
            "mae",
            "rmse",
            "mape_pct",
            "mean_error_bias",
        ],
    )
    make_regional_win_count_chart(regional_summary)

    run_qa(national_summary, regional_summary)

    print("\nRunning regional 2026-2030 forward forecast (9 regions x 7 models)...")
    regional_forward = regional_forward_forecast(regions, models=EXTENDED_MODELS)
    write_csv(
        OUTPUTS_DIR / "regional_forecast_2026_2030_extended.csv",
        regional_forward,
        ["region_code", "region_name", "model", "target_year", "forecast"],
    )

    selected = select_regional_forecast(regional_summary, regional_forward)
    write_csv(
        OUTPUTS_DIR / "regional_forecast_selected_2026_2030.csv",
        selected,
        ["region_code", "region_name", "target_year", "horizon_years", "selected_model", "mape_pct_at_selection", "forecast"],
    )

    competitive_models = [m for m in EXTENDED_MODELS if m != "linear_trend"]
    pct_change_rows = regional_pct_change_2030(regions, selected, regional_forward, competitive_models)
    write_csv(
        OUTPUTS_DIR / "regional_forecast_change_2025_2030.csv",
        pct_change_rows,
        [
            "region_code", "region_name", "actual_2025", "forecast_2030", "selected_model",
            "pct_change", "pct_change_min_across_models", "pct_change_max_across_models",
        ],
    )

    make_regional_change_chart(pct_change_rows)
    make_regional_trajectory_chart(regions, regional_forward, selected)

    run_regional_forward_qa(regional_forward, selected, models=EXTENDED_MODELS)

    print("\n--- Regional 2025 -> 2030 change: backtest-selected model vs. range across 6 competitive models ---")
    for row in sorted(pct_change_rows, key=lambda r: r["pct_change"]):
        print(
            f"{row['region_name']:<28}{MODEL_LABELS.get(row['selected_model'], row['selected_model']):<24}"
            f"{row['pct_change']:>+7.1f}%   range [{row['pct_change_min_across_models']:>+6.1f}%, "
            f"{row['pct_change_max_across_models']:>+6.1f}%]"
        )

    print(
        "\nWrote outputs/model_results_extended.csv, outputs/backtest_predictions_extended.csv, "
        "outputs/regional_model_results_extended.csv, outputs/national_forecast_2026_2030_extended.csv, "
        "outputs/regional_forecast_2026_2030_extended.csv, outputs/regional_forecast_selected_2026_2030.csv, "
        "outputs/regional_forecast_change_2025_2030.csv"
    )
    print(
        "Wrote outputs/figures/backtest_one_step_ahead_extended.png, "
        "outputs/figures/backtest_mape_by_horizon_extended.png, "
        "outputs/figures/regional_win_counts_extended.png, "
        "outputs/figures/regional_forecast_change_2025_2030.png, "
        "outputs/figures/regional_forecast_trajectories_2026_2030.png"
    )


if __name__ == "__main__":
    main()
