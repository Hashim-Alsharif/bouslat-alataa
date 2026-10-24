"""Read the official CSV without changing it and write a source-quality check.

Run from the Data Analysis directory with Python 3.12 or newer.
No web requests, model calls or spreadsheet applications are used.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_raw" / "ncnp_qassim_source.csv"
EXPECTED_COLUMNS = [
    "الرقم الوطني الموحد", "اسم الكيان", "المدينة", "التصنيف النوعي",
    "التصنيف الفرعي الاول", "التصنيف الفرعي الثاني", "نوع الكيان", "جهة الإشراف",
]


def main():
    raw_bytes = SOURCE.read_bytes()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        raw_rows = list(csv.reader(stream))
    header_indices = [i for i, row in enumerate(raw_rows) if row == EXPECTED_COLUMNS]
    if len(header_indices) != 1:
        raise ValueError("Expected exactly one known header; inspect the source before proceeding.")
    header_index = header_indices[0]
    if any(any(cell.strip() for cell in row) for row in raw_rows[:header_index]):
        raise ValueError("Unexpected nonempty content before the header.")
    body = raw_rows[header_index + 1:]
    nonempty = [row for row in body if any(cell.strip() for cell in row)]
    malformed = [i for i, row in enumerate(body, header_index + 2)
                 if any(cell.strip() for cell in row) and len(row) != len(EXPECTED_COLUMNS)]
    if malformed:
        raise ValueError("Unexpected record widths; no data have been cleaned.")
    records = [dict(zip(EXPECTED_COLUMNS, row)) for row in nonempty]
    identifiers = [row["الرقم الوطني الموحد"].strip() for row in records]
    identifier_counts = Counter(identifiers)
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "source_bytes": len(raw_bytes),
        "encoding": "UTF-8 with optional BOM",
        "csv_record_count_including_header_and_blanks": len(raw_rows),
        "header_record_number": header_index + 1,
        "blank_records_before_header": header_index,
        "blank_records_after_header": len(body) - len(nonempty),
        "entity_records": len(records),
        "columns": EXPECTED_COLUMNS,
        "malformed_record_count": len(malformed),
        "missing_or_whitespace_by_column": {
            key: sum(not row[key].strip() for row in records) for key in EXPECTED_COLUMNS
        },
        "duplicate_full_record_excess": len(nonempty) - len(set(map(tuple, nonempty))),
        "duplicate_identifier_excess": sum(max(0, count - 1) for count in identifier_counts.values()),
        "invalid_ten_digit_identifier_count": sum(not bool(re.fullmatch(r"[0-9]{10}", value)) for value in identifiers),
        "entity_type_counts_as_published": dict(Counter(row["نوع الكيان"] for row in records)),
        "distinct_city_labels_before_normalization": len({row["المدينة"] for row in records}),
        "distinct_main_classifications_before_normalization": len({row["التصنيف النوعي"] for row in records}),
        "checks_scope": "Structural preflight only; no geographic, semantic or registry-completeness validation yet.",
        "normalization_applied_to_source": False,
        "limitations": [
            "Empty records and an empty leading record are publisher formatting, not missing entity observations.",
            "Entity types include associations and foundations; do not label all rows as associations.",
            "Region is supplied by dataset provenance, not a column in this CSV.",
            "City labels may include governorates or cities; they require reviewed geographic mapping.",
            "There is no per-entity observation date or historical series in the CSV.",
            "Zero blank cells does not establish factual correctness or complete coverage."
        ]
    }
    destination = ROOT / "research" / "qassim_preflight.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("QASSIM_SOURCE_PREFLIGHT_OK")
    print("Records:", report["entity_records"])
    print("Types:", json.dumps(report["entity_type_counts_as_published"], ensure_ascii=True))
    print("Raw source unchanged; report saved to research/qassim_preflight.json")


if __name__ == "__main__":
    main()
