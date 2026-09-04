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
    require(sum(model == "naive" for model in actual_primary.values()) == 6, "Expected six naive regional primary models")

    national_points = [round(float(row["point_forecast"])) for row in loaded["national_forecast_2026_2028.csv"]]
    require(national_points == [1348467, 1354819, 1359901], f"National forecast regression failed: {national_points}")
    sensitivity_order = ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]
    expected_sensitivity = {
        "1998": {"damped_mae": 134013, "damped_rank": 3, "naive_mae": 120905},
        "2005": {"damped_mae": 108166, "damped_rank": 5, "naive_mae": 73809},
    }
    for start_year, expected in expected_sensitivity.items():
        records = [
            row for row in loaded["national_history_sensitivity.csv"]
            if row["history_start_year"] == start_year
        ]
        scores = {
            model: sum(
                float(row["mae_households"])
                for row in records
                if row["model"] == model and row["horizon_years"] in {"1", "2", "3"}
            )
            / 3
            for model in sensitivity_order
        }
        ranking = sorted(
            sensitivity_order,
            key=lambda model: (scores[model], sensitivity_order.index(model)),
        )
        require(round(scores["damped_trend"]) == expected["damped_mae"], f"Damped-Holt MAE changed for {start_year}")
        require(ranking.index("damped_trend") + 1 == expected["damped_rank"], f"Damped-Holt rank changed for {start_year}")
        require(round(scores["naive"]) == expected["naive_mae"], f"Naive MAE changed for {start_year}")
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
        "HAILIE · Evidence report", "England social housing waiting-list forecast",
        "Separate housing-association waiting lists", "1,359,901", "mean Y1–Y3 MAE",
        "Limitations", "History-window sensitivity",
        "does not identify a robust national increase or decrease",
        "134,013", "3 of 7", "108,166", "5 of 7",
        "95% diagnostic-range warning", "only 27 errors",
        "not stable 95% probability limits",
        "regional backtests do not support a strong directional call",
        "property of the model, not evidence that the register count will remain unchanged",
        "2028 80% range", "likely to overstate households still requiring social housing",
        "Reference dates", "Telford &amp; Wrekin", "Epping Forest",
        "effectively equivalent baselines", "no formal Diebold–Mariano",
    ]:
        require(phrase in report, f"Final report is missing: {phrase}")
    require("Illustrative 2026" not in report, "Archived report language remains")
    require('<th scope="col">Direction</th>' not in report, "Regional report still presents a direction column")
    for private_phrase in ["internal review matrix", "named reviewer", "unfinished work register"]:
        require(private_phrase not in report, f"Public report contains internal wording: {private_phrase}")
    require("<html lang=\"en\">" in report and "Skip to main content" in report, "Accessibility shell missing")
    require('alt="Line chart of England households' in report and 'alt="Small-multiple line charts' in report, "Report chart alt text missing")
    require("#9a6a00" in report, "Report focus indicator contrast token missing")
    dashboard = (ROOT / "outputs" / "HAILIE_dashboard.html").read_text(encoding="utf-8")
    for phrase in [
        "Interactive forecast dashboard", "Where could waiting lists be heading?",
        "Regional picture", "2026–2030 planning",
        "does not identify a robust national increase or decrease",
        "National history-window sensitivity",
        "Shading shows the empirical 80% range",
        "Six of nine regions use a naive model",
        "model properties, not evidence of stability",
        "2028 80% range", "Source-noted breaks include Telford", "publisher says the total is likely to overstate",
    ]:
        require(phrase in dashboard, f"Dashboard is missing: {phrase}")
    for private_phrase in ["internal review matrix", "named reviewer", "unfinished work register"]:
        require(private_phrase not in dashboard, f"Dashboard contains internal wording: {private_phrase}")
    require("lower95" not in dashboard and "upper95" not in dashboard, "Dashboard still embeds 95% bounds")
    require("<th>95% range</th>" not in dashboard, "Dashboard still publishes a 95% range column")
    require("<th>Change</th>" not in dashboard, "Regional dashboard still presents an unsupported change column")
    require('aria-pressed="true"' in dashboard and 'aria-live="polite"' in dashboard, "Dashboard state accessibility attributes missing")
    require('scope="col"' in dashboard and 'aria-hidden="true"' not in dashboard, "Dashboard table/legend accessibility attributes missing")
    require("#9a6a00" in dashboard and "--teal:#0d6f68" in dashboard, "Dashboard contrast tokens missing")
    require("No uncertainty was computed for these regional extension points" in dashboard, "Dashboard regional extension warning missing")
    public_chart_builder = (ROOT / "scripts" / "build_public_charts.py").read_text(encoding="utf-8")
    require("lower_95" not in public_chart_builder and "upper_95" not in public_chart_builder, "Public chart still draws 95% bounds")
    briefing_builder = (ROOT / "scripts" / "build_public_briefing.py").read_text(encoding="utf-8")
    require("lower_95" not in briefing_builder and "upper_95" not in briefing_builder, "Public briefing still publishes 95% bounds")
    require("regional_model_selection.csv" in briefing_builder, "Briefing regional table is missing model selections")
    require("row['lower_80']" in briefing_builder and "row['upper_80']" in briefing_builder, "Briefing regional table is missing 80% ranges")
    require("Regional backtests do not support a strong directional call" in briefing_builder, "Briefing regional caveat is missing")
    require("Most regions are broadly stable" not in briefing_builder, "Briefing still presents regional stability as a finding")
    require("xerr=[lower_errors, upper_errors]" in public_chart_builder, "Regional chart is missing 80% error bars")
    briefing = ROOT / "outputs" / "pdf" / "HAILIE_social_housing_waiting_list_briefing.pdf"
    require(briefing.exists() and briefing.stat().st_size > 100_000, "Public briefing PDF is missing or unexpectedly small")
    require(not (ROOT / "data" / "raw" / "~$Live_Table_600.ods").exists(), "Office lock file remains")

    print("Final output schemas and row counts: PASS")
    print("Model selections and forecast regression checks: PASS")
    print("National history-window sensitivity regression checks: PASS")
    print("Public 80%-only uncertainty presentation checks: PASS")
    print("Regional carry-forward wording and 80% range checks: PASS")
    print("Prediction interval ordering and finite values: PASS")
    print("Regional-to-national reconciliation (39 years): PASS")
    print("Reproducibility manifest hashes: PASS")
    print("Report language, skip link and chart accessibility checks: PASS")
    print("FINAL PUBLICATION QA: PASS")


if __name__ == "__main__":
    main()
