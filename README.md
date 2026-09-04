# HAILIE social housing waiting-list forecast

Final reproducible analysis of social housing waiting-list demand using
households on local-authority housing registers in England from MHCLG Live
Table 600, 1987–2025.

## Project status

**Final national and nine-region modelling is complete.** The repository
contains the validated data pipeline, seven-model rolling-origin comparison,
final 2026–2028 forecasts, cautious 2026–2030 extensions, public empirical 80%
ranges, a standalone interactive dashboard and a self-contained final report.
Diagnostic 95% ranges are retained in the technical report and machine-readable
outputs, with an explicit small-sample warning.

Open the canonical deliverable:

- [Interactive HAILIE forecast dashboard](outputs/HAILIE_dashboard.html)
- [Five-page public briefing](outputs/pdf/HAILIE_social_housing_waiting_list_briefing.pdf)
- [Final HAILIE analytical report](outputs/HAILIE_final_report.html)

Authoritative full-precision results are under [`outputs/final/`](outputs/final/).
Earlier exploratory scripts and results are retained only under
[`archive/forecasting_phase/`](archive/forecasting_phase/) and are not used by
the final report.

## Headline result

England had **1,340,527 households** on local-authority housing registers in
2025. The evidence does not identify a robust national increase or decrease
over the next three years. The model selected on the full 1987–2025 history,
damped Holt, gives a central estimate of **1,359,901 in 2028** (+1.4%). However,
naive performs better when validation is restricted to both later-history
windows. Damped Holt ranks **3rd of 7** for 1998–2025 (mean Y1–Y3 MAE 134,013,
versus 120,905 for naive) and **5th of 7** for 2005–2025 (108,166, versus 73,809
for naive). Its 2028 empirical 80% prediction interval is
**1,169,171–1,667,851**.

At five years, the naive model outperformed trend extrapolation on the primary
MAE criterion and is used as a cautious extension. Regional models are selected
independently because model performance differs across the nine regions. For
six of nine regions, backtesting selected a naive model that carries the 2025
observation forward. Those repeated central estimates are properties of the
selected models, not evidence that regional waiting lists will remain
unchanged. The regional evidence does not support a strong directional call,
and each public 2028 regional estimate is paired with its 80% range.

## Why the result is defensible

- The raw MHCLG source file is retained with documented provenance.
- The nine regions reconcile exactly to England in all 39 years.
- Publisher markers, replacements and imputation are explicitly audited; the project introduced no new numerical imputations.
- Six London periods were independently checked against LG Inform and matched after year-label alignment.
- Seven candidate labels are evaluated using expanding-window rolling-origin backtesting without future-data leakage; restricted ARIMA and SES often collapse to the naive carry-forward on this series, so they are not seven wholly distinct forecasts.
- MAE is the pre-specified primary selection metric; RMSE, MAPE and bias are retained as diagnostics.
- The primary and five-year models are selected separately and their overlapping forecasts are compared directly.
- History-window sensitivity is tested by restarting the national analysis in 1998 and 2005; the changing near-term winner is reported rather than hidden.
- Six naive regional carry-forwards are identified as model properties, with 80% ranges shown beside all regional central estimates.
- Point forecasts are presented with empirical uncertainty and clear limitations.

## Start here

| Purpose | Location |
|---|---|
| Interactive national and regional dashboard | [`outputs/HAILIE_dashboard.html`](outputs/HAILIE_dashboard.html) |
| Five-page publication briefing | [`outputs/pdf/HAILIE_social_housing_waiting_list_briefing.pdf`](outputs/pdf/HAILIE_social_housing_waiting_list_briefing.pdf) |
| Final analytical report | [`outputs/HAILIE_final_report.html`](outputs/HAILIE_final_report.html) |
| Canonical forecasting methodology | [`docs/final_forecast_methodology.md`](docs/final_forecast_methodology.md) |
| Data-quality and provenance evidence | [`docs/data_quality_audit.md`](docs/data_quality_audit.md) |
| Missing-data and publisher-imputation evidence | [`docs/missing_data_and_imputation.md`](docs/missing_data_and_imputation.md) |
| Machine-readable final results and run manifest | [`outputs/final/`](outputs/final/) |

## Reproduce the published analysis

Python 3.9 or later is supported.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python scripts/generate_final_outputs.py
python3 scripts/build_dashboard.py
python3 scripts/build_report.py
.venv/bin/python scripts/build_public_charts.py
.venv/bin/python scripts/build_public_briefing.py
python3 scripts/validate_final_submission.py
```

The final generator computes all national and regional backtests and writes
stable CSVs to `outputs/final/`. Add `--check-regression` when you want the
published model selections to be checked as a regression guard; the normal
reproduction path still produces outputs and reports any changed selection in
the resulting files. The report builder consumes only those files and does not
read archived exploratory data.

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
| `scripts/build_dashboard.py` | Standalone interactive dashboard generator |
| `scripts/build_report.py` | Self-contained final report generator |
| `scripts/build_public_charts.py` | Publication chart generator |
| `scripts/build_public_briefing.py` | Five-page public PDF generator |
| `scripts/validate_final_submission.py` | Final output and report QA |
| `docs/` | Methodology, data-quality evidence and decision records |
| `outputs/final/` | Authoritative machine-readable results |
| `archive/forecasting_phase/` | Superseded exploratory work retained for transparency |

## Important limitations

The Table 600 count is not a complete measure of housing need. Separate
housing-association waiting lists are not included; applicants may appear on
more than one authority register, and the publisher says periodic reviews and
duplicate listings mean the total likely overstates households still requiring
social housing at any one time. Register administration, policy changes and
local-authority practice can affect the series. The forecasts are statistical
rather than causal, longer-horizon backtests are based on small overlapping
samples, and the empirical intervals capture historical model error rather than
every future or source-data uncertainty. The source reference date is 1 April
up to 2018 and 31 March from 2019 onward. The public dashboard and briefing
show 80% ranges only. The wider 95% ranges remain available as diagnostic
historical ranges in the technical report, but their tails are too dependent on
a few extreme observations to be treated as stable probability limits.
