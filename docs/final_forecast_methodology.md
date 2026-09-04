# Final forecasting methodology and decisions

## Status and scope

This is the canonical methodology for the final HAILIE social housing
waiting-list forecast.
It supersedes the exploratory forecasting material retained under
`archive/forecasting_phase/` and the historical development sections in
`docs/statistical_models_methodology.md`.

The outcome modelled is the published annual number of households on local
authority housing registers. The primary forecast covers 2026–2028 for England
and the nine English regions. A separately selected, deliberately cautious
extension covers 2026–2030.

## Data used

- Source: MHCLG Live Table 600.
- Geography: England and nine English regions.
- Frequency: annual.
- Modelling period: 1987–2025.
- Observations per series: 39.
- Missing England observations: none.
- Additional numerical imputations by this project: none.
- Regional reconciliation: the nine regions sum to England in all 39 years.

Publisher-supplied imputations, suppression markers and genuine zeroes are
audited separately in `docs/missing_data_and_imputation.md`. The model treats
published replacement values as observations because they are part of the
official series, but the resulting source uncertainty is not claimed to be
captured by the model prediction intervals.

## Candidate models

Seven deliberately interpretable candidates were evaluated for every series:

1. Naive: hold the last observation constant.
2. Drift: extend the average historical change.
3. Linear trend: extrapolate an ordinary least-squares time trend.
4. Simple exponential smoothing: estimate a changing level without a trend.
5. Holt linear trend: estimate a level and unrestricted trend.
6. Damped Holt trend: allow a trend that gradually flattens.
7. ARIMA: select by AIC from `(0,1,0)`, `(1,1,0)`, `(0,1,1)` and `(1,1,1)` within each training window; failed or non-converged fits are excluded.

Seasonal models were not used because the observations are annual and contain
no within-year seasonal frequency. The final models use the annual register
series directly and are interpreted as statistical forecasts rather than
causal estimates.

## Rolling-origin backtesting

The comparison uses expanding-window rolling-origin evaluation. The first
origin is 1996, after ten annual training observations. At each origin the
model is fitted only to data available at that time.

| Horizon | Origins | Forecasts per series |
|---|---|---:|
| 1 year | 1996–2024 | 29 |
| 2 years | 1996–2023 | 28 |
| 3 years | 1996–2022 | 27 |
| 5 years | 1996–2020 | 25 |

A four-year backtest is used only to estimate the 2029 uncertainty interval
for the national extension. It is not used for model selection.

## Metrics and selection rules

Mean absolute error (MAE) is the primary metric because it expresses typical
forecast error directly in households and is less dominated by a small number
of large misses than RMSE. RMSE, MAPE and signed mean error (bias) are retained
as supporting diagnostics.

The rules were applied consistently:

- Primary 2026–2028 model: lowest average MAE across the 1-, 2- and 3-year backtests.
- 2026–2030 extension model: lowest 5-year MAE.
- Tie-break: prefer the simpler, more interpretable model where performance is equal or effectively indistinguishable.

The national primary winner is damped Holt, with mean Y1–Y3 MAE of about
115,961 households. The five-year naive model has MAE of about 306,435 and is
selected over effectively equivalent SES and ARIMA results on parsimony.

## Final national results

| Year | Primary point forecast | 80% interval | 95% interval |
|---|---:|---:|---:|
| 2026 | 1,348,467 | 1,288,128–1,420,408 | 1,168,582–1,494,999 |
| 2027 | 1,354,819 | 1,183,078–1,510,443 | 1,013,012–1,656,568 |
| 2028 | 1,359,901 | 1,169,171–1,667,851 | 736,752–1,857,482 |

The forecast rises from 1,340,527 households in 2025 to approximately 1.36
million in 2028, an increase of about 1.4%. This is a modest direction signal,
not evidence for a large or certain rise.

The naive extension holds the 2025 observation constant through 2030. The
2026–2028 differences between the primary and extension tracks are about
7,940, 14,292 and 19,374 households respectively. These differences are small
relative to the empirical prediction intervals and are not materially
contradictory.

## Final regional selections

| Region | Primary 2026–2028 model | Extension 2026–2030 model |
|---|---|---|
| East Midlands | ARIMA | Naive |
| East of England | Naive | Naive |
| London | Naive | Naive |
| North East | Naive | ARIMA |
| North West | Naive | Naive |
| South East | Damped Holt | Damped Holt |
| South West | Drift | Drift |
| West Midlands | Naive | Naive |
| Yorkshire and The Humber | Naive | Naive |

One model is selected for all three primary forecast years in each region. This
avoids switching methods between adjacent years merely because one individual
horizon produces a marginally lower error.

## Prediction intervals

For a selected model and horizon, the historical rolling-origin forecast
errors at that horizon form an empirical error distribution. The 10th/90th
percentile and 2.5th/97.5th percentile error quantiles are applied to the final
point forecast to produce 80% and 95% intervals. NumPy linear interpolation is
used for sample quantiles in both national and regional pipelines.

These intervals capture historically observed model error. They do not fully
capture administrative change, source revisions, boundary changes, policy
shocks, economic shocks or uncertainty associated with publisher imputation.

## History-window sensitivity

The national comparison was repeated using only 1998–2025 and 2005–2025. The
primary Y1–Y3 winner changes from damped Holt on the pre-specified full history
to naive from 1998 and ARIMA from 2005. The naive model remains the five-year
winner in both shorter windows. The 2005 ARIMA advantage over naive is small
(mean Y1–Y3 MAE about 73,288 versus 73,809 households).

These MAEs are not directly comparable across windows because the later
windows contain fewer and different forecast origins. The result shows that the
identity of the best near-term model is sensitive to historical coverage. It
does not overturn the full-history pre-specified selection, but it strengthens
the cautious interpretation and the decision to foreground uncertainty.

## Limitations

- The register count is not a complete measure of housing need.
- Register cleanses can change reported counts without an equivalent change in underlying need.
- No causal claim is made; all models are univariate forecasts.
- Longer-horizon backtest origins overlap and are not independent trials.
- Regional models are independent and are not constrained to sum to the national forecast.
- The alternative-window check is not a formal causal analysis of individual policy breaks.

The full-precision metrics, selections, forecasts and reproducibility hashes
are stored in `outputs/final/`.
