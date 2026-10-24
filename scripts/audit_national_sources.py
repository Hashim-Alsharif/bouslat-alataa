"""Audit all 13 official regional resources, rejecting HTML disguised as CSV."""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_source import EXPECTED_COLUMNS


def read_regional_source(root, source):
    path = root / source["local_file"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != source["source_sha256"]:
        raise ValueError("Source hash changed: " + source["region"])
    if payload.lstrip().lower().startswith((b"<html", b"<!doctype html")):
        raise ValueError("DOWNLOAD_RETURNED_HTML_REQUEST_REJECTED")
    encoding = "utf-8-sig"
    try:
        text = payload.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1256"
        text = payload.decode(encoding, errors="strict")
    records = list(csv.reader(io.StringIO(text, newline="")))
    expected=source.get("source_columns_expected",EXPECTED_COLUMNS)
    if expected not in [EXPECTED_COLUMNS,EXPECTED_COLUMNS[1:]]:
        raise ValueError("UNREVIEWED_SOURCE_SCHEMA")
    headers = [i for i, row in enumerate(records) if [x.strip() for x in row] == expected]
    if len(headers) != 1:
        raise ValueError("UNEXPECTED_SCHEMA")
    header_index = headers[0]
    if any(any(cell.strip() for cell in row) for row in records[:header_index]):
        raise ValueError("NONEMPTY_RECORD_BEFORE_HEADER")
    body = []
    for index, row in enumerate(records[header_index + 1:], header_index + 2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(expected):
            raise ValueError(f"MALFORMED_WIDTH:{index}")
        record=dict(zip(expected,row))
        # Blank means unpublished, never a generated national identifier.
        record.setdefault("الرقم الوطني الموحد","")
        body.append({**record,"source_record":index})
    return body, {
        "encoding": encoding, "source_header": records[header_index],
        "header_record": header_index + 1, "csv_records": len(records),
        "blank_format_records": len(records) - len(body) - 1,
        "source_columns":expected,"column_count":len(expected),
        "identifier_column_present":"الرقم الوطني الموحد" in expected,
    }


def audit(root=ROOT):
    manifest = json.loads((root / "research/national_sources.json").read_text(encoding="utf-8"))
    inventory, data_rows = [], []
    for source in manifest["sources"]:
        item = {key:source[key] for key in ["region", "slug", "dataset_url", "local_file", "reference_period_as_displayed", "updated_at_as_displayed", "license_url", "source_sha256"]}
        try:
            rows, info = read_regional_source(root, source)
        except ValueError as error:
            item.update({"status":"blocked_download", "reason":str(error), "records":None,
                         "schema_compatible":False, "encoding":None})
        else:
            ids = [row["الرقم الوطني الموحد"].strip() for row in rows if row["الرقم الوطني الموحد"].strip()]
            item.update({"status":"readable", "reason":"", "records":len(rows), "schema_compatible":True,
                         **info, "missing_cells":sum(not row[key].strip() for row in rows for key in info["source_columns"]),
                         "records_without_national_id":len(rows)-len(ids),
                         "duplicate_id_excess":len(ids)-len(set(ids)),
                         "invalid_id_records":sum(not bool(re.fullmatch(r"[0-9]{10}", value)) for value in ids),
                         "type_counts":dict(Counter(row["نوع الكيان"] for row in rows))})
            data_rows.extend({**row,"source_region":source["region"],"source_slug":source["slug"]} for row in rows)
        inventory.append(item)
    id_locations = {}
    for row in data_rows:
        identifier = row["الرقم الوطني الموحد"].strip()
        if not identifier:
            continue
        id_locations.setdefault(identifier,[]).append({"region":row["source_region"],"record":row["source_record"],"name":row["اسم الكيان"]})
    duplicates = {key:value for key,value in id_locations.items() if len(value)>1}
    summary = {
        "regions_catalogued":len(inventory), "readable_regions":sum(x["status"]=="readable" for x in inventory),
        "blocked_regions":[x["region"] for x in inventory if x["status"]!="readable"],
        "readable_source_records":len(data_rows), "duplicate_identifier_groups":len(duplicates),
        "duplicate_identifier_excess":sum(len(x)-1 for x in duplicates.values()),
        "records_with_national_id":sum(bool(row["الرقم الوطني الموحد"].strip()) for row in data_rows),
        "records_without_national_id":sum(not row["الرقم الوطني الموحد"].strip() for row in data_rows),
        "all_13_regional_files_readable":all(x["status"]=="readable" for x in inventory),
        "complete_national_entity_deduplication_possible":all(bool(row["الرقم الوطني الموحد"].strip()) for row in data_rows),
        "comparability":"Multiple publication dates; Jouf 2025 reference period, Asir extended period. No common per-entity observation date.",
    }
    report = {"checked_on":"2026-10-23", "summary":summary, "inventory":inventory, "duplicate_identifiers":duplicates}
    (root/"research/national_preflight.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    columns = ["region","status","records","column_count","identifier_column_present","records_without_national_id","schema_compatible","encoding","missing_cells","duplicate_id_excess","invalid_id_records","updated_at_as_displayed","reference_period_as_displayed","dataset_url","reason"]
    with (root/"research/national_inventory.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction="ignore")
        writer.writeheader(); writer.writerows(inventory)
    values={field:dict(Counter(row[field] for row in data_rows)) for field in EXPECTED_COLUMNS[2:]}
    values["locations_by_region"]={source["region"]:dict(Counter(row["المدينة"] for row in data_rows if row["source_region"]==source["region"])) for source in manifest["sources"]}
    (root/"research/national_values.json").write_text(json.dumps(values,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for item in inventory:
        print(item["region"], item["status"], item["records"], item.get("missing_cells"),item.get("invalid_id_records"))
    return report


if __name__ == "__main__":
    audit()
