#!/usr/bin/env python3
"""Week 1 national/regional exploratory analysis for MHCLG Live Table 600.

Reads data/processed/regional_waiting_lists_long.csv (produced by
scripts/prepare_data.py) with the standard-library csv module, prints
summary statistics used in docs/initial_eda_findings.md, and generates four
charts under outputs/figures/. Does not forecast, does not alter the
processed or raw data, and does not make causal claims.

Requires matplotlib (installed only in the project-local .venv, not
globally). Run with:

    .venv/bin/python3 scripts/explore_national.py
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
FIGURES_DIR = REPO_ROOT / "outputs" / "figures"

ENGLAND_AREA_CODE = "E92000001"
SOURCE_CAPTION = (
    "Source: MHCLG Live Table 600, Regional Data worksheet, retrieved 7 Aug 2026. "
    "Households on the register at 1 April each year, 1987–2025."
)

# --- Palette (data-viz skill reference palette, light mode) ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"   # categorical slot 1 / sequential hue
RED = "#e34948"    # categorical slot 8 / diverging pole

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


def load_regional_data():
    """Return {area_code: {"name": str, "series": {year: value}}}."""
    data = {}
    with PROCESSED_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["Area code"]
            year = int(row["year"])
            raw_value = row["households_on_register"]
            value = int(raw_value) if raw_value != "" else None
            if code not in data:
                data[code] = {"name": row["Region"], "series": {}}
            data[code]["series"][year] = value
    return data


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))


def line_chart(years, values, title, ylabel, out_path, xlabel="Year (as at 1 April)"):
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    style_axes(ax)
    ax.plot(years, values, color=BLUE, linewidth=2, solid_joinstyle="round", solid_capstyle="round")
    ax.scatter([years[-1]], [values[-1]], s=28, color=BLUE, zorder=3, edgecolors=SURFACE, linewidths=1.5)
    ax.annotate(
        f"{values[-1]:,.0f}",
        xy=(years[-1], values[-1]),
        xytext=(6, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        color=INK_PRIMARY,
    )
    ax.set_title(title, fontsize=13, color=INK_PRIMARY, loc="left", pad=12)
    ax.set_xlabel(xlabel, fontsize=10, color=INK_SECONDARY)
    ax.set_ylabel(ylabel, fontsize=10, color=INK_SECONDARY)
    fig.text(0.02, 0.01, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_england_full_chart(england_series):
    years = sorted(england_series)
    values = [england_series[y] for y in years]
    line_chart(
        years,
        values,
        "England social housing waiting list: households on local authority registers, 1987–2025",
        "Households on the register",
        FIGURES_DIR / "england_waiting_list_1987_2025.png",
    )


def make_england_recent_chart(england_series):
    years = sorted(y for y in england_series if 2010 <= y <= 2025)
    values = [england_series[y] for y in years]
    line_chart(
        years,
        values,
        "England social housing waiting list: households on local authority registers, 2010–2025",
        "Households on the register",
        FIGURES_DIR / "england_waiting_list_2010_2025.png",
    )


def make_regional_small_multiples(regional_data):
    fig, axes = plt.subplots(3, 3, figsize=(13, 10), facecolor=SURFACE, sharex=True)
    fig.suptitle(
        "Social housing waiting list: households on local authority registers by English region, 1987–2025",
        fontsize=14,
        color=INK_PRIMARY,
        x=0.02,
        ha="left",
    )
    for ax, (code, name) in zip(axes.flat, REGION_ORDER):
        series = regional_data[code]["series"]
        years = sorted(series)
        values = [series[y] for y in years]
        style_axes(ax)
        ax.plot(years, values, color=BLUE, linewidth=1.6)
        ax.set_title(name, fontsize=10, color=INK_PRIMARY, loc="left")
        ax.set_xlim(1987, 2025)
        ax.set_xticks([1987, 2000, 2010, 2025])
        ax.tick_params(labelsize=7.5)

    fig.text(
        0.02,
        0.955,
        "Note: each panel has its own y-axis scale (households on the register) — magnitudes are not comparable across panels at a glance; read the axis ticks. England total excluded.",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.text(0.02, 0.005, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.93))
    fig.savefig(FIGURES_DIR / "regional_waiting_list_trends.png", dpi=150)
    plt.close(fig)


def make_pct_change_chart(england_series):
    years = sorted(england_series)
    pct_changes = []
    change_years = []
    for prev_y, y in zip(years, years[1:]):
        prev_v, v = england_series[prev_y], england_series[y]
        pct_changes.append(100 * (v - prev_v) / prev_v)
        change_years.append(y)

    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor=SURFACE)
    style_axes(ax)
    colors = [BLUE if c >= 0 else RED for c in pct_changes]
    ax.bar(change_years, pct_changes, color=colors, width=0.7, zorder=2)
    ax.axhline(0, color=BASELINE, linewidth=1)
    ax.set_title(
        "England: year-on-year percentage change in households on the register, 1988–2025",
        fontsize=13,
        color=INK_PRIMARY,
        loc="left",
        pad=12,
    )
    ax.set_xlabel("Year (change from previous year, as at 1 April)", fontsize=10, color=INK_SECONDARY)
    ax.set_ylabel("Year-on-year change (%)", fontsize=10, color=INK_SECONDARY)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    fig.text(0.02, 0.045, SOURCE_CAPTION, fontsize=8, color=INK_MUTED)
    fig.text(
        0.02,
        0.005,
        "Register counts can move for administrative reasons (e.g. list reviews) as well as changing demand — see data/README.md.",
        fontsize=8,
        color=INK_MUTED,
    )
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIGURES_DIR / "england_annual_percentage_change.png", dpi=150)
    plt.close(fig)
    return change_years, pct_changes


def print_summary_stats(regional_data):
    england_series = regional_data[ENGLAND_AREA_CODE]["series"]
    years = sorted(england_series)

    print("\n--- England total: headline stats ---")
    v1987, v2025 = england_series[1987], england_series[2025]
    print(f"1987 value: {v1987:,}")
    print(f"2025 value: {v2025:,}")
    print(f"Change 1987-2025: {v2025 - v1987:,} ({100*(v2025-v1987)/v1987:.1f}%)")

    peak_year = max(years, key=lambda y: england_series[y])
    trough_year = min(years, key=lambda y: england_series[y])
    print(f"Peak: {peak_year} = {england_series[peak_year]:,}")
    print(f"Trough: {trough_year} = {england_series[trough_year]:,}")

    v2020, v2024 = england_series[2020], england_series[2024]
    print(f"2020 value: {v2020:,}")
    print(f"2024 value: {v2024:,}")
    print(f"Change 2020-2025: {v2025 - v2020:,} ({100*(v2025-v2020)/v2020:.1f}%)")

    change_years, pct_changes = [], []
    for prev_y, y in zip(years, years[1:]):
        prev_v, v = england_series[prev_y], england_series[y]
        change_years.append(y)
        pct_changes.append(100 * (v - prev_v) / prev_v)

    max_idx = max(range(len(pct_changes)), key=lambda i: pct_changes[i])
    min_idx = min(range(len(pct_changes)), key=lambda i: pct_changes[i])
    print(f"Largest YoY increase: {change_years[max_idx]} = {pct_changes[max_idx]:+.1f}%")
    print(f"Largest YoY decrease: {change_years[min_idx]} = {pct_changes[min_idx]:+.1f}%")

    n_up = sum(1 for c in pct_changes if c > 0)
    n_down = sum(1 for c in pct_changes if c < 0)
    print(f"Years with YoY increase: {n_up}, decrease: {n_down}, flat: {len(pct_changes)-n_up-n_down}")

    print("\n--- Regions: 2025 snapshot (England total excluded) ---")
    region_2025 = {name: regional_data[code]["series"][2025] for code, name in REGION_ORDER}
    for name, v in sorted(region_2025.items(), key=lambda kv: -kv[1]):
        print(f"{name}: {v:,}")
    total_regions_2025 = sum(region_2025.values())
    print(f"Sum of 9 regions, 2025: {total_regions_2025:,} (England total row, 2025: {v2025:,})")

    print("\n--- Regions: change 1987-2025 (England total excluded) ---")
    for code, name in REGION_ORDER:
        series = regional_data[code]["series"]
        v87, v25 = series[1987], series[2025]
        print(f"{name}: {v87:,} -> {v25:,} ({100*(v25-v87)/v87:+.1f}%)")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    regional_data = load_regional_data()
    england_series = regional_data[ENGLAND_AREA_CODE]["series"]

    make_england_full_chart(england_series)
    make_england_recent_chart(england_series)
    make_regional_small_multiples(regional_data)
    make_pct_change_chart(england_series)

    print("Wrote charts to", FIGURES_DIR.relative_to(REPO_ROOT))
    print_summary_stats(regional_data)


if __name__ == "__main__":
    main()
