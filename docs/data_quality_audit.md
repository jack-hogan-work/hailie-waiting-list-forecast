# Data Quality and Methodology Audit

> **Final status update — 4 September 2026:** the decision gate below was the
> checkpoint used before final modelling. Its seven conditions have now been
> addressed for national and regional analysis, and forecasting has resumed and
> completed. See `docs/final_forecast_methodology.md` and the José closure table
> in `outputs/HAILIE_final_report.html`. Local-authority forecasting remains
> deliberately excluded because current-boundary continuity was not validated.

**Status at 18 August 2026:** first source audit complete; forecasting remains exploratory.

## Decision gate

The existing forecasts are preserved as feasibility work, but they are not yet suitable for operational or planning use. Forecasting should resume only after the source chain, definitions, geography and intended analytical question are agreed.

## Table 600: first-pass audit complete

`scripts/audit_table_600.py` independently checks the complete source-to-output chain:

- the original `Live_Table_600.ods` Regional and Local Authority worksheets match the stored CSV extracts cell for cell;
- all 390 regional and 14,664 local-authority processed records match the extracts after the documented numeric/missing-value conversion;
- the final local-authority table contains 1,421 `[z]` values, 2 `[x]` values and 8 reported zeroes;
- no negative values are present in either the regional or local-authority series;
- the ODS `Imputations` worksheet contains 45 publisher-made replacements: 11 original `[x]` markers, 8 original zeroes and 26 original numeric values;
- the nine English regions sum exactly to the published England total in all 39 years.

This establishes that the repository faithfully reproduces the published table. It does **not** establish that every published value is an unaltered council return or that the series is comparable over time.

### Three manual traces

| Case | Published extract | Processed long file | Result |
| --- | --- | --- | --- |
| Straightforward: Adur, 2025 | `1,033` | `1033` | Correct numeric conversion; comma removed only. |
| Missing marker: Canterbury, 2024 | `[x]` | blank | Correctly retained as missing, not converted to zero. |
| Reorganisation: Aylesbury Vale / Buckinghamshire | Aylesbury Vale reports `2,096` in 2020 then `[z]`; Buckinghamshire is `[z]` in 2020 then reports `6,179` in 2021 | The two historic codes remain separate, with `[z]` represented as blank | Intake is faithful, but this is not yet a continuous current-boundary Buckinghamshire series. |

### Interpretation risks carried forward

- The measure is households on local-authority housing registers, not all households waiting for social housing or all households in housing need.
- Applicants may appear on more than one authority's register, while existing council tenants seeking a transfer are generally excluded.
- Register reviews, choice-based lettings and changes to local qualification rules can create administrative changes in the series.
- The publisher says the 1987–2004 figures are more prone to error because validation was less rigorous.
- The source flags specific comparability issues for Telford and Wrekin and Epping Forest.
- The 376 historical authority rows map to 296 current LAD24 codes. A current-boundary local series has not yet been constructed or validated.

## Jose's four points

| Point | Evidence/status | Decision |
| --- | --- | --- |
| **Table 600** | Source workbook, extracts and processed files now reconcile exactly. Source definitions, markers and 45 publisher imputations are documented. | Use as the core administrative waiting-list series, subject to the remaining geography and comparability work. |
| **Table 602** | The 25 June 2026 workbook is an England-only annual series of local-authority-owned dwellings let by local authorities, 1981–82 to 2024–25. Latest total lets are 85,229; source notes warn that falling lettings partly reflect stock transfer/sales/demolition and pre-2009–10 data are less certain. | Do not use it to validate or replace Table 600: it is a lettings **flow**, whereas Table 600 is a waiting-list **stock**. Consider it later as national context or a pressure/turnover denominator, with date and scope alignment made explicit. |
| **London / LG Inform** | LG Inform metric 105 is the same LAHS Section C concept. Its London values for 2019/20–2024/25 are 250,922; 296,322; 307,365; 323,637; 336,357; and 341,009. These match Table 600's London values for 2020–2025 exactly (6/6). | External consistency check passed for the six available periods. Record the year-label mapping: LG Inform financial-year labels refer to the 31 March endpoint used as the Table 600 year. |
| **Indices of Multiple Deprivation** | The current source is the English Indices of Deprivation 2025. It is primarily an LSOA-level relative deprivation measure; File 10 provides summaries for 296 local-authority districts, and the publisher says there is no single best authority summary. | Park this until the core waiting-list data and current geography are validated. Then use IoD 2025 for context, segmentation or explanatory analysis—not to clean Table 600 and not automatically as a forecasting input. Test more than one authority summary and document the choice. |

## What must be true before forecasting resumes

1. The analytical question is explicit: national trend, regional planning, or current-authority comparison.
2. The relevant Table 600 definition and reference-date changes are documented in the output.
3. A reproducible current-geography method is agreed if authority-level analysis is required.
4. Missing markers, source imputations, reported zeroes and special cases have documented handling rules.
5. At least one independent consistency check is passed at each geography used. London now passes; more checks can be sampled if local-authority modelling proceeds.
6. Table 602 and IoD are added only for a stated analytical purpose and at a compatible geography/time level.
7. Models are re-run with leakage-free backtesting, simple baselines and sensitivity tests after the dataset is frozen.

## Reproduce this audit

```text
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
```

## External sources checked

- [MHCLG live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies) — official Table 600 and Table 602 workbooks, last updated 25 June 2026.
- [LG Inform: Total households on the housing waiting list at 31st March in London](https://lginform.local.gov.uk/reports/lgastandard?mod-area=E12000007&mod-group=E12000007&mod-metric=105) — metric 105 consistency check.
- [English Indices of Deprivation 2025 statistical release](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025/english-indices-of-deprivation-2025-statistical-release) — current official deprivation release and usage guidance.
