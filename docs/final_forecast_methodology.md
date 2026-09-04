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
- Reference dates: 1 April up to 2018 and 31 March from 2019 onward.
- Data retrieved: 7 August 2026.

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

Although seven candidate labels are evaluated, the restricted ARIMA search
selects `(0,1,0)` on this series and simple exponential smoothing converges to
alpha approximately 1, so both reproduce the naive carry-forward in many
windows. They should not be read as seven wholly distinct forecasts.

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

Selection differences are descriptive only. Forecast origins overlap, and no
formal Diebold–Mariano or equivalent test was used; small MAE gaps should not
be treated as statistically significant.

The national primary winner is damped Holt, with mean Y1–Y3 MAE of about
115,961 households. The five-year naive model has MAE of about 306,435 and is
selected over effectively equivalent SES and ARIMA results on parsimony.

## Final national results

| Year | Primary point forecast | 80% interval | 95% diagnostic range |
|---|---:|---:|---:|
| 2026 | 1,348,467 | 1,288,128–1,420,408 | 1,168,582–1,494,999 |
| 2027 | 1,354,819 | 1,183,078–1,510,443 | 1,013,012–1,656,568 |
| 2028 | 1,359,901 | 1,169,171–1,667,851 | 736,752–1,857,482 |

The evidence does not identify a robust national increase or decrease over the
next three years. The damped-Holt model selected on the full 1987–2025 history
gives a central estimate of 1,359,901 households in 2028, 1.4% above 2025, but
naive performs better in both later-history sensitivity windows.

The naive extension holds the 2025 observation constant through 2030. The
2026–2028 differences between the primary and extension tracks are about
7,940, 14,292 and 19,374 households respectively. These differences are small
relative to the empirical prediction intervals and are not materially
contradictory.

The 2029 uncertainty interval uses a separate four-year backtest only for
interval construction. That horizon is not included in the published metrics
CSV, so the interval is a diagnostic extension rather than a separately
validated model-selection result.

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

For six of the nine regions, the primary winner is naive. Their 2028 central
estimates therefore repeat the 2025 observations by construction. This is a
property of the selected carry-forward model, not evidence that the underlying
register counts will remain unchanged. The regional backtests do not support a
strong directional call, so public regional presentation pairs every central
estimate with its selected model and 80% empirical range.

Two source-noted regional comparability breaks should remain visible when these
forecasts are used: Telford & Wrekin stopped operating a housing register from
31 March 2021, affecting the West Midlands and England totals, and Epping
Forest changed its treatment of transfer applicants from 2022–23, affecting the
East of England series. No re-modelling was applied for these breaks.

## Prediction intervals

For a selected model and horizon, the historical rolling-origin forecast
errors at that horizon form an empirical error distribution. The 10th/90th
percentile and 2.5th/97.5th percentile error quantiles are applied to the final
point forecast to produce 80% and 95% empirical ranges. NumPy linear
interpolation is used for sample quantiles in both national and regional
pipelines.

The primary three-year backtest contains only 27 errors. At that sample size,
each 2.5th/97.5th percentile bound is interpolated from the first and second
most extreme observations. Those extremes include periods associated with the
introduction of choice-based lettings around 2003 and qualification changes
following the Localism Act 2011. The 95% ranges are therefore highly sensitive
to a few identifiable historical regime changes and should not be interpreted
as stable 95% probability limits for the next three years.

The public dashboard and briefing show the 80% ranges only. The 95% figures are
retained in this technical methodology, the analytical report and the
machine-readable outputs as diagnostic historical ranges for transparency.
Neither range captures every possible administrative change, source revision,
boundary change, policy or economic shock, or uncertainty associated with
publisher imputation.

## History-window sensitivity

The national comparison was repeated using only 1998–2025 and 2005–2025. The
selected full-history damped-Holt model's later-window performance is shown
explicitly below. Rankings use mean MAE across the one-, two- and three-year
backtests; lower is better.

| History window | Y1–Y3 winner | Winner mean MAE | Damped-Holt mean MAE | Damped-Holt rank | Naive mean MAE |
|---|---|---:|---:|---:|---:|
| 1987–2025 (pre-specified full history) | Damped Holt | 115,961 | 115,961 | 1 of 7 | 124,554 |
| 1998–2025 | Naive | 120,905 | 134,013 | 3 of 7 | 120,905 |
| 2005–2025 | ARIMA | 73,288 | 108,166 | 5 of 7 | 73,809 |

Naive therefore outperforms damped Holt in both later-history windows,
especially in the 2005–2025 window. The 2005 ARIMA advantage over naive is
small (mean Y1–Y3 MAE about 73,288 versus 73,809 households). The naive model
also remains the five-year winner in both shorter windows.

These MAEs are not directly comparable across windows because the later
windows contain fewer and different forecast origins. The result shows that the
identity of the best near-term model is sensitive to historical coverage. It
does not change the preserved full-history selection or its central estimate,
but it means the evidence does not support a robust directional national claim.

## Limitations

- The register count is not a complete measure of housing need.
- Register cleanses can change reported counts without an equivalent change in underlying need.
- No causal claim is made; all models are univariate forecasts.
- Longer-horizon backtest origins overlap and are not independent trials.
- Regional models are independent and are not constrained to sum to the national forecast.
- The alternative-window check is not a formal causal analysis of individual policy breaks.
- The regional 2026–2030 extension contains point forecasts without calculated uncertainty bands and should not be used as a standalone planning forecast.

The full-precision metrics, selections, forecasts and reproducibility hashes
are stored in `outputs/final/`.
