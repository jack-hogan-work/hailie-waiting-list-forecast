# National Forecasting Plan

> **Plan completed.** This document preserves the pre-modelling specification.
> The final implementation and results are recorded in
> `docs/final_forecast_methodology.md` and `outputs/final/`.

## Purpose

This note sets out the current forecasting approach agreed in principle for the next stage of the project.

The immediate objective is to forecast the annual number of households on local-authority housing waiting lists in England using MHCLG Live Table 600.

The national forecast will be developed first. Regional forecasts will then be considered where the data and model performance support them.
## Candidate models and model selection

Seven forecasting approaches will be compared:

- naive (last observed value);
- drift;
- linear trend;
- simple exponential smoothing (SES);
- Holt's linear trend;
- damped-trend exponential smoothing (ETS);
- ARIMA.

The final approach will be chosen using out-of-sample rolling-origin performance rather than in-sample fit alone.

For the initial 3-year forecast, model performance will be assessed across the 1-, 2- and 3-year horizons together. MAE will be the primary error measure, with RMSE, MAPE and mean-error bias used as supporting diagnostics.

The 5-year exercise will then be evaluated separately. If a different modelling approach is preferred at 5 years, its overlapping Y1, Y2 and Y3 forecasts will be compared directly with those from the 3-year approach before the final forecast is reported.
## In-sample and out-of-sample evaluation

The project does not rely on one fixed train/test split. Instead, forecasting performance is evaluated using an expanding-window rolling-origin design.

At each forecast origin, the in-sample dataset contains every annual observation from 1987 up to and including that origin year. The forecast is then evaluated only against later observations that were not used to fit the model.

The current evaluation periods are:

- 1-year horizon: origins 1996–2024, evaluated against 1997–2025;
- 2-year horizon: origins 1996–2023, evaluated against 1998–2025;
- 3-year horizon: origins 1996–2022, evaluated against 1999–2025;
- 5-year horizon: origins 1996–2020, evaluated against 2001–2025.

The first training window is therefore 1987–1996 (10 annual observations). This expanding-window structure gives repeated genuinely out-of-sample tests while retaining as much of the short annual series as possible.
## Scope beyond the national baseline

The national Table 600 forecast will be established first.

Table 602 will not replace Table 600. It will be considered later as a possible augmenting variable because it measures lettings flow rather than the stock of households on waiting lists. It will only be included if it adds useful predictive information and can be used without introducing information that would not have been available at the forecast origin.

Other datasets, such as deprivation, housing supply or demographic indicators, will also be considered only after the national baseline forecast is established.

Regional forecasts will follow the national analysis where the data and out-of-sample model performance are sufficiently reliable.
## Initial forecast output and uncertainty

The first decision-ready output will be the national England forecast.

This will include:

- point forecasts for the first 3 years;
- an extension to 5 years;
- prediction intervals around the forecasts;
- out-of-sample performance metrics for the selected approach;
- and a clear note on data-quality and imputation limitations.

Prediction intervals will be interpreted as model-based uncertainty. They will not be presented as capturing all uncertainty in the underlying administrative data, because publisher imputations and source-data quality introduce additional uncertainty that is documented separately in `missing_data_and_imputation.md`.

The national forecast and its prediction intervals will be reviewed first before deciding what additional regional or explanatory outputs are appropriate.
## Dataset freeze

The national modelling dataset is now frozen for the final forecasting stage.

- Source: MHCLG Live Table 600
- Geography: England
- Period: 1987–2025
- Annual observations: 39
- Missing national values: 0
- National validation: PASS
- Full Table 600 source-to-output audit: PASS
- Regional-to-national reconciliation: PASS for all 39 years

No further cleaning, imputation or transformation will be applied to the national modelling series unless a genuine source or processing error is identified.
