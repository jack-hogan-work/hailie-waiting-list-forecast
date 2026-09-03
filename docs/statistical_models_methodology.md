# Statistical Model Comparison — Methodology and Results (Week 2 extension)

**Scope note:** the session guardrails asked that no third-party package be installed without checking first. The user was asked directly whether to install `statsmodels` for ARIMA/Holt-Winters, extend to local-authority forecasting instead, or stop; they chose to install `statsmodels`. `requirements.txt` has been updated (`statsmodels==0.14.6`, pulling in `scipy`, `pandas`, `patsy` as transitive dependencies) and the package was installed only into the project-local `.venv`.

**Source:** same validated England-total and nine-region series used throughout (`docs/national_forecast_methodology.md`, `docs/regional_forecast_methodology.md`).
**Script:** `scripts/forecast_statistical.py`. This does not duplicate the backtest harness: `run_backtest()`, `forward_forecast()`, and the two chart functions in `scripts/forecast_national.py` were given an optional `models=`/`model_colors=`/`model_labels=` parameter (defaulting to the original five benchmarks, so all prior outputs are unaffected — reproducibility re-confirmed below) specifically so this script could pass in an extended seven-model dict without rewriting the harness. Run with:

```
.venv/bin/python3 scripts/forecast_statistical.py
```

Runtime: ~52 seconds wall-clock (national: <1s; regional: ~50s, dominated by the ARIMA AIC grid search across 9 regions x 30 origins).

**Outputs:**
- `outputs/model_results_extended.csv` — national MAE/RMSE/MAPE/bias, all 7 models x 4 horizons (28 rows).
- `outputs/backtest_predictions_extended.csv` — national detail, all 7 models (109 origin/horizon combinations x 7 models = 763 rows).
- `outputs/regional_model_results_extended.csv` — regional summary only (no detail CSV — see Limitations), 9 regions x 7 models x 4 horizons = 252 rows.
- `outputs/national_forecast_2026_2030_extended.csv` — illustrative forward forecast, all 7 models fit on the full 1987-2025 series, 5 forward years (2026-2030), 35 rows.
- `outputs/regional_forecast_2026_2030_extended.csv` — same forward forecast, all 7 models, per region: 9 regions x 7 models x 5 years = 315 rows.
- `outputs/regional_forecast_selected_2026_2030.csv` — one row per region per backtested horizon (1/2/3/5-year → 2026/2027/2028/2030; 2029/horizon-4 excluded, see §5) giving the forward forecast from whichever model actually won that region's backtest at that horizon: 9 regions x 4 horizons = 36 rows.
- `outputs/regional_forecast_change_2025_2030.csv` — per region: 2025 actual, 2030 forecast under the backtest-selected 5-year model, and the min/max 2030 forecast across the 6 competitive models (`linear_trend` excluded — see §5): 9 rows.
- `outputs/figures/backtest_one_step_ahead_extended.png`, `outputs/figures/backtest_mape_by_horizon_extended.png` — national, 7-model versions of the two charts from the base national note.
- `outputs/figures/regional_win_counts_extended.png` — 7-model version of the regional win-count chart.
- `outputs/figures/regional_forecast_change_2025_2030.png` — regional 2025→2030 % change: backtest-selected model (dot) vs. range across the 6 competitive models (span), one row per region.
- `outputs/figures/regional_forecast_trajectories_2026_2030.png` — 3x3 small multiples, one panel per region, actual 2015-2025 plus the backtest-selected model's 2026-2030 forecast.

## 1. New models

| Model | Definition |
| --- | --- |
| `ets_damped` | Holt's damped-trend exponential smoothing (`statsmodels.tsa.holtwinters.ExponentialSmoothing`, `trend="add"`, `damped_trend=True`, `seasonal=None` — annual data has no sub-year period to model as seasonal). Chosen specifically because the pure-Python `holt` model (undamped trend, `docs/national_forecast_methodology.md` Finding 1) showed a strong 1-year win but a severe long-horizon overshoot; damping is the standard fix for exactly that failure mode. |
| `arima` | ARIMA(p,d,q), order chosen per origin by an in-sample AIC grid search (`d` in {1,2}, `p`,`q` in {0,1,2} = 18 candidate orders), restricted to well-conditioned fits (see §2 — a real degeneracy was found and fixed during development). Same no-leakage principle as the alpha/beta grid searches in `scripts/forecast_national.py`: the search only ever sees the training window. |

Both integrate into the existing `MODELS` dict pattern (`EXTENDED_MODELS = {**MODELS, "ets_damped": ..., "arima": ...}`) and therefore automatically get the same leakage-free, expanding-window, `MIN_TRAIN_YEARS=10`, `HORIZONS=[1,2,3,5]` treatment as the five base benchmarks — nothing about the backtest design changed for this extension.

## 2. A real bug found and fixed during development: degenerate ARIMA fits

The first version of `arima_forecast()` selected purely by lowest AIC with no other check. On the national series at origin year 2003 (17-year training window, 1987-2003), this selected ARIMA(2,2,2) with AIC=10.0 against ~368 for the next-best candidate — an enormous, suspicious gap. Diagnosis (reproduced independently, not just observed in aggregate output):

- The fitted AR and MA roots were both `0.99999999 ± 0.0001j`, i.e. sitting essentially exactly on the unit circle — a near-cancelling, numerically degenerate parameterisation where the AR and MA polynomials almost cancel each other out.
- The resulting forecast was **exactly 0.0 households** for every horizon at that origin (verified directly against `outputs/backtest_predictions_extended.csv` before the fix: origin=2003 produced `forecast=0.0` at h=1,2,3,5, each an error of roughly -1.4 to -1.8 million households).
- This single origin's four rows dominated the national ARIMA MAE/RMSE, making ARIMA look far worse than it actually is: before the fix, ARIMA's 1-year MAPE was 7.76% (worse than every model except linear-trend); after the fix, 4.19% (second-best of all seven models, behind only `ets_damped`).

**Fix:** candidate orders are now rejected if either the AR or MA roots come within 1.05 of the unit circle (`_is_well_conditioned()` in `scripts/forecast_statistical.py`), the standard safeguard against this failure mode. Re-running origin 2003 after the fix selects ARIMA(0,2,0) (AIC 367.9, the best surviving candidate) instead of the degenerate (2,2,2). This is a genuine correctness fix, not a modelling-style choice — it was verified against the actual root values and actual pre/post-fix forecasts, not assumed.

A milder, related issue remains and is **not** treated as a bug (see §6): at a small number of other origins, the AIC-best well-conditioned model is ARIMA(0,2,0) — a "double-drift" random walk on the twice-differenced series — which linearly extrapolates the series' recent *acceleration*. This is a legitimate model choice that can still produce implausible long-horizon forecasts (including one negative value) when the origin sits near a sharp turning point; see §6.

## 3. Results

### 3.1 National (`outputs/model_results_extended.csv`)

| Model | 1y MAPE | 2y MAPE | 3y MAPE | 5y MAPE |
| --- | ---: | ---: | ---: | ---: |
| ets_damped | **4.09%** | **8.51%** | 13.59% | 26.16% |
| arima | 4.19% | 9.10% | 14.50% | 30.97% |
| holt | 4.25% | 9.25% | 14.74% | 31.36% |
| naive | 4.71% | 9.03% | **13.32%** | **22.10%** |
| ses | 4.75% | 9.06% | 13.36% | 22.12% |
| drift | 5.03% | 9.82% | 14.71% | 25.89% |
| linear_trend | 19.16% | 22.71% | 26.41% | 34.16% |

**Headline findings:**

1. **`ets_damped` is the new best model at 1- and 2-year horizons** (4.09% and 8.51% MAPE), beating every one of the five original benchmarks including the previously-best `holt` and `naive`/`ses`. This confirms the hypothesis behind adding it: damping fixes most of `holt`'s overshoot problem while keeping its ability to track a genuine trend — but only at the shorter horizons.
2. **At 3- and 5-year, `naive` (and `ses`, within a near-tie of it) are best**, not `ets_damped`. At 3-year, `naive` (13.32%) and `ses` (13.36%) both edge out `ets_damped` (13.59%) — a smaller gap than at 5-year, where `naive` (22.10%) is well clear of `ets_damped` (26.16%) and `drift` (25.89%). So the crossover from "damped-trend model wins" to "flat model wins" happens between the 2- and 3-year horizons, not between 3- and 5-year as might be assumed from the 1-year result alone.
3. **`arima` is competitive but not the best model at any horizon** after the degeneracy fix — consistently the second- or third-best trend-aware model, close behind `ets_damped` and `holt` at short-to-medium horizons, and — per §6 — prone to occasional implausible long-horizon forecasts even after the fix.
4. **This directly answers the question posed at the end of the dependency-light phase** (`docs/national_forecast_methodology.md` §4: "these benchmarks exist to set a floor that any more complex model should be expected to beat before being adopted"): `ets_damped` clears that floor at 1- and 2-year horizons only; `arima` does not clear it at any horizon tested; at 3-year and 5-year, the simplest model (naive) remains best, undefeated by any of the six more complex models added since the dependency-light phase.

### 3.2 Regional (`outputs/regional_model_results_extended.csv`, `outputs/figures/regional_win_counts_extended.png`)

`ets_damped` wins outright in 1 of 9 regions at every horizon (a smaller, real margin, not a tie), and is competitive without winning in most others. `naive` still wins the majority of regions at every horizon (5, 6, 8, 8 of 9 at 1/2/3/5-years respectively) — but as established in `docs/regional_forecast_methodology.md` §2.4, most of those wins are near-ties against SES (<0.1 MAPE points), a caution repeated on this chart. `arima` and `linear_trend` never win a single region at any horizon. This is a more muted version of the national result: `ets_damped` is a genuine improvement in aggregate but does not dominate every individual region the way it dominates the smoother national series.

## 5. Regional 2026-2030 forward forecast

Extends the national forward forecast (`forward_forecast()`, now parameterised by `models=` — see §Outputs) to each of the 9 regions individually, fit on that region's full 1987-2025 series. Three related outputs, in increasing order of interpretation:

- **`outputs/regional_forecast_2026_2030_extended.csv`** — the raw grid: every model's forecast for every region and year. No selection applied.
- **`outputs/regional_forecast_selected_2026_2030.csv`** — for each region and each *backtested* horizon (1/2/3/5-year), the forward forecast from whichever model actually had the lowest MAPE for that region at that horizon (`outputs/regional_model_results_extended.csv`) — the same "use the evaluation result, don't pick separately" principle applied to the national forecast in `scripts/build_report.py` (see §6). 2029 (horizon 4) is excluded from this file for the same reason it's unhighlighted nationally: `HORIZONS=[1,2,3,5]` never evaluates a 4-year horizon, so there is no backtest result to select from.
- **`outputs/regional_forecast_change_2025_2030.csv`** and its chart (`outputs/figures/regional_forecast_change_2025_2030.png`) — 2025→2030 % change under the selected model, alongside the min/max % change across the 6 competitive models (`linear_trend` excluded — it is the worst-performing model at every horizon in every region, per §3.2 and `docs/regional_forecast_methodology.md` §2.5, and including it would make its known overshoot read as genuine model disagreement).

**Headline finding: naive (flat) is the 5-year-horizon selected model in 8 of the 9 regions** (South East is the exception, selecting `ets_damped`, -0.5%) — consistent with §3.2's finding that naive wins the majority of regions at every horizon. Read at face value, the "selected" forecast says almost nothing changes anywhere by 2030. But the range across the other competitive models tells a different story in some regions:

| Region | Selected (5y) | Range across 6 models | Read |
| --- | ---: | ---: | --- |
| West Midlands | naive, +0.0% | -2.4% to **+36.2%** | Models disagree sharply — flat is not a confident call here. |
| East Midlands | naive, +0.0% | **-17.8%** to +1.3% | Same pattern, opposite direction. |
| East of England | naive, +0.0% | -9.5% to +2.8% | Moderate disagreement. |
| London | naive, +0.0% | -0.0% to +15.6% | All non-naive models see growth; only naive/ses are flat. |
| North West | naive, +0.0% | -0.0% to +10.1% | Same pattern as London, smaller magnitude. |
| Yorkshire and The Humber | naive, +0.0% | -0.0% to +15.6% | Same pattern. |
| South West | naive, +0.0% | -0.0% to +11.5% | Same pattern. |
| North East | naive, +0.0% | -7.1% to +1.4% | Narrow range, mildly downside-skewed. |
| South East | ets_damped, -0.5% | -3.5% to +0.0% | Narrowest range of all 9 — the one region where the backtest actually prefers a trend-aware model, and the range agrees it's a small move. |

West Midlands and East Midlands have the widest ranges and are flagged as the least reliable single-point forecasts in this set: no model has been shown to beat naive there historically, but the trend-aware models don't agree with each other either, so the "flat" call should be read as "no established alternative", not as "confidently flat." South East is the most internally consistent region: it's the only one where a trend-aware model wins the backtest, and the full model range agrees on direction and magnitude.

No negative forecast values occurred in the regional forward run (checked via `run_regional_forward_qa()` in `scripts/forecast_statistical.py` — see §Outputs and script docstrings for the full QA: region/year completeness, duplicate rows, non-finite values, and an explicit negative-value check reported rather than silently clipped, per this project's existing convention).

## 6. Limitations

- **ARIMA's "double-drift" (0,2,0) fallback can produce implausible forecasts.** At national origins 2011 and 2014 (both near the 2012 peak / subsequent sharp decline), the AIC-best well-conditioned order was ARIMA(0,2,0), which linearly extrapolates the series' second difference (acceleration). At origin 2011 this produced a 2016 forecast of 2,230,643 households (actual: 1,184,750 — 88% too high); at origin 2014, a 2019 forecast of **-217,035** households (actual: 1,160,261) — a negative value, which is impossible for a real household count. These are legitimate outputs of a well-conditioned model, not numerical bugs (verified: no AR/MA roots, i.e. nothing for the root-distance check to catch), but they show that "well-conditioned" is a necessary, not sufficient, safeguard — an AIC-only search with no plausibility check on the forecast itself can still produce nonsensical results at long horizons from certain origins. No forecast values were clipped or post-processed to hide this; it is reported here instead, consistent with how `holt`'s overshoot was reported rather than patched in the base national note.
- **Regional detail predictions were not written.** Unlike the national extended detail (`outputs/backtest_predictions_extended.csv`), the regional run only writes summary rows (`outputs/regional_model_results_extended.csv`) — a full regional detail file at 7 models would be roughly 9× the national file's 763 rows without adding proportional value for this comparison; if that individual-forecast-level detail is needed later, `run_regional_summary_only()` in `scripts/forecast_statistical.py` would need a small change to also collect and write `r_detail`.
- **AIC grid is bounded (`d` in {1,2}, `p`,`q` in {0,1,2}), not a full auto-ARIMA search.** A wider grid (higher-order p/q, seasonal terms, or an exogenous-regressor ARIMAX) was not attempted; 18 candidates per origin was chosen to keep the regional run (270 origin-fits) under a minute while covering the orders most plausible for a 10-38 point annual series.
- **All limitations from the national and regional notes still apply**, in full: expanding window, `MIN_TRAIN_YEARS=10`, no exogenous drivers, small/overlapping 5-year origins, and the 2029/h=4 forward-forecast gap. `forecast_statistical.py` now also writes `outputs/national_forecast_2026_2030_extended.csv` (all 7 models, via the same `forward_forecast()` used by `forecast_national.py`, now parameterised by `models=`), and `scripts/build_report.py` highlights, per forecast year, whichever model had the lowest backtested MAPE at that horizon — except 2029 (horizon 4), which the backtest never evaluates (`HORIZONS=[1,2,3,5]`), so no model is highlighted there.
- **`statsmodels` and its dependencies (`scipy`, `pandas`, `patsy`) are now required** to run this script (though not `scripts/forecast_national.py` or `scripts/forecast_regional.py`, which remain dependency-light as before) — installed only in the project-local `.venv`, recorded in `requirements.txt`.
## 7. Final national modelling rebuild — September 2026

This section records the final national modelling pipeline rebuilt against the frozen and validated England series. It supersedes the earlier exploratory national model results above. The earlier work is retained for transparency and as a record of development, but the model-selection decisions and forecasts below are the final national results.

### 7.1 Frozen modelling dataset

The national series is the published England total from MHCLG Live Table 600 for 1987–2025.

- Geography: England
- Period: 1987–2025
- Annual observations: 39
- Missing national observations: 0
- First value (1987): 1,289,492 households
- Latest observed value (2025): 1,340,527 households
- National source-to-output validation: PASS
- Regional-to-national reconciliation: PASS for all 39 years

No additional cleaning, interpolation or imputation was introduced for the England series before modelling.

### 7.2 Candidate models

Seven models were compared:

1. Naive
2. Drift
3. Linear trend
4. Simple Exponential Smoothing (SES)
5. Holt trend
6. Damped Holt trend
7. ARIMA

The annual data have no within-year seasonal frequency, so seasonal models were not used.

SES, Holt and damped Holt were fitted using optimised smoothing parameters within each training window rather than fixed teaching values.

ARIMA was deliberately restricted to a small candidate set:

- ARIMA(0,1,0)
- ARIMA(1,1,0)
- ARIMA(0,1,1)
- ARIMA(1,1,1)

Within each historical training window the converged candidate with the lowest AIC was selected. Failed or non-converged candidate fits were not eligible for selection. Some candidate ARIMA fits generated optimisation warnings during estimation; these are retained as diagnostics rather than hidden. ARIMA ultimately produced results very similar to the naive benchmark and was not selected as the final forecasting model.

### 7.3 Backtesting design

Models were evaluated using expanding-window rolling-origin backtesting.

The first forecast origin was 1996, giving a minimum initial training period of ten annual observations (1987–1996). At each origin, only information available at that date was used.

Evaluated horizons were:

- 1 year: origins 1996–2024 (29 forecasts)
- 2 years: origins 1996–2023 (28 forecasts)
- 3 years: origins 1996–2022 (27 forecasts)
- 5 years: origins 1996–2020 (25 forecasts)

A 4-year backtest was additionally used only to estimate uncertainty for the 2029 point in the final five-year forecast; it was not used for model selection.

The primary model-selection metric was MAE because it is expressed directly in households and is straightforward to interpret. RMSE, MAPE and signed mean error (bias) were retained as supporting diagnostics.

### 7.4 Y1–Y3 model comparison

Damped trend produced the lowest MAE at each of the three primary forecast horizons.

| Model | Y1 MAE | Y2 MAE | Y3 MAE |
| --- | ---: | ---: | ---: |
| Naive | 64,900 | 125,174 | 183,588 |
| Drift | 68,236 | 133,089 | 197,251 |
| Linear trend | 259,259 | 309,472 | 362,839 |
| SES | 64,900 | 125,174 | 183,588 |
| Holt | 59,578 | 128,795 | 204,938 |
| Damped trend | **55,349** | **114,134** | **178,402** |
| ARIMA | 64,900 | 125,174 | 183,588 |

Across Y1–Y3, damped trend therefore provided the most consistent performance on the pre-specified primary metric.

Its average MAE across Y1–Y3 was approximately 115,962 households, compared with approximately 124,554 for the naive benchmark, an improvement of around 6.9%.

Damped trend did not dominate every supporting metric at every horizon. In particular, at the three-year horizon the naive/SES/ARIMA forecasts produced slightly lower RMSE and MAPE. The selection therefore should not be interpreted as damped trend being universally superior; rather, it was the most consistent model under the primary selection criterion established before the final comparison.

### 7.5 Five-year model comparison

At the five-year horizon, the simple naive forecast performed best on MAE.

| Model | 5-year MAE |
| --- | ---: |
| Naive | **306,435** |
| SES | **306,435** |
| ARIMA | **306,435** |
| Drift | 352,355 |
| Damped trend | 348,686 |
| Holt | 433,940 |
| Linear trend | 477,815 |

Because naive, SES and ARIMA produced effectively equivalent five-year performance, the naive model was selected for the five-year extension on grounds of parsimony and interpretability.

The final modelling strategy is therefore horizon-specific:

- 2026–2028 primary national forecast: damped trend
- 2026–2030 five-year extension: naive

### 7.6 Final national point forecasts

Using the complete 1987–2025 England series, the selected damped-trend model gives:

| Year | Damped-trend forecast |
| --- | ---: |
| 2026 | 1,348,467 |
| 2027 | 1,354,819 |
| 2028 | 1,359,901 |

The model therefore suggests a modest increase from the observed 2025 level of 1,340,527 households to approximately 1.36 million by 2028.

The selected five-year naive extension holds the most recent observed level constant:

| Year | Naive five-year forecast |
| --- | ---: |
| 2026 | 1,340,527 |
| 2027 | 1,340,527 |
| 2028 | 1,340,527 |
| 2029 | 1,340,527 |
| 2030 | 1,340,527 |

This flat long-horizon forecast should not be interpreted as a claim that the waiting list will literally remain unchanged. It reflects the finding that, historically, more elaborate trend extrapolation did not improve five-year forecast accuracy relative to the simple last-observation benchmark.

### 7.7 Empirical prediction intervals

Prediction intervals were derived from the empirical distribution of out-of-sample rolling-origin forecast errors at each horizon.

For the selected damped-trend three-year forecast:

| Year | Point forecast | 80% PI | 95% PI |
| --- | ---: | ---: | ---: |
| 2026 | 1,348,467 | 1,288,128–1,420,408 | 1,168,582–1,494,999 |
| 2027 | 1,354,819 | 1,183,078–1,510,443 | 1,013,012–1,656,568 |
| 2028 | 1,359,901 | 1,169,171–1,667,851 | 736,752–1,857,482 |

For the naive five-year extension:

| Year | Point forecast | 80% PI | 95% PI |
| --- | ---: | ---: | ---: |
| 2026 | 1,340,527 | 1,260,300–1,440,785 | 1,130,491–1,510,648 |
| 2027 | 1,340,527 | 1,179,777–1,545,556 | 892,904–1,634,728 |
| 2028 | 1,340,527 | 1,026,076–1,625,737 | 805,122–1,755,252 |
| 2029 | 1,340,527 | 881,080–1,740,476 | 726,978–1,855,037 |
| 2030 | 1,340,527 | 802,346–1,841,719 | 671,653–1,923,915 |

The widening intervals are an important result rather than a defect: historical forecast error increases substantially with the forecast horizon.

The empirical intervals describe uncertainty observed in historical model performance. They do not automatically include every source of uncertainty in the underlying administrative data, including historical changes in reporting practice, register management, geography or publisher imputation. The very wide long-horizon 95% intervals should therefore be interpreted as indicative uncertainty ranges rather than precise probabilistic guarantees.

### 7.8 Final interpretation

The national modelling does not support a confident claim of a large near-term rise or fall in England's housing waiting list.

The selected three-year model suggests a small upward movement from approximately 1.34 million households in 2025 to approximately 1.36 million in 2028. However, historical forecast errors are sufficiently large that a wide range of outcomes remains plausible.

At five years, simple persistence outperformed extrapolating a trend. This reinforces the conclusion that the point forecast becomes substantially less informative as the horizon increases and that uncertainty should be presented alongside any headline forecast.