# Missing Data, Imputation and National Reconciliation

## Purpose

This note documents how missing, suppressed and imputed values are handled in MHCLG Local Authority Housing Statistics (LAHS), how those values appear in Live Table 600, and how the published England total is treated in this project.

The aim is to distinguish clearly between:

- values originally reported by local authorities;
- values suppressed or marked as unavailable/not applicable;
- imputations made by MHCLG before publication;
- and transformations made by this repository.

The repository does not create new imputations. It uses the published MHCLG figures and preserves source missing-value markers as missing values during processing.
## MHCLG data quality and imputation process

The latest MHCLG Local Authority Housing Statistics technical notes explain that local-authority returns are checked within the DELTA collection system and are then subject to further validation by MHCLG statisticians.

Where an apparent issue is identified, MHCLG contacts the relevant data provider for clarification or correction. If no response is received, the submitted value may be left unchanged, suppressed, or imputed. Where a figure is considered highly likely to be incorrect, MHCLG may impute a value for the purposes of producing regional and national totals.

MHCLG describes five general approaches to imputation:

1. carrying forward the previous year's value where figures are not expected to change greatly;
2. deriving a value from related sub-categories that have been reported;
3. correcting obvious unit errors where the intended value can be established;
4. suppressing/removing highly anomalous values where clarification cannot be obtained;
5. pro-rating totals across sub-categories using previous-year proportions.

MHCLG states that imputations are identified in the published statistical tables.

Source: MHCLG, *Local Authority Housing Statistics: Technical notes 2024-25*, sections on Data Quality and Imputations, published 12 February 2026.
## What appears in Live Table 600

The source workbook contains an `Imputations` worksheet. The repository audit found 45 publisher-made replacements already embedded in the published data:

- 11 values that were originally `[x]`;
- 8 values that were originally reported as zero;
- 26 values that were originally numeric.

In the local-authority data, the final processed table contains:

- 1,421 `[z]` values represented as missing;
- 2 `[x]` values represented as missing;
- 8 genuine reported zeroes preserved as zero.

The repository does not replace these missing values with estimated values. It preserves the distinction between source-level missing markers, genuine zeroes and values already imputed by MHCLG.
## National reconciliation

The published England total is retained directly from MHCLG Live Table 600 rather than reconstructed from local-authority rows.

The audit confirms that:

- the nine published English regional totals sum exactly to the published England total in all 39 years from 1987 to 2025;
- the original Table 600 workbook and the stored regional CSV extract match cell-for-cell;
- all 390 processed regional records match the published extract after the documented numeric and missing-value conversions;
- the processing step does not introduce any additional imputation.

This means the national modelling series used in the project is a faithful reproduction of the published MHCLG England series.
## Implications for forecasting and uncertainty

The forecasting models will be fitted to the published MHCLG England series, which already incorporates any publisher-level imputations used by MHCLG.

Standard model prediction intervals quantify uncertainty arising from the forecasting model and the historical variation in the observed series. They do not automatically capture additional uncertainty created by source-data quality issues, suppressed values, or publisher imputations.

For that reason:

- the published England series will be used directly rather than reconstructed from incomplete local-authority rows;
- MHCLG imputations and missing-data limitations will be documented alongside the forecasts;
- model performance will be assessed using out-of-sample backtesting;
- where practicable, sensitivity checks will be used to assess whether periods affected by data-quality concerns materially change the forecast;
- prediction intervals will therefore be interpreted as model-based uncertainty, not as a complete measure of all uncertainty in the underlying administrative data.
## Sources and related project evidence

### Official MHCLG sources

- [MHCLG Local Authority Housing Statistics: Technical notes 2024-25](https://www.gov.uk/government/statistics/local-authority-housing-statistics-technical-notes-2024-to-2025/local-authority-housing-statistics-technical-notes-2024-25) — see sections **3 Data collection**, **4 Data quality** and **8 Imputations**.
- [MHCLG Live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies) — source page for **Live Table 600**.

### Repository evidence

- [`data_quality_audit.md`](data_quality_audit.md) — source-to-processed-data audit, source imputations and regional-to-national reconciliation.
- [`national_validation.md`](national_validation.md) — validation of the published England series through the processing pipeline.
- [`../data/README.md`](../data/README.md) — documented transformations and missing-value handling.
- [`../scripts/audit_table_600.py`](../scripts/audit_table_600.py) — reproducible audit script.
- [`../scripts/validate_national.py`](../scripts/validate_national.py) — reproducible national validation script.

