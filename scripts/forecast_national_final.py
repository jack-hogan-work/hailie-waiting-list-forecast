import csv
from pathlib import Path
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"

ENGLAND_REGION = "England"
FIRST_YEAR = 1987
LAST_YEAR = 2025
MIN_TRAIN_YEARS = 10
HORIZONS = [1, 2, 3, 5]
ARIMA_ORDERS = [
    (0, 1, 0),
    (1, 1, 0),
    (0, 1, 1),
    (1, 1, 1),
]
def load_england_series():
    years = []
    values = []

    with DATA_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["Region"] == ENGLAND_REGION:
                years.append(int(row["year"]))
                values.append(int(row["households_on_register"]))

    return years, values
def validate_england_series(years, values):
    expected_years = list(range(FIRST_YEAR, LAST_YEAR + 1))

    if years != expected_years:
        raise ValueError(
            f"Unexpected year range. Expected {FIRST_YEAR}-{LAST_YEAR}, "
            f"got {years[0]}-{years[-1]}"
        )

    if len(values) != len(expected_years):
        raise ValueError(
            f"Expected {len(expected_years)} observations, found {len(values)}"
        )

        if any(value < 0 for value in values):
            raise ValueError("Negative household values found in England series")
def get_backtest_origins(years, horizon):
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

    origins = get_backtest_origins(years, horizon)

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
    errors = np.array(
        [result["error"] for result in results],
        dtype=float,
    )

    alpha = 1 - coverage

    lower_error = np.quantile(errors, alpha / 2)
    upper_error = np.quantile(errors, 1 - alpha / 2)

    lower_bound = point_forecast - upper_error
    upper_bound = point_forecast - lower_error

    return lower_bound, upper_bound
if __name__ == "__main__":
    years, values = load_england_series()
    validate_england_series(years, values)

    print(f"Loaded England series: {years[0]}-{years[-1]}")
    print(f"Observations: {len(values)}")
    print(f"First value: {values[0]:,}")
    print(f"Last value: {values[-1]:,}")
    print("Validation: PASS")
    example_train = values[:10]
    example_forecast = forecast_naive(example_train, 3)

    print("Naive test forecast:", example_forecast)
    drift_forecast = forecast_drift(example_train, 3)
    print("Drift test forecast:", drift_forecast)

    linear_trend_forecast = forecast_linear_trend(example_train, 3)
    print("Linear trend test forecast:", linear_trend_forecast)

    ses_forecast = forecast_ses(example_train, 3)
    print("SES test forecast:", ses_forecast)
    
    holt_forecast = forecast_holt(example_train, 3)
    print("Holt test forecast:", holt_forecast)

    damped_forecast = forecast_damped_trend(example_train, 3)
    print("Damped trend test forecast:", damped_forecast)

    arima_forecast = forecast_arima(example_train, 3)
    print("ARIMA test forecast:", arima_forecast)

    naive_3yr_results = backtest_model(
        years,
        values,
        forecast_naive,
        3,
    )

    print("Naive 3-year backtest:")
    print("Number of forecasts:", len(naive_3yr_results))
    print("First result:", naive_3yr_results[0])
    print("Last result:", naive_3yr_results[-1])

    naive_3yr_metrics = calculate_metrics(naive_3yr_results)

    print("Naive 3-year metrics:")
    print(naive_3yr_metrics)

    drift_3yr_results = backtest_model(
        years,
        values,
        forecast_drift,
        3,
    )

    linear_3yr_results = backtest_model(
        years,
        values,
        forecast_linear_trend,
        3,
    )

    print("Drift 3-year metrics:")
    print(calculate_metrics(drift_3yr_results))

    print("Linear trend 3-year metrics:")
    print(calculate_metrics(linear_3yr_results))
    ses_3yr_results = backtest_model(
        years,
        values,
        forecast_ses,
        3,
    )

    holt_3yr_results = backtest_model(
        years,
        values,
        forecast_holt,
        3,
    )

    damped_3yr_results = backtest_model(
        years,
        values,
        forecast_damped_trend,
        3,
    )

    print("SES 3-year metrics:")
    print(calculate_metrics(ses_3yr_results))

    print("Holt 3-year metrics:")
    print(calculate_metrics(holt_3yr_results))

    print("Damped trend 3-year metrics:")
    print(calculate_metrics(damped_3yr_results))
    arima_3yr_results = backtest_model(
        years,
        values,
        forecast_arima,
        3,
    )

    print("ARIMA 3-year metrics:")
    print(calculate_metrics(arima_3yr_results))

    models = {
        "Naive": forecast_naive,
        "Drift": forecast_drift,
        "Linear trend": forecast_linear_trend,
        "SES": forecast_ses,
        "Holt": forecast_holt,
        "Damped trend": forecast_damped_trend,
        "ARIMA": forecast_arima,
    }

    print("\nY1/Y2/Y3 model comparison:")

    for horizon in [1, 2, 3]:
        print(f"\n{horizon}-year horizon")

        for model_name, forecast_function in models.items():
            results = backtest_model(
                years,
                values,
                forecast_function,
                horizon,
            )

            metrics = calculate_metrics(results)

            print(
                f"{model_name}: "
                f"MAE={metrics['MAE']:.0f}, "
                f"RMSE={metrics['RMSE']:.0f}, "
                f"MAPE={metrics['MAPE']:.2f}%, "
                f"Bias={metrics['Bias']:.0f}"
            )
    print("\n5-year model comparison:")

    for model_name, forecast_function in models.items():
        results = backtest_model(
            years,
            values,
            forecast_function,
            5,
        )

        metrics = calculate_metrics(results)

        print(
            f"{model_name}: "
            f"MAE={metrics['MAE']:.0f}, "
            f"RMSE={metrics['RMSE']:.0f}, "
            f"MAPE={metrics['MAPE']:.2f}%, "
            f"Bias={metrics['Bias']:.0f}"
        )
    final_3yr_forecast = forecast_damped_trend(values, 3)
    final_5yr_forecast = forecast_naive(values, 5)
    damped_y1_results = backtest_model(
        years,
        values,
        forecast_damped_trend,
        1,
    )

    damped_y2_results = backtest_model(
        years,
        values,
        forecast_damped_trend,
        2,
    )

    damped_y3_results = backtest_model(
        years,
        values,
        forecast_damped_trend,
        3,
    )
    print("\nDamped trend prediction intervals:")

    for year, point_forecast, results in zip(
        [2026, 2027, 2028],
        final_3yr_forecast,
        [damped_y1_results, damped_y2_results, damped_y3_results],
    ):
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
            f"{year}: "
            f"point={point_forecast:,.0f}, "
            f"80% PI=({lower_80:,.0f}, {upper_80:,.0f}), "
            f"95% PI=({lower_95:,.0f}, {upper_95:,.0f})"
        )
    naive_interval_results = {
        horizon: backtest_model(
            years,
            values,
            forecast_naive,
            horizon,
        )
        for horizon in [1, 2, 3, 4, 5]
    }

    print("\nNaive 5-year prediction intervals:")

    for horizon, (year, point_forecast) in enumerate(
        zip(
            [2026, 2027, 2028, 2029, 2030],
            final_5yr_forecast,
        ),
        start=1,
    ):
        results = naive_interval_results[horizon]

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
            f"{year}: "
            f"point={point_forecast:,.0f}, "
            f"80% PI=({lower_80:,.0f}, {upper_80:,.0f}), "
            f"95% PI=({lower_95:,.0f}, {upper_95:,.0f})"
        )
    print("\nFinal national point forecasts:")

    for year, forecast in zip(
        [2026, 2027, 2028],
        final_3yr_forecast,
    ):
        print(
            f"Damped trend {year}: "
            f"{forecast:,.0f} households"
        )

    for year, forecast in zip(
        [2026, 2027, 2028, 2029, 2030],
        final_5yr_forecast,
    ):
        print(
            f"Naive 5-year {year}: "
            f"{forecast:,.0f} households"
        )
    for horizon in HORIZONS:
        origins = get_backtest_origins(years, horizon)

        print(
            f"{horizon}-year horizon: "
            f"{origins[0]}-{origins[-1]} "
            f"({len(origins)} origins)"
        )
