# hailie-waiting-list-forecast

Analysis and forecasting of households on local authorities' housing waiting lists in England (MHCLG Live Table 600, 1987–2025).

> **Current phase: data-quality and methodology validation.** The forecasts in this repository are exploratory outputs, not validated estimates for operational or planning use. The immediate priority is to prove the Table 600 source-to-output chain, understand publisher imputations and missing values, reconcile changing local-authority geography, and complete external consistency checks before any forecast is treated as a result.

**Start here:** `docs/data_quality_audit.md` for the current evidence and open decisions, then `docs/project_plan_plain_english.md` for the route through the project. `outputs/report.html` preserves the exploratory forecasting work completed so far, but it should be read as provisional.

## What's in this repository

| Stage | Script | Output |
| --- | --- | --- |
| Source audit | `scripts/audit_table_600.py` | Console: original ODS → CSV extract → processed-data checks, source marker/imputation counts, and regional-total reconciliation |
| Data intake | `scripts/prepare_data.py` | `data/processed/*.csv` — raw MHCLG extracts reshaped to long format |
| Validation | `scripts/validate_national.py` | Console: England-total figures checked against the raw extract |
| Exploratory analysis | `scripts/explore_national.py` | `outputs/figures/england_*.png`, `regional_waiting_list_trends.png` |
| National forecasting | `scripts/forecast_national.py` | `outputs/model_results.csv`, `outputs/backtest_predictions.csv` (naive, drift, linear-trend, SES, Holt) |
| Regional forecasting | `scripts/forecast_regional.py` | `outputs/regional_model_results.csv` (same 5 models, per region) |
| Statistical models | `scripts/forecast_statistical.py` | `outputs/model_results_extended.csv`, `outputs/regional_model_results_extended.csv`, `outputs/national_forecast_2026_2030_extended.csv`, `outputs/regional_forecast_2026_2030_extended.csv`, `outputs/regional_forecast_selected_2026_2030.csv`, `outputs/regional_forecast_change_2025_2030.csv` (+ ARIMA, damped-trend ETS) |
| Report | `scripts/build_report.py` | **`outputs/report.html`** — the consolidated deliverable |

Findings, methodology, and honest limitations for each stage are written up in `docs/`:

- `data/README.md` — source, columns, and transformations for the processed data
- `docs/data_quality_audit.md` — current validation status, evidence, Jose's four questions, and the gate before modelling resumes
- `docs/missing_data_and_imputation.md` - MHCLG missing-data and imputation methodology, Table 600 source imputations, national reconciliation, and implications for forecast uncertainty

- `docs/project_plan_plain_english.md` — the whole project plan without modelling jargon
- `docs/initial_feasibility_note.md` — Week 1 QA findings, boundary-change and suppression-code handling
- `docs/national_validation.md` — England-total figures checked against the raw extract
- `docs/initial_eda_findings.md` — descriptive read of the national and regional series
- `docs/national_forecast_methodology.md` — the 5 dependency-light benchmarks, backtest design, results
- `docs/regional_forecast_methodology.md` — the same backtest extended to the 9 English regions
- `docs/statistical_models_methodology.md` — adding ARIMA and damped-trend ETS, including a real bug found and fixed during development

## Running the pipeline

Two scripts (`prepare_data.py`, `validate_national.py`) use only the Python standard library. The rest need the project-local virtual environment (matplotlib for charts; statsmodels for ARIMA/ETS):

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then, in order:

```
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python3 scripts/explore_national.py
.venv/bin/python3 scripts/forecast_national.py
.venv/bin/python3 scripts/forecast_regional.py
.venv/bin/python3 scripts/forecast_statistical.py
python3 scripts/build_report.py
```

Every script re-derives its own QA checks and prints them to stdout; every output file is reproducible from the raw data in `data/raw/` and `data/extracts/`, which are never modified by any script. Run the source audit before rebuilding or interpreting downstream outputs.

## Exploratory forecasting result

In the existing backtest, no single forecasting model wins at every horizon. A damped-trend exponential smoother is most accurate 1–2 years out, while carrying the last observed value forward is hardest to beat from 3 years out. This is a useful feasibility finding, not a validated forecast: the analysis predates completion of the source, geography, comparability and external-consistency audit. See `outputs/report.html` for the exploratory work completed so far.

## Data source

MHCLG Live Table 600, "Number of households on local authorities' housing waiting lists (housing register), by district," retrieved 7 August 2026 from [GOV.UK: Live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies). See `data/README.md` for the full source, columns, and transformation reference, and its Limitations section for what this measure does and doesn't capture.
