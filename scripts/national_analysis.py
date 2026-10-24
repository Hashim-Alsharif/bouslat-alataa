"""Regional compatibility analysis. Never call an incomplete union all Saudi data."""
# %% imports
from pathlib import Path
from collections import Counter
import csv
import hashlib
import io
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
from qassim_analysis import EXPECTED_COLUMNS, normalize_text, clean_entities, count_table, configure_charts
from audit_national_sources import read_regional_source
from verify_source_pairs import verify_source_pairs

LICENSE_URL="https://open.data.gov.sa/ar/pages/policies/license"


def project_root():
    cwd=Path.cwd()
    for path in [cwd,cwd/"bouslat-alataa-national",*cwd.parents]:
        if (path/"research/national_sources.json").is_file():
            return path
    raise FileNotFoundError("استخرج حزمة المشروع التي تحتوي research/national_sources.json أولاً.")


# %% load
def load_sources(root, require_all_regions=True):
    manifest=json.loads((root/"research/national_sources.json").read_text(encoding="utf-8"))
    frames, inventory=[],[]
    for source in manifest["sources"]:
        entry={key:source[key] for key in ["region","slug","dataset_url","updated_at_as_displayed","reference_period_as_displayed","local_file"]}
        try:
            rows, details=read_regional_source(root,source)
        except ValueError as error:
            entry.update(status="unavailable",reason=str(error),records=None,encoding=None)
        else:
            frame=pd.DataFrame(rows,dtype=object)
            frame["source_region"]=source["region"]
            frame["source_slug"]=source["slug"]
            frame["source_dataset_id"]=source["dataset_id"]
            frame["source_dataset_url"]=source["dataset_url"]
            frame["source_updated_at"]=source["updated_at_as_displayed"]
            frame["source_reference_period"]=source["reference_period_as_displayed"]
            frame["source_has_national_id"]=details["identifier_column_present"]
            frame["record_key"]=source["slug"]+":"+frame["source_record"].astype(str)
            frames.append(frame)
            entry.update(status="readable",reason="",records=len(frame),**details)
        inventory.append(entry)
    inventory=pd.DataFrame(inventory)
    missing=inventory.loc[inventory.status.ne("readable"),"region"].tolist()
    if require_all_regions and missing:
        raise ValueError("لا يمكن اعتماد تغطية 13/13؛ المصادر غير المتاحة: "+"، ".join(missing))
    if not frames:
        raise ValueError("لا توجد ملفات صالحة للتحليل.")
    return pd.concat(frames,ignore_index=True),inventory,manifest


# %% normalize
def normalize_national(raw,rules):
    # record_key is a source-row key, never a substitute national identifier.
    cleaned,changes,issues=clean_entities(raw[EXPECTED_COLUMNS],raw["source_record"].tolist(),rules,audit_keys=raw["record_key"])
    for column in raw.columns:
        if column not in EXPECTED_COLUMNS:
            cleaned[column]=raw[column].to_numpy()
    cleaned["region"]=raw["source_region"].to_numpy()
    cleaned["has_national_id"]=cleaned.entity_id.ne("")
    cleaned["standard_main_group"]=cleaned.main_group_code.str.match(r"G[0-9]{2}$")
    cleaned["subcategory_1_comparable"]=~cleaned.source_slug.isin(rules["source_level_flags"])
    additional=[]
    def issue(index,code,field,reason):
        additional.append({"record_key":cleaned.at[index,"record_key"],"issue_code":code,
                           "source_field":field,"source_value":raw.at[index,field],"reason":reason})
    for index,row in cleaned.iterrows():
        if not row.has_national_id:
            issue(index,"NATIONAL_ID_NOT_PUBLISHED","الرقم الوطني الموحد","حقل الرقم الوطني غير منشور في هذا المصدر؛ تُرك فارغاً، ولا يشمله فحص التكرار بالأرقام الوطنية.")
        if row.geo_status=="named_unit_unstated":
            issue(index,"LOCATION_UNIT_NOT_PUBLISHED","المدينة","اسم موقع دون نوع وحدة في المصدر؛ لم نفترض أنه مدينة أو محافظة.")
        if not row.standard_main_group:
            issue(index,"NONSTANDARD_MAIN_CLASSIFICATION","التصنيف النوعي",rules["main_groups"][row["التصنيف النوعي"]]["reason"])
        for column in EXPECTED_COLUMNS:
            if column=="الرقم الوطني الموحد" and not row.source_has_national_id:
                continue
            if not str(raw.at[index,column]).strip():
                issue(index,"SOURCE_CELL_BLANK",column,"خلية أصلية فارغة؛ لم نملأها بتخمين.")
        if not row.subcategory_1_comparable:
            issue(index,"SUBCATEGORY_LEVELS_IDENTICAL_SOURCE","التصنيف الفرعي الاول",rules["source_level_flags"][row.source_slug])
        for candidate in rules["location_cross_file_review"]:
            if row.region==candidate["region"] and row.location_label==candidate["location_label"]:
                issue(index,"LOCATION_CROSS_FILE_REVIEW","المدينة",
                      "الاسم نفسه يظهر أيضاً في مجموعة "+candidate["also_seen_in"]+"؛ مرشح لمراجعة الموقع، دون نقل الصف إلى منطقة أخرى.")
    issues=pd.concat([issues,pd.DataFrame(additional)],ignore_index=True)
    unknown_names=set(cleaned.loc[~cleaned.has_national_id,"entity_name"])
    known_names=set(cleaned.loc[cleaned.has_national_id,"entity_name"])
    for index in cleaned.index[~cleaned.has_national_id & cleaned.entity_name.isin(unknown_names & known_names)]:
        issues=pd.concat([issues,pd.DataFrame([{"record_key":cleaned.at[index,"record_key"],"issue_code":"NAME_MATCH_WITHOUT_NATIONAL_ID","source_field":"اسم الكيان","source_value":raw.at[index,"اسم الكيان"],"reason":"اسم مطابق بعد ضبط المسافات يظهر في مصدر ذي معرّف؛ تشابه الاسم لا يكفي للربط أو حذف السجل."}])],ignore_index=True)
    issues=issues.merge(cleaned[["record_key","entity_id","region","source_csv_record"]],on="record_key",validate="many_to_one")
    cleaned["needs_review"]=cleaned.record_key.isin(issues.record_key)
    changes=changes.merge(cleaned[["record_key","entity_id","region"]],on="record_key",validate="many_to_one")
    changes.loc[changes.field.eq("location_label"),"reason"]="توحيد مسافات واسم الموقع وفق خريطة صريحة، مع إبقاء نوع الوحدة والمصدر الأصلي."
    return cleaned,changes,issues


# %% validate
def check_national(root,raw,cleaned,inventory,manifest):
    expected_regions={source["region"] for source in manifest["sources"]}
    hashes={source["slug"]:hashlib.sha256((root/source["local_file"]).read_bytes()).hexdigest()==source["source_sha256"] for source in manifest["sources"]}
    companion_hashes=[hashlib.sha256((root/item["local_file"]).read_bytes()).hexdigest()==item["sha256"] for source in manifest["sources"] for item in source.get("companion_attachments",[])]
    identified=cleaned.loc[cleaned.has_national_id,"entity_id"]
    checks={
        "all_13_regions_catalogued":len(expected_regions)==len(manifest["sources"])==13,
        "source_bytes_unchanged":all(hashes.values()),
        "all_supplied_companion_bytes_unchanged":all(companion_hashes),
        "all_readable_source_records_preserved":len(raw)==len(cleaned),
        "all_published_original_cells_preserved":raw[EXPECTED_COLUMNS].equals(cleaned[EXPECTED_COLUMNS]),
        "published_national_identifiers_unique":identified.is_unique,
        "published_identifiers_are_ten_digit_strings":bool(identified.str.fullmatch(r"[0-9]{10}").all()),
        "source_record_keys_unique":cleaned.record_key.is_unique,
        "unpublished_national_identifiers_remain_blank":bool(cleaned.loc[~cleaned.source_has_national_id,"entity_id"].eq("").all()),
        "published_id_columns_have_no_missing_ids":bool(cleaned.loc[cleaned.source_has_national_id,"has_national_id"].all()),
        "unavailable_regions_have_no_zero_counts":bool(inventory.loc[inventory.status.ne("readable"),"records"].isna().all()),
        "region_counts_reconcile":int(inventory.loc[inventory.status.eq("readable"),"records"].sum())==len(cleaned),
        "entity_types_preserved":raw["نوع الكيان"].value_counts().to_dict()==cleaned.entity_type.value_counts().to_dict(),
        "nonstandard_main_values_flagged":set(cleaned.loc[~cleaned.standard_main_group,"record_key"]).issubset(set(cleaned.loc[cleaned.needs_review,"record_key"])),
        "makkah_subcategory_1_excluded_from_comparisons":not bool(cleaned.loc[cleaned.source_slug.eq("makkah"),"subcategory_1_comparable"].any()),
    }
    if not all(checks.values()):
        raise AssertionError({name:value for name,value in checks.items() if not value})
    return checks


def require_complete_national_identifiers(cleaned):
    missing=int((~cleaned.has_national_id).sum())
    if missing:
        raise ValueError(f"لا يمكن اعتماد فحص تكرار وطني كامل: {missing} سجلاً بلا رقم وطني منشور.")


# %% summarize
def summarize_national(cleaned,inventory):
    covered=inventory.loc[inventory.status.eq("readable"),"region"].nunique()
    tables={
        "regions":count_table(cleaned,["region"]),
        "entity_types":count_table(cleaned,["entity_type"]),
        "main_groups":count_table(cleaned,["main_group_code","main_group_name","standard_main_group"]),
        "locations":count_table(cleaned,["region","location_label","locality_unit"]),
        "associations_by_region":count_table(cleaned.loc[cleaned.entity_type.eq("جمعية أهلية")],["region"]),
        "foundations_by_region":count_table(cleaned.loc[cleaned.entity_type.eq("مؤسسة أهلية")],["region"]),
        "subcategories_1_comparable":count_table(cleaned.loc[cleaned.subcategory_1_comparable & cleaned.standard_main_group],["main_group_code","subcategory_1"]),
        "identifier_coverage_by_region":cleaned.groupby("region").agg(source_records=("record_key","size"),records_with_national_id=("has_national_id","sum")).reset_index(),
    }
    matrix=pd.crosstab(cleaned.region,cleaned.main_group_code).reindex(index=tables["regions"].region,fill_value=0)
    matrix.index.name="region"
    tables["region_main_matrix"]=matrix.reset_index()
    within=cleaned.groupby(["region","main_group_code","main_group_name"]).size().reset_index(name="entity_count")
    within["region_denominator"]=within.region.map(cleaned.region.value_counts())
    within["share_within_region_percent"]=(100*within.entity_count/within.region_denominator).round(2)
    tables["main_groups_within_region"]=within
    tables["identifier_coverage_by_region"]["records_without_national_id"]=tables["identifier_coverage_by_region"].source_records-tables["identifier_coverage_by_region"].records_with_national_id
    for name in ["regions","entity_types","main_groups","locations"]:
        if int(tables[name].entity_count.sum())!=len(cleaned):
            raise AssertionError("Totals mismatch: "+name)
        tables[name]["covered_regions"]=covered
        tables[name]["expected_regions"]=13
    return tables


# %% figures
def source_footer(fig,covered):
    fig.text(.03,.078,"المصدر: المركز الوطني لتنمية القطاع غير الربحي — الملفات الإقليمية المتاحة ("+str(covered)+"/13).",fontsize=8)
    fig.text(.03,.055,"Sources and per-region dates: research/national_sources.json — open.data.gov.sa",fontsize=7)
    fig.text(.03,.034,"License: "+LICENSE_URL,fontsize=7)


def national_figures(root,tables,inventory,manifest):
    configure_charts()
    folder=root/"outputs/national/figures"
    folder.mkdir(parents=True,exist_ok=True)
    covered=int(inventory.status.eq("readable").sum())
    total=int(tables["regions"].entity_count.sum())
    metadata={"Description":json.dumps({"sources":[s["dataset_url"] for s in manifest["sources"] if s["region"] in set(tables["regions"].region)],"license":LICENSE_URL},ensure_ascii=False)}
    for filename,table,label,title,wrap in [
        ("01_regions.png",tables["regions"],"region",f"سجلات الجهات بحسب منطقة المصدر — {covered}/13 منطقة، {total} سجلاً",None),
        ("02_main_groups.png",tables["main_groups"],"main_group_name",f"التصنيفات المنشورة — {covered}/13 منطقة؛ القيم غير القياسية معروضة منفصلة",31),
    ]:
        selected=table.iloc[::-1]
        labels=["\n".join(textwrap.wrap(str(value),wrap)) if wrap else str(value) for value in selected[label]]
        fig,ax=plt.subplots(figsize=(13,10))
        colors=["#b87513" if label=="main_group_name" and not bool(row.standard_main_group) else "#147d78" for row in selected.itertuples()]
        bars=ax.barh(labels,selected.entity_count,color=colors)
        ax.bar_label(bars,padding=4,fontsize=10)
        ax.set_xlim(0,float(selected.entity_count.max())*1.17)
        ax.set_xlabel("عدد سجلات الجهات؛ الجوف بلا أرقام وطنية، وفحص التكرار فيها غير مكتمل")
        ax.set_title(title,pad=18,fontsize=13)
        ax.spines[["right","top"]].set_visible(False)
        fig.subplots_adjust(left=.40 if wrap else .19,right=.96,top=.91,bottom=.17)
        source_footer(fig,covered)
        fig.savefig(folder/filename,dpi=150,metadata=metadata,facecolor="white")
        plt.close(fig)
    matrix=tables["region_main_matrix"].set_index("region")
    fig,ax=plt.subplots(figsize=(14,10))
    im=ax.imshow(matrix.to_numpy(),cmap="YlGnBu",aspect="auto")
    ax.set_xticks(range(len(matrix.columns)),matrix.columns)
    ax.set_yticks(range(len(matrix)),matrix.index)
    for y in range(len(matrix)):
        for x in range(len(matrix.columns)):
            value=int(matrix.iloc[y,x])
            ax.text(x,y,str(value),ha="center",va="center",fontsize=9,color="white" if value>matrix.to_numpy().max()*.55 else "#173344")
    fig.colorbar(im,ax=ax,fraction=.025,pad=.02)
    unavailable=inventory.loc[inventory.status.ne("readable"),"region"].tolist()
    suffix="؛ غير متاح: "+"، ".join(unavailable) if unavailable else ""
    ax.set_title(f"منطقة المصدر × التصنيف — تغطية {covered}/13؛ العد للسجلات"+suffix,pad=17,fontsize=13)
    legend=tables["main_groups"].sort_values("main_group_code")
    legend_text="\n".join(f"{r.main_group_code}: {r.main_group_name}" for r in legend.itertuples())
    fig.text(.96,.34,legend_text,ha="right",va="top",fontsize=9,linespacing=1.4)
    fig.subplots_adjust(left=.16,right=.92,top=.91,bottom=.40)
    source_footer(fig,covered)
    fig.savefig(folder/"03_region_main_matrix.png",dpi=150,metadata=metadata,facecolor="white")
    plt.close(fig)
    return sorted(folder.glob("*.png"))


# %% export
def export_national(root,raw,cleaned,changes,issues,inventory,tables,checks,manifest):
    folder=root/"outputs/national"
    for relative in ["tables","quality"]:
        (folder/relative).mkdir(parents=True,exist_ok=True)
    destination=root/"data_clean/national_entities_available.csv"
    cleaned.to_csv(destination,index=False,encoding="utf-8-sig")
    reloaded=pd.read_csv(destination,dtype=str,keep_default_na=False,encoding="utf-8-sig")
    if reloaded.entity_id.tolist()!=cleaned.entity_id.tolist():
        raise AssertionError("CSV identifier roundtrip failed")
    checks["csv_identifier_roundtrip"]=True
    inventory.to_csv(folder/"tables/source_inventory_13_regions.csv",index=False,encoding="utf-8-sig")
    for name,table in tables.items():
        table.to_csv(folder/f"tables/{name}.csv",index=False,encoding="utf-8-sig")
    changes.to_csv(folder/"quality/text_changes.csv",index=False,encoding="utf-8-sig")
    issues.to_csv(folder/"quality/review_issues.csv",index=False,encoding="utf-8-sig")
    issue_counts={str(k):int(v) for k,v in issues.issue_code.value_counts().items()}
    coverage={"catalogued":13,"readable":int(inventory.status.eq("readable").sum()),
              "unavailable_regions":inventory.loc[inventory.status.ne("readable"),"region"].tolist(),
              "complete":bool(inventory.status.eq("readable").all()),"scope":"Regional publication availability only; not registry completeness."}
    report={"coverage":coverage,"records":len(cleaned),"entity_types":{str(k):int(v) for k,v in cleaned.entity_type.value_counts().items()},
            "unique_published_national_ids":int(cleaned.loc[cleaned.has_national_id,"entity_id"].nunique()),
            "records_with_national_id":int(cleaned.has_national_id.sum()),"records_without_national_id":int((~cleaned.has_national_id).sum()),
            "complete_national_entity_deduplication":bool(cleaned.has_national_id.all()),
            "counting_unit":"Source entity record. Records without a published national identifier are not nationally deduplicated.",
            "checks":checks,"issue_counts":issue_counts,
            "entities_with_review_issues":int(cleaned.needs_review.sum()),"standard_main_records":int(cleaned.standard_main_group.sum()),
            "source_cells_unchanged":True,"observation_scope":"Available regional publications; not a simultaneous or complete national census.",
            "subcategory_1_comparison_excludes":"makkah: all 1365 source rows have identical first/second subcategory values; publisher review needed."}
    (folder/"quality/quality_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (folder/"source_links.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report


def run(root=None,require_all_regions=True):
    root=Path(root) if root else project_root()
    verify_source_pairs(root)
    raw,inventory,manifest=load_sources(root,require_all_regions)
    rules=json.loads((root/"config/national_mappings.json").read_text(encoding="utf-8"))
    cleaned,changes,issues=normalize_national(raw,rules)
    checks=check_national(root,raw,cleaned,inventory,manifest)
    tables=summarize_national(cleaned,inventory)
    figures=national_figures(root,tables,inventory,manifest)
    report=export_national(root,raw,cleaned,changes,issues,inventory,tables,checks,manifest)
    return {"raw":raw,"cleaned":cleaned,"changes":changes,"issues":issues,"inventory":inventory,"tables":tables,"figures":figures,"report":report}


if __name__=="__main__":
    result=run()
    print("NATIONAL_AVAILABLE_DATA_ANALYSIS_OK")
    print(json.dumps(result["report"],ensure_ascii=False,indent=2))
