# National Forecasting & Backtesting — Methodology and Results (Week 2)

**Source:** MHCLG Live Table 600, Regional Data worksheet, England total (`Area code` = `E92000001`), 1987-2025, 39 annual observations, 0 missing. Validated against the raw extract for 1987, 2015, 2020, 2024 and 2025 in `docs/national_validation.md`; re-confirmed at the start of this work by rerunning `scripts/prepare_data.py` and `scripts/validate_national.py` with no differences.
**Script:** `scripts/forecast_national.py` (standard-library `csv`/`math` for all data and model logic; matplotlib, project-local `.venv` only, for charts). Run with:

```
.venv/bin/python3 scripts/forecast_national.py
```

**Outputs:**
- `outputs/model_results.csv` — MAE / RMSE / MAPE / mean-error bias per model per horizon (the headline results table).
- `outputs/backtest_predictions.csv` — every individual backtest forecast (545 rows: model x origin x horizon), for transparency and re-analysis.
- `outputs/national_forecast_2026_2030.csv` — illustrative 2026-2030 forecast from each model fit on the full 1987-2025 series (not itself backtested — see Limitations).
- `outputs/figures/backtest_one_step_ahead.png` — actual series vs. each model's 1-year-ahead rolling-origin forecast.
- `outputs/figures/backtest_mape_by_horizon.png` — MAPE by model, grouped by horizon.

## 1. Approach

### 1.1 Models

Five dependency-light benchmarks, all pure Python (no forecasting libraries):

| Model | Definition |
| --- | --- |
| `naive` | Forecast = last observed value, held flat for every horizon. |
| `drift` | Forecast = last value + h x average historical slope, where the slope is `(last value - first value) / (n - 1)` over the training window (Hyndman & Athanasopoulos's drift method). |
| `linear_trend` | Ordinary-least-squares straight line fit to `households_on_register` against calendar year over the training window, extrapolated h years past the origin. |
| `ses` | Simple exponential smoothing: forecast is flat at the fitted level (no trend term). The smoothing parameter alpha is chosen per origin by a grid search (0.01-0.99, step 0.01) minimising one-step-ahead in-sample SSE on the training window only — no test/future data is used in this selection, so it does not introduce leakage. |
| `holt` | Holt's linear (double) exponential smoothing: forecast = fitted level + h x fitted trend. Unlike `ses`, this has an explicit trend term that is itself smoothed. (alpha, beta) are jointly grid-searched (0.01-0.99 each, 9,801 combinations) minimising one-step-ahead in-sample SSE on the training window only — same no-leakage principle as `ses`. |

`naive`, `drift`, and `linear_trend` were the three benchmarks required before any additional package could be requested (session scope). `ses` was added afterwards as a fourth benchmark, still with no third-party dependency, following on from this note's original recommendation to test a statistical smoothing method against the same backtest harness before considering a package-dependent model (ARIMA, Holt-Winters, etc.). `holt` was added as a fifth benchmark immediately after, specifically because the `ses` results (§2, Finding 2) showed that a level-only smoother could not usefully separate "recent level" from "ongoing trend" on this series — Holt's method adds exactly that missing trend term while remaining dependency-light.

### 1.2 Rolling-origin backtesting design

- **Expanding training window.** At each origin year, the model is trained on every year from 1987 up to and including the origin — not a fixed-size sliding window. With only 39 annual observations, a fixed window would either discard usable history or force very short, unstable early windows; an expanding window lets each successive origin use all the history available up to that point, which is the standard choice for short annual macro-style series.
- **`MIN_TRAIN_YEARS = 10`.** The first origin is 1996 (trained on 1987-1996). Fewer than 10 points was judged too few for a stable OLS trend fit; a much higher minimum would leave few origins left to backtest over, given the series is only 39 years long.
- **Horizons: 1, 2, 3 and 5 years.** This covers both a standard one-year-ahead check and multi-year forecasts, as requested. Horizons stop at 5 years because the number of origins with a known outcome shrinks as the horizon grows (see `n_origins` in the results table) — going further would leave too few origins for a stable error estimate.
- **No leakage.** At every origin, the model is fit only on data up to and including that origin year; the actual value compared against is always strictly later. This is enforced structurally by `run_backtest()` in the script, and checked by an assertion in `run_qa()` that the number of backtest rows produced matches the number expected from the origin/horizon grid.
- **Origins per horizon:** 1-year = 29 origins (1996-2024), 2-year = 28 (1996-2023), 3-year = 27 (1996-2022), 5-year = 25 (1996-2020). 
For clarity, this project does not use one fixed in-sample/out-of-sample split. Instead, out-of-sample performance is evaluated repeatedly using an expanding-window rolling-origin design. At each forecast origin, the in-sample dataset consists of all observations from 1987 up to that origin year, and the forecast is evaluated only against later observations that were not used to fit that model. This provides multiple genuinely out-of-sample tests rather than relying on the result of a single train/test split.

### 1.3 Metrics

For each model x horizon combination, aggregated across all valid origins:

- **MAE** (mean absolute error, households) — the primary, unit-preserving error measure.
- **RMSE** (root mean squared error, households) — penalises large misses more than MAE; the gap between MAE and RMSE flags how much error is concentrated in a few bad forecasts (notably around the 2012-2014 turning point).
- **MAPE** (mean absolute percentage error, %) — the "understandable" percentage metric requested; safe to use here since the England total never approaches zero (range ~1.02m-1.85m over the series).
- **Mean error (bias)** — signed mean of (forecast - actual), included to show whether a model systematically over- or under-forecasts rather than just how large its errors are. 
### 1.4 Model-selection rule for the final national forecast

The final forecasting approach will be selected using out-of-sample rolling-origin performance rather than in-sample fit alone.

For the initial 3-year forecast, one forecasting approach will be selected based on its performance across the 1-, 2- and 3-year horizons, with each horizon considered rather than choosing a different model independently for each forecast year. MAE will be the primary error measure, with RMSE, MAPE and mean-error bias used as supporting diagnostics.

The 5-year forecasting exercise will then be evaluated separately. If the evidence supports a different modelling approach at the longer horizon, the overlapping Y1, Y2 and Y3 forecasts from the 3-year and 5-year approaches will be compared directly before a final forecast is reported.

This is intended to avoid selecting a model that performs very well at one horizon but deteriorates materially at another.
The candidate set comprises seven approaches: naive (last observation), drift, linear trend, simple exponential smoothing (SES), Holt's linear trend, damped-trend exponential smoothing (ETS), and ARIMA. Simple benchmark models are retained deliberately so that the additional statistical complexity is only preferred where it produces better out-of-sample forecasting performance.


## 2. Results

From `outputs/model_results.csv`:

| Model | Horizon | n | MAE | RMSE | MAPE | Bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| naive | 1y | 29 | 64,900 | 94,773 | 4.71% | -9,598 |
| drift | 1y | 29 | 68,236 | 98,010 | 5.03% | -9,187 |
| linear_trend | 1y | 29 | 259,259 | 303,462 | 19.16% | +933 |
| ses | 1y | 29 | 65,415 | 95,417 | 4.75% | -9,683 |
| holt | 1y | 29 | 58,121 | 77,686 | 4.25% | -1,501 |
| naive | 2y | 28 | 125,174 | 176,067 | 9.03% | -20,975 |
| drift | 2y | 28 | 133,089 | 187,093 | 9.82% | -20,202 |
| linear_trend | 2y | 28 | 309,472 | 357,324 | 22.71% | -10,452 |
| ses | 2y | 28 | 125,607 | 176,609 | 9.06% | -21,046 |
| holt | 2y | 28 | 125,117 | 175,624 | 9.25% | -7,319 |
| naive | 3y | 27 | 183,588 | 247,374 | 13.32% | -31,658 |
| drift | 3y | 27 | 197,251 | 269,958 | 14.71% | -30,450 |
| linear_trend | 3y | 27 | 362,839 | 412,748 | 26.41% | -23,251 |
| ses | 3y | 27 | 184,108 | 247,833 | 13.36% | -31,705 |
| holt | 3y | 27 | 195,870 | 281,499 | 14.74% | -18,374 |
| naive | 5y | 25 | 306,435 | 371,023 | 22.10% | -47,200 |
| drift | 5y | 25 | 352,355 | 427,036 | 25.89% | -43,989 |
| linear_trend | 5y | 25 | 477,815 | 524,069 | 34.16% | -53,558 |
| ses | 5y | 25 | 306,809 | 371,382 | 22.12% | -47,220 |
| holt | 5y | 25 | 416,668 | 509,188 | 31.36% | -38,569 |

**Headline findings:**

1. **No single model wins at every horizon — Holt is best at 1-year but worst (or near-worst) at 5-year.** At 1-year, Holt has the lowest MAE, RMSE and MAPE of all five models (58,121 / 77,686 / 4.25%, vs. naive's 64,900 / 94,773 / 4.71%) and by far the smallest bias (-1,501 vs. naive's -9,598) — its trend term captures the post-2020 renewed rise that the flat models lag behind on. But that same trend term compounds badly at longer horizons: by 5-year, Holt's MAPE (31.36%) is worse than drift's (25.89%) and close to linear-trend's (34.16%), the worst of the five. This is visible directly in `outputs/figures/backtest_one_step_ahead.png` — the pink Holt line overshoots furthest above the actual series around the 2009-2013 peak and undershoots furthest below it around 2014-2015, both classic symptoms of extrapolating an estimated trend straight through a turning point.
2. **Naive and SES remain essentially tied for best at the 2-, 3- and 5-year horizons**, both clearly ahead of drift, and all three comfortably ahead of linear trend throughout. Naive edges out SES by 0.02-0.04 MAPE percentage points at every horizon; the gap to drift is larger (0.3-3.8 points), and the gap to linear trend is large throughout (3-4x naive's MAPE at every horizon).
3. **SES converges to an alpha of 0.99 — the edge of the search grid — at every single one of the 30 backtest origins.** This means the in-sample-SSE-optimal smoothing parameter is pushed as high as the grid allows, so SES's fitted level tracks almost the entire weight onto the most recent observation, which is why its forecasts and errors are nearly indistinguishable from naive's (visible in `outputs/figures/backtest_one_step_ahead.png`, where the violet SES line sits almost exactly on top of the orange naive line throughout). This is a real property of the series, not a bug: because the series exhibits strong persistence with large trend-driven swings rather than noise around a stable level, there is no interior alpha that smooths away meaningful noise without also lagging genuine level shifts, so the optimiser keeps pushing toward alpha=1 (pure naive).
4. **The linear-trend model is a poor fit for this series and should not be used as-is.** England's waiting-list count is not a monotonic trend — it traces two broad cycles (fall to a 1998 trough, rise to a 2012 peak, fall to a ~2018 trough, renewed rise to 2025; see `docs/initial_eda_findings.md`). A straight line fit to an expanding window systematically lags each turning point, which is visible directly in `outputs/figures/backtest_one_step_ahead.png` — the red linear-trend line is still climbing years after the actual series has turned down, and vice versa.
5. **Naive and drift are close because the series' average historical drift is close to flat.** Over the full 1987-2025 window the endpoints are similar (1,289,492 to 1,340,527, +4.0%), so the drift model's slope term is small and it behaves similarly to a flat carry-forward; this would not necessarily hold if evaluated from a different pair of endpoints.
6. **All models degrade sharply as horizon lengthens**, as expected: naive's MAPE rises from 4.7% (1-year) to 22.1% (5-year). This is a real property of the series' volatility (year-on-year swings of up to +16.1%/-18.8% are documented in `docs/initial_eda_findings.md`), not an artefact of the backtest design. Holt is the exception to "degrades gradually" — its error grows faster than the others' between 3- and 5-year (MAPE +16.6 points vs. naive's +8.8), consistent with Finding 1.
7. **All five models are negatively biased (under-forecast) at every horizon except linear-trend's near-zero 1-year bias**, consistent with the series' strong renewed growth since 2020 outpacing what a model trained mostly on earlier, flatter or falling periods would expect. Holt's bias is consistently the smallest in magnitude of the four negatively-biased models at every horizon, again reflecting its trend term picking up the recent rise fastest.

See `outputs/figures/backtest_one_step_ahead.png` for the visual comparison and `outputs/figures/backtest_mape_by_horizon.png` for the MAPE-by-horizon summary.

## 3. Illustrative 2026-2030 forecast

`outputs/national_forecast_2026_2030.csv` fits each model on the **full** 1987-2025 series (not backtested) and extrapolates. This is included as a direct, natural output of "create a national forecasting script," not as a validated prediction — given naive/SES's ~4-5% 1-year and ~22% 5-year MAPE in backtesting, Holt's much lower 1-year but much higher 5-year MAPE, and drift's and linear-trend's larger errors throughout, any of these forecasts should be treated as a wide-uncertainty benchmark rather than a point estimate to plan against. In particular: linear-trend's 2026-2030 path (rising from ~1.41m to ~1.43m) should be read with the caveat in Finding 4 above; SES's flat ~1,340,423 forecast (essentially identical to naive's flat 1,340,527) should be read with the alpha=0.99 boundary-solution caveat in Finding 3; and Holt's path (rising from ~1.35m in 2026 to ~1.39m in 2030) is the model with the strongest 1-year backtested accuracy but the weakest by 5 years out, so its later years in this table carry the least backtested support of the five models, not the most.

## 4. Limitations

- **Seven candidate models are now compared.** The final comparison includes naive, drift, linear trend, SES, Holt, damped-trend ETS and ARIMA. The simpler five-model benchmark results are retained as an earlier stage of the analysis, but they are no longer the full candidate set.
- **No single model should be chosen solely because it wins at one horizon.** The final national approach will follow the model-selection rule in Section 1.4: the initial 3-year approach is judged across Y1–Y3, with the 5-year exercise evaluated separately and overlapping Y1–Y3 forecasts compared if the preferred approach changes.
- **Single-series, national-level only.** This backtest evaluates the England total only. It does not extend to the nine regions or to local authorities (which have their own boundary-change and missing-data complications documented in `docs/initial_feasibility_note.md`), and results here should not be assumed to transfer to those series.
- **Small number of independent 5-year-horizon origins.** 25 origins sounds reasonable, but consecutive origins share almost all of their training data and many overlapping target years, so the backtest is not 25 independent trials — treat the horizon-level MAE/RMSE/MAPE as indicative of relative model performance, not as precise, independent-sample confidence intervals.
- **No exogenous drivers.** All five models use only the England total's own history. None accounts for policy changes, register "cleanse" events, or economic conditions that `docs/initial_eda_findings.md` and `docs/initial_feasibility_note.md` note can move the reported count for administrative as well as demand-driven reasons. A model unaware of an upcoming cleanse (or its absence) cannot anticipate the resulting swing.
- **Backtest window starts in 1996, not 1987.** The `MIN_TRAIN_YEARS = 10` choice means the first nine years of the series (1987-1995) are used only as training data for later origins and never appear as a forecast target — the backtest says nothing about forecast accuracy in that period.
- **2026-2030 forecast is unvalidated.** As noted in §3, the forward forecast is a direct extrapolation, not a value taken from or checked against the backtest; it is provided for illustration only.
- **2029 forecast (h=4) has no backtested error rate.** The forward forecast produces every year 2026-2030 (h=1..5), but the backtest only evaluates h∈{1,2,3,5} — h=4 was skipped as a horizon choice (§1.2), so the 2029 row in `national_forecast_2026_2030.csv` isn't backed by an h=4 MAE/RMSE/MAPE the way the other four years are.
