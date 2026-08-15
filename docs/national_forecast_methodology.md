# National Forecasting & Backtesting — Methodology and Results (Week 2)

**Source:** MHCLG Live Table 600, Regional Data worksheet, England total (`Area code` = `E92000001`), 1987-2025, 39 annual observations, 0 missing. Validated against the raw extract for 1987, 2015, 2020, 2024 and 2025 in `docs/national_validation.md`; re-confirmed at the start of this work by rerunning `scripts/prepare_data.py` and `scripts/validate_national.py` with no differences.
**Script:** `scripts/forecast_national.py` (standard-library `csv`/`math` for all data and model logic; matplotlib, project-local `.venv` only, for charts). Run with:

```
.venv/bin/python3 scripts/forecast_national.py
```

**Outputs:**
- `outputs/model_results.csv` — MAE / RMSE / MAPE / mean-error bias per model per horizon (the headline results table).
- `outputs/backtest_predictions.csv` — every individual backtest forecast (327 rows: model x origin x horizon), for transparency and re-analysis.
- `outputs/national_forecast_2026_2030.csv` — illustrative 2026-2030 forecast from each model fit on the full 1987-2025 series (not itself backtested — see Limitations).
- `outputs/figures/backtest_one_step_ahead.png` — actual series vs. each model's 1-year-ahead rolling-origin forecast.
- `outputs/figures/backtest_mape_by_horizon.png` — MAPE by model, grouped by horizon.

## 1. Approach

### 1.1 Models

Three dependency-light benchmarks, all pure Python (no forecasting libraries):

| Model | Definition |
| --- | --- |
| `naive` | Forecast = last observed value, held flat for every horizon. |
| `drift` | Forecast = last value + h x average historical slope, where the slope is `(last value - first value) / (n - 1)` over the training window (Hyndman & Athanasopoulos's drift method). |
| `linear_trend` | Ordinary-least-squares straight line fit to `households_on_register` against calendar year over the training window, extrapolated h years past the origin. |

These were chosen because the task scope required dependency-light benchmarks before any additional package could be requested; all three are standard textbook baselines that any more sophisticated model (ARIMA, exponential smoothing, etc.) should be expected to beat before being adopted.

### 1.2 Rolling-origin backtesting design

- **Expanding training window.** At each origin year, the model is trained on every year from 1987 up to and including the origin — not a fixed-size sliding window. With only 39 annual observations, a fixed window would either discard usable history or force very short, unstable early windows; an expanding window lets each successive origin use all the history available up to that point, which is the standard choice for short annual macro-style series.
- **`MIN_TRAIN_YEARS = 10`.** The first origin is 1996 (trained on 1987-1996). Fewer than 10 points was judged too few for a stable OLS trend fit; a much higher minimum would leave few origins left to backtest over, given the series is only 39 years long.
- **Horizons: 1, 2, 3 and 5 years.** This covers both a standard one-year-ahead check and multi-year forecasts, as requested. Horizons stop at 5 years because the number of origins with a known outcome shrinks as the horizon grows (see `n_origins` in the results table) — going further would leave too few origins for a stable error estimate.
- **No leakage.** At every origin, the model is fit only on data up to and including that origin year; the actual value compared against is always strictly later. This is enforced structurally by `run_backtest()` in the script, and checked by an assertion in `run_qa()` that the number of backtest rows produced matches the number expected from the origin/horizon grid.
- **Origins per horizon:** 1-year = 29 origins (1996-2024), 2-year = 28 (1996-2023), 3-year = 27 (1996-2022), 5-year = 25 (1996-2020).

### 1.3 Metrics

For each model x horizon combination, aggregated across all valid origins:

- **MAE** (mean absolute error, households) — the primary, unit-preserving error measure.
- **RMSE** (root mean squared error, households) — penalises large misses more than MAE; the gap between MAE and RMSE flags how much error is concentrated in a few bad forecasts (notably around the 2012-2014 turning point).
- **MAPE** (mean absolute percentage error, %) — the "understandable" percentage metric requested; safe to use here since the England total never approaches zero (range ~1.02m-1.85m over the series).
- **Mean error (bias)** — signed mean of (forecast - actual), included to show whether a model systematically over- or under-forecasts rather than just how large its errors are.

## 2. Results

From `outputs/model_results.csv`:

| Model | Horizon | n | MAE | RMSE | MAPE | Bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| naive | 1y | 29 | 64,900 | 94,773 | 4.71% | -9,598 |
| drift | 1y | 29 | 68,236 | 98,010 | 5.03% | -9,187 |
| linear_trend | 1y | 29 | 259,259 | 303,462 | 19.16% | +933 |
| naive | 2y | 28 | 125,174 | 176,067 | 9.03% | -20,975 |
| drift | 2y | 28 | 133,089 | 187,093 | 9.82% | -20,202 |
| linear_trend | 2y | 28 | 309,472 | 357,324 | 22.71% | -10,452 |
| naive | 3y | 27 | 183,588 | 247,374 | 13.32% | -31,658 |
| drift | 3y | 27 | 197,251 | 269,958 | 14.71% | -30,450 |
| linear_trend | 3y | 27 | 362,839 | 412,748 | 26.41% | -23,251 |
| naive | 5y | 25 | 306,435 | 371,023 | 22.10% | -47,200 |
| drift | 5y | 25 | 352,355 | 427,036 | 25.89% | -43,989 |
| linear_trend | 5y | 25 | 477,815 | 524,069 | 34.16% | -53,558 |

**Headline findings:**

1. **Naive beats drift beats linear trend, at every single horizon.** This holds on MAE, RMSE and MAPE without exception. The margin between naive and drift is small (naive's MAPE is 0.3-3.8 percentage points lower); the margin between either of those and linear trend is large (linear trend's MAPE is 3-4x naive's at every horizon).
2. **The linear-trend model is a poor fit for this series and should not be used as-is.** England's waiting-list count is not a monotonic trend — it traces two broad cycles (fall to a 1998 trough, rise to a 2012 peak, fall to a ~2018 trough, renewed rise to 2025; see `docs/initial_eda_findings.md`). A straight line fit to an expanding window systematically lags each turning point, which is visible directly in `outputs/figures/backtest_one_step_ahead.png` — the red linear-trend line is still climbing years after the actual series has turned down, and vice versa.
3. **Naive and drift are close because the series' average historical drift is close to flat.** Over the full 1987-2025 window the endpoints are similar (1,289,492 to 1,340,527, +4.0%), so the drift model's slope term is small and it behaves similarly to a flat carry-forward; this would not necessarily hold if evaluated from a different pair of endpoints.
4. **All models degrade sharply as horizon lengthens**, as expected: naive's MAPE rises from 4.7% (1-year) to 22.1% (5-year). This is a real property of the series' volatility (year-on-year swings of up to +16.1%/-18.8% are documented in `docs/initial_eda_findings.md`), not an artefact of the backtest design.
5. **All three models are negatively biased (under-forecast) at every horizon except linear-trend's near-zero 1-year bias**, consistent with the series' strong renewed growth since 2020 outpacing what a model trained mostly on earlier, flatter or falling periods would expect.

See `outputs/figures/backtest_one_step_ahead.png` for the visual comparison and `outputs/figures/backtest_mape_by_horizon.png` for the MAPE-by-horizon summary.

## 3. Illustrative 2026-2030 forecast

`outputs/national_forecast_2026_2030.csv` fits each model on the **full** 1987-2025 series (not backtested) and extrapolates. This is included as a direct, natural output of "create a national forecasting script," not as a validated prediction — given naive/drift's ~5% 1-year and ~22-26% 5-year MAPE in backtesting, and linear-trend's much larger errors, any of these forecasts should be treated as a wide-uncertainty benchmark rather than a point estimate to plan against. In particular, linear-trend's 2026-2030 path (rising from ~1.41m to ~1.43m) should be read with the caveat in Finding 2 above.

## 4. Limitations

- **Three benchmarks only, no statistical or ML models.** Per the session's dependency-light scope, no seasonal, ARIMA, exponential-smoothing, or regression-with-covariates model was fitted. These benchmarks exist to set a floor that any more complex model should be expected to beat before being adopted; that comparison has not yet been made.
- **Single-series, national-level only.** This backtest evaluates the England total only. It does not extend to the nine regions or to local authorities (which have their own boundary-change and missing-data complications documented in `docs/initial_feasibility_note.md`), and results here should not be assumed to transfer to those series.
- **Small number of independent 5-year-horizon origins.** 25 origins sounds reasonable, but consecutive origins share almost all of their training data and many overlapping target years, so the backtest is not 25 independent trials — treat the horizon-level MAE/RMSE/MAPE as indicative of relative model performance, not as precise, independent-sample confidence intervals.
- **No exogenous drivers.** All three models use only the England total's own history. None accounts for policy changes, register "cleanse" events, or economic conditions that `docs/initial_eda_findings.md` and `docs/initial_feasibility_note.md` note can move the reported count for administrative as well as demand-driven reasons. A model unaware of an upcoming cleanse (or its absence) cannot anticipate the resulting swing.
- **Backtest window starts in 1996, not 1987.** The `MIN_TRAIN_YEARS = 10` choice means the first nine years of the series (1987-1995) are used only as training data for later origins and never appear as a forecast target — the backtest says nothing about forecast accuracy in that period.
- **2026-2030 forecast is unvalidated.** As noted in §3, the forward forecast is a direct extrapolation, not a value taken from or checked against the backtest; it is provided for illustration only.
- **2029 forecast (h=4) has no backtested error rate.** The forward forecast produces every year 2026-2030 (h=1..5), but the backtest only evaluates h∈{1,2,3,5} — h=4 was skipped as a horizon choice (§1.2), so the 2029 row in `national_forecast_2026_2030.csv` isn't backed by an h=4 MAE/RMSE/MAPE the way the other four years are.
