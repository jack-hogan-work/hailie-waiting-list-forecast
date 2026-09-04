# Forecast delivery record

The final forecasting system uses the annual MHCLG Live Table 600 series for
England and the nine English regions, covering 1987–2025.

Delivered components:

- seven transparent candidate models;
- expanding-window rolling-origin evaluation at 1-, 2-, 3- and 5-year horizons;
- MAE-led model selection with RMSE, MAPE and bias retained as diagnostics;
- separate near-term and five-year model selection;
- 2026–2028 core forecasts and 2026–2030 planning extensions;
- empirical 80% and 95% prediction intervals; and
- sensitivity checks using alternative historical starting points.

The complete method is documented in `docs/final_forecast_methodology.md` and
the full-precision results are stored in `outputs/final/`.
