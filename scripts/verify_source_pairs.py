"""Recheck the copied CSV/XLSX pairs without reading user Downloads."""
from pathlib import Path
import csv
import hashlib
import io
import json


def verify_source_pairs(root):
    import openpyxl
    comparisons=json.loads((root/"research/user_supplied_comparison.json").read_text(encoding="utf-8"))["comparisons"]
    results=[]
    for comparison in comparisons:
        attachments={item["format"]:item for item in comparison["attachments"]}
        for attachment in attachments.values():
            if hashlib.sha256((root/attachment["local_file"]).read_bytes()).hexdigest()!=attachment["sha256"]:
                raise ValueError("Attached original bytes changed: "+attachment["local_file"])
        text=(root/attachments["CSV"]["local_file"]).read_bytes().decode(comparison["encoding"],errors="strict")
        csv_rows=[row for row in csv.reader(io.StringIO(text,newline="")) if any(value.strip() for value in row)]
        workbook=openpyxl.load_workbook(root/attachments["XLSX"]["local_file"],read_only=True,data_only=False)
        sheet=workbook[comparison["sheet_compared"]]
        xlsx_rows=[]
        for cells in sheet.iter_rows():
            if any(cell.data_type=="f" for cell in cells):
                raise ValueError("Unexpected formula in original data sheet")
            values=[]
            for cell in cells:
                value=cell.value
                if value is None:
                    value=""
                elif isinstance(value,float) and value.is_integer():
                    value=str(int(value))
                else:
                    value=str(value)
                values.append(value)
            if any(value.strip() for value in values):
                xlsx_rows.append(values)
        workbook.close()
        if csv_rows!=xlsx_rows or len(csv_rows)-1!=comparison["data_records"]:
            raise AssertionError("CSV/XLSX cell comparison failed: "+comparison["region"])
        results.append({"region":comparison["region"],"data_records":len(csv_rows)-1,
                        "csv_xlsx_all_cells_equal":True,"all_four_source_files_unchanged":True,
                        "national_id_column_present":"الرقم الوطني الموحد" in csv_rows[0]})
    return results


if __name__=="__main__":
    print(json.dumps(verify_source_pairs(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
