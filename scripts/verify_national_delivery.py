"""Targeted delivery checks for adding a source with unpublished identifiers."""
from pathlib import Path
import hashlib
import json
import sys
import nbformat
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import qassim_analysis as q
from national_analysis import load_sources,require_complete_national_identifiers
from verify_source_pairs import verify_source_pairs


def main():
    pairs=verify_source_pairs(ROOT)
    report=json.loads((ROOT/"outputs/national/quality/quality_report.json").read_text(encoding="utf-8"))
    assert all(report["checks"].values())
    assert report["coverage"]["readable"]==13 and report["records"]==6403
    assert report["unique_published_national_ids"]==6341
    frame=pd.read_csv(ROOT/"data_clean/national_entities_available.csv",dtype=str,keep_default_na=False,encoding="utf-8-sig")
    jouf=frame.loc[frame.region.eq("الجوف")]
    assert len(jouf)==62 and jouf.entity_id.eq("").all() and frame.record_key.is_unique
    assert frame.loc[frame.entity_id.ne(""),"entity_id"].is_unique
    issues=pd.read_csv(ROOT/"outputs/national/quality/review_issues.csv",dtype=str,keep_default_na=False,encoding="utf-8-sig")
    missing=issues.loc[issues.issue_code.eq("NATIONAL_ID_NOT_PUBLISHED")]
    assert len(missing)==missing.record_key.nunique()==62
    assert missing.region.eq("الجوف").all() and missing.entity_id.eq("").all()
    raw,inventory,manifest=load_sources(ROOT,require_all_regions=True)
    assert len(raw)==6403 and inventory.status.eq("readable").all()
    try:
        require_complete_national_identifiers(pd.DataFrame({"has_national_id":frame.has_national_id.eq("True")}))
    except ValueError:
        identifier_gate_rejected=True
    else:
        raise AssertionError("Incomplete identifier gate accepted missing identifiers")
    # The shared cleaner's default behavior must preserve the earlier Qassim output.
    qraw,numbers,_=q.read_source(ROOT)
    qrules=json.loads((ROOT/"config/qassim_mappings.json").read_text(encoding="utf-8"))
    qclean,_,_=q.clean_entities(qraw,numbers,qrules)
    previous=pd.read_csv(ROOT/"data_clean/qassim_entities.csv",dtype=str,keep_default_na=False,encoding="utf-8-sig")
    assert qclean.astype(str).equals(previous[qclean.columns])
    notebook=nbformat.read(ROOT/"analysis_national.ipynb",as_version=4)
    nbformat.validate(notebook)
    code=[cell for cell in notebook.cells if cell.cell_type=="code"]
    assert all(cell.execution_count is not None for cell in code)
    assert not any(output.output_type=="error" for cell in code for output in cell.outputs)
    result={"regional_files_readable":13,"source_records":6403,"unique_published_national_ids":6341,
            "jouf_unpublished_identifiers_preserved":62,"csv_xlsx_pairs_rechecked":len(pairs),
            "all_pipeline_checks_passed":len(report["checks"]),"executed_notebook_code_cells":len(code),
            "national_identifier_completeness_gate_rejected_as_expected":identifier_gate_rejected,
            "qassim_default_cleaner_matches_previous_output":True,"source_record_keys_unique":True}
    (ROOT/"outputs/national/quality/delivery_check.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NATIONAL_13_REGION_DELIVERY_OK")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
