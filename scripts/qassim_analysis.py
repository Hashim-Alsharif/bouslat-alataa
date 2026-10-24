"""Reproducible Qassim registry analysis. Notebook cells use this exact source.

No web requests or AI calls; no changes to the publisher CSV.
"""
# %% imports
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re
import textwrap
import unicodedata

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

EXPECTED_COLUMNS = [
    "الرقم الوطني الموحد", "اسم الكيان", "المدينة", "التصنيف النوعي",
    "التصنيف الفرعي الاول", "التصنيف الفرعي الثاني", "نوع الكيان", "جهة الإشراف",
]
EXPECTED_SHA256 = "86eb8568793376e5cf63040ee226cd4fe6a71d1658a9c5119328b725202cfe8e"
SOURCE_URL = "https://open.data.gov.sa/ar/datasets/view/2b6dacda-3aac-4aa6-9824-43f33f71963b"
LICENSE_URL = "https://open.data.gov.sa/ar/pages/policies/license"


def find_project_root():
    """Support local Jupyter and an extracted project ZIP in Colab."""
    cwd = Path.cwd()
    candidates = [cwd, cwd / "bouslat-alataa-qassim", *cwd.parents]
    for candidate in candidates:
        if (candidate / "data_raw/ncnp_qassim_source.csv").is_file():
            return candidate
    raise FileNotFoundError(
        "استخرج حزمة bouslat-alataa-qassim.zip أولاً، ثم شغّل Notebook من مجلدها."
    )


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value):
    """NFC and whitespace only; never globally fold distinct Arabic letters."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


# %% source
def read_source(root):
    source = root / "data_raw/ncnp_qassim_source.csv"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("تغيّر الملف الأصلي: راجع المصدر والقواعد قبل متابعة التنظيف.")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.reader(stream))
    headers = [i for i, row in enumerate(records) if row == EXPECTED_COLUMNS]
    if len(headers) != 1:
        raise ValueError("لم يُعثر على رأس الأعمدة المعروف مرة واحدة بالضبط.")
    start = headers[0]
    if any(any(cell.strip() for cell in row) for row in records[:start]):
        raise ValueError("محتوى غير متوقع قبل رأس الأعمدة.")
    rows, record_numbers = [], []
    for index, row in enumerate(records[start + 1:], start + 2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(EXPECTED_COLUMNS):
            raise ValueError(f"عدد حقول غير متوقع في سجل CSV رقم {index}")
        rows.append(row)
        record_numbers.append(index)
    frame = pd.DataFrame(rows, columns=EXPECTED_COLUMNS, dtype=str)
    audit = {
        "source_sha256": digest,
        "csv_records_total": len(records),
        "header_csv_record": start + 1,
        "blank_records_before_header": start,
        "blank_records_after_header": sum(
            not any(cell.strip() for cell in row) for row in records[start + 1:]
        ),
        "entity_records": len(frame),
        "missing_or_blank_cells": int(frame.map(lambda x: not x.strip()).sum().sum()),
        "duplicate_entity_id_excess": int(frame[EXPECTED_COLUMNS[0]].duplicated().sum()),
        "duplicate_full_record_excess": int(frame.duplicated().sum()),
    }
    return frame, record_numbers, audit


# %% clean
def clean_entities(raw, record_numbers, rules, audit_keys=None):
    """Apply explicit mappings, preserve all original columns, log changes."""
    city_rules = rules["locations"]
    main_rules = rules["main_groups"]
    for field, mapping in [("المدينة", city_rules), ("التصنيف النوعي", main_rules)]:
        unexpected = set(raw[field]) - set(mapping)
        if unexpected:
            raise ValueError(f"قيم بلا قاعدة صريحة في {field}: {unexpected}")

    cleaned = raw.copy(deep=True)
    cleaned["source_csv_record"] = record_numbers
    cleaned["entity_id"] = raw["الرقم الوطني الموحد"].map(normalize_text)
    cleaned["region"] = "القصيم"  # Dataset provenance, not a source CSV field.
    changes, issues = [], []
    audit_field="record_key" if audit_keys is not None else "entity_id"
    text_fields = {
        "اسم الكيان": "entity_name", "نوع الكيان": "entity_type",
        "جهة الإشراف": "supervisor",
    }
    for source_field, derived_field in text_fields.items():
        cleaned[derived_field] = raw[source_field].map(normalize_text)

    derived_rows = []
    for index, row in raw.iterrows():
        identifier = audit_keys.at[index] if audit_keys is not None else cleaned.at[index, "entity_id"]
        city = city_rules[row["المدينة"]]
        main = main_rules[row["التصنيف النوعي"]]
        derived = {
            "locality_name": city["name"], "locality_unit": city["unit"],
            "location_label": city["label"], "geo_status": city["status"],
            "main_group_code": main["code"], "main_group_name": main["name"],
            "main_description_review": main["description_review"],
        }
        if city["status"] == "unspecified":
            issues.append({
                audit_field: identifier, "issue_code": "LOCATION_UNSPECIFIED",
                "source_field": "المدينة", "source_value": row["المدينة"],
                "reason": "ورد الموقع «أخرى»؛ لم نستنتج موقعاً من اسم الكيان.",
            })
        if main["description_review"]:
            issues.append({
                audit_field: identifier, "issue_code": "MAIN_DESCRIPTION_CONFLICT",
                "source_field": "التصنيف النوعي", "source_value": row["التصنيف النوعي"],
                "reason": main["reason"],
            })
        for source_field, derived_field, level in [
            ("التصنيف الفرعي الاول", "subcategory_1", "subcategory_1"),
            ("التصنيف الفرعي الثاني", "subcategory_2", "subcategory_2"),
        ]:
            original = row[source_field]
            value = normalize_text(original)
            reason = "توحيد المسافات وترميز Unicode NFC فقط."
            for rule in rules["subcategory_aliases"]:
                if rule["level"] == level and rule["group"] == main["code"] and rule["from"] == value:
                    value = rule["to"]
                    reason = rule["reason"]
                    break
            derived[derived_field] = value
            if value != original:
                changes.append({
                    audit_field: identifier, "field": derived_field,
                    "original": original, "normalized": value, "reason": reason,
                })
        if city["label"] != row["المدينة"]:
            changes.append({
                audit_field: identifier, "field": "location_label",
                "original": row["المدينة"], "normalized": city["label"],
                "reason": "توحيد المسافات، مع الاحتفاظ بنوع الوحدة: مدينة أو محافظة.",
            })
        for source_field, derived_field in text_fields.items():
            if row[source_field] != cleaned.at[index, derived_field]:
                changes.append({
                    audit_field: identifier, "field": derived_field,
                    "original": row[source_field], "normalized": cleaned.at[index, derived_field],
                    "reason": "توحيد المسافات وترميز Unicode NFC فقط.",
                })
        derived_rows.append(derived)
    derived_frame = pd.DataFrame(derived_rows, index=raw.index)
    cleaned = pd.concat([cleaned, derived_frame], axis=1)
    cleaned["needs_review"] = cleaned["main_description_review"] | cleaned["geo_status"].eq("unspecified")
    change_columns = [audit_field, "field", "original", "normalized", "reason"]
    issue_columns = [audit_field, "issue_code", "source_field", "source_value", "reason"]
    return cleaned, pd.DataFrame(changes, columns=change_columns), pd.DataFrame(issues, columns=issue_columns)


# %% validate
def validate_results(root, raw, cleaned):
    """Stop on data loss, changed identifiers, or accidental raw-data mutation."""
    checks = {
        "source_hash_unchanged": hashlib.sha256((root / "data_raw/ncnp_qassim_source.csv").read_bytes()).hexdigest() == EXPECTED_SHA256,
        "all_source_rows_preserved": len(cleaned) == len(raw) == 562,
        "all_original_columns_unchanged": raw.equals(cleaned[EXPECTED_COLUMNS]),
        "identifiers_are_unique": cleaned["entity_id"].is_unique,
        "identifiers_are_ten_digit_text": bool(cleaned["entity_id"].str.fullmatch(r"[0-9]{10}").all()),
        "no_derived_missing_cells": not bool(cleaned.isna().any().any()),
        "types_conserved": cleaned["entity_type"].value_counts().to_dict() == {"جمعية أهلية": 533, "مؤسسة أهلية": 29},
        "ten_explicit_main_groups": cleaned["main_group_code"].nunique() == 10,
        "all_six_unspecified_locations_retained": int(cleaned["geo_status"].eq("unspecified").sum()) == 6,
        "description_review_records_flagged": int(cleaned["main_description_review"].sum()) == 23,
    }
    if not all(checks.values()):
        raise AssertionError({key: value for key, value in checks.items() if not value})
    return checks


# %% summarize
def count_table(frame, fields):
    denominator = len(frame)
    result = frame.groupby(fields, dropna=False).size().reset_index(name="entity_count")
    result["share_percent"] = (100 * result["entity_count"] / denominator).round(2)
    result["denominator"] = denominator
    return result.sort_values(["entity_count", *fields], ascending=[False, *([True] * len(fields))]).reset_index(drop=True)


def summarize_entities(cleaned):
    associations = cleaned[cleaned["entity_type"].eq("جمعية أهلية")].copy()
    tables = {
        "entity_types": count_table(cleaned, ["entity_type"]),
        "locations_all_entities": count_table(cleaned, ["location_label", "locality_name", "locality_unit", "geo_status"]),
        "main_groups_all_entities": count_table(cleaned, ["main_group_code", "main_group_name"]),
        "locations_associations_only": count_table(associations, ["location_label", "locality_unit"]),
        "main_groups_associations_only": count_table(associations, ["main_group_code", "main_group_name"]),
        "subcategories_1": count_table(cleaned, ["main_group_code", "subcategory_1"]),
        "subcategories_2": count_table(cleaned, ["main_group_code", "subcategory_1", "subcategory_2"]),
    }
    matrix = pd.crosstab(cleaned["location_label"], cleaned["main_group_code"])
    order = tables["locations_all_entities"]["location_label"]
    matrix = matrix.reindex(index=order, columns=sorted(cleaned["main_group_code"].unique()), fill_value=0)
    matrix.index.name = "location_label"
    tables["location_by_main_group"] = matrix.reset_index()
    for name in ["entity_types", "locations_all_entities", "main_groups_all_entities"]:
        if int(tables[name]["entity_count"].sum()) != len(cleaned):
            raise AssertionError(f"لم تتطابق مجاميع الجدول {name}")
    return tables


# %% charts
def ar(text, width=None):
    lines = textwrap.wrap(str(text), width) if width else str(text).splitlines()
    # Matplotlib 3.11 shapes Arabic natively. Keep Unicode in logical order.
    return "\n".join(lines)


def configure_charts():
    available = {font.name for font in font_manager.fontManager.ttflist}
    font = next((name for name in ["Arial", "DejaVu Sans"] if name in available), "sans-serif")
    plt.rcParams.update({"font.family": font, "font.size": 11, "axes.unicode_minus": False})


def add_source_footer(fig):
    fig.text(0.03, 0.065, ar("المصدر: المركز الوطني لتنمية القطاع غير الربحي — الكيانات غير الربحية في منطقة القصيم"), fontsize=8)
    fig.text(0.03, 0.043, "Source: " + SOURCE_URL, fontsize=6.4)
    fig.text(0.03, 0.024, "Open data license: " + LICENSE_URL, fontsize=6.4)


def draw_bar(table, label_column, title, destination, wrap=None):
    table = table.iloc[::-1]
    fig, ax = plt.subplots(figsize=(13, 10))
    bars = ax.barh([ar(value, wrap) for value in table[label_column]], table["entity_count"], color="#147d78")
    ax.bar_label(bars, padding=5, fontsize=10)
    ax.set_xlim(0, table["entity_count"].max() * 1.18)
    ax.set_xlabel(ar("عدد الكيانات المسجلة في الملف — جمعية أو مؤسسة"))
    ax.set_title(ar(title), pad=18, fontsize=15)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.grid(True, alpha=0.18)
    ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.37 if wrap else 0.21, right=0.95, top=0.91, bottom=0.15)
    add_source_footer(fig)
    fig.savefig(destination, dpi=150, facecolor="white")
    plt.close(fig)


def make_figures(root, tables):
    configure_charts()
    output = root / "outputs/figures"
    output.mkdir(parents=True, exist_ok=True)
    draw_bar(tables["locations_all_entities"], "location_label", "الحضور المسجل بحسب الموقع — 562 كياناً", output / "01_locations.png")
    draw_bar(tables["main_groups_all_entities"], "main_group_name", "التخصصات الرئيسية — 562 كياناً، 10 مجموعات", output / "02_main_groups.png", wrap=32)
    matrix = tables["location_by_main_group"].set_index("location_label")
    fig, ax = plt.subplots(figsize=(13, 12))
    im = ax.imshow(matrix.to_numpy(), cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns)
    ax.set_yticks(range(len(matrix)), [ar(label) for label in matrix.index])
    for y in range(len(matrix)):
        for x in range(len(matrix.columns)):
            value = int(matrix.iloc[y, x])
            ax.text(x, y, str(value), ha="center", va="center", fontsize=9,
                    color="white" if value > matrix.to_numpy().max() * 0.55 else "#173344")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02).set_label(ar("عدد الكيانات"))
    ax.set_title(ar("الموقع × المجموعة الرئيسية — الصفر يعني غياب سجل في هذا الملف فقط"), pad=18, fontsize=14)
    names = tables["main_groups_all_entities"].sort_values("main_group_code")
    legend = "\n".join(ar(f"{row.main_group_code}: {row.main_group_name}") for row in names.itertuples())
    fig.text(0.96, 0.30, legend, ha="right", va="top", fontsize=9, linespacing=1.5)
    fig.subplots_adjust(left=0.20, right=0.93, top=0.92, bottom=0.36)
    add_source_footer(fig)
    fig.savefig(output / "03_location_group_matrix.png", dpi=150, facecolor="white")
    plt.close(fig)
    return sorted(output.glob("*.png"))


# %% export
def export_results(root, raw, cleaned, changes, issues, tables, source_audit, checks, rules):
    for folder in ["data_clean", "outputs/tables", "outputs/quality"]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    clean_path = root / "data_clean/qassim_entities.csv"
    cleaned.to_csv(clean_path, index=False, encoding="utf-8-sig")
    roundtrip = pd.read_csv(clean_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if roundtrip["entity_id"].tolist() != cleaned["entity_id"].tolist():
        raise AssertionError("تغيّرت المعرّفات عند إعادة قراءة ملف التنظيف.")
    checks["csv_roundtrip_ids_preserved"] = True
    for name, table in tables.items():
        table.to_csv(root / f"outputs/tables/{name}.csv", index=False, encoding="utf-8-sig")
    changes.to_csv(root / "outputs/quality/text_changes.csv", index=False, encoding="utf-8-sig")
    issues.to_csv(root / "outputs/quality/review_issues.csv", index=False, encoding="utf-8-sig")
    mapping_rows = []
    for original, rule in rules["main_groups"].items():
        mapping_rows.append({"source_value": original, **rule, "entity_count": int(raw["التصنيف النوعي"].eq(original).sum())})
    pd.DataFrame(mapping_rows).to_csv(root / "outputs/quality/main_group_mapping_audit.csv", index=False, encoding="utf-8-sig")
    quality = {
        "source_audit": source_audit,
        "checks": checks,
        "normalization": {
            "raw_main_labels": int(raw["التصنيف النوعي"].nunique()),
            "canonical_main_groups": int(cleaned["main_group_code"].nunique()),
            "raw_subcategory_1_labels": int(raw["التصنيف الفرعي الاول"].nunique()),
            "canonical_subcategory_1_labels": int(cleaned["subcategory_1"].nunique()),
            "raw_subcategory_2_labels": int(raw["التصنيف الفرعي الثاني"].nunique()),
            "canonical_subcategory_2_labels": int(cleaned["subcategory_2"].nunique()),
            "changed_text_cells": len(changes),
            "entities_with_text_changes": int(changes["entity_id"].nunique()),
            "review_issue_records": len(issues),
            "entities_needing_review": int(cleaned["needs_review"].sum()),
            "issue_counts": {str(k): int(v) for k, v in issues["issue_code"].value_counts().items()},
        },
        "raw_rows_dropped": 0,
        "semantic_scope": "Registered entity presence, not verified service coverage or need.",
        "manual_review_status": "Rules proposed by analysis; publisher has not confirmed flagged descriptions or unspecified locations.",
    }
    write_json(root / "outputs/quality/quality_report.json", quality)
    write_json(root / "outputs/quality/source_and_license.json", json.loads((root / "research/qassim-source.json").read_text(encoding="utf-8")))
    return quality


def run_analysis(root=None):
    root = Path(root) if root else find_project_root()
    rules = json.loads((root / "config/qassim_mappings.json").read_text(encoding="utf-8"))
    raw, record_numbers, audit = read_source(root)
    cleaned, changes, issues = clean_entities(raw, record_numbers, rules)
    checks = validate_results(root, raw, cleaned)
    tables = summarize_entities(cleaned)
    figures = make_figures(root, tables)
    quality = export_results(root, raw, cleaned, changes, issues, tables, audit, checks, rules)
    return {"raw": raw, "cleaned": cleaned, "changes": changes, "issues": issues,
            "tables": tables, "figures": figures, "quality": quality}


if __name__ == "__main__":
    result = run_analysis()
    print("QASSIM_ANALYSIS_OK")
    print(json.dumps(result["quality"], ensure_ascii=False, indent=2))
