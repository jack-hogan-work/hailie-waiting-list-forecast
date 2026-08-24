#!/usr/bin/env python3
"""Week 2 regional forecasting & rolling-origin backtesting for MHCLG Live Table 600.

Extends the national forecasting work (scripts/forecast_national.py) to each of
the nine English regions individually. Reuses that script's five dependency-light
benchmark models (naive, drift, linear_trend, ses, holt) and its leakage-free
rolling-origin backtest harness (run_backtest, summarize) unchanged - nothing is
reimplemented here beyond region-specific data loading, output writing, and two
region-comparison charts. See docs/regional_forecast_methodology.md for the full
rationale and findings.

Scope note: the original session goal was national-only forecasting; this script
extends that to regional level as a deliberate, user-approved follow-on, not an
unprompted scope change.

Standard library only for data/model logic; matplotlib (project-local .venv) for
charts. Run with:

    .venv/bin/python3 scripts/forecast_regional.py
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from forecast_national import (
    HORIZONS,
    MIN_TRAIN_YEARS,
    MODEL_LABELS,
    MODELS,
    PROCESSED_PATH,
    SOURCE_CAPTION,
    INK_MUTED,
    INK_PRIMARY,
    SURFACE,
    run_backtest,
    style_axes,
    summarize,
    write_csv,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

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
REGION_CODES = {code for code, _ in REGION_ORDER}

# Blue sequential ramp (data-viz skill reference palette, light mode, steps 100-700).
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#184f95", "#0d366b"]
BLUE_CMAP = LinearSegmentedColormap.from_list("blue_seq", BLUE_RAMP)


# --- Data loading -------------------------------------------------------------


def load_all_regions():
    """Return {area_code: {"name": str, "years": [...], "values": [...]}}."""
    raw = {}
    with PROCESSED_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Area code"]
            if code not in REGION_CODES:
                continue
            year = int(row["year"])
            raw_value = row["households_on_register"]
            if raw_value == "":
                raise ValueError(f"Unexpected missing value: {code} {year}")
            raw.setdefault(code, {})[year] = int(raw_value)

    regions = {}
    for code, name in REGION_ORDER:
        series = raw[code]
        years = sorted(series)
        expected = list(range(years[0], years[-1] + 1))
        if years != expected:
            raise ValueError(f"{name} series has gaps: expected {expected}, got {years}")
        regions[code] = {"name": name, "years": years, "values": [series[y] for y in years]}
    return regions


# --- Run the (unmodified) national backtest harness per region ----------------


def run_all_regions(regions):
    """Run run_backtest()/summarize() from forecast_national.py once per region."""
    detail = []
    summary = []
    for code, name in REGION_ORDER:
        r = regions[code]
        r_detail = run_backtest(r["years"], r["values"])
        for row in r_detail:
            row = dict(row)
            row["region_code"] = code
            row["region_name"] = name
            detail.append(row)

        r_summary = summarize(r_detail)
        for row in r_summary:
            row = dict(row)
            row["region_code"] = code
            row["region_name"] = name
            summary.append(row)
    return detail, summary


# --- Charts --------------------------------------------------------------------


def make_mape_heatmap(summary):
    """Two side-by-side heatmaps (1-year, 5-year) of MAPE (%) by region x model."""
    model_names = list(MODELS)
    region_names = [name for _, name in REGION_ORDER]
    horizons_to_show = [1, 5]

    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5), facecolor=SURFACE)
    im = None
    for ax, h in zip(axes, horizons_to_show):
        matrix = []
        for code, name in REGION_ORDER:
            row_vals = []
            for m in model_names:
                match = [
                    s for s in summary if s["region_code"] == code and s["model"] == m and s["horizon_years"] == h
                ]
                row_vals.append(match[0]["mape_pct"] if match else float("nan"))
            matrix.append(row_vals)

        im = ax.imshow(matrix, cmap=BLUE_CMAP, aspect="auto")
        ax.set_xticks(range(len(model_names)))
        ax.set_xticklabels([MODEL_LABELS[m] for m in model_names], rotation=30, ha="right", fontsize=8, color=INK_PRIMARY)
        ax.set_yticks(range(len(region_names)))
        ax.set_yticklabels(region_names, fontsize=8, color=INK_PRIMARY)
        ax.set_title(f"{h}-year horizon", fontsize=11, color=INK_PRIMARY, loc="left")
        for spine in ax.spines.values():
            spine.set_visible(False)

        vmax = max(v for row in matrix for v in row)
        for i, row_vals in enumerate(matrix):
            for j, val in enumerate(row_vals):
                text_color = "white" if val > vmax * 0.6 else INK_PRIMARY
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7.5, color=text_color)

    fig.suptitle(
        "Regional rolling-origin backtest MAPE (%) by model, 1-year vs. 5-year horizon",
        fontsize=13,
        color=INK_PRIMARY,
        x=0.02,
        ha="left",
    )
    fig.subplots_adjust(left=0.16, right=0.9, top=0.87, bottom=0.2, wspace=0.5)
    cbar = fig.colorbar(im, ax=axes, shrink=0.7, pad=0.02)
    cbar.ax.tick_params(labelsize=8, colors=INK_MUTED)
    cbar.set_label("MAPE (%)", fontsize=9, color=INK_MUTED)
    fig.text(0.02, 0.02, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.savefig(FIGURES_DIR / "regional_backtest_mape_heatmap.png", dpi=150)
    plt.close(fig)


def make_win_count_chart(summary):
    """Grouped bar chart: how many of the 9 regions each model 'wins' (lowest MAPE), by horizon."""
    from forecast_national import MODEL_COLORS

    model_names = list(MODELS)
    n_models = len(model_names)
    counts = {m: [0] * len(HORIZONS) for m in model_names}

    for hi, h in enumerate(HORIZONS):
        for code, _ in REGION_ORDER:
            region_rows = [s for s in summary if s["region_code"] == code and s["horizon_years"] == h]
            best = min(region_rows, key=lambda s: s["mape_pct"])
            counts[best["model"]][hi] += 1

    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
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
            color=MODEL_COLORS[model_name],
            label=MODEL_LABELS[model_name],
            zorder=2,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([f"{h}-year" for h in HORIZONS])
    ax.set_ylim(0, 9)
    ax.set_yticks(range(0, 10))
    ax.set_title(
        "Regions where each model has the lowest MAPE, by horizon (of 9 regions)",
        fontsize=13,
        color=INK_PRIMARY,
        loc="left",
        pad=12,
    )
    ax.set_xlabel("Forecast horizon", fontsize=10, color="#52514e")
    ax.set_ylabel("Number of regions (of 9) where this model wins", fontsize=10, color="#52514e")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.text(
        0.02,
        0.045,
        "Caution: most naive vs. SES wins are decided by <0.1 MAPE points (effectively a tie); "
        "drift/Holt wins carry larger margins - see the methodology note.",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIGURES_DIR / "regional_model_win_counts.png", dpi=150)
    plt.close(fig)


# --- QA --------------------------------------------------------------------------


def run_qa(regions, detail, summary):
    print("\n--- QA: forecast_regional ---")
    print(f"Regions: {len(regions)} (expected 9)")
    assert len(regions) == 9, f"expected 9 regions, got {len(regions)}"

    for code, r in regions.items():
        assert r["years"][0] == 1987 and r["years"][-1] == 2025, f"{r['name']}: unexpected year range"
        assert len(r["years"]) == 39, f"{r['name']}: expected 39 years"

    expected_rows_per_region = 0
    n = 39
    for origin_idx in range(MIN_TRAIN_YEARS - 1, n):
        expected_rows_per_region += len(MODELS) * len([h for h in HORIZONS if origin_idx + h < n])
    expected_total = expected_rows_per_region * 9
    print(f"Backtest rows: {len(detail)} (expected {expected_total})")
    assert len(detail) == expected_total, f"expected {expected_total} rows, got {len(detail)}"

    expected_summary_rows = len(MODELS) * len(HORIZONS) * 9
    print(f"Summary rows: {len(summary)} (expected {expected_summary_rows})")
    assert len(summary) == expected_summary_rows, f"expected {expected_summary_rows} summary rows, got {len(summary)}"

    leakage = [r for r in detail if r["target_year"] <= r["origin_year"]]
    print(f"Leakage violations: {len(leakage)}")
    assert len(leakage) == 0, f"found {len(leakage)} leakage violations"

    print("All QA checks passed.")


# --- Main ------------------------------------------------------------------------


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    regions = load_all_regions()
    detail, summary = run_all_regions(regions)

    write_csv(
        OUTPUTS_DIR / "regional_backtest_predictions.csv",
        detail,
        [
            "region_code",
            "region_name",
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
        OUTPUTS_DIR / "regional_model_results.csv",
        summary,
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

    make_mape_heatmap(summary)
    make_win_count_chart(summary)

    run_qa(regions, detail, summary)

    print("\n--- 1-year MAPE by region (best model highlighted) ---")
    for code, name in REGION_ORDER:
        region_1y = [s for s in summary if s["region_code"] == code and s["horizon_years"] == 1]
        best = min(region_1y, key=lambda s: s["mape_pct"])
        print(f"{name:<28}best={MODEL_LABELS[best['model']]:<32}MAPE={best['mape_pct']:.2f}%")

    print(
        "\nWrote outputs/regional_backtest_predictions.csv, outputs/regional_model_results.csv"
    )
    print(
        "Wrote outputs/figures/regional_backtest_mape_heatmap.png, "
        "outputs/figures/regional_model_win_counts.png"
    )


if __name__ == "__main__":
    main()
