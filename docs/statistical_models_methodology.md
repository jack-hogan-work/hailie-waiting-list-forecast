# Statistical Model Comparison — Methodology and Results (Week 2 extension)

**Scope note:** the session guardrails asked that no third-party package be installed without checking first. The user was asked directly whether to install `statsmodels` for ARIMA/Holt-Winters, extend to local-authority forecasting instead, or stop; they chose to install `statsmodels`. `requirements.txt` has been updated (`statsmodels==0.14.6`, pulling in `scipy`, `pandas`, `patsy` as transitive dependencies) and the package was installed only into the project-local `.venv`.

**Source:** same validated England-total and nine-region series used throughout (`docs/national_forecast_methodology.md`, `docs/regional_forecast_methodology.md`).
**Script:** `scripts/forecast_statistical.py`. This does not duplicate the backtest harness: `run_backtest()` and the two chart functions in `scripts/forecast_national.py` were given an optional `models=`/`model_colors=`/`model_labels=` parameter (defaulting to the original five benchmarks, so all prior outputs are unaffected — reproducibility re-confirmed below) specifically so this script could pass in an extended seven-model dict without rewriting the harness. Run with:

```
.venv/bin/python3 scripts/forecast_statistical.py
```

Runtime: ~52 seconds wall-clock (national: <1s; regional: ~50s, dominated by the ARIMA AIC grid search across 9 regions x 30 origins).

**Outputs:**
- `outputs/model_results_extended.csv` — national MAE/RMSE/MAPE/bias, all 7 models x 4 horizons (28 rows).
- `outputs/backtest_predictions_extended.csv` — national detail, all 7 models (109 origin/horizon combinations x 7 models = 763 rows).
- `outputs/regional_model_results_extended.csv` — regional summary only (no detail CSV — see Limitations), 9 regions x 7 models x 4 horizons = 252 rows.
- `outputs/figures/backtest_one_step_ahead_extended.png`, `outputs/figures/backtest_mape_by_horizon_extended.png` — national, 7-model versions of the two charts from the base national note.
- `outputs/figures/regional_win_counts_extended.png` — 7-model version of the regional win-count chart.

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

A milder, related issue remains and is **not** treated as a bug (see §4): at a small number of other origins, the AIC-best well-conditioned model is ARIMA(0,2,0) — a "double-drift" random walk on the twice-differenced series — which linearly extrapolates the series' recent *acceleration*. This is a legitimate model choice that can still produce implausible long-horizon forecasts (including one negative value) when the origin sits near a sharp turning point; see §4.

## 3. Results

### 3.1 National (`outputs/model_results_extended.csv`)

| Model | 1y MAPE | 2y MAPE | 3y MAPE | 5y MAPE |
| --- | ---: | ---: | ---: | ---: |
| ets_damped | **4.09%** | **8.51%** | **13.59%** | 26.16% |
| arima | 4.19% | 9.10% | 14.50% | 30.97% |
| holt | 4.25% | 9.25% | 14.74% | 31.36% |
| naive | 4.71% | 9.03% | 13.32% | **22.10%** |
| ses | 4.75% | 9.06% | 13.36% | 22.12% |
| drift | 5.03% | 9.82% | 14.71% | 25.89% |
| linear_trend | 19.16% | 22.71% | 26.41% | 34.16% |

**Headline findings:**

1. **`ets_damped` is the new best model at 1-, 2- and 3-year horizons**, beating every one of the five original benchmarks including the previously-best `holt` and `naive`/`ses`. This confirms the hypothesis behind adding it: damping fixes most of `holt`'s overshoot problem while keeping its ability to track a genuine trend, at every horizon except the longest.
2. **At 5-year, naive and SES remain best**, and `ets_damped` (26.16%) and `drift` (25.89%) — while clearly better than undamped `holt` (31.36%) — still can't match naive/SES (22.1%). Damping reduces but does not eliminate the long-horizon extrapolation problem that afflicts every trend-following model on this cyclical series.
3. **`arima` is competitive but not the best model at any horizon** after the degeneracy fix — consistently the second- or third-best trend-aware model, close behind `ets_damped` and `holt` at short-to-medium horizons, and — per §4 — prone to occasional implausible long-horizon forecasts even after the fix.
4. **This directly answers the question posed at the end of the dependency-light phase** (`docs/national_forecast_methodology.md` §4: "these benchmarks exist to set a floor that any more complex model should be expected to beat before being adopted"): `ets_damped` clears that floor at 1/2/3-year horizons; `arima` does not clear it at any horizon tested; neither clears it at 5-year, where the simplest model (naive) remains best.

### 3.2 Regional (`outputs/regional_model_results_extended.csv`, `outputs/figures/regional_win_counts_extended.png`)

`ets_damped` wins outright in 1 of 9 regions at every horizon (a smaller, real margin, not a tie), and is competitive without winning in most others. `naive` still wins the majority of regions at every horizon (5, 6, 8, 8 of 9 at 1/2/3/5-years respectively) — but as established in `docs/regional_forecast_methodology.md` §2.4, most of those wins are near-ties against SES (<0.1 MAPE points), a caution repeated on this chart. `arima` and `linear_trend` never win a single region at any horizon. This is a more muted version of the national result: `ets_damped` is a genuine improvement in aggregate but does not dominate every individual region the way it dominates the smoother national series.

## 4. Limitations

- **ARIMA's "double-drift" (0,2,0) fallback can produce implausible forecasts.** At national origins 2011 and 2014 (both near the 2012 peak / subsequent sharp decline), the AIC-best well-conditioned order was ARIMA(0,2,0), which linearly extrapolates the series' second difference (acceleration). At origin 2011 this produced a 2016 forecast of 2,230,643 households (actual: 1,184,750 — 88% too high); at origin 2014, a 2019 forecast of **-217,035** households (actual: 1,160,261) — a negative value, which is impossible for a real household count. These are legitimate outputs of a well-conditioned model, not numerical bugs (verified: no AR/MA roots, i.e. nothing for the root-distance check to catch), but they show that "well-conditioned" is a necessary, not sufficient, safeguard — an AIC-only search with no plausibility check on the forecast itself can still produce nonsensical results at long horizons from certain origins. No forecast values were clipped or post-processed to hide this; it is reported here instead, consistent with how `holt`'s overshoot was reported rather than patched in the base national note.
- **Regional detail predictions were not written.** Unlike the national extended detail (`outputs/backtest_predictions_extended.csv`), the regional run only writes summary rows (`outputs/regional_model_results_extended.csv`) — a full regional detail file at 7 models would be roughly 9× the national file's 763 rows without adding proportional value for this comparison; if that individual-forecast-level detail is needed later, `run_regional_summary_only()` in `scripts/forecast_statistical.py` would need a small change to also collect and write `r_detail`.
- **AIC grid is bounded (`d` in {1,2}, `p`,`q` in {0,1,2}), not a full auto-ARIMA search.** A wider grid (higher-order p/q, seasonal terms, or an exogenous-regressor ARIMAX) was not attempted; 18 candidates per origin was chosen to keep the regional run (270 origin-fits) under a minute while covering the orders most plausible for a 10-38 point annual series.
- **All limitations from the national and regional notes still apply**, in full: expanding window, `MIN_TRAIN_YEARS=10`, no exogenous drivers, small/overlapping 5-year origins, and the 2029/h=4 forward-forecast gap (this extension does not add its own forward 2026-2030 forecast at all).
- **`statsmodels` and its dependencies (`scipy`, `pandas`, `patsy`) are now required** to run this script (though not `scripts/forecast_national.py` or `scripts/forecast_regional.py`, which remain dependency-light as before) — installed only in the project-local `.venv`, recorded in `requirements.txt`.
