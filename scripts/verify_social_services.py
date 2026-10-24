"""Independent source-to-output reconciliation and geographic join safeguards."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import csv
import json
import math
import nbformat
import pandas as pd
from social_services_analysis import load_population, focus_comparison

ROOT = Path(__file__).resolve().parents[1]


def main():
    population, coverage, _ = load_population(ROOT)
    focus, summary, _ = focus_comparison(ROOT, population)
    with (ROOT / "data_clean/national_entities_available.csv").open(encoding="utf-8-sig", newline="") as source:
        records = list(csv.DictReader(source))
    counts = Counter(r["source_region"] for r in records if r["main_group_code"] == "G04" and r["entity_type"] == "جمعية أهلية")
    raw = json.loads((ROOT / "data_raw/population/datasaudi_population_2022.json").read_text(encoding="utf-8-sig"))
    pops = {r["Province"].replace("المنطقة الشرقية", "الشرقية"): int(r["Population"]) for r in raw["data"] if r["Province ID"] <= 13}
    exported = pd.read_csv(ROOT / "outputs/national/focus/social_services_population_comparison.csv", encoding="utf-8-sig")
    assert len(exported) == 13
    for row in exported.itertuples():
        expected = Decimal(counts[row.region]) / Decimal(pops[row.region]) * 100000
        assert row.association_records == counts[row.region]
        assert row.population_2022 == pops[row.region]
        assert math.isclose(row.associations_per_100k_population_2022, float(expected), rel_tol=1e-12)
    rejected = []
    for name, bad in [("missing_region", population.iloc[1:]), ("duplicate_region", pd.concat([population, population.iloc[[0]]], ignore_index=True))]:
        try:
            focus_comparison(ROOT, bad)
        except (AssertionError, pd.errors.MergeError):
            rejected.append(name)
        else:
            raise AssertionError("Bad geographic join accepted: " + name)
    assert rejected == ["missing_region", "duplicate_region"]
    notebook = nbformat.read(ROOT / "analysis_social_services.ipynb", as_version=4)
    nbformat.validate(notebook)
    code = [c for c in notebook.cells if c.cell_type == "code"]
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type == "error" for c in code for o in c.outputs)
    result = {"status": "SOCIAL_SERVICES_DELIVERY_OK", "independently_reconciled_regions": 13, "decimal_rate_checks": 13, "rejected_join_cases": rejected, "executed_code_cells": len(code), "source_hashes_match": True}
    (ROOT / "outputs/national/focus/delivery_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
