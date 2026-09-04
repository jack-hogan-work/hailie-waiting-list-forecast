#!/usr/bin/env python3
"""Create publication charts used in the HAILIE public briefing."""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "outputs" / "final"
DATA = ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
FIGURES = ROOT / "outputs" / "figures"
ENGLAND = "E92000001"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    history = read_csv(DATA)
    national = read_csv(FINAL / "national_forecast_2026_2028.csv")
    regional = read_csv(FINAL / "regional_forecast_2026_2028.csv")
    england = sorted((int(r["year"]), int(r["households_on_register"])) for r in history if r["Area code"] == ENGLAND)
    years = [year for year, _ in england if year >= 2000]
    values = [value for year, value in england if year >= 2000]
    fy = [int(r["forecast_year"]) for r in national]
    fp = [float(r["point_forecast"]) for r in national]
    fig, ax = plt.subplots(figsize=(10.5, 4.8), facecolor="white")
    ax.fill_between(fy, [float(r["lower_80"]) for r in national], [float(r["upper_80"]) for r in national], color="#afd9d4", label="80% range")
    ax.plot(years, values, color="#176d8d", linewidth=2.5, label="Published count")
    ax.plot([2025] + fy, [values[-1]] + fp, color="#16877e", linewidth=2.8, linestyle="--", label="Central forecast")
    ax.scatter([2025], [values[-1]], color="#176d8d", s=28, zorder=4)
    ax.set_title("England register counts and the 2026–2028 forecast", loc="left", fontsize=15, weight="bold", color="#102f46")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1_000_000:.1f}m"))
    ax.grid(axis="y", color="#d4dee3", linewidth=.8); ax.spines[["top", "right", "left"]].set_visible(False); ax.tick_params(colors="#526675")
    ax.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, -0.28), fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, 1)); fig.savefig(FIGURES / "public_national_forecast.png", dpi=180, bbox_inches="tight"); plt.close(fig)

    latest = {r["Region"]: int(r["households_on_register"]) for r in history if r["year"] == "2025" and r["Area code"].startswith("E12")}
    f2028_rows = {r["region"]: r for r in regional if r["forecast_year"] == "2028"}
    f2028 = {name: float(row["point_forecast"]) for name, row in f2028_rows.items()}
    names = sorted(f2028, key=f2028.get); y = list(range(len(names)))
    lower_errors = [f2028[name] - float(f2028_rows[name]["lower_80"]) for name in names]
    upper_errors = [float(f2028_rows[name]["upper_80"]) - f2028[name] for name in names]
    fig, ax = plt.subplots(figsize=(10.5, 5.8), facecolor="white")
    ax.barh([i - .18 for i in y], [latest[name] for name in names], height=.34, color="#b9cbd4", label="2025 published")
    ax.barh([i + .18 for i in y], [f2028[name] for name in names], height=.34, color="#16877e", label="2028 central forecast")
    ax.errorbar([f2028[name] for name in names], [i + .18 for i in y], xerr=[lower_errors, upper_errors], fmt="none", ecolor="#102f46", elinewidth=1.2, capsize=2.5, label="2028 80% range")
    ax.set_yticks(y, names); ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
    ax.grid(axis="x", color="#d4dee3", linewidth=.8); ax.spines[["top", "right", "left"]].set_visible(False); ax.tick_params(colors="#526675")
    ax.set_title("Regional register counts: 2025 and 2028", loc="left", fontsize=15, weight="bold", color="#102f46")
    ax.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, -0.17), fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(FIGURES / "public_regional_outlook.png", dpi=180, bbox_inches="tight"); plt.close(fig)
    print("Wrote public briefing charts")


if __name__ == "__main__":
    main()
