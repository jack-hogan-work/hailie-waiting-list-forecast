# National (England Total) Validation

**Purpose:** Check that the England-total row (`Area code` = `E92000001`) survived the wide-to-long transformation in `scripts/prepare_data.py` unchanged, for a sample of years spanning the series.

**Method:** `scripts/validate_national.py` reads `data/extracts/regional_data_raw_extract.csv` and `data/processed/regional_waiting_lists_long.csv` with Python's standard-library `csv` module (no shell text tools), locates the England row/rows by column name and `Area code` value, and compares the `households_on_register` figure for each selected year.

**Run:** `python3 scripts/validate_national.py`

## Results

| Year | Raw value (extract) | Processed value | Difference | Result |
| --- | ---: | ---: | ---: | :---: |
| 1987 | 1,289,492 | 1,289,492 | 0 | PASS |
| 2015 | 1,256,575 | 1,256,575 | 0 | PASS |
| 2020 | 1,137,234 | 1,137,234 | 0 | PASS |
| 2024 | 1,330,602 | 1,330,602 | 0 | PASS |
| 2025 | 1,340,527 | 1,340,527 | 0 | PASS |

All five selected years match exactly (difference = 0).

## Scope and limitations

This check confirms that the CSV-to-long-format transformation performed by `scripts/prepare_data.py` did not alter, drop, or mis-map the England-total figures for the years tested. It is **not** a complete independent audit of the underlying MHCLG publication — it does not verify:

- that the raw extract (`data/extracts/regional_data_raw_extract.csv`) itself correctly reflects the original `Live_Table_600.ods` workbook cell-for-cell,
- that MHCLG's own published England totals are internally consistent or correctly sum the nine regions,
- any years outside the five sampled here (though the transformation logic is uniform across years, so a systematic error would be expected to surface in more than one sampled year).
