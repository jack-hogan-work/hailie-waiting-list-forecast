# Authoritative final outputs

This directory contains the machine-readable results used by
`outputs/HAILIE_final_report.html`. These files are generated from the frozen
1987–2025 processed series by `scripts/generate_final_outputs.py` and do not use
anything under `archive/forecasting_phase/`.

## National outputs

- `national_model_metrics.csv`: all seven models at the 1-, 2-, 3- and 5-year horizons; MAE is primary and RMSE, MAPE and bias are diagnostics.
- `national_model_selection.csv`: the selected 2026–2028 primary model and 2026–2030 extension model, with their selection rules and scores.
- `national_forecast_2026_2028.csv`: final damped-Holt point forecasts with empirical 80% and 95% prediction intervals.
- `national_extension_2026_2030.csv`: cautious naive-model extension with empirical 80% and 95% prediction intervals.
- `national_history_sensitivity.csv`: diagnostic model performance after restarting the national history in 1998 and 2005, used to test how dependent selection is on the earliest observations.

## Regional outputs

- `regional_model_metrics.csv`: all seven models, four horizons and nine regions.
- `regional_model_selection.csv`: one consistent Y1–Y3 model and one Y5 model for each region, selected using MAE.
- `regional_forecast_2026_2028.csv`: 27 primary forecasts with empirical 80% and 95% prediction intervals.
- `regional_extension_2026_2030.csv`: 45 longer-horizon point forecasts. Prediction intervals are intentionally not added here because they were not part of the reviewed regional extension method.

`run_manifest.json` records the model configuration, runtime versions and
SHA-256 hashes of the source data and final modelling code.

Numbers are stored at greater precision than displayed in the report. Rounding
is applied only for presentation.
