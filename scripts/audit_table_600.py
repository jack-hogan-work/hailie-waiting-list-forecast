#!/usr/bin/env python3
"""Audit the Table 600 source-to-processed-data chain.

Checks the original ODS worksheets against the two stored CSV extracts,
checks every extract value against the processed long files, counts source
markers and publisher imputations, and confirms that the nine regional rows
sum to the published England total in every year.

Standard library only; exits non-zero if an audit check fails.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parent.parent
ODS_PATH = REPO_ROOT / "data" / "raw" / "Live_Table_600.ods"
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS = {"table": TABLE_NS}

DATASETS = [
    {
        "label": "regional",
        "sheet": "Regional_Data",
        "extract": REPO_ROOT / "data" / "extracts" / "regional_data_raw_extract.csv",
        "processed": REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv",
        "key": "Area code",
    },
    {
        "label": "local_authority",
        "sheet": "Local_Authority_Data",
        "extract": REPO_ROOT / "data" / "extracts" / "local_authority_data_raw_extract.csv",
        "processed": REPO_ROOT / "data" / "processed" / "local_authority_waiting_lists_long.csv",
        "key": "Local authority code",
    },
]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def load_ods_root():
    with ZipFile(ODS_PATH) as archive:
        return ET.fromstring(archive.read("content.xml"))


def cell_text(cell):
    return " ".join("".join(cell.itertext()).split())


def ods_sheet_rows(root, sheet_name, width=None):
    name_attr = f"{{{TABLE_NS}}}name"
    repeat_attr = f"{{{TABLE_NS}}}number-columns-repeated"
    sheet = next(
        table
        for table in root.findall(".//table:table", NS)
        if table.attrib.get(name_attr) == sheet_name
    )

    output = []
    for row in sheet.findall("table:table-row", NS):
        values = []
        for cell in row.findall("table:table-cell", NS):
            repeat = int(cell.attrib.get(repeat_attr, "1"))
            if width is not None:
                repeat = min(repeat, max(0, width - len(values)))
            values.extend([cell_text(cell)] * repeat)
            if width is not None and len(values) >= width:
                break
        if width is not None:
            values = (values + [""] * width)[:width]
        else:
            while values and values[-1] == "":
                values.pop()
        if any(values):
            output.append(values)
    return output


def find_header(rows):
    return next(i for i, row in enumerate(rows) if "1987" in row)


def parse_published_value(value):
    value = value.strip()
    if not value or (value.startswith("[") and value.endswith("]")):
        return None
    return int(value.replace(",", ""))


def audit_extract_against_ods(root, spec):
    extract_rows = read_csv(spec["extract"])
    width = max(len(row) for row in extract_rows)
    ods_rows = ods_sheet_rows(root, spec["sheet"], width)
    assert ods_rows == extract_rows, f"{spec['label']}: ODS and CSV extract differ"
    return extract_rows


def expected_long_records(extract_rows, key_column):
    header_index = find_header(extract_rows)
    header = extract_rows[header_index]
    key_index = header.index(key_column)
    year_columns = [(i, value.strip()) for i, value in enumerate(header) if YEAR_RE.match(value.strip())]
    records = {}
    marker_counts = Counter()
    source_zeros = 0
    negative_values = 0

    for row in extract_rows[header_index + 1 :]:
        if not any(cell.strip() for cell in row):
            continue
        key = row[key_index].strip()
        for column, year in year_columns:
            raw = row[column].strip()
            if raw.startswith("[") and raw.endswith("]"):
                marker_counts[raw] += 1
            value = parse_published_value(raw)
            source_zeros += value == 0
            negative_values += value is not None and value < 0
            records[(key, int(year))] = value
    return records, marker_counts, source_zeros, negative_values


def audit_processed(spec, expected):
    with spec["processed"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = {}
    for row in rows:
        raw = row["households_on_register"].strip()
        actual[(row[spec["key"]], int(row["year"]))] = int(raw) if raw else None
    assert actual == expected, f"{spec['label']}: processed long file differs from extract"
    return len(actual)


def audit_regional_rollup():
    path = REPO_ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
    by_year = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_year[int(row["year"])].append(row)

    for year, rows in by_year.items():
        england = next(
            int(row["households_on_register"])
            for row in rows
            if row["Area code"] == "E92000001"
        )
        regions = sum(
            int(row["households_on_register"])
            for row in rows
            if row["Area code"] != "E92000001"
        )
        assert england == regions, f"{year}: regions sum to {regions}, England is {england}"
    return len(by_year)


def audit_publisher_imputations(root):
    rows = ods_sheet_rows(root, "Imputations")
    header_index = next(i for i, row in enumerate(rows) if row and row[0] == "Local authority")
    header = rows[header_index]
    records = [dict(zip(header, row)) for row in rows[header_index + 1 :]]
    original = Counter(record["Original value"] for record in records)
    categories = Counter(
        "marker" if value.startswith("[") else "zero" if value == "0" else "numeric"
        for value in original.elements()
    )
    assert len(records) == 45, f"expected 45 publisher imputations, found {len(records)}"
    return len(records), categories


def main():
    root = load_ods_root()
    print("Table 600 source-to-output audit")
    print("================================")

    for spec in DATASETS:
        extract_rows = audit_extract_against_ods(root, spec)
        expected, markers, zeros, negatives = expected_long_records(extract_rows, spec["key"])
        record_count = audit_processed(spec, expected)
        assert negatives == 0, f"{spec['label']}: found {negatives} negative values"
        print(
            f"PASS {spec['label']}: ODS == CSV extract == processed values "
            f"({record_count:,} long records; markers {dict(markers)}; "
            f"{zeros} final zero values; {negatives} negative values)"
        )

    imputation_count, categories = audit_publisher_imputations(root)
    print(
        f"PASS publisher imputations: {imputation_count} documented replacements "
        f"(original values: {dict(categories)})"
    )

    years = audit_regional_rollup()
    print(f"PASS regional reconciliation: nine regions sum to England in all {years} years")
    print("\nAll Table 600 audit checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
