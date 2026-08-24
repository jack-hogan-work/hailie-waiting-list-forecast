# Initial Feasibility Note — Week 1 Data Intake

**Source:** MHCLG Live Table 600, "Number of households on local authorities' housing waiting lists (housing register), by district," England, 1987–2025. Retrieved 7 August 2026 from [Live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies) (GOV.UK).
**Pipeline:** `scripts/prepare_data.py`, run 7 August 2026. See `data/README.md` for the full column and transformation reference.

## 1. QA findings

| Check | Regional | Local authority |
| --- | --- | --- |
| Wide-format source rows | 10 | 376 |
| Long-format rows (rows × 39 years) | 390 | 14,664 |
| Year coverage | 1987–2025 (39 years, complete) | 1987–2025 (39 years, complete) |
| Missing values | 0 (0.0%) | 1,423 (9.7%) |
| Genuine zero values | 0 | 8 |
| Duplicate identifier/year rows | 0 | 0 |

The regional file is complete with no missing values and passes all QA checks cleanly. It includes an `England` total row (`E92000001`) alongside the nine English regions, which should be excluded when summing region-level figures to avoid double-counting.

The local-authority file has no duplicate `Local authority code`/year combinations, but 9.7% of cells are missing. All 1,423 missing cells trace back exactly to the source's own suppression markers: 1,421 cells marked `[z]` and 2 cells marked `[x]`. No blank (unmarked) cells were found. Missing values are not concentrated in a handful of authorities — every authority code has at least one populated year, and 273 of 376 authority codes have a complete 1987–2025 series. The remaining 103 have partial gaps, almost all explained by local government reorganisation (see §2).

Missing-cell counts by year rise in two clear steps that line up with England's two main unitarisation waves:

- **1987–2009:** ~22 missing cells per year (a stable baseline).
- **2010–2019:** ~50 missing cells per year, stepping up after the 2009 unitary reorganisation (e.g. Cornwall, County Durham, Northumberland, Shropshire, Wiltshire, Cheshire East/West, Bedford, Central Bedfordshire).
- **2020–2025:** rising from 59 to 82 missing cells per year, reflecting the 2019–2023 wave (Buckinghamshire; Bournemouth, Christchurch and Poole; Dorset; East/West Suffolk; the Northamptonshire split; the Cumbria split into Cumberland and Westmorland and Furness; Somerset).

No imputation is added by the repository pipeline — all final `[x]`/`[z]` cells are left blank in the processed CSVs. The published workbook itself does contain an `Imputations` worksheet with 45 source-level replacements, so published values are not all untouched council returns. See §4 and `docs/data_quality_audit.md`.

## 2. Boundary changes

The local-authority extract is **not** a clean one-row-per-current-authority time series. It contains 376 source rows but only 296 distinct current (`LAD24CD`) authorities — 21 current authorities are represented by more than one historic source row, up to 7 in one case (Northumberland).

Concretely, the raw worksheet mixes two kinds of row for any authority that has been through reorganisation:

1. **Legacy district rows**, keyed on the old district code, populated up to the year the district was abolished and then `[z]` afterwards. Example: `E07000004` (Aylesbury Vale) reports real figures through 2019 and `[z]` for 2020–2025, with `LAD24CD` pointing to the new unitary `E06000060` (Buckinghamshire).
2. **New unitary rows**, keyed on the new unitary code, populated from the year it was created and `[z]` for all years before it existed. Example: `E06000060` (Buckinghamshire) itself reports `[z]` for 1987–2019 (the district predecessors' era) and real figures from 2021.

This means a naive `GROUP BY LAD24CD` sum over the processed long file will silently double-count nothing (predecessor and successor periods don't overlap) but will also not automatically produce a continuous current-boundary series — the predecessor rows have to be summed across districts for the pre-reorganisation years and stitched to the successor's own row for the post-reorganisation years, authority by authority. This reconciliation has **not** been done in this pipeline; `data/processed/local_authority_waiting_lists_long.csv` retains the source's original row-per-historic-code structure, with `LAD24CD`/`LAD24NM` provided as a lookup for anyone doing that reconciliation downstream.

## 3. `[z]` and `[x]` values

Two suppression marker codes appear in the source workbook:

- `[z]` (1,421 occurrences) — not applicable, almost entirely because the authority did not exist under that code in that year (see §2).
- `[x]` (2 occurrences) — not available. The two final markers are on Canterbury and Telford and Wrekin in the worksheet's `2024` column.

Separately, the West Midlands region row and the Telford and Wrekin authority row each carry a `[note 5]` reference in the source's `Notes` column. This is a footnote pointer, not a value-suppression marker, and its meaning is not resolved by this extract — the source workbook's Notes worksheet (not pulled into `data/extracts`) should be consulted if that annotation matters to downstream analysis. `parse_numeric()` only strips numeric year-column markers; the `Notes` column text is passed through unchanged as an identifier field.

Both are converted to a missing (blank) value in the processed output by `parse_numeric()` in `scripts/prepare_data.py`, which treats any bracketed code as missing regardless of its specific letter. Genuine reported zeroes (8 in the local-authority file, e.g. Wyre 2007–2014 dropping to single-digit and Allerdale 2015–2018 reporting `0`) are preserved as `0` and are **not** treated as missing — these look like real, low, register counts rather than suppressions, but are flagged here as worth a sense check before use in any model, since a run of exact-zero years is unusual.

## 4. Imputation

No imputation is performed by `scripts/prepare_data.py`. The processed files carry the published table's final marker values through as blanks.

There is nevertheless imputation in the source. The original ODS contains 45 documented publisher replacements in its `Imputations` worksheet, covering years reported there as 2004–2025. Eleven original entries are `[x]`, eight are zero, and the remainder are numeric values that MHCLG replaced. The published Regional and Local Authority worksheets already contain the replacement values, so these are source-level imputations rather than transformations introduced by this repository.

Any additional project imputation (for example, while building a continuous current-boundary series) should be a separate, explicit and sensitivity-tested step. It must not be folded into the intake pipeline.

## 5. Local authority registers vs. broader social-housing waiting lists

Live Table 600 counts households on **local authorities' own housing registers (waiting lists)** as returned by councils to MHCLG. Two limitations follow for interpreting it as a general measure of housing need:

- **Administrative review effects.** Councils periodically review and "cleanse" their registers, removing applicants who are no longer eligible, no longer respond, or no longer wish to be considered. This is routine administrative practice, not a change in underlying need, but it can produce falls (or level shifts around review dates) in the reported count that have nothing to do with demand. The table does not indicate when or how often each authority reviews its register, so this effect cannot be separated from genuine change using this data alone.
- **Scope: local authority registers only.** In many areas, social housing is let through a shared choice-based lettings scheme covering both the council and local housing associations (private registered providers), in which case this table captures most of the relevant list. In other areas, housing associations maintain their own, separate waiting lists that are not part of a council's register and are not reported in Live Table 600 at all. Because most social rented homes in England are now owned by housing associations rather than councils, the true scale of households seeking social housing nationally is very likely understated by this table, and the degree of understatement varies by area depending on local lettings arrangements. This dataset should be treated as a lower bound on, and a specific administrative slice of, overall social housing waiting demand — not a complete count of it.

These two points, together with the boundary-change reconciliation in §2, are the main caveats to carry into any Week 2+ forecasting work built on this intake.
