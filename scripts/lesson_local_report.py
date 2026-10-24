"""Teaching example: a new descriptive report from the reviewed clean data.

Run from the project directory:
    python scripts/lesson_local_report.py
This does not modify the official sources or the main reports.
"""
from pathlib import Path
import base64
import html
import json

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_clean/national_entities_available.csv"
OUTPUT = ROOT / "outputs/learning"
OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(
    SOURCE, encoding="utf-8-sig", dtype=str,
    keep_default_na=False,
)
required = {"record_key", "main_group_code", "region"}
assert required.issubset(df.columns)
assert df["record_key"].is_unique
assert len(df) > 0

summary = (
    df.groupby("main_group_code", dropna=False)
    .size().reset_index(name="records")
    .sort_values("records", ascending=False)
)
assert int(summary["records"].sum()) == len(df)
summary["share_percent"] = (
    summary["records"] / len(df) * 100
).round(2)
summary.to_csv(
    OUTPUT / "main_groups.csv", index=False,
    encoding="utf-8-sig",
)

fig, ax = plt.subplots(figsize=(9, 5))
ordered = summary.sort_values("records")
ax.barh(ordered["main_group_code"], ordered["records"],
        color="#16746c")
ax.set_xlabel("Source records")
ax.set_title("Recorded entities by main group")
fig.tight_layout()
chart = OUTPUT / "main_groups.png"
fig.savefig(chart, dpi=160, bbox_inches="tight")
plt.close(fig)

table = summary.to_html(
    index=False, border=0, escape=True,
    float_format=lambda value: f"{value:.2f}",
)
encoded = base64.b64encode(chart.read_bytes()).decode("ascii")
title = html.escape("Bouslat Al-Ataa | Learning report")
page = f'''<!doctype html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
body {{font:17px/1.8 Arial; background:#f3f6f7; color:#17303e}}
main {{max-width:1000px; margin:auto; padding:24px}}
section {{background:white; padding:24px; border-radius:12px}}
table {{width:100%; border-collapse:collapse}}
th,td {{padding:9px; text-align:right; border-bottom:1px solid #ddd}}
img {{width:100%; height:auto}}
</style></head>
<body><main><section>
<h1 dir="ltr">{title}</h1>
<p dir="ltr">Source records: {len(df):,}. Not service coverage.</p>
{table}
<img src="data:image/png;base64,{encoded}" alt="Main groups chart">
<p dir="ltr">Source: NCNP regional publications. Counts are records.</p>
<p dir="ltr">Keep DATA_LICENSE.md and the source manifest with this report.</p>
</section></main></body></html>'''
report = OUTPUT / "lesson_report.html"
report.write_text(page, encoding="utf-8")
(OUTPUT / "checks.json").write_text(
    json.dumps({"records": len(df), "checks_passed": True}, indent=2),
    encoding="utf-8",
)
print("LESSON_REPORT_OK")
print(report)
