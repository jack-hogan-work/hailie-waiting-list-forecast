#!/usr/bin/env python3
"""Week 2 national forecasting & rolling-origin backtesting for MHCLG Live Table 600.

Loads the validated England-total series (Area code E92000001) from
data/processed/regional_waiting_lists_long.csv, fits five dependency-light
benchmark forecasting models, evaluates them with leakage-free rolling-origin
("walk-forward") backtesting at 1/2/3/5-year horizons, writes result CSVs to
outputs/, and produces two comparison charts under outputs/figures/.

Models (all pure Python, no third-party forecasting libraries):
  - naive      : forecast = last observed value (all future horizons).
  - drift      : forecast = last value + h * average historical slope
                 (Hyndman & Athanasopoulos's drift method).
  - linear_trend: ordinary-least-squares straight line fit to the training
                 window, extrapolated h years beyond the origin.
  - ses        : simple exponential smoothing; forecast is flat at the
                 fitted level, with alpha grid-searched (0.01-0.99) to
                 minimise in-sample SSE on the training window only.
  - holt       : Holt's linear (double) exponential smoothing; forecast is
                 the fitted level plus h * fitted trend, with (alpha, beta)
                 jointly grid-searched (0.01-0.99 each) on in-sample SSE.

Backtesting design (see docs/national_forecast_methodology.md for the full
rationale):
  - Expanding training window: each origin's model is fit on all years from
    1987 up to and including the origin year (not a fixed-size sliding
    window), so later origins see more history. This suits a 39-observation
    annual series better than a fixed window, which would either discard
    history or force very short early windows.
  - MIN_TRAIN_YEARS = 10: the first origin is 1996 (trained on 1987-1996).
    Fewer than 10 points was judged too few for a stable trend fit; the
    series is short enough that a much higher minimum would leave few
    origins to backtest over.
  - HORIZONS = 1, 2, 3, 5 years: covers a standard one-year-ahead check plus
    multi-year horizons, capped at 5 because origins-with-a-known-outcome
    shrink as horizon grows (only 39 years of data in total).
  - No leakage: at every origin, only data up to and including that origin
    year is used to fit; the actual outcome compared against is always a
    year strictly after the origin.

Standard library only for all data/model logic (csv, math); matplotlib
(project-local .venv only) is used for the two comparison charts. Run with:

    .venv/bin/python3 scripts/forecast_national.py
"""

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
OUTPUTS_DIR = REPO_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

ENGLAND_AREA_CODE = "E92000001"
SOURCE_CAPTION = (
    "Source: MHCLG Live Table 600, Regional Data worksheet, retrieved 7 Aug 2026. "
    "Households on the register at 1 April each year, 1987-2025."
)

MIN_TRAIN_YEARS = 10
HORIZONS = [1, 2, 3, 5]
FORWARD_YEARS = [2026, 2027, 2028, 2029, 2030]

# --- Palette (data-viz skill reference palette, light mode) ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"     # actual series / categorical slot 1
ORANGE = "#c1720a"   # naive / categorical slot 2
GREEN = "#3f8f5f"    # drift / categorical slot 3
RED = "#e34948"      # linear_trend / diverging pole
VIOLET = "#4a3aa7"   # ses / categorical slot 7
MAGENTA = "#e87ba4"  # holt / categorical slot 5

MODEL_COLORS = {
    "naive": ORANGE,
    "drift": GREEN,
    "linear_trend": RED,
    "ses": VIOLET,
    "holt": MAGENTA,
}
MODEL_LABELS = {
    "naive": "Naive (last observation)",
    "drift": "Drift",
    "linear_trend": "Linear trend (OLS)",
    "ses": "Simple exponential smoothing",
    "holt": "Holt's linear (level + trend)",
}


# --- Data loading -----------------------------------------------------------


def load_england_series():
    """Return (years, values) for the England total row, sorted by year."""
    series = {}
    with PROCESSED_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Area code"] != ENGLAND_AREA_CODE:
                continue
            year = int(row["year"])
            raw_value = row["households_on_register"]
            if raw_value == "":
                raise ValueError(f"Unexpected missing England value for year {year}")
            series[year] = int(raw_value)

    years = sorted(series)
    expected = list(range(years[0], years[-1] + 1))
    if years != expected:
        raise ValueError(f"England series has gaps: expected {expected}, got {years}")

    values = [series[y] for y in years]
    return years, values


# --- Forecast models ---------------------------------------------------------
# Every model has the signature (train_years, train_values, horizons) -> {h: forecast}.


def naive_forecast(train_years, train_values, horizons):
    last = train_values[-1]
    return {h: last for h in horizons}


def drift_forecast(train_years, train_values, horizons):
    n = len(train_values)
    slope = (train_values[-1] - train_values[0]) / (n - 1)
    last = train_values[-1]
    return {h: last + h * slope for h in horizons}


def ols_fit(xs, ys):
    """Simple ordinary-least-squares fit; returns (intercept, slope)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var = sum((x - mean_x) ** 2 for x in xs)
    slope = cov / var
    intercept = mean_y - slope * mean_x
    return intercept, slope


def linear_trend_forecast(train_years, train_values, horizons):
    intercept, slope = ols_fit(train_years, train_values)
    origin_year = train_years[-1]
    return {h: intercept + slope * (origin_year + h) for h in horizons}


def ses_level(train_values, alpha):
    """Run simple exponential smoothing over train_values; return the final level."""
    level = train_values[0]
    for y in train_values[1:]:
        level = alpha * y + (1 - alpha) * level
    return level


def ses_in_sample_sse(train_values, alpha):
    """One-step-ahead in-sample SSE for a given alpha (training data only)."""
    level = train_values[0]
    sse = 0.0
    for y in train_values[1:]:
        sse += (y - level) ** 2
        level = alpha * y + (1 - alpha) * level
    return sse


def ses_forecast(train_years, train_values, horizons):
    """Simple exponential smoothing; forecast is flat at the fitted level (no trend term).

    alpha is chosen by grid search (0.01-0.99, step 0.01) minimising one-step-ahead
    in-sample SSE on the training window only - no future/test data is used, so this
    selection step does not introduce leakage.
    """
    best_alpha, best_sse = 0.5, float("inf")
    for i in range(1, 100):
        alpha = i / 100
        sse = ses_in_sample_sse(train_values, alpha)
        if sse < best_sse:
            best_sse = sse
            best_alpha = alpha
    level = ses_level(train_values, best_alpha)
    return {h: level for h in horizons}


def holt_level_trend(train_values, alpha, beta):
    """Run Holt's linear (double exponential smoothing) recursion; return (level, trend)."""
    level = train_values[0]
    trend = train_values[1] - train_values[0] if len(train_values) > 1 else 0.0
    for y in train_values[1:]:
        new_level = alpha * y + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level, trend = new_level, new_trend
    return level, trend


def holt_in_sample_sse(train_values, alpha, beta):
    """One-step-ahead in-sample SSE for a given (alpha, beta) pair (training data only)."""
    level = train_values[0]
    trend = train_values[1] - train_values[0] if len(train_values) > 1 else 0.0
    sse = 0.0
    for y in train_values[1:]:
        sse += (y - (level + trend)) ** 2
        new_level = alpha * y + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level, trend = new_level, new_trend
    return sse


def holt_forecast(train_years, train_values, horizons):
    """Holt's linear exponential smoothing; forecast = fitted level + h * fitted trend.

    Unlike ses_forecast, this has a trend term, so it can extrapolate a slope rather
    than a flat level. (alpha, beta) are chosen by a joint grid search (0.01-0.99,
    step 0.01 each) minimising one-step-ahead in-sample SSE on the training window
    only - no leakage, same principle as ses_forecast's alpha search.
    """
    best_params, best_sse = (0.5, 0.5), float("inf")
    for ai in range(1, 100):
        alpha = ai / 100
        for bi in range(1, 100):
            beta = bi / 100
            sse = holt_in_sample_sse(train_values, alpha, beta)
            if sse < best_sse:
                best_sse = sse
                best_params = (alpha, beta)
    level, trend = holt_level_trend(train_values, *best_params)
    return {h: level + h * trend for h in horizons}


MODELS = {
    "naive": naive_forecast,
    "drift": drift_forecast,
    "linear_trend": linear_trend_forecast,
    "ses": ses_forecast,
    "holt": holt_forecast,
}


# --- Rolling-origin backtesting ----------------------------------------------


def run_backtest(years, values, models=None):
    """Leakage-free rolling-origin backtest. Returns a list of detail dicts.

    models defaults to the module-level MODELS dict (the five dependency-light
    benchmarks); callers can pass a different {name: forecast_fn} dict - e.g.
    scripts/forecast_statistical.py passes MODELS extended with statsmodels-based
    models - without duplicating this function.
    """
    if models is None:
        models = MODELS
    n = len(years)
    detail = []
    for origin_idx in range(MIN_TRAIN_YEARS - 1, n):
        train_years = years[: origin_idx + 1]
        train_values = values[: origin_idx + 1]
        origin_year = years[origin_idx]

        valid_horizons = [h for h in HORIZONS if origin_idx + h < n]
        if not valid_horizons:
            continue

        for model_name, model_fn in models.items():
            forecasts = model_fn(train_years, train_values, valid_horizons)
            for h in valid_horizons:
                target_idx = origin_idx + h
                target_year = years[target_idx]
                actual = values[target_idx]
                forecast = forecasts[h]
                error = forecast - actual
                abs_error = abs(error)
                pct_error = 100 * abs_error / abs(actual)
                detail.append(
                    {
                        "model": model_name,
                        "origin_year": origin_year,
                        "train_length": origin_idx + 1,
                        "horizon": h,
                        "target_year": target_year,
                        "actual": actual,
                        "forecast": round(forecast, 1),
                        "error": round(error, 1),
                        "abs_error": round(abs_error, 1),
                        "pct_error": round(pct_error, 3),
                    }
                )
    return detail


def summarize(detail):
    """Aggregate MAE / RMSE / MAPE / mean-error bias per model x horizon."""
    groups = {}
    for row in detail:
        key = (row["model"], row["horizon"])
        groups.setdefault(key, []).append(row)

    summary = []
    for (model, horizon), rows in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        n = len(rows)
        errors = [r["error"] for r in rows]
        abs_errors = [r["abs_error"] for r in rows]
        pct_errors = [r["pct_error"] for r in rows]
        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(e * e for e in errors) / n)
        mape = sum(pct_errors) / n
        bias = sum(errors) / n
        summary.append(
            {
                "model": model,
                "horizon_years": horizon,
                "n_origins": n,
                "first_origin_year": min(r["origin_year"] for r in rows),
                "last_origin_year": max(r["origin_year"] for r in rows),
                "mae": round(mae, 1),
                "rmse": round(rmse, 1),
                "mape_pct": round(mape, 2),
                "mean_error_bias": round(bias, 1),
            }
        )
    return summary


# --- Forward forecast (illustrative, fit on the full series) ----------------


def forward_forecast(years, values):
    """Forecast 2026-2030 with each model fit on the full 1987-2025 series."""
    rows = []
    for model_name, model_fn in MODELS.items():
        forecasts = model_fn(years, values, [y - years[-1] for y in FORWARD_YEARS])
        for target_year, h in zip(FORWARD_YEARS, [y - years[-1] for y in FORWARD_YEARS]):
            rows.append(
                {
                    "model": model_name,
                    "target_year": target_year,
                    "forecast": round(forecasts[h], 1),
                }
            )
    return rows


# --- CSV output ---------------------------------------------------------------


def write_csv(path, rows, fieldnames):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# --- Charts --------------------------------------------------------------------


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)


def make_one_step_ahead_chart(
    detail,
    years,
    values,
    models=None,
    model_colors=None,
    model_labels=None,
    title="England: actual vs. 1-year-ahead rolling-origin forecasts, 1997-2025",
    out_path=None,
):
    """Actual series with each model's 1-year-ahead rolling-origin forecast.

    models/model_colors/model_labels default to the module-level MODELS/MODEL_COLORS/
    MODEL_LABELS (the five dependency-light benchmarks); callers can pass an extended
    set - e.g. scripts/forecast_statistical.py adds statsmodels-based models - without
    duplicating this chart's drawing code.
    """
    models = models if models is not None else MODELS
    model_colors = model_colors if model_colors is not None else MODEL_COLORS
    model_labels = model_labels if model_labels is not None else MODEL_LABELS
    out_path = out_path if out_path is not None else FIGURES_DIR / "backtest_one_step_ahead.png"

    fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=SURFACE)
    style_axes(ax)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax.plot(years, values, color=INK_PRIMARY, linewidth=2, label="Actual", zorder=3)

    h1_rows = [r for r in detail if r["horizon"] == 1]
    for model_name in models:
        model_rows = sorted((r for r in h1_rows if r["model"] == model_name), key=lambda r: r["target_year"])
        xs = [r["target_year"] for r in model_rows]
        ys = [r["forecast"] for r in model_rows]
        ax.plot(
            xs,
            ys,
            color=model_colors[model_name],
            linewidth=1.4,
            linestyle="--",
            marker="o",
            markersize=3,
            label=model_labels[model_name],
            zorder=2,
        )

    ax.set_title(title, fontsize=13, color=INK_PRIMARY, loc="left", pad=12)
    ax.set_xlabel("Year", fontsize=10, color=INK_SECONDARY)
    ax.set_ylabel("Households on the register", fontsize=10, color=INK_SECONDARY)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.text(
        0.02,
        0.045,
        "Each forecast point uses only data up to the prior year (expanding training window, no leakage).",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_mape_by_horizon_chart(
    summary,
    models=None,
    model_colors=None,
    model_labels=None,
    title="England: rolling-origin backtest MAPE by forecast horizon",
    out_path=None,
):
    """Grouped bar chart of MAPE (%) by model, across the four horizons."""
    models = models if models is not None else MODELS
    model_colors = model_colors if model_colors is not None else MODEL_COLORS
    model_labels = model_labels if model_labels is not None else MODEL_LABELS
    out_path = out_path if out_path is not None else FIGURES_DIR / "backtest_mape_by_horizon.png"

    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    style_axes(ax)

    model_names = list(models)
    n_models = len(model_names)
    x = list(range(len(HORIZONS)))
    width = 0.8 / n_models
    center = (n_models - 1) / 2

    for i, model_name in enumerate(model_names):
        mapes = []
        for h in HORIZONS:
            match = [s for s in summary if s["model"] == model_name and s["horizon_years"] == h]
            mapes.append(match[0]["mape_pct"] if match else 0)
        offsets = [xi + (i - center) * width for xi in x]
        ax.bar(offsets, mapes, width=width, color=model_colors[model_name], label=model_labels[model_name], zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}-year" for h in HORIZONS])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.set_title(title, fontsize=13, color=INK_PRIMARY, loc="left", pad=12)
    ax.set_xlabel("Forecast horizon", fontsize=10, color=INK_SECONDARY)
    ax.set_ylabel("Mean absolute percentage error", fontsize=10, color=INK_SECONDARY)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# --- QA ------------------------------------------------------------------------


def run_qa(years, values, detail, summary):
    print("\n--- QA: forecast_national ---")
    print(f"England series : {years[0]}-{years[-1]} ({len(years)} years, 0 missing)")
    print(f"Min train years: {MIN_TRAIN_YEARS} (first origin = {years[MIN_TRAIN_YEARS - 1]})")
    print(f"Horizons       : {HORIZONS}")
    print(f"Backtest rows  : {len(detail)}")

    expected_rows = 0
    n = len(years)
    for origin_idx in range(MIN_TRAIN_YEARS - 1, n):
        expected_rows += len(MODELS) * len([h for h in HORIZONS if origin_idx + h < n])
    assert len(detail) == expected_rows, f"expected {expected_rows} backtest rows, got {len(detail)}"

    for model_name in MODELS:
        for h in HORIZONS:
            match = [s for s in summary if s["model"] == model_name and s["horizon_years"] == h]
            assert len(match) == 1, f"expected exactly one summary row for {model_name}/{h}y"

    print("All QA checks passed.")


# --- Main ------------------------------------------------------------------------


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    years, values = load_england_series()
    detail = run_backtest(years, values)
    summary = summarize(detail)
    forward = forward_forecast(years, values)

    write_csv(
        OUTPUTS_DIR / "backtest_predictions.csv",
        detail,
        ["model", "origin_year", "train_length", "horizon", "target_year", "actual", "forecast", "error", "abs_error", "pct_error"],
    )
    write_csv(
        OUTPUTS_DIR / "model_results.csv",
        summary,
        ["model", "horizon_years", "n_origins", "first_origin_year", "last_origin_year", "mae", "rmse", "mape_pct", "mean_error_bias"],
    )
    write_csv(
        OUTPUTS_DIR / "national_forecast_2026_2030.csv",
        forward,
        ["model", "target_year", "forecast"],
    )

    make_one_step_ahead_chart(detail, years, values)
    make_mape_by_horizon_chart(summary)

    run_qa(years, values, detail, summary)

    print("\n--- Model results summary (MAE / RMSE / MAPE by horizon) ---")
    print(f"{'model':<14}{'horizon':>8}{'n':>5}{'MAE':>12}{'RMSE':>12}{'MAPE%':>9}{'bias':>12}")
    for s in summary:
        print(
            f"{s['model']:<14}{s['horizon_years']:>7}y{s['n_origins']:>5}"
            f"{s['mae']:>12,.0f}{s['rmse']:>12,.0f}{s['mape_pct']:>9.2f}{s['mean_error_bias']:>12,.0f}"
        )

    print(
        "\nWrote outputs/backtest_predictions.csv, outputs/model_results.csv, "
        "outputs/national_forecast_2026_2030.csv"
    )
    print("Wrote outputs/figures/backtest_one_step_ahead.png, outputs/figures/backtest_mape_by_horizon.png")


if __name__ == "__main__":
    main()
