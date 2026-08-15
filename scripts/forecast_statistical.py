#!/usr/bin/env python3
"""Week 2 statistical-model comparison for MHCLG Live Table 600 (national + regional).

Adds two statsmodels-based models to the five dependency-light benchmarks defined
in scripts/forecast_national.py, then reuses that script's (and
scripts/forecast_regional.py's) unmodified backtest harness, chart functions, and
data loaders to compare all seven models on the same leakage-free rolling-origin
design (expanding window, MIN_TRAIN_YEARS=10, HORIZONS=[1,2,3,5]). Nothing about
the harness itself is reimplemented; run_backtest() and the two chart functions in
forecast_national.py were given an optional `models=`/`model_colors=`/`model_labels=`
parameter (defaulting to the original five) specifically so this script did not
need to duplicate them.

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

import warnings
from pathlib import Path

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from forecast_national import (
    HORIZONS,
    MODEL_COLORS,
    MODEL_LABELS,
    MODELS,
    load_england_series,
    make_mape_by_horizon_chart,
    make_one_step_ahead_chart,
    run_backtest,
    summarize,
    write_csv,
)
from forecast_regional import REGION_ORDER, load_all_regions

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

    print(
        "\nWrote outputs/model_results_extended.csv, outputs/backtest_predictions_extended.csv, "
        "outputs/regional_model_results_extended.csv"
    )
    print(
        "Wrote outputs/figures/backtest_one_step_ahead_extended.png, "
        "outputs/figures/backtest_mape_by_horizon_extended.png, "
        "outputs/figures/regional_win_counts_extended.png"
    )


if __name__ == "__main__":
    main()
