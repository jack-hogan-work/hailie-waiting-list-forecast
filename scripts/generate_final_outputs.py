#!/usr/bin/env python3
"""Generate the authoritative final forecast outputs used by the report.

This script deliberately imports the reviewed national and regional modelling
implementations rather than re-implementing their forecasting methods.  It
turns their in-memory results into stable CSV files so the report never has to
read the archived exploratory outputs.
"""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
from pathlib import Path
import platform
import warnings

import forecast_national_final as national
import forecast_regional_final as regional
import statsmodels
from statsmodels.tools.sm_exceptions import ConvergenceWarning


REPO_ROOT = Path(__file__).resolve().parent.parent
FINAL_OUTPUTS_DIR = REPO_ROOT / "outputs" / "final"

MODEL_ORDER = [
    "naive",
    "drift",
    "linear_trend",
    "ses",
    "holt",
    "damped_trend",
    "arima",
]

MODEL_LABELS = {
    "naive": "Naive",
    "drift": "Drift",
    "linear_trend": "Linear trend",
    "ses": "Simple exponential smoothing",
    "holt": "Holt linear trend",
    "damped_trend": "Damped Holt trend",
    "arima": "ARIMA",
}

NATIONAL_MODELS = {
    "naive": national.forecast_naive,
    "drift": national.forecast_drift,
    "linear_trend": national.forecast_linear_trend,
    "ses": national.forecast_ses,
    "holt": national.forecast_holt,
    "damped_trend": national.forecast_damped_trend,
    "arima": national.forecast_arima,
}

REGIONAL_MODELS = {
    "naive": regional.forecast_naive,
    "drift": regional.forecast_drift,
    "linear_trend": regional.forecast_linear_trend,
    "ses": regional.forecast_ses,
    "holt": regional.forecast_holt,
    "damped_trend": regional.forecast_damped_trend,
    "arima": regional.forecast_arima,
}


def write_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> None:
    path = FINAL_OUTPUTS_DIR / filename
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path.relative_to(REPO_ROOT)} ({len(rows)} rows)")


def serialise_number(value: float) -> str:
    return f"{float(value):.6f}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_model(metric_by_model: dict[str, float]) -> str:
    """Choose the lowest metric, using parsimony order for exact ties."""
    return min(MODEL_ORDER, key=lambda model: (metric_by_model[model], MODEL_ORDER.index(model)))


def generate_national_outputs(check_regression: bool = False) -> None:
    years, values = national.load_england_series()
    national.validate_england_series(years, values)

    backtests = {}
    metric_rows = []
    metrics_by_model_horizon = {}

    for model_name, forecast_function in NATIONAL_MODELS.items():
        for horizon in [1, 2, 3, 5]:
            results = national.backtest_model(years, values, forecast_function, horizon)
            metrics = national.calculate_metrics(results)
            backtests[(model_name, horizon)] = results
            metrics_by_model_horizon[(model_name, horizon)] = metrics
            metric_rows.append(
                {
                    "geography": "England",
                    "area_code": "E92000001",
                    "model": model_name,
                    "model_label": MODEL_LABELS[model_name],
                    "horizon_years": horizon,
                    "forecast_origins": len(results),
                    "mae_households": serialise_number(metrics["MAE"]),
                    "rmse_households": serialise_number(metrics["RMSE"]),
                    "mape_pct": serialise_number(metrics["MAPE"]),
                    "bias_households": serialise_number(metrics["Bias"]),
                }
            )

    primary_scores = {
        model_name: sum(metrics_by_model_horizon[(model_name, horizon)]["MAE"] for horizon in [1, 2, 3]) / 3
        for model_name in MODEL_ORDER
    }
    extension_scores = {
        model_name: metrics_by_model_horizon[(model_name, 5)]["MAE"] for model_name in MODEL_ORDER
    }
    primary_model = choose_model(primary_scores)
    extension_model = choose_model(extension_scores)

    if check_regression and (primary_model != "damped_trend" or extension_model != "naive"):
        raise AssertionError(
            "National model selection differs from the published run: "
            f"primary={primary_model}, extension={extension_model}"
        )

    selection_rows = [
        {
            "geography": "England",
            "area_code": "E92000001",
            "forecast_role": "primary_2026_2028",
            "selected_model": primary_model,
            "selected_model_label": MODEL_LABELS[primary_model],
            "selection_metric": "mean_mae_y1_y3",
            "selection_score_households": serialise_number(primary_scores[primary_model]),
            "selection_note": "Lowest mean MAE across the 1-, 2- and 3-year backtests",
        },
        {
            "geography": "England",
            "area_code": "E92000001",
            "forecast_role": "extension_2026_2030",
            "selected_model": extension_model,
            "selected_model_label": MODEL_LABELS[extension_model],
            "selection_metric": "mae_y5",
            "selection_score_households": serialise_number(extension_scores[extension_model]),
            "selection_note": "Lowest 5-year MAE; parsimonious model used where performance ties",
        },
    ]

    primary_forecasts = NATIONAL_MODELS[primary_model](values, 3)
    primary_rows = []
    for horizon, (year, point_forecast) in enumerate(zip(range(2026, 2029), primary_forecasts), start=1):
        results = backtests[(primary_model, horizon)]
        lower_80, upper_80 = national.empirical_prediction_interval(results, point_forecast, 0.80)
        lower_95, upper_95 = national.empirical_prediction_interval(results, point_forecast, 0.95)
        primary_rows.append(
            {
                "geography": "England",
                "area_code": "E92000001",
                "forecast_year": year,
                "horizon_years": horizon,
                "selected_model": primary_model,
                "selected_model_label": MODEL_LABELS[primary_model],
                "point_forecast": serialise_number(point_forecast),
                "lower_80": serialise_number(lower_80),
                "upper_80": serialise_number(upper_80),
                "lower_95": serialise_number(lower_95),
                "upper_95": serialise_number(upper_95),
            }
        )

    extension_forecasts = NATIONAL_MODELS[extension_model](values, 5)
    extension_rows = []
    for horizon, (year, point_forecast) in enumerate(zip(range(2026, 2031), extension_forecasts), start=1):
        results = national.backtest_model(years, values, NATIONAL_MODELS[extension_model], horizon)
        lower_80, upper_80 = national.empirical_prediction_interval(results, point_forecast, 0.80)
        lower_95, upper_95 = national.empirical_prediction_interval(results, point_forecast, 0.95)
        extension_rows.append(
            {
                "geography": "England",
                "area_code": "E92000001",
                "forecast_year": year,
                "horizon_years": horizon,
                "selected_model": extension_model,
                "selected_model_label": MODEL_LABELS[extension_model],
                "point_forecast": serialise_number(point_forecast),
                "lower_80": serialise_number(lower_80),
                "upper_80": serialise_number(upper_80),
                "lower_95": serialise_number(lower_95),
                "upper_95": serialise_number(upper_95),
            }
        )

    write_csv(
        "national_model_metrics.csv",
        [
            "geography",
            "area_code",
            "model",
            "model_label",
            "horizon_years",
            "forecast_origins",
            "mae_households",
            "rmse_households",
            "mape_pct",
            "bias_households",
        ],
        metric_rows,
    )
    write_csv(
        "national_model_selection.csv",
        [
            "geography",
            "area_code",
            "forecast_role",
            "selected_model",
            "selected_model_label",
            "selection_metric",
            "selection_score_households",
            "selection_note",
        ],
        selection_rows,
    )
    forecast_fields = [
        "geography",
        "area_code",
        "forecast_year",
        "horizon_years",
        "selected_model",
        "selected_model_label",
        "point_forecast",
        "lower_80",
        "upper_80",
        "lower_95",
        "upper_95",
    ]
    write_csv("national_forecast_2026_2028.csv", forecast_fields, primary_rows)
    write_csv("national_extension_2026_2030.csv", forecast_fields, extension_rows)


def generate_regional_outputs(check_regression: bool = False) -> None:
    regions = regional.load_regional_series()
    regional.validate_regional_series(regions)

    metric_rows = []
    selection_rows = []
    primary_rows = []
    extension_rows = []

    for area_code, region_data in sorted(regions.items(), key=lambda item: item[1]["name"]):
        years = region_data["years"]
        values = region_data["values"]
        metrics_by_model_horizon = {}
        backtests = {}

        for model_name, forecast_function in REGIONAL_MODELS.items():
            for horizon in [1, 2, 3, 5]:
                results = regional.backtest_model(years, values, forecast_function, horizon)
                metrics = regional.calculate_metrics(results)
                backtests[(model_name, horizon)] = results
                metrics_by_model_horizon[(model_name, horizon)] = metrics
                metric_rows.append(
                    {
                        "region": region_data["name"],
                        "area_code": area_code,
                        "model": model_name,
                        "model_label": MODEL_LABELS[model_name],
                        "horizon_years": horizon,
                        "forecast_origins": len(results),
                        "mae_households": serialise_number(metrics["MAE"]),
                        "rmse_households": serialise_number(metrics["RMSE"]),
                        "mape_pct": serialise_number(metrics["MAPE"]),
                        "bias_households": serialise_number(metrics["Bias"]),
                    }
                )

        primary_scores = {
            model_name: sum(
                metrics_by_model_horizon[(model_name, horizon)]["MAE"] for horizon in [1, 2, 3]
            )
            / 3
            for model_name in MODEL_ORDER
        }
        extension_scores = {
            model_name: metrics_by_model_horizon[(model_name, 5)]["MAE"] for model_name in MODEL_ORDER
        }
        primary_model = choose_model(primary_scores)
        extension_model = choose_model(extension_scores)

        selection_rows.append(
            {
                "region": region_data["name"],
                "area_code": area_code,
                "primary_model": primary_model,
                "primary_model_label": MODEL_LABELS[primary_model],
                "mean_y1_y3_mae_households": serialise_number(primary_scores[primary_model]),
                "extension_model": extension_model,
                "extension_model_label": MODEL_LABELS[extension_model],
                "y5_mae_households": serialise_number(extension_scores[extension_model]),
            }
        )

        primary_forecasts = REGIONAL_MODELS[primary_model](values, 3)
        for horizon, (year, point_forecast) in enumerate(zip(range(2026, 2029), primary_forecasts), start=1):
            results = backtests[(primary_model, horizon)]
            lower_80, upper_80 = regional.empirical_prediction_interval(results, point_forecast, 0.80)
            lower_95, upper_95 = regional.empirical_prediction_interval(results, point_forecast, 0.95)
            primary_rows.append(
                {
                    "region": region_data["name"],
                    "area_code": area_code,
                    "forecast_year": year,
                    "horizon_years": horizon,
                    "selected_model": primary_model,
                    "selected_model_label": MODEL_LABELS[primary_model],
                    "point_forecast": serialise_number(point_forecast),
                    "lower_80": serialise_number(lower_80),
                    "upper_80": serialise_number(upper_80),
                    "lower_95": serialise_number(lower_95),
                    "upper_95": serialise_number(upper_95),
                }
            )

        extension_forecasts = REGIONAL_MODELS[extension_model](values, 5)
        for horizon, (year, point_forecast) in enumerate(zip(range(2026, 2031), extension_forecasts), start=1):
            extension_rows.append(
                {
                    "region": region_data["name"],
                    "area_code": area_code,
                    "forecast_year": year,
                    "horizon_years": horizon,
                    "selected_model": extension_model,
                    "selected_model_label": MODEL_LABELS[extension_model],
                    "point_forecast": serialise_number(point_forecast),
                }
            )

    expected_primary_models = {
        "East Midlands": "arima",
        "East of England": "naive",
        "London": "naive",
        "North East": "naive",
        "North West": "naive",
        "South East": "damped_trend",
        "South West": "drift",
        "West Midlands": "naive",
        "Yorkshire and The Humber": "naive",
    }
    expected_extension_models = {
        "East Midlands": "naive",
        "East of England": "naive",
        "London": "naive",
        "North East": "arima",
        "North West": "naive",
        "South East": "damped_trend",
        "South West": "drift",
        "West Midlands": "naive",
        "Yorkshire and The Humber": "naive",
    }
    actual_primary_models = {row["region"]: row["primary_model"] for row in selection_rows}
    actual_extension_models = {row["region"]: row["extension_model"] for row in selection_rows}
    if check_regression and actual_primary_models != expected_primary_models:
        raise AssertionError(f"Regional primary selections differ from the published run: {actual_primary_models}")
    if check_regression and actual_extension_models != expected_extension_models:
        raise AssertionError(f"Regional extension selections differ from the published run: {actual_extension_models}")

    metric_fields = [
        "region",
        "area_code",
        "model",
        "model_label",
        "horizon_years",
        "forecast_origins",
        "mae_households",
        "rmse_households",
        "mape_pct",
        "bias_households",
    ]
    write_csv("regional_model_metrics.csv", metric_fields, metric_rows)
    write_csv(
        "regional_model_selection.csv",
        [
            "region",
            "area_code",
            "primary_model",
            "primary_model_label",
            "mean_y1_y3_mae_households",
            "extension_model",
            "extension_model_label",
            "y5_mae_households",
        ],
        selection_rows,
    )
    primary_fields = [
        "region",
        "area_code",
        "forecast_year",
        "horizon_years",
        "selected_model",
        "selected_model_label",
        "point_forecast",
        "lower_80",
        "upper_80",
        "lower_95",
        "upper_95",
    ]
    write_csv("regional_forecast_2026_2028.csv", primary_fields, primary_rows)
    write_csv(
        "regional_extension_2026_2030.csv",
        [
            "region",
            "area_code",
            "forecast_year",
            "horizon_years",
            "selected_model",
            "selected_model_label",
            "point_forecast",
        ],
        extension_rows,
    )


def generate_history_sensitivity() -> None:
    """Re-run national selection after excluding the earliest history."""
    all_years, all_values = national.load_england_series()
    output_rows = []

    for first_year in [1998, 2005]:
        start_index = all_years.index(first_year)
        years = all_years[start_index:]
        values = all_values[start_index:]

        for model_name, forecast_function in NATIONAL_MODELS.items():
            for horizon in [1, 2, 3, 5]:
                results = []
                for origin_index in range(national.MIN_TRAIN_YEARS - 1, len(years) - horizon):
                    prediction = forecast_function(values[: origin_index + 1], horizon)[horizon - 1]
                    actual = values[origin_index + horizon]
                    results.append(
                        {
                            "origin": years[origin_index],
                            "target_year": years[origin_index + horizon],
                            "actual": actual,
                            "forecast": prediction,
                            "error": prediction - actual,
                        }
                    )
                metrics = national.calculate_metrics(results)
                output_rows.append(
                    {
                        "history_start_year": first_year,
                        "model": model_name,
                        "model_label": MODEL_LABELS[model_name],
                        "horizon_years": horizon,
                        "forecast_origins": len(results),
                        "mae_households": serialise_number(metrics["MAE"]),
                        "rmse_households": serialise_number(metrics["RMSE"]),
                        "mape_pct": serialise_number(metrics["MAPE"]),
                        "bias_households": serialise_number(metrics["Bias"]),
                    }
                )

    write_csv(
        "national_history_sensitivity.csv",
        [
            "history_start_year",
            "model",
            "model_label",
            "horizon_years",
            "forecast_origins",
            "mae_households",
            "rmse_households",
            "mape_pct",
            "bias_households",
        ],
        output_rows,
    )


def write_manifest() -> None:
    tracked_inputs = {
        "raw_source": REPO_ROOT / "data" / "raw" / "Live_Table_600.ods",
        "processed_regional_series": REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv",
        "national_model_code": REPO_ROOT / "scripts" / "forecast_national_final.py",
        "regional_model_code": REPO_ROOT / "scripts" / "forecast_regional_final.py",
        "output_generator_code": Path(__file__).resolve(),
    }
    manifest = {
        "purpose": "Reproducibility manifest for the authoritative final HAILIE forecast outputs",
        "data_period": {"first_year": 1987, "last_year": 2025, "observations_per_series": 39},
        "forecast_origin_year": 2025,
        "horizons_evaluated": [1, 2, 3, 5],
        "minimum_training_years": 10,
        "primary_selection_metric": "MAE",
        "primary_selection_rule": "lowest mean MAE across horizons 1, 2 and 3",
        "extension_selection_rule": "lowest horizon-5 MAE with a parsimonious tie-break",
        "prediction_intervals": "empirical 80% and 95% quantiles of rolling-origin forecast errors",
        "python_version": platform.python_version(),
        "numpy_version": national.np.__version__,
        "statsmodels_version": statsmodels.__version__,
        "sha256": {name: sha256(path) for name, path in tracked_inputs.items()},
    }
    path = FINAL_OUTPUTS_DIR / "run_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate authoritative HAILIE forecast outputs")
    parser.add_argument(
        "--check-regression",
        action="store_true",
        help="fail if model selections differ from the published run",
    )
    args = parser.parse_args()
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    warnings.filterwarnings("ignore", message="Non-invertible starting MA parameters found.*")
    warnings.filterwarnings("ignore", message="Non-stationary starting autoregressive parameters found.*")
    FINAL_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    generate_national_outputs(check_regression=args.check_regression)
    generate_regional_outputs(check_regression=args.check_regression)
    generate_history_sensitivity()
    write_manifest()
    print("Final output generation: PASS")


if __name__ == "__main__":
    main()
