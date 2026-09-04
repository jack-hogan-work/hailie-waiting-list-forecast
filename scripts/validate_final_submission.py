#!/usr/bin/env python3
"""Fail-fast QA checks for the final HAILIE repository and report."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "outputs" / "final"


def rows(filename: str) -> list[dict[str, str]]:
    with (FINAL / filename).open(encoding="utf-8", newline="") as input_file:
        return list(csv.DictReader(input_file))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def unique(records: list[dict[str, str]], fields: tuple[str, ...], label: str) -> None:
    keys = [tuple(row[field] for field in fields) for row in records]
    require(len(keys) == len(set(keys)), f"Duplicate composite key in {label}: {fields}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_intervals(records: list[dict[str, str]], label: str) -> None:
    for row in records:
        numbers = [float(row[name]) for name in ["lower_95", "lower_80", "point_forecast", "upper_80", "upper_95"]]
        require(all(math.isfinite(value) for value in numbers), f"Non-finite value in {label}")
        require(numbers == sorted(numbers), f"Unordered interval in {label}: {row}")
        require(float(row["point_forecast"]) >= 0, f"Negative point forecast in {label}: {row}")


def main() -> None:
    expected_counts = {
        "national_model_metrics.csv": 28,
        "national_model_selection.csv": 2,
        "national_forecast_2026_2028.csv": 3,
        "national_extension_2026_2030.csv": 5,
        "national_history_sensitivity.csv": 56,
        "regional_model_metrics.csv": 252,
        "regional_model_selection.csv": 9,
        "regional_forecast_2026_2028.csv": 27,
        "regional_extension_2026_2030.csv": 45,
    }
    loaded = {}
    for filename, expected in expected_counts.items():
        loaded[filename] = rows(filename)
        require(len(loaded[filename]) == expected, f"{filename}: expected {expected} rows")

    unique(loaded["national_model_metrics.csv"], ("model", "horizon_years"), "national metrics")
    unique(loaded["national_history_sensitivity.csv"], ("history_start_year", "model", "horizon_years"), "history sensitivity")
    unique(loaded["regional_model_metrics.csv"], ("area_code", "model", "horizon_years"), "regional metrics")
    unique(loaded["regional_model_selection.csv"], ("area_code",), "regional selections")
    unique(loaded["regional_forecast_2026_2028.csv"], ("area_code", "forecast_year"), "regional forecasts")

    origin_counts = {"1": "29", "2": "28", "3": "27", "5": "25"}
    for filename in ["national_model_metrics.csv", "regional_model_metrics.csv"]:
        for row in loaded[filename]:
            require(
                row["forecast_origins"] == origin_counts[row["horizon_years"]],
                f"Unexpected origin count in {filename}: {row}",
            )

    national_selection = {row["forecast_role"]: row["selected_model"] for row in loaded["national_model_selection.csv"]}
    require(national_selection == {"primary_2026_2028": "damped_trend", "extension_2026_2030": "naive"}, "National selections changed")
    expected_primary = {
        "East Midlands": "arima", "East of England": "naive", "London": "naive",
        "North East": "naive", "North West": "naive", "South East": "damped_trend",
        "South West": "drift", "West Midlands": "naive", "Yorkshire and The Humber": "naive",
    }
    actual_primary = {row["region"]: row["primary_model"] for row in loaded["regional_model_selection.csv"]}
    require(actual_primary == expected_primary, "Regional primary selections changed")

    national_points = [round(float(row["point_forecast"])) for row in loaded["national_forecast_2026_2028.csv"]]
    require(national_points == [1348467, 1354819, 1359901], f"National forecast regression failed: {national_points}")
    check_intervals(loaded["national_forecast_2026_2028.csv"], "national primary")
    check_intervals(loaded["national_extension_2026_2030.csv"], "national extension")
    check_intervals(loaded["regional_forecast_2026_2028.csv"], "regional primary")

    with (ROOT / "data" / "processed" / "regional_waiting_lists_long.csv").open(encoding="utf-8", newline="") as input_file:
        data_rows = list(csv.DictReader(input_file))
    for year in range(1987, 2026):
        current = [row for row in data_rows if int(row["year"]) == year]
        england = int(next(row["households_on_register"] for row in current if row["Area code"] == "E92000001"))
        regional_sum = sum(int(row["households_on_register"]) for row in current if row["Area code"].startswith("E12"))
        require(england == regional_sum, f"Regional reconciliation failed in {year}")

    manifest_path = FINAL / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_paths = {
        "raw_source": ROOT / "data" / "raw" / "Live_Table_600.ods",
        "processed_regional_series": ROOT / "data" / "processed" / "regional_waiting_lists_long.csv",
        "national_model_code": ROOT / "scripts" / "forecast_national_final.py",
        "regional_model_code": ROOT / "scripts" / "forecast_regional_final.py",
        "output_generator_code": ROOT / "scripts" / "generate_final_outputs.py",
    }
    for name, path in manifest_paths.items():
        require(manifest["sha256"][name] == sha256(path), f"Manifest hash mismatch: {name}")

    report = (ROOT / "outputs" / "HAILIE_final_report.html").read_text(encoding="utf-8")
    for phrase in [
        "Final analytical submission", "England social housing waiting-list forecast",
        "separate housing-association waiting list", "1,359,901", "mean Y1–Y3 MAE",
        "José’s concerns", "Scoped out", "Sensitivity to history and policy breaks",
    ]:
        require(phrase in report, f"Final report is missing: {phrase}")
    require("Illustrative 2026" not in report, "Archived report language remains")
    require("<html lang=\"en\">" in report and "Skip to main content" in report, "Accessibility shell missing")
    require(not (ROOT / "data" / "raw" / "~$Live_Table_600.ods").exists(), "Office lock file remains")

    print("Final output schemas and row counts: PASS")
    print("Model selections and forecast regression checks: PASS")
    print("Prediction interval ordering and finite values: PASS")
    print("Regional-to-national reconciliation (39 years): PASS")
    print("Reproducibility manifest hashes: PASS")
    print("Final report content and accessibility shell: PASS")
    print("FINAL SUBMISSION QA: PASS")


if __name__ == "__main__":
    main()
