# Data Quality and Methodology Audit

> **Final status update — 4 September 2026:** the decision gate below was the
> checkpoint used before final modelling. Its conditions have now been
> addressed for national and regional analysis, and forecasting has resumed and
> completed. See `docs/final_forecast_methodology.md` and the source assessment
> below in `outputs/HAILIE_final_report.html`.

**Status at 18 August 2026 (superseded by the final status update above):** first source audit complete; forecasting was exploratory at that checkpoint.

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

## Source assessment

| Point | Evidence/status | Decision |
| --- | --- | --- |
| **Table 600** | Source workbook, extracts and processed files now reconcile exactly. Source definitions, markers and 45 publisher imputations are documented. | Use as the core administrative waiting-list series for England and the nine regions. |
| **London / LG Inform** | LG Inform metric 105 is the same LAHS Section C concept. Its London values for 2019/20–2024/25 are 250,922; 296,322; 307,365; 323,637; 336,357; and 341,009. These match Table 600's London values for 2020–2025 exactly (6/6). | External consistency check passed for the six available periods. Record the year-label mapping: LG Inform financial-year labels refer to the 31 March endpoint used as the Table 600 year. |

## What must be true before forecasting resumes

1. The analytical question is explicit: national trend, regional planning, or current-authority comparison.
2. The relevant Table 600 definition and reference-date changes are documented in the output.
3. Missing markers, source imputations, reported zeroes and special cases have documented handling rules.
4. An independent consistency check is passed for the London regional series.
5. Models are re-run with leakage-free backtesting, simple baselines and sensitivity tests after the dataset is frozen.

## Reproduce this audit

```text
python3 scripts/audit_table_600.py
python3 scripts/prepare_data.py
python3 scripts/validate_national.py
```

## External sources checked

- [MHCLG live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies) — official source for Table 600, last updated 25 June 2026.
- [LG Inform: Total households on the housing waiting list at 31st March in London](https://lginform.local.gov.uk/reports/lgastandard?mod-area=E12000007&mod-group=E12000007&mod-metric=105) — metric 105 consistency check.
