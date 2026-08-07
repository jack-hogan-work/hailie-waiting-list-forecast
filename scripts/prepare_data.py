#!/usr/bin/env python3
"""Week 1 data-intake workflow for MHCLG Live Table 600 waiting-list extracts.

Reads the raw regional and local-authority CSV extracts in data/extracts,
skips the metadata rows above the real header, converts the 1987-2025
year columns to numeric values (blanks and bracketed codes such as [z]
and [x] become missing, genuine zeroes are kept), reshapes each dataset
from wide to long format, writes the results to data/processed, and runs
basic QA checks on the output.

Standard library only - no third-party dependencies.
"""

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACTS_DIR = REPO_ROOT / "data" / "extracts"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

DATASETS = [
    {
        "label": "regional",
        "input": EXTRACTS_DIR / "regional_data_raw_extract.csv",
        "output": PROCESSED_DIR / "regional_waiting_lists_long.csv",
        # Columns (in the order they appear in the source) that together
        # uniquely identify a row (excluding year).
        "key_columns": ["Area code"],
    },
    {
        "label": "local_authority",
        "input": EXTRACTS_DIR / "local_authority_data_raw_extract.csv",
        "output": PROCESSED_DIR / "local_authority_waiting_lists_long.csv",
        "key_columns": ["Local authority code"],
    },
]


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def find_header_row(rows):
    """Return the index of the real header row.

    MHCLG worksheet exports carry a handful of title/notes rows above the
    real header. The real header is identified as the first row that
    contains a "1987" cell, since that is the first year column in every
    Live Table 600 worksheet.
    """
    for i, row in enumerate(rows):
        if "1987" in row:
            return i
    raise ValueError("Could not locate header row (no '1987' column found)")


def parse_numeric(raw):
    """Convert a raw cell to an int, or None if missing.

    Blank cells and bracketed marker codes (e.g. "[z]" = not available,
    "[x]" = not applicable) are treated as missing. Genuine zeroes are
    preserved. Thousands separators are stripped before conversion.
    """
    value = raw.strip()
    if value == "" or (value.startswith("[") and value.endswith("]")):
        return None
    return int(value.replace(",", ""))


def load_dataset(path):
    rows = read_rows(path)
    header_idx = find_header_row(rows)
    header = rows[header_idx]
    data_rows = [r for r in rows[header_idx + 1 :] if any(c.strip() for c in r)]

    year_indices = [i for i, col in enumerate(header) if YEAR_RE.match(col.strip())]
    id_indices = [i for i in range(len(header)) if i not in year_indices]

    id_columns = [header[i].strip() for i in id_indices]
    years = [header[i].strip() for i in year_indices]

    return {
        "id_columns": id_columns,
        "id_indices": id_indices,
        "years": years,
        "year_indices": year_indices,
        "data_rows": data_rows,
    }


def reshape_long(dataset):
    long_rows = []
    for row in dataset["data_rows"]:
        identifiers = {
            col: row[idx].strip() for col, idx in zip(dataset["id_columns"], dataset["id_indices"])
        }
        for year, idx in zip(dataset["years"], dataset["year_indices"]):
            long_rows.append(
                {
                    **identifiers,
                    "year": int(year),
                    "households_on_register": parse_numeric(row[idx]),
                }
            )
    return long_rows


def write_long_csv(path, long_rows, id_columns):
    fieldnames = id_columns + ["year", "households_on_register"]
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in long_rows:
            writer.writerow(row)


def run_qa(label, dataset, long_rows, key_columns):
    print(f"\n--- QA: {label} ---")

    n_wide_rows = len(dataset["data_rows"])
    n_long_rows = len(long_rows)
    n_years = len(dataset["years"])
    print(f"Wide-format data rows : {n_wide_rows}")
    print(f"Long-format rows      : {n_long_rows} (expected {n_wide_rows} x {n_years} = {n_wide_rows * n_years})")
    assert n_long_rows == n_wide_rows * n_years, "row count mismatch after reshape"

    years_present = sorted(set(r["year"] for r in long_rows))
    expected_years = sorted(int(y) for y in dataset["years"])
    print(f"Year coverage         : {years_present[0]}-{years_present[-1]} ({len(years_present)} years)")
    assert years_present == expected_years, "year coverage mismatch"

    n_missing = sum(1 for r in long_rows if r["households_on_register"] is None)
    pct_missing = 100 * n_missing / n_long_rows if n_long_rows else 0
    print(f"Missing values        : {n_missing} ({pct_missing:.1f}% of rows)")

    n_zero = sum(1 for r in long_rows if r["households_on_register"] == 0)
    print(f"Genuine zero values   : {n_zero}")

    seen = {}
    duplicates = 0
    for r in long_rows:
        key = tuple(r[c] for c in key_columns) + (r["year"],)
        if key in seen:
            duplicates += 1
        else:
            seen[key] = True
    print(f"Duplicate id/year keys: {duplicates}")
    assert duplicates == 0, f"found {duplicates} duplicate identifier/year rows"

    return {
        "wide_rows": n_wide_rows,
        "long_rows": n_long_rows,
        "year_min": years_present[0],
        "year_max": years_present[-1],
        "n_years": len(years_present),
        "missing": n_missing,
        "pct_missing": pct_missing,
        "zeros": n_zero,
        "duplicates": duplicates,
    }


def main():
    summary = {}
    for spec in DATASETS:
        dataset = load_dataset(spec["input"])
        long_rows = reshape_long(dataset)
        write_long_csv(spec["output"], long_rows, dataset["id_columns"])
        summary[spec["label"]] = run_qa(spec["label"], dataset, long_rows, spec["key_columns"])
        print(f"Wrote {spec['output'].relative_to(REPO_ROOT)}")

    print("\n--- Summary ---")
    for label, s in summary.items():
        print(
            f"{label}: {s['wide_rows']} rows x {s['n_years']} years -> {s['long_rows']} long rows, "
            f"{s['missing']} missing ({s['pct_missing']:.1f}%), {s['zeros']} zeros, {s['duplicates']} duplicates"
        )


if __name__ == "__main__":
    sys.exit(main())
