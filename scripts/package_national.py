"""Build a local coverage report and portable Notebook bundle."""
from pathlib import Path
import base64
import hashlib
import html
import json
import zipfile
import pandas as pd
import nbformat

ROOT=Path(__file__).resolve().parents[1]


def make_report():
    folder=ROOT/"outputs/national"
    quality=json.loads((folder/"quality/quality_report.json").read_text(encoding="utf-8"))
    manifest=json.loads((ROOT/"research/national_sources.json").read_text(encoding="utf-8"))
    inventory=pd.read_csv(folder/"tables/source_inventory_13_regions.csv",encoding="utf-8-sig",keep_default_na=False)
    def table(name,columns):
        frame=pd.read_csv(folder/f"tables/{name}.csv",encoding="utf-8-sig")
        return frame[list(columns)].rename(columns=columns).to_html(index=False,border=0,escape=True,float_format=lambda value:f"{value:.2f}")
    def figure(filename,caption):
        encoded=base64.b64encode((folder/"figures"/filename).read_bytes()).decode("ascii")
        return f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>'
    inventory_rows=[]
    for row in inventory.itertuples():
        available=row.status=="readable"
        count=str(int(float(row.records))) if available else "غير متاح"
        if available:
            has_id=str(row.identifier_column_present).lower()=="true"
            state=f"{int(float(row.column_count))} أعمدة؛ "+("الرقم الوطني منشور" if has_id else "الرقم الوطني غير منشور")
        else:
            state="ملف غير متاح؛ مستبعد"
        inventory_rows.append(f'<tr><td>{html.escape(row.region)}</td><td>{count}</td><td>{state}</td><td><bdi>{html.escape(row.updated_at_as_displayed)}</bdi></td><td><bdi>{html.escape(row.reference_period_as_displayed)}</bdi></td><td><a href="{html.escape(row.dataset_url)}">المصدر</a></td></tr>')
    issue_descriptions={
        "SUBCATEGORY_LEVELS_IDENTICAL_SOURCE":"مكة: التصنيفان الفرعيان متطابقان؛ المستوى الأول مستبعد من المقارنة",
        "MAIN_DESCRIPTION_CONFLICT":"تعارض وصف مجموعة البيئة مع اسمها ورقمها",
        "LOCATION_UNSPECIFIED":"الموقع مسجل باسم «أخرى»",
        "NONSTANDARD_MAIN_CLASSIFICATION":"تصنيف رئيسي خارج المجموعات العشر (22 منشأة بأمر ملكي و2 HMS_Check)",
        "LOCATION_CROSS_FILE_REVIEW":"اسم الموقع يظهر في ملف منطقة أخرى؛ مراجعة دون نقل السجل",
        "SOURCE_CELL_BLANK":"خلية جهة إشراف فارغة في ملف تبوك؛ لم تُملأ بتخمين",
        "NATIONAL_ID_NOT_PUBLISHED":"الجوف: لا يوجد حقل الرقم الوطني في المصدر، ولم يُنشأ رقم بديل",
        "LOCATION_UNIT_NOT_PUBLISHED":"الجوف: اسم موقع دون نوع وحدة منشور؛ لا افتراض لمدينة أو محافظة",
        "NAME_MATCH_WITHOUT_NATIONAL_ID":"تشابه اسم لسجل بلا معرّف؛ لم يُربط أو يُحذف تلقائياً",
    }
    issues="".join(f'<tr><td>{html.escape(issue_descriptions[key])}</td><td>{value}</td></tr>' for key,value in quality["issue_counts"].items())
    source_links="".join(f'<li><a href="{source["dataset_url"]}">{html.escape(source["title"])}</a> — <a href="{source["resources_url"]}">الملفات</a></li>' for source in manifest["sources"])
    content=f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>بوصلة العطاء — حصر المناطق الـ13</title><style>
body{{margin:0;background:#f5f7f9;color:#172b3a;font:17px/1.9 Arial,sans-serif}}main{{max-width:1150px;margin:auto;padding:30px 22px 60px}}h1,h2{{color:#111}}h1{{font-size:31px}}h2{{font-size:23px;margin:10px 0}}
section,.card{{background:white;border:1px solid #d9e1e5;border-radius:10px;padding:20px;margin:20px 0}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px}}.cards .card{{margin:0}}.number{{display:block;font-size:30px;color:#136e69}}
.notice{{background:#fff5df;border-right:5px solid #b87513;padding:16px}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;text-align:right;font-size:15px}}td,th{{padding:10px;border-bottom:1px solid #dce4e7;vertical-align:top}}th{{background:#edf4f3}}a{{color:#075d91;overflow-wrap:anywhere}}img{{width:100%;height:auto}}figure{{margin:20px 0}}figcaption,footer{{font-size:14px;color:#4f626f}}code{{direction:ltr;unicode-bidi:embed}}@media print{{body{{background:white}}section{{break-inside:avoid}}}}
</style></head><body><main>
<h1>بوصلة العطاء — حصر المناطق الـ13</h1><p>تحقق المصادر وتوافق الملفات؛ نسخة المقارنة بتاريخ 23 أكتوبر 2026.</p>
<p class="notice"><strong>ملفات المناطق الـ13 متاحة ومقروءة.</strong> أضيفت عسير والجوف من الملفات الصحيحة التي أرفقها صاحب المشروع، وتطابقت كل خلايا البيانات بين CSV وExcel لكل منطقة. <strong>العد للسجلات:</strong> الجوف تنشر 62 سجلًا بلا أرقام وطنية، لذلك لا يؤكد المجموع تفرّد كل جهة عبر المملكة. لم تُستخدم التنزيلات السابقة المرفوضة.</p>
<div class="cards"><div class="card"><strong class="number">13/13</strong>ملفات مناطق مقروءة</div><div class="card"><strong class="number">{quality['records']:,}</strong>سجلات جهات</div><div class="card"><strong class="number">{quality['records_with_national_id']:,}</strong>بأرقام وطنية فريدة</div><div class="card"><strong class="number">{quality['records_without_national_id']:,}</strong>بلا رقم وطني منشور</div></div>
<p>الأنواع كما نشرت: {quality['entity_types']['جمعية أهلية']:,} سجل جمعية أهلية و{quality['entity_types']['مؤسسة أهلية']:,} سجل مؤسسة أهلية. أضيفت عسير بـ536 سجلًا والجوف بـ62. لكل سجل مفتاح داخلي <code>record_key</code> لتتبّع المصدر والصف، وهو ليس رقماً وطنياً ولا دليلاً على هوية الجهة.</p>
<section><h2>حصر المصادر وتواريخها</h2><p>الأعداد حسب مجموعة المصدر الإقليمية، وليست تحققاً من مقر كل كيان أو نطاق خدماته. يوجد مصدر أقدم بديل للرياض، استُبعد لتفادي تكرار التغطية.</p>
<div class="scroll"><table><thead><tr><th>المنطقة</th><th>السجلات</th><th>حالة الوصول والبنية</th><th>تحديث البطاقة</th><th>الفترة المرجعية</th><th>الرابط</th></tr></thead><tbody>{''.join(inventory_rows)}</tbody></table></div>
<p class="notice">الجوف مصدر أقدم بفترة 2025، وعسير ذات فترة ممتدة. الفترات المرجعية لا تمثل تاريخ ملاحظة لكل جهة ولا تحققاً من تواريخ مستقبلية. المقارنة بين منشورات مختلفة التواريخ وليست إحصاءً وطنياً متزامناً.</p></section>
<section><h2>هل الملفات متوافقة؟</h2><p>اثنا عشر ملفاً لها 8 أعمدة، والجوف لها 7 أعمدة مشتركة دون الرقم الوطني. دُمجت الحقول المشتركة وحُفظت الخلايا الأصلية، وبقي معرّف الجوف فارغاً. عسير وتبوك ونجران بترميز Windows-1256، والبقية UTF-8؛ الطلاسم عند فتح CSV بترميز خاطئ لا تعني تلف المصدر.</p>
<p>الأرقام الوطنية المنشورة الـ6,341 نصوص من 10 خانات، دون تكرار بينها. فحص التكرار بالأرقام لا يشمل سجلات الجوف الـ62. أسماء المواقع في الجوف بلا نوع وحدة، فحُفظت دون افتراض مدينة أو محافظة.</p>
<p><strong>التوافق البنيوي لا يعني توافق المحتوى كاملاً:</strong> في مكة يطابق التصنيف الفرعي الأول الثاني في كل السجلات؛ المستوى الأول مستبعد من المقارنة. القيم الرئيسية غير القياسية معروضة منفصلة.</p>
<table><thead><tr><th>سبب المراجعة</th><th>عدد الحالات</th></tr></thead><tbody>{issues}</tbody></table><p>قد يحمل السجل أكثر من علامة؛ مجموع الحالات ليس عدد الكيانات المختلفة. عدد الكيانات التي تحمل علامة واحدة على الأقل: {quality['entities_with_review_issues']:,}. لا يعني ذلك أن السجل كله خاطئ أو محذوف.</p></section>
<section><h2>التوزيع حسب منطقة المصدر</h2><p>المقام {quality['records']:,} سجلات من منشورات المناطق الـ13. النسب تخص سجلات هذه الملفات، ولا تمثل حصة مؤكدة من كامل سجل الجهات أو قياساً للاحتياج.</p><div class="scroll">{table('regions',{'region':'منطقة المصدر','entity_count':'السجلات','share_percent':'النسبة من سجلات المصدر %','denominator':'المقام'})}</div>
{figure('01_regions.png','مقارنة وصفية لملفات المناطق الـ13؛ عد للسجلات، والجوف بلا معرّفات وطنية.')}</section>
<section><h2>التخصصات الرئيسية</h2><div class="scroll">{table('main_groups',{'main_group_code':'الرمز','main_group_name':'التصنيف','entity_count':'العدد','share_percent':'النسبة من المتاح %'})}</div>
{figure('02_main_groups.png','عشر مجموعات منشورة وقيمتان غير قياسيتين؛ 234 وصفاً للبيئة يحتاج المراجعة.')}
{figure('03_region_main_matrix.png','الصفر يعني عدم وجود سجل في ملف منطقة متاحة، وليس غياب الخدمة.')}</section>
<section><h2>المرحلة المتخصصة وما بقي للتحقق</h2><p>اختار صاحب المشروع الخدمات الاجتماعية. أُنجزت <a href="focus/social_services_and_population.html">مقارنة الجمعيات نسبة إلى سكان 2022</a> مع فصل المؤسسات وتوضيح اختلاف التواريخ. افتح التقرير المتخصص لقراءة الأعداد والمعدلات معاً.</p><ol><li>البحث عن أرقام وطنية رسمية للجوف إذا احتجنا اعتماد إزالة تكرار وطنية شاملة؛ لا يكفي تشابه الأسماء.</li><li>مراجعة مشكلة تصنيفات مكة والقيم التقنية والمواقع المتعارضة. اكتمال المناطق لا يزيل هذه القيود.</li><li>إضافة نطاق الخدمة والمستفيدين والطاقة التشغيلية قبل توصيات التوسع؛ العدد والمعدل السكاني لا يثبتان الاحتياج.</li></ol><p>نجح وضع اشتراط ملفات 13/13، بينما يرفض فحص اكتمال الأرقام الوطنية اعتماد التكرار الشامل بسبب السجلات الـ62. لا نصدر توقعاً زمنياً من أعداد السجلات وحدها.</p></section>
<section><h2>روابط المصادر والإسناد</h2><p>المصدر: المركز الوطني لتنمية القطاع غير الربحي، مجموعات الكيانات الإقليمية على المنصة الوطنية للبيانات المفتوحة. تخضع البيانات ومشتقاتها لـ<a href="https://open.data.gov.sa/ar/pages/policies/license">رخصة البيانات المفتوحة</a>؛ نسخة الرخصة محفوظة بالحزمة.</p><ul>{source_links}</ul></section>
<footer>البيانات الأصلية لم تُعدّل. قواعد التوحيد قرارات تحليل موثقة، ولم يعتمد الناشر تصحيحاتها. هذه النسخة ليست التسليم النهائي للهاكاثون.</footer>
</main></body></html>'''
    (folder/"coverage_and_results.html").write_text(content,encoding="utf-8")


def package():
    nb=nbformat.read(ROOT/"analysis_national.ipynb",as_version=4)
    nbformat.validate(nb)
    code=[cell for cell in nb.cells if cell.cell_type=="code"]
    if not all(cell.execution_count is not None for cell in code):
        raise ValueError("Notebook is not fully executed")
    if any(output.output_type=="error" for cell in code for output in cell.outputs):
        raise ValueError("Notebook contains errors")
    make_report()
    focus_nb=ROOT/"analysis_social_services.ipynb"
    if focus_nb.exists():
        focused=nbformat.read(focus_nb,as_version=4)
        nbformat.validate(focused)
        assert all(cell.execution_count is not None for cell in focused.cells if cell.cell_type=="code")
        assert not any(output.output_type=="error" for cell in focused.cells if cell.cell_type=="code" for output in cell.outputs)
    top=["analysis_national.ipynb","NATIONAL_README.md","DATA_LICENSE.md","ai_usage_log.md","requirements.txt"]
    if focus_nb.exists():
        top.append("analysis_social_services.ipynb")
    files=[ROOT/name for name in top]
    for folder in ["config","data_raw","data_clean","outputs/national","research","scripts"]:
        files.extend(path for path in (ROOT/folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    files=sorted(set(files))
    archive=ROOT/"bouslat-alataa-national.zip"
    manifest={path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for path in files:
            bundle.write(path,"bouslat-alataa-national/"+path.relative_to(ROOT).as_posix())
        bundle.writestr("bouslat-alataa-national/MANIFEST.sha256.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        for name,digest in manifest.items():
            assert hashlib.sha256(bundle.read("bouslat-alataa-national/"+name)).hexdigest()==digest
        assert not any("/.tools/" in name for name in bundle.namelist())
    print("NATIONAL_PACKAGE_OK",len(files),"files;",archive.stat().st_size,"bytes")


if __name__=="__main__":
    package()
