# HAILIE social housing waiting-list forecast

Final reproducible analysis of social housing waiting-list demand using
households on local-authority housing registers in England from MHCLG Live
Table 600, 1987–2025.

## Project status

**Final national and nine-region modelling is complete.** The repository
contains the validated data pipeline, seven-model rolling-origin comparison,
final 2026–2028 forecasts, cautious 2026–2030 extensions, empirical 80% and 95%
prediction intervals, a supervisor concern-to-evidence matrix and a
self-contained final report.

Open the canonical deliverable:

- [Final HAILIE report and decision dashboard](outputs/HAILIE_final_report.html)

Authoritative full-precision results are under [`outputs/final/`](outputs/final/).
Earlier exploratory scripts and results are retained only under
[`archive/forecasting_phase/`](archive/forecasting_phase/) and are not used by
the final report.

## Headline result

England had **1,340,527 households** on local-authority housing registers in
2025. The selected damped-Holt model gives a modest increase to approximately
**1,359,901 in 2028** (+1.4%). Its 2028 empirical 80% prediction interval is
**1,169,171–1,667,851**, so the analysis does not support a confident claim of
a large near-term rise or fall.

At five years, the naive model outperformed trend extrapolation on the primary
MAE criterion and is used as a cautious extension. Regional models are selected
independently because model performance differs across the nine regions.

## Why the result is defensible

- The raw MHCLG source file is retained with documented provenance.
- The nine regions reconcile exactly to England in all 39 years.
- Publisher markers, replacements and imputation are explicitly audited; the project introduced no new numerical imputations.
- Six London periods were independently checked against LG Inform and matched after year-label alignment.
- Seven models are evaluated using expanding-window rolling-origin backtesting without future-data leakage.
- MAE is the pre-specified primary selection metric; RMSE, MAPE and bias are retained as diagnostics.
- The primary and five-year models are selected separately and their overlapping forecasts are compared directly.
- History-window sensitivity is tested by restarting the national analysis in 1998 and 2005; the changing near-term winner is reported rather than hidden.
- Point forecasts are presented with empirical uncertainty and clear limitations.

## Start here

| Purpose | Location |
|---|---|
| Final report, regional selector and supervisor review evidence | [`outputs/HAILIE_final_report.html`](outputs/HAILIE_final_report.html) |
| Canonical forecasting methodology | [`docs/final_forecast_methodology.md`](docs/final_forecast_methodology.md) |
| Data-quality and provenance evidence | [`docs/data_quality_audit.md`](docs/data_quality_audit.md) |
| Missing-data and publisher-imputation evidence | [`docs/missing_data_and_imputation.md`](docs/missing_data_and_imputation.md) |
| Final report design and review record | [`docs/report_design_and_review.md`](docs/report_design_and_review.md) |
| Machine-readable final results and run manifest | [`outputs/final/`](outputs/final/) |

## Reproduce the final submission

Python 3.9 or later is supported.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python scripts/generate_final_outputs.py
python3 scripts/build_report.py
python3 scripts/validate_final_submission.py
```

The final generator computes all national and regional backtests, asserts the
reviewed model selections and writes stable CSVs to `outputs/final/`. The report
builder consumes only those files and does not read archived exploratory data.

## Repository structure

| Location | Purpose |
|---|---|
| `data/raw/` | Retained MHCLG source file |
| `data/processed/` | Validated long-format analytical datasets |
| `scripts/prepare_data.py` | Source preparation |
| `scripts/validate_national.py` | Reconciliation and validation checks |
| `scripts/forecast_national_final.py` | Final national forecasting functions |
| `scripts/forecast_regional_final.py` | Final regional forecasting functions |
| `scripts/generate_final_outputs.py` | Authoritative metrics, selection, forecast and interval generation |
| `scripts/build_report.py` | Self-contained final report generator |
| `scripts/validate_final_submission.py` | Final output and report QA |
| `docs/` | Methodology, data-quality evidence and decision records |
| `outputs/final/` | Authoritative machine-readable results |
| `archive/forecasting_phase/` | Superseded exploratory work retained for transparency |

## Important limitations

The Table 600 count is not a complete measure of housing need. Register
administration, policy changes and local-authority practice can affect the
series. The models contain no causal or external predictors, longer-horizon
backtests are based on small overlapping samples, and the empirical intervals
capture historical model error rather than every future or source-data
uncertainty. Local-authority forecasts were excluded because changing
geographies were not reconciled into continuous current-boundary series.
