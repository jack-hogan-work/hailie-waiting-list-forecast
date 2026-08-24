# Hailie Waiting List Forecast

Analysis of households on local authorities' housing waiting lists in England using MHCLG Live Table 600 (1987–2025).

## Project overview

This project builds a reproducible data pipeline to analyse housing waiting list trends across England.

The main objectives are:

- acquiring and documenting the source data
- cleaning and transforming the dataset
- validating consistency across years and local authorities
- producing transparent exploratory analysis

Forecasting approaches have been explored as a secondary phase. These models are currently treated as exploratory outputs and require further validation before being used for decision-making.

## Current project phase

**Current focus: data quality, validation, and analytical foundations.**

The immediate goal is to establish a clean and reproducible analytical dataset with documented assumptions and limitations.

## Start here

- `docs/data_quality_audit.md` — current validation evidence and open decisions
- `docs/project_plan_plain_english.md` — project workflow and objectives

## Repository structure

| Stage | Location | Purpose |
|---|---|---|
| Source audit | `scripts/audit_table_600.py` | Checks source data extraction and provenance |
| Data preparation | `scripts/prepare_data.py` | Cleans and reshapes raw MHCLG extracts |
| Validation | `scripts/validate_national.py` | Checks consistency against source totals |
| Exploratory analysis | `scripts/explore_national.py` | Produces descriptive analysis and figures |
| Forecasting | `scripts/forecast_*.py` | Exploratory modelling experiments |
| Reporting | `scripts/build_report.py` | Builds consolidated report |

## Documentation

Key documentation is stored in `docs/`:

- data quality audit
- project plan
- validation findings
- exploratory analysis findings
- forecasting methodology

## Running the pipeline

Create the environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
.venv/bin/python3 scripts/explore_national.py
.venv/bin/python3 scripts/forecast_national.py
.venv/bin/python3 scripts/forecast_regional.py
.venv/bin/python3 scripts/forecast_statistical.py
python3 scripts/build_report.py
