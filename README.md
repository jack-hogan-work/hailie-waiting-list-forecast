# hailie-waiting-list-forecast

Analysis and forecasting of households on local authorities' housing waiting lists in England (MHCLG Live Table 600, 1987–2025).

**Start here:** `outputs/report.html` — a self-contained report consolidating the national trend, the regional breakdown, and a leakage-free rolling-origin backtest of seven forecasting models. Open it in any browser; no server or dependencies required.

## What's in this repository

| Stage | Script | Output |
| --- | --- | --- |
| Data intake | `scripts/prepare_data.py` | `data/processed/*.csv` — raw MHCLG extracts reshaped to long format |
| Validation | `scripts/validate_national.py` | Console: England-total figures checked against the raw extract |
| Exploratory analysis | `scripts/explore_national.py` | `outputs/figures/england_*.png`, `regional_waiting_list_trends.png` |
| National forecasting | `scripts/forecast_national.py` | `outputs/model_results.csv`, `outputs/backtest_predictions.csv` (naive, drift, linear-trend, SES, Holt) |
| Regional forecasting | `scripts/forecast_regional.py` | `outputs/regional_model_results.csv` (same 5 models, per region) |
| Statistical models | `scripts/forecast_statistical.py` | `outputs/model_results_extended.csv`, `outputs/regional_model_results_extended.csv` (+ ARIMA, damped-trend ETS) |
| Report | `scripts/build_report.py` | **`outputs/report.html`** — the consolidated deliverable |

Findings, methodology, and honest limitations for each stage are written up in `docs/`:

- `data/README.md` — source, columns, and transformations for the processed data
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
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python3 scripts/explore_national.py
.venv/bin/python3 scripts/forecast_national.py
.venv/bin/python3 scripts/forecast_regional.py
.venv/bin/python3 scripts/forecast_statistical.py
python3 scripts/build_report.py
```

Every script re-derives its own QA checks and prints them to stdout; every output file is reproducible from the raw data in `data/raw/` and `data/extracts/`, which are never modified by any script.

## Headline result

No single forecasting model wins at every horizon. A damped-trend exponential smoother is most accurate 1–2 years out; the simplest possible model — carrying the last observed value forward — is hardest to beat from 3 years out, because England's waiting-list total is cyclical rather than trending, and every trend-aware model eventually overshoots when the cycle turns. See `outputs/report.html` for the full picture.

## Data source

MHCLG Live Table 600, "Number of households on local authorities' housing waiting lists (housing register), by district," retrieved 7 August 2026 from [GOV.UK: Live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies). See `data/README.md` for the full source, columns, and transformation reference, and its Limitations section for what this measure does and doesn't capture.
