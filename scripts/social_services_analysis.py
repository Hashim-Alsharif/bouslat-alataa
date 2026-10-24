"""Reproducible descriptive comparison; never interprets density as unmet need."""
from pathlib import Path
import base64
import hashlib
import html
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_population(root):
    meta = json.loads((root / "research/population_sources.json").read_text(encoding="utf-8"))
    for item in meta["files"]:
        assert hashlib.sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
    assert hashlib.sha256((root / "data_clean/national_entities_available.csv").read_bytes()).hexdigest() == meta["entity_input_sha256"], "Entity input changed; review provenance before rerunning"
    payload = json.loads((root / meta["selected_file"]).read_text(encoding="utf-8-sig"))
    data = pd.DataFrame(payload["data"])
    assert len(data) == payload["page"]["total"] == 14
    assert data["Year"].eq(2022).all()
    assert data["Sex ID"].eq(3).all() and data["Nationality ID"].eq(3).all()
    assert data["Population"].gt(0).all() and (data["Population"] % 1).eq(0).all()
    assert data["Province ID"].is_unique
    national = data.loc[data["Province ID"].eq(15), "Population"]
    assert len(national) == 1
    pop = data.loc[data["Province ID"].between(1, 13)].copy()
    assert set(pop["Province ID"]) == set(range(1, 14))
    assert int(pop["Population"].sum()) == int(national.iloc[0]) == 32175224
    # Explicit name mapping; the unmodified official name is retained.
    pop["region"] = pop["Province"].replace({"المنطقة الشرقية": "الشرقية"})
    pop = pop.rename(columns={"Province": "population_region_original", "Population": "population_2022"})
    pop["population_2022"] = pop["population_2022"].astype("int64")
    pop["population_year"] = 2022
    pop["population_scope"] = "جميع السكان؛ الجنسيات والجنسين"
    pop["population_source_url"] = meta["api_url"]
    years = json.loads((root / "data_raw/population/datasaudi_population_years.json").read_text(encoding="utf-8-sig"))
    annual = pd.DataFrame(years["data"])
    assert len(annual) == years["page"]["total"]
    coverage = annual.groupby("Year").agg(rows=("Province ID", "size"), regional_rows=("Province ID", lambda v: v.between(1, 13).sum())).reset_index()
    assert int(coverage.loc[coverage.regional_rows.eq(13), "Year"].max()) == 2022
    return pop, coverage, meta


def focus_comparison(root, population):
    entities = pd.read_csv(root / "data_clean/national_entities_available.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    assert entities.record_key.is_unique and len(entities) == 6403
    assert set(entities.source_region) == set(population.region)
    focus = entities.loc[entities.main_group_code.eq("G04")].copy()
    assert set(focus.entity_type) == {"جمعية أهلية", "مؤسسة أهلية"}
    associations = focus.loc[focus.entity_type.eq("جمعية أهلية")].copy()
    foundations = focus.loc[focus.entity_type.eq("مؤسسة أهلية")].copy()
    assert (len(focus), len(associations), len(foundations)) == (1607, 1546, 61)
    counts = focus.groupby(["source_region", "entity_type"]).size().unstack(fill_value=0).rename(columns={"جمعية أهلية": "association_records", "مؤسسة أهلية": "foundation_records"})
    missing = associations.loc[associations.entity_id.eq("")].groupby("source_region").size()
    dates = entities.groupby("source_region").agg(entity_reference_period=("source_reference_period", "first"), entity_source_updated_at=("source_updated_at", "first"), entity_source_url=("source_dataset_url", "first"))
    summary = population.merge(counts, left_on="region", right_index=True, how="outer", validate="one_to_one", indicator=True)
    assert summary._merge.eq("both").all() and len(summary) == 13
    summary = summary.drop(columns="_merge").merge(dates, left_on="region", right_index=True, validate="one_to_one")
    summary["association_records_without_id"] = summary.region.map(missing).fillna(0).astype(int)
    assert summary.association_records_without_id.sum() == 30
    summary["all_social_service_records"] = summary.association_records + summary.foundation_records
    # Full-precision rate is preserved; rounding is a presentation operation only.
    summary["associations_per_100k_population_2022"] = summary.association_records / summary.population_2022 * 100000
    summary["interpretation_note"] = "حضور مسجل؛ المقام 2022؛ اختلاف تواريخ المصادر؛ لا يقيس الاحتياج أو الطاقة التشغيلية"
    summary.loc[summary.region.eq("الجوف"), "interpretation_note"] += "; 30 جمعية بلا معرّف وطني منشور؛ مصدر الجهات 2025"
    assert summary.association_records.sum() == len(associations)
    assert summary.foundation_records.sum() == len(foundations)
    assert np.isfinite(summary.associations_per_100k_population_2022).all()
    # A transparent sensitivity view: no invented IDs and no zero substituted for missing IDs.
    identified = summary.loc[summary.association_records_without_id.eq(0)].copy()
    identified["scope_note"] = "12 منطقة فقط؛ الجوف مستبعدة لغياب المعرّفات؛ ليست نتيجة وطنية بديلة"
    return focus, summary, identified


def draw_focus(summary, folder):
    plt.rcParams.update({"font.family": "Arial", "font.size": 11})
    fig, axes = plt.subplots(1, 2, figsize=(15, 8))
    views = [("association_records", "عدد سجلات جمعيات الخدمات الاجتماعية", "سجل جمعية"),
             ("associations_per_100k_population_2022", "الحضور المسجل نسبة إلى سكان 2022", "سجل جمعية لكل 100 ألف نسمة — سكان 2022")]
    for ax, (column, title, xlabel) in zip(axes, views):
        values = summary.sort_values(column)
        labels = [name + (" *" if name == "الجوف" else "") for name in values.region]
        ax.barh(labels, values[column], color=["#b47a25" if name == "الجوف" else "#16746c" for name in values.region])
        ax.set_title(title, pad=16, fontsize=14)
        ax.set_xlabel(xlabel)
        ax.set_xlim(0, values[column].max() * 1.18)
        ax.grid(axis="x", alpha=.15)
        ax.set_axisbelow(True)
        for i, value in enumerate(values[column]):
            ax.text(value + values[column].max() * .015, i, f"{value:.2f}" if column != "association_records" else str(int(value)), va="center", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("بوصلة العطاء | جمعيات الخدمات الاجتماعية — مقارنة وصفية للمناطق الـ13", fontsize=17)
    fig.text(.5, .025, "منشورات الجهات مختلفة التواريخ (2025–2026)؛ السكان 2022. * الجوف: معرّفات الجمعيات الثلاثين غير منشورة.\nالعدد والمعدل لا يقيسان نطاق الخدمة أو حجم الاحتياج؛ لا تُستنتج منهما أولوية تمويل.", ha="center", fontsize=11)
    fig.tight_layout(rect=(0, .09, 1, .94), w_pad=4)
    path = folder / "counts_and_rates.png"
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def export_focus(root, focus, summary, identified, coverage, meta, chart):
    folder = root / "outputs/national/focus"
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in [("social_services_records", focus), ("social_services_population_comparison", summary), ("identified_regions_sensitivity", identified), ("population_year_coverage", coverage)]:
        data.to_csv(folder / f"{name}.csv", index=False, encoding="utf-8-sig")
    population_columns = ["region", "population_region_original", "population_2022", "population_year", "population_scope", "population_source_url"]
    summary[population_columns].to_csv(root / "data_clean/population_regions_2022.csv", index=False, encoding="utf-8-sig")
    row = summary.set_index("region")
    national_rate = summary.association_records.sum() / summary.population_2022.sum() * 100000
    shown = summary[["region", "association_records", "foundation_records", "population_2022", "associations_per_100k_population_2022", "association_records_without_id"]].sort_values("associations_per_100k_population_2022", ascending=False)
    shown.columns = ["المنطقة", "سجلات الجمعيات", "سجلات المؤسسات", "سكان 2022", "جمعيات لكل 100 ألف — سكان 2022", "جمعيات بلا معرّف منشور"]
    table = shown.to_html(index=False, border=0, escape=True, float_format=lambda v: f"{v:.2f}")
    encoded = base64.b64encode(chart.read_bytes()).decode("ascii")
    report = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>بوصلة العطاء — الخدمات الاجتماعية والسكان</title><style>
body{{margin:0;background:#f3f6f7;color:#172e3b;font:17px/1.9 Arial,sans-serif}}main{{max-width:1200px;margin:auto;padding:26px 24px 60px}}section{{background:white;border:1px solid #dce4e6;border-radius:12px;padding:24px;margin:22px 0}}h1,h2{{color:#115d57}}h1{{font-size:32px}}h2{{font-size:24px}}.notice{{background:#fff3d9;border-right:5px solid #b47a25;padding:18px}}.cards{{display:flex;flex-wrap:wrap;gap:15px}}.card{{background:#e8f2ef;padding:16px;flex:1;min-width:170px}}.number{{display:block;font-size:32px;font-weight:bold;color:#126b63}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:15px}}th,td{{padding:10px;border-bottom:1px solid #dbe4e5;text-align:right}}th{{background:#e8f2ef}}img{{width:100%;height:auto}}a{{color:#08639b;overflow-wrap:anywhere}}code{{direction:ltr;unicode-bidi:embed}}footer,figcaption{{font-size:14px;color:#51656e}}</style></head><body><main>
<h1>بوصلة العطاء — الخدمات الاجتماعية</h1><p>السؤال: كيف يتغير وصف الحضور المسجل للجمعيات عند مراعاة حجم سكان المنطقة؟ نسخة 23 أكتوبر 2026.</p>
<p class="notice"><strong>مقارنة مع خط أساس سكاني لعام 2022.</strong> هذه ليست كثافة حالية لعام 2026: منشورات الجهات تعود لفترات 2025–2026 ومختلفة التحديث. 2022 أحدث سنة في مجموعة السكان المفحوصة تغطي المناطق الـ13؛ 2023 و2024 إجماليان وطنيان فقط. لم نوزع الإجمالي الوطني على المناطق ولم نتنبأ بسكانها.</p>
<div class="cards"><div class="card"><span class="number">1,607</span>سجلات الخدمات الاجتماعية</div><div class="card"><span class="number">1,546</span>سجلات الجمعيات — البسط الأساسي</div><div class="card"><span class="number">61</span>سجلات المؤسسات — منفصلة</div><div class="card"><span class="number">13/13</span>مناطق مرتبطة بسكان 2022</div></div>
<section><h2>لماذا اخترنا هذا التخصص؟</h2><p>اختاره صاحب المشروع بعد المراجعة. الخدمات الاجتماعية أكبر مجموعة رئيسية في الملفات ({1607 / 6403 * 100:.1f}% من سجلات الجهات)، وتظهر في المناطق الـ13. نقارن على مستوى التصنيف الرئيسي G04، ونفصل الجمعيات عن المؤسسات. لا يعتمد البسط على التصنيف الفرعي الأول المتطابق مع الثاني في مصدر مكة.</p><p>المستفيد من التحليل: فريق تخطيط جمعية أو جهة مانحة يريد تحديد أسئلة لدراسة ميدانية وشراكات. المخرج قائمة مقارنة موثقة، وليس توصية تلقائية بتوزيع التمويل.</p></section>
<section><h2>ما الذي تغير بعد إضافة السكان؟</h2><p>مكة لديها أكبر عدد في الملفات: <strong>{int(row.loc['مكة المكرمة','association_records'])} سجل جمعية</strong>، ومعدلها {row.loc['مكة المكرمة','associations_per_100k_population_2022']:.2f} لكل 100 ألف من سكان 2022. الرياض {int(row.loc['الرياض','association_records'])} ومعدلها {row.loc['الرياض','associations_per_100k_population_2022']:.2f}، بينما القصيم {int(row.loc['القصيم','association_records'])} ومعدلها {row.loc['القصيم','associations_per_100k_population_2022']:.2f}. لذا ترتيب الأعداد يختلف عن ترتيب المعدلات، دون أن يثبت أي منهما كفاية الخدمة.</p>
<figure><img src="data:image/png;base64,{encoded}" alt="مقارنة عدد سجلات جمعيات الخدمات الاجتماعية ومعدلها لكل مئة ألف من سكان 2022"><figcaption>المصدر: المركز الوطني لتنمية القطاع غير الربحي؛ السكان: الهيئة العامة للإحصاء عبر بيانات السعودية. الحساب والترتيب من إعداد المشروع.</figcaption></figure></section>
<section><h2>جدول المقارنة — المقام سكان 2022</h2><p><strong>المعدل = سجلات جمعيات الخدمات الاجتماعية ÷ جميع سكان المنطقة في 2022 × 100,000.</strong> يشمل المقام السعوديين وغير السعوديين والجنسين؛ لا نملك توزيع المستفيدين الفعليين. المؤسسات لا تدخل البسط الأساسي. إجمالي المقام {int(summary.population_2022.sum()):,} نسمة؛ معدل تجميع السجلات {national_rate:.2f} وليس متوسط معدلات المناطق.</p><div class="scroll">{table}</div><p class="notice">الجوف: الجمعيات الثلاثون بلا أرقام وطنية منشورة، ومصدر الجهات لعام 2025؛ لا يؤكد عدّها تفرّد هويتها عبر المملكة. أرفقنا جدول حساسية للمناطق الـ12 ذات المعرّفات فقط، دون تغيير معدل أي منطقة باقية أو تقديمه كمجموع وطني.</p></section>
<section><h2>ما الذي نستطيع اتخاذه من قرار؟</h2><p>نستطيع اختيار مناطق وأسئلة للتحقق: هل تخدم الجمعيات خارج منطقة تسجيلها؟ كم مستفيداً وطاقة تشغيلية وميزانية لكل جمعية؟ ما حجم الفئة المستهدفة؟ وما تغير بعد 2022؟ المعدلات المنخفضة هنا تستدعي البحث، ولا تعني تلقائياً نقصاً؛ والمرتفعة لا تثبت كفاية الخدمة.</p><p>القيود: عدّ سجلات حسب منطقة مجموعة المصدر؛ التغطية الفعلية للجهات غير مثبتة، وتواريخ النشر غير متزامنة، ولا توجد أوزان لحجم الجهة أو بيانات احتياج. لا ننتج درجة احتياج مركبة أو تنبؤاً من هذه اللقطة.</p></section>
<section><h2>المصادر وإعادة الاستخدام</h2><ul><li><a href="../coverage_and_results.html">مصادر الجهات الـ13 وتواريخها ومشكلات الجودة</a> — المركز الوطني لتنمية القطاع غير الربحي، رخصة البيانات المفتوحة.</li><li><a href="{html.escape(meta['explorer_url'])}">جدول السكان المختار — الهيئة العامة للإحصاء عبر بيانات السعودية</a>؛ <a href="{html.escape(meta['api_url'])}">JSON العام الأصلي</a>.</li><li><a href="https://www.stats.gov.sa/ar/use-policy">سياسة الهيئة العامة للإحصاء</a>، بندا 1.2.2 و1.4.2: إعادة الاستخدام مع الإسناد وتوضيح التعديلات، دون تقديم النتائج المعدلة كإحصاء رسمي أو إيحاء باعتماد الهيئة لها.</li></ul><p>معالجة المشروع: اختيار الإجمالي مرة واحدة لكل جنس وجنسية، فصل الإجمالي الوطني قبل الجمع، توحيد «المنطقة الشرقية» إلى «الشرقية» مع حفظ الأصل، ثم الربط 1:1 وحساب المعدل. بصمات الملفات والتواريخ محفوظة في سجل المصادر.</p></section>
<footer>نتائج وصفية مشتقة، لم يعتمدها الناشر. فحوص التنفيذ محفوظة بجانب التقرير. افتح Notebook المتخصص للتدرج من المصدر حتى المقارنة.</footer></main></body></html>'''
    (folder / "social_services_and_population.html").write_text(report, encoding="utf-8")
    verification = {"status": "FOCUS_POPULATION_OK", "population_year": 2022, "regions": len(summary), "population_total": int(summary.population_2022.sum()), "social_service_records": len(focus), "association_records": int(summary.association_records.sum()), "foundation_records": int(summary.foundation_records.sum()), "associations_without_id": int(summary.association_records_without_id.sum()), "join": "one_to_one; 13 matched; 0 unmatched", "national_rate_per_100k_population_2022": float(national_rate), "source_hashes_checked": True}
    (folder / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    return verification


def run(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    pop, coverage, meta = load_population(root)
    focus, summary, identified = focus_comparison(root, pop)
    folder = root / "outputs/national/focus"
    folder.mkdir(parents=True, exist_ok=True)
    chart = draw_focus(summary, folder)
    result = export_focus(root, focus, summary, identified, coverage, meta, chart)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    run()
