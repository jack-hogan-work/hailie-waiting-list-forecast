# Data: MHCLG Live Table 600 — Households on Local Authorities' Housing Waiting Lists

## Source

- **Dataset:** Live Table 600 — "Number of households on local authorities' housing waiting lists (housing register), by district," England, since 1987.
- **Publisher:** Ministry of Housing, Communities & Local Government (MHCLG).
- **Source page:** [Live tables on rents, lettings and tenancies](https://www.gov.uk/government/statistical-data-sets/live-tables-on-rents-lettings-and-tenancies) (GOV.UK statistical data set collection).
- **Retrieved:** 7 August 2026.

## Files

### Raw

- `data/raw/Live_Table_600.ods` — the original MHCLG spreadsheet as published, containing multiple worksheets (including regional, local-authority and notes tabs).
- `data/extracts/regional_data_raw_extract.csv` — the "Regional Data" worksheet exported to CSV, unmodified other than the export itself.
- `data/extracts/local_authority_data_raw_extract.csv` — the "Local Authority Data" worksheet exported to CSV, unmodified other than the export itself.

Both extracts carry three metadata/title rows above the real header row, as published by MHCLG.

### Processed

- `data/processed/regional_waiting_lists_long.csv` — regional data, reshaped to long format (one row per region/country per year).
- `data/processed/local_authority_waiting_lists_long.csv` — local-authority data, reshaped to long format (one row per local authority per year).

Both are produced by `scripts/prepare_data.py` and can be regenerated at any time with:

```
python3 scripts/prepare_data.py
```

## Columns

**Regional long file** (`regional_waiting_lists_long.csv`):

| Column | Description |
| --- | --- |
| `Area code` | ONS region/country code (e.g. `E12000004`, `E92000001` for the England total). |
| `Country` | Country (England for all rows in this extract). |
| `Notes` | Free-text note reference from the source worksheet, where present. |
| `Region` | Region or country name. Includes an `England` total row alongside the nine English regions — do not double-count it when summing regions. |
| `year` | Calendar year, 1987–2025. |
| `households_on_register` | Households on the housing register at 1 April of that year. Blank = missing/not available for that year. |

**Local authority long file** (`local_authority_waiting_lists_long.csv`):

| Column | Description |
| --- | --- |
| `Local authority code` | The authority code as published for that row in the source (historic where the authority has since been reorganised). Unique per source row. |
| `Local authority` | Authority name as published for that row (historic where reorganised). |
| `LAD24NM` | Current (2024 boundaries) local authority district name. |
| `LAD24CD` | Current (2024 boundaries) local authority district code. Several historic `Local authority code` rows can map to a single `LAD24CD` where authorities have merged — see Limitations below. |
| `Region code` / `Region name` | The region containing the authority. |
| `Country` | Country (England for all rows in this extract). |
| `Notes` | Free-text note reference from the source worksheet, where present. |
| `year` | Calendar year, 1987–2025. |
| `households_on_register` | Households on the housing register at 1 April of that year. Blank = missing/not available for that year. |

## Transformations (`scripts/prepare_data.py`)

1. Each raw CSV is read with the standard library `csv` module; the three metadata/title rows above the real header are detected automatically (the header row is identified as the first row containing a `1987` column) and skipped.
2. Identifier columns are everything to the left of the `1987` column; year columns are every column matching a four-digit `19xx`/`20xx` pattern.
3. Year-column values are converted to numeric:
   - Thousands separators (`,`) are stripped and the value cast to `int`.
   - Blank cells and bracketed marker codes from the source (`[z]`, `[x]`, etc.) are converted to a missing value (empty cell in the output CSV), **not** to zero.
   - Genuine `0` values in the source are preserved as `0`.
4. Each dataset is reshaped from wide (one column per year) to long (one row per authority/region per year) format.
5. Basic QA is run and printed to stdout on every run (see `docs/initial_feasibility_note.md` for the results from the 7 August 2026 run): row counts, year coverage, missing-value counts, count of genuine zero values, and a duplicate identifier/year check.

## Limitations

- **Boundary changes.** Local authority boundaries have changed repeatedly since 1987 (mergers into unitary authorities, most recently in 2019–2023). The extract's `Local authority code` reflects the authority as it was recorded in that source row, while `LAD24CD`/`LAD24NM` map it to the current (2024) authority. Several old codes can map to the same current authority, so summing `households_on_register` by `LAD24CD` across years mixes data collected under different boundaries. See `docs/initial_feasibility_note.md` for detail and counts.
- **Missing/suppressed values.** `[z]` and `[x]` marker codes from MHCLG (not available / not applicable) are treated as missing in the processed data; no imputation has been performed.
- **Not the same as unmet housing need.** This table counts households on local authorities' housing registers (waiting lists), not all households in housing need. Registers are periodically reviewed and applicants removed, so figures can fall for administrative reasons (a register "cleanse") as well as genuine reductions in demand. This is a narrower and differently-defined measure than housing-association or combined-register waiting list figures reported elsewhere — see `docs/initial_feasibility_note.md`.
- **England total row.** The regional extract includes an `England` total row (`Area code` = `E92000001`) alongside the nine English regions.
