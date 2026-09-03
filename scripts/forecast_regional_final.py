import csv
from pathlib import Path
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"

FIRST_YEAR = 1987
LAST_YEAR = 2025
EXPECTED_YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
MIN_TRAIN_YEARS = 10
ENGLAND_CODE = "E92000001"
EXPECTED_REGION_COUNT = 9
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