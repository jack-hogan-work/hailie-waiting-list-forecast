#!/usr/bin/env python3
"""Validate England-total figures in the processed regional file against the raw extract.

Compares the England row (Area code E92000001) in
data/extracts/regional_data_raw_extract.csv with the corresponding rows in
data/processed/regional_waiting_lists_long.csv for a set of selected years.

Standard library only (csv module) - no grep/awk/shell text tools.
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = REPO_ROOT / "data" / "extracts" / "regional_data_raw_extract.csv"
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"

SELECTED_YEARS = ["1987", "2015", "2020", "2024", "2025"]
ENGLAND_AREA_CODE = "E92000001"


def find_header_row(rows):
    for i, row in enumerate(rows):
        if "1987" in row:
            return i
    raise ValueError("Could not locate header row (no '1987' column found)")


def get_raw_england_values():
    with RAW_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header_idx = find_header_row(rows)
    header = rows[header_idx]
    area_code_col = header.index("Area code")

    england_row = None
    for row in rows[header_idx + 1 :]:
        if len(row) > area_code_col and row[area_code_col].strip() == ENGLAND_AREA_CODE:
            england_row = row
            break
    if england_row is None:
        raise ValueError(f"Could not find row with Area code {ENGLAND_AREA_CODE}")

    values = {}
    for year in SELECTED_YEARS:
        col_idx = header.index(year)
        raw_value = england_row[col_idx].strip()
        values[year] = int(raw_value.replace(",", ""))
    return values


def get_processed_england_values():
    with PROCESSED_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        area_code_idx = header.index("Area code")
        year_idx = header.index("year")
        value_idx = header.index("households_on_register")

        values = {}
        for row in reader:
            if row[area_code_idx].strip() != ENGLAND_AREA_CODE:
                continue
            if row[year_idx] in SELECTED_YEARS:
                values[row[year_idx]] = int(row[value_idx])
    return values


def main():
    raw_values = get_raw_england_values()
    processed_values = get_processed_england_values()

    print(f"{'Year':<6}{'Raw':>12}{'Processed':>12}{'Diff':>10}{'Result':>8}")
    all_pass = True
    for year in SELECTED_YEARS:
        raw = raw_values[year]
        processed = processed_values[year]
        diff = processed - raw
        result = "PASS" if diff == 0 else "FAIL"
        all_pass = all_pass and (diff == 0)
        print(f"{year:<6}{raw:>12,}{processed:>12,}{diff:>10,}{result:>8}")

    print("\nOverall:", "ALL PASS" if all_pass else "SOME FAILED")


if __name__ == "__main__":
    main()
