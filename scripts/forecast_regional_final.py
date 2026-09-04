import csv
from pathlib import Path
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt
from statsmodels.tsa.arima.model import ARIMA

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"

FIRST_YEAR = 1987
LAST_YEAR = 2025
EXPECTED_YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
MIN_TRAIN_YEARS = 10
ENGLAND_CODE = "E92000001"
EXPECTED_REGION_COUNT = 9
ARIMA_ORDERS = [
    (0, 1, 0),
    (1, 1, 0),
    (0, 1, 1),
    (1, 1, 1),
]
def load_regional_series():
    regions = {}

    with DATA_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            area_code = row["Area code"]
            region_name = row["Region"]

            if area_code == ENGLAND_CODE:
                continue

            if not region_name:
                continue

            year = int(row["year"])
            value = float(row["households_on_register"])

            if area_code not in regions:
                regions[area_code] = {
                    "name": region_name,
                    "years": [],
                    "values": [],
                }

            regions[area_code]["years"].append(year)
            regions[area_code]["values"].append(value)

    if len(regions) != EXPECTED_REGION_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_REGION_COUNT} regions, found {len(regions)}"
        )

    return regions
def validate_regional_series(regions):
    for area_code, region in regions.items():
        years = region["years"]
        values = region["values"]

        if years != EXPECTED_YEARS:
            raise ValueError(
                f"{region['name']} ({area_code}) has an unexpected year range: "
                f"{years[0]}–{years[-1]}"
            )

        if len(values) != len(EXPECTED_YEARS):
            raise ValueError(
                f"{region['name']} ({area_code}) should have "
                f"{len(EXPECTED_YEARS)} observations, found {len(values)}"
            )

        if any(value < 0 for value in values):
            raise ValueError(
                f"Negative household value found in "
                f"{region['name']} ({area_code})"
            )

    return True
def get_backtest_origins(horizon):
    first_origin = FIRST_YEAR + MIN_TRAIN_YEARS - 1
    last_origin = LAST_YEAR - horizon

    return list(range(first_origin, last_origin + 1))
def forecast_naive(train_values, horizon):
    last_value = train_values[-1]

    return [last_value] * horizon
def forecast_drift(train_values, horizon):
    first_value = train_values[0]
    last_value = train_values[-1]
    periods = len(train_values) - 1

    average_change = (last_value - first_value) / periods

    return [
        last_value + average_change * step
        for step in range(1, horizon + 1)
    ]
def forecast_linear_trend(train_values, horizon):
    n = len(train_values)

    x_mean = (n - 1) / 2
    y_mean = sum(train_values) / n

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in enumerate(train_values)
    )

    denominator = sum(
        (x - x_mean) ** 2
        for x in range(n)
    )

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    return [
        intercept + slope * (n - 1 + step)
        for step in range(1, horizon + 1)
    ]
def forecast_ses(train_values, horizon):
    model = SimpleExpSmoothing(
        train_values,
        initialization_method="estimated",
    )

    fitted_model = model.fit(optimized=True)

    forecast = fitted_model.forecast(horizon)

    return list(forecast)
def forecast_holt(train_values, horizon):
    model = Holt(
        train_values,
        damped_trend=False,
        initialization_method="estimated",
    )

    fitted_model = model.fit(optimized=True)

    forecast = fitted_model.forecast(horizon)

    return list(forecast)
def forecast_damped_trend(train_values, horizon):
    model = Holt(
        train_values,
        damped_trend=True,
        initialization_method="estimated",
    )

    fitted_model = model.fit(optimized=True)

    forecast = fitted_model.forecast(horizon)

    return list(forecast)
def forecast_arima(train_values, horizon):
    best_model = None
    best_aic = float("inf")

    for order in ARIMA_ORDERS:
        try:
            model = ARIMA(train_values, order=order)
            fitted_model = model.fit()

            if not fitted_model.mle_retvals.get("converged", True):
                continue

            if fitted_model.aic < best_aic:
                best_aic = fitted_model.aic
                best_model = fitted_model

        except Exception:
            continue

    if best_model is None:
        raise ValueError("No ARIMA candidate model could be fitted")

    forecast = best_model.forecast(steps=horizon)

    return list(forecast)
def backtest_model(years, values, forecast_function, horizon):
    results = []

    origins = get_backtest_origins(horizon)

    for origin in origins:
        origin_index = years.index(origin)

        train_values = values[: origin_index + 1]

        forecast = forecast_function(train_values, horizon)
        prediction = forecast[horizon - 1]

        target_year = origin + horizon
        target_index = years.index(target_year)
        actual = values[target_index]

        results.append(
            {
                "origin": origin,
                "target_year": target_year,
                "actual": actual,
                "forecast": prediction,
                "error": prediction - actual,
            }
        )

    return results
def calculate_metrics(results):
    errors = [result["error"] for result in results]
    actuals = [result["actual"] for result in results]

    mae = sum(abs(error) for error in errors) / len(errors)

    rmse = (
        sum(error ** 2 for error in errors) / len(errors)
    ) ** 0.5

    mape = (
        sum(
            abs(error) / actual
            for error, actual in zip(errors, actuals)
        )
        / len(errors)
        * 100
    )

    bias = sum(errors) / len(errors)

    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "Bias": bias,
    }
def empirical_prediction_interval(results, point_forecast, coverage):
    errors = sorted(result["error"] for result in results)

    alpha = 1 - coverage

    lower_index = int((alpha / 2) * (len(errors) - 1))
    upper_index = int((1 - alpha / 2) * (len(errors) - 1))

    lower_error = errors[lower_index]
    upper_error = errors[upper_index]

    lower_bound = point_forecast - upper_error
    upper_bound = point_forecast - lower_error

    return lower_bound, upper_bound
if __name__ == "__main__":
    regions = load_regional_series()
    validate_regional_series(regions)

    print(f"Regional series loaded: {len(regions)}")

    for area_code, region in regions.items():
        print(
            f"{region['name']} ({area_code}): "
            f"{region['years'][0]}–{region['years'][-1]}, "
            f"{len(region['values'])} observations"
        )

    print("Regional validation: PASS")
    for horizon in [1, 2, 3, 5]:
        origins = get_backtest_origins(horizon)

        print(
            f"{horizon}-year horizon: "
            f"{origins[0]}–{origins[-1]} "
            f"({len(origins)} origins)"
        )
    first_region_code = sorted(regions.keys())[0]
    first_region = regions[first_region_code]

    example_train = first_region["values"][:10]

    example_forecast = forecast_naive(example_train, 3)
    print(
        f"Naive test for {first_region['name']} "
        f"({first_region_code}): {example_forecast}"
    )

    drift_forecast = forecast_drift(example_train, 3)
    print(
        f"Drift test for {first_region['name']} "
        f"({first_region_code}): {drift_forecast}"
    )
    linear_trend_forecast = forecast_linear_trend(example_train, 3)

    print(
        f"Linear trend test for {first_region['name']} "
        f"({first_region_code}): {linear_trend_forecast}"
    )
    ses_forecast = forecast_ses(example_train, 3)

    print(
        f"SES test for {first_region['name']} "
        f"({first_region_code}): {ses_forecast}"
    )
    holt_forecast = forecast_holt(example_train, 3)

    print(
        f"Holt test for {first_region['name']} "
        f"({first_region_code}): {holt_forecast}"
    )
    damped_forecast = forecast_damped_trend(example_train, 3)

    print(
        f"Damped trend test for {first_region['name']} "
        f"({first_region_code}): {damped_forecast}"
    )
    arima_forecast = forecast_arima(example_train, 3)

    print(
        f"ARIMA test for {first_region['name']} "
        f"({first_region_code}): {arima_forecast}"
    )
    naive_3yr_results = backtest_model(
        first_region["years"],
        first_region["values"],
        forecast_naive,
        3,
    )
    naive_3yr_metrics = calculate_metrics(naive_3yr_results)

    print(
        f"North East naive 3-year backtest: "
        f"{len(naive_3yr_results)} forecasts"
    )

    print("North East naive 3-year metrics:")
    print(naive_3yr_metrics)
    models = {
        "Naive": forecast_naive,
        "Drift": forecast_drift,
        "Linear trend": forecast_linear_trend,
        "SES": forecast_ses,
        "Holt": forecast_holt,
        "Damped trend": forecast_damped_trend,
        "ARIMA": forecast_arima,
    }

    print("\nNorth East 3-year model comparison:")

    for model_name, forecast_function in models.items():
        results = backtest_model(
            first_region["years"],
            first_region["values"],
            forecast_function,
            3,
        )

        metrics = calculate_metrics(results)

        print(
            f"{model_name}: "
            f"MAE={metrics['MAE']:.0f}, "
            f"RMSE={metrics['RMSE']:.0f}, "
            f"MAPE={metrics['MAPE']:.2f}%, "
            f"Bias={metrics['Bias']:.0f}"
        )
    print("\nRegional Y1/Y2/Y3 model comparison:")

    for area_code, region in regions.items():
        print(f"\n{region['name']} ({area_code})")

        for horizon in [1, 2, 3]:
            print(f"  {horizon}-year horizon")

            for model_name, forecast_function in models.items():
                results = backtest_model(
                    region["years"],
                    region["values"],
                    forecast_function,
                    horizon,
                )

                metrics = calculate_metrics(results)

                print(
                    f"    {model_name}: "
                    f"MAE={metrics['MAE']:.0f}, "
                    f"RMSE={metrics['RMSE']:.0f}, "
                    f"MAPE={metrics['MAPE']:.2f}%, "
                    f"Bias={metrics['Bias']:.0f}"
                )
    best_regional_models = []

    for area_code, region in regions.items():
        for horizon in [1, 2, 3]:
            model_results = []

            for model_name, forecast_function in models.items():
                results = backtest_model(
                    region["years"],
                    region["values"],
                    forecast_function,
                    horizon,
                )

                metrics = calculate_metrics(results)

                model_results.append(
                    {
                        "model": model_name,
                        "MAE": metrics["MAE"],
                    }
                )

            best = min(model_results, key=lambda x: x["MAE"])

            best_regional_models.append(
                {
                    "region": region["name"],
                    "area_code": area_code,
                    "horizon": horizon,
                    "model": best["model"],
                    "MAE": best["MAE"],
                }
            )

    print("\nCLEAN REGIONAL MODEL WINNERS:")

    for result in best_regional_models:
        print(
            f"{result['region']} | "
            f"{result['horizon']}-year | "
            f"{result['model']} | "
            f"MAE={result['MAE']:.0f}"
        )
    print("\nCOMBINED Y1/Y2/Y3 REGIONAL MODEL SELECTION:")

    selected_3yr_models = {}

    for area_code, region in regions.items():
        combined_results = []

        for model_name, forecast_function in models.items():
            horizon_maes = []

            for horizon in [1, 2, 3]:
                results = backtest_model(
                    region["years"],
                    region["values"],
                    forecast_function,
                    horizon,
                )

                metrics = calculate_metrics(results)
                horizon_maes.append(metrics["MAE"])

            combined_mae = sum(horizon_maes) / len(horizon_maes)

            combined_results.append(
                {
                    "model": model_name,
                    "combined_mae": combined_mae,
                }
            )

        best = min(
            combined_results,
            key=lambda x: x["combined_mae"],
        )

        selected_3yr_models[area_code] = best["model"]

        print(
            f"{region['name']} | "
            f"{best['model']} | "
            f"mean Y1-Y3 MAE={best['combined_mae']:.0f}"
        )
    print("\nFINAL SELECTED 3-YEAR REGIONAL MODELS:")

    for area_code, model_name in selected_3yr_models.items():
        print(
            f"{regions[area_code]['name']} | "
            f"{model_name}"
        )
    print("\n5-YEAR REGIONAL MODEL SELECTION:")

    selected_5yr_models = {}

    for area_code, region in regions.items():
        five_year_results = []

        for model_name, forecast_function in models.items():
            results = backtest_model(
                region["years"],
                region["values"],
                forecast_function,
                5,
            )

            metrics = calculate_metrics(results)

            five_year_results.append(
                {
                    "model": model_name,
                    "MAE": metrics["MAE"],
                }
            )

        best = min(
            five_year_results,
            key=lambda x: x["MAE"],
        )

        selected_5yr_models[area_code] = best["model"]

        print(
            f"{region['name']} | "
            f"{best['model']} | "
            f"5-year MAE={best['MAE']:.0f}"
        )
    print("\nFINAL SELECTED 5-YEAR REGIONAL MODELS:")

    for area_code, model_name in selected_5yr_models.items():
        print(
            f"{regions[area_code]['name']} | "
            f"{model_name}"
        )
    print("\nFINAL REGIONAL FORECASTS:")

    for area_code, region in regions.items():
        model_3yr_name = selected_3yr_models[area_code]
        model_5yr_name = selected_5yr_models[area_code]

        model_3yr_function = models[model_3yr_name]
        model_5yr_function = models[model_5yr_name]

        forecast_3yr = model_3yr_function(
            region["values"],
            3,
        )

        forecast_5yr = model_5yr_function(
            region["values"],
            5,
        )

        print(f"\n{region['name']} ({area_code})")

        for year, value in zip(
            [2026, 2027, 2028],
            forecast_3yr,
        ):
            print(
                f"  3-year model {year}: "
                f"{value:,.0f}"
            )

        for year, value in zip(
            [2026, 2027, 2028, 2029, 2030],
            forecast_5yr,
        ):
            print(
                f"  5-year model {year}: "
                f"{value:,.0f}"
            )
    print("\nFINAL REGIONAL FORECASTS:")

    for area_code, region in regions.items():
        model_3yr_name = selected_3yr_models[area_code]
        model_5yr_name = selected_5yr_models[area_code]

        model_3yr_function = models[model_3yr_name]
        model_5yr_function = models[model_5yr_name]

        forecast_3yr = model_3yr_function(
            region["values"],
            3,
        )

        forecast_5yr = model_5yr_function(
            region["values"],
            5,
        )

        print(f"\n{region['name']} ({area_code})")

        for year, value in zip(
            [2026, 2027, 2028],
            forecast_3yr,
        ):
            print(
                f"  3-year model {year}: "
                f"{value:,.0f}"
            )

        for year, value in zip(
            [2026, 2027, 2028, 2029, 2030],
            forecast_5yr,
        ):
            print(
                f"  5-year model {year}: "
                f"{value:,.0f}"
            )
    print("\nFINAL REGIONAL PREDICTION INTERVALS:")

    for area_code, region in regions.items():
        model_name = selected_3yr_models[area_code]
        forecast_function = models[model_name]

        point_forecasts = forecast_function(
            region["values"],
            3,
        )

        print(f"\n{region['name']} ({area_code})")

        for horizon, (year, point_forecast) in enumerate(
            zip([2026, 2027, 2028], point_forecasts),
            start=1,
        ):
            results = backtest_model(
                region["years"],
                region["values"],
                forecast_function,
                horizon,
            )

            lower_80, upper_80 = empirical_prediction_interval(
                results,
                point_forecast,
                0.80,
            )

            lower_95, upper_95 = empirical_prediction_interval(
                results,
                point_forecast,
                0.95,
            )

            print(
                f"  {year}: "
                f"point={point_forecast:,.0f}, "
                f"80% PI=({lower_80:,.0f}, {upper_80:,.0f}), "
                f"95% PI=({lower_95:,.0f}, {upper_95:,.0f})"
            )