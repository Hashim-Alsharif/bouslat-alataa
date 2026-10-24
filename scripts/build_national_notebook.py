"""Build an Arabic compatibility Notebook from the same analysis functions."""
from pathlib import Path
import inspect
import sys
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import qassim_analysis as q
from audit_national_sources import read_regional_source
from verify_source_pairs import verify_source_pairs


def build():
    source=(ROOT/"scripts/national_analysis.py").read_text(encoding="utf-8")
    sections={}
    for chunk in source.split("# %% ")[1:]:
        name,code=chunk.split("\n",1)
        sections[name.strip()]=code.split('\nif __name__=="__main__":')[0].strip()
    cells=[]
    def md(text):
        cells.append(nbf.v4.new_markdown_cell('<div dir="rtl">\n\n'+text+'\n\n</div>'))
    def code(text):
        cells.append(nbf.v4.new_code_cell(text.strip()))
    md("""# بوصلة العطاء — حصر المناطق الـ13 ومقارنة الملفات المتاحة

**حالة النسخة: ملفات المناطق الـ13 مقروءة، مع نقص الأرقام الوطنية في مصدر الجوف.**

أرفق صاحب المشروع ملفات CSV وExcel صحيحة لعسير والجوف بعد تعذر التنزيل السابق. حُفظت الملفات الأربعة دون تغيير، وتطابقت كل خلايا البيانات بين الصيغتين لكل منطقة. بقيت التنزيلات المرفوضة محفوظة كأثر جمع سابق ولم تستخدم في التحليل.

النسخة المنفذة تضم **6,403 سجلات جهات من 13 منطقة**: 6,341 سجلاً بأرقام وطنية فريدة، و62 سجلًا للجوف دون حقل الرقم الوطني في الأصل. لم نخترع أرقاماً لها؛ `record_key` مفتاح صف داخل المشروع فقط. العد للسجلات، ولا يؤكد تفرّد الجهات بلا معرّف عبر المملكة.

الأعداد حسب **منطقة مجموعة المصدر**، وليست تحققاً من مقر كل جهة أو نطاق خدماتها. نحتفظ بنسخة القصيم ونسخة 11 منطقة السابقتين للرجوع.""")
    md("""## 1. تجهيز البيئة

اقرأ المخرجات المحفوظة مباشرة، أو شغّل الخلايا بالترتيب. في Colab ارفع حزمة `bouslat-alataa-national.zip` وفكّها باستخدام:

`!unzip -q -o /content/bouslat-alataa-national.zip -d /content`

التحليل لا يستدعي نموذجاً أو API مدفوعة. خلية التثبيت وحدها تحتاج الإنترنت؛ قراءة المصادر تتم من ملفات الحزمة. لا تشغّل أدوات التنزيل لإعادة التحليل.""")
    code('''import sys
if "google.colab" in sys.modules:
    import subprocess
    subprocess.check_call([sys.executable,"-m","pip","install","-q",
                           "pandas==3.0.1","numpy==2.5.4","matplotlib==3.11.2","openpyxl==3.1.5"])
else:
    print("محلياً: ثبّت requirements.txt في بيئة مستقلة قبل التشغيل.")''')
    imports=sections["imports"]
    imports="\n".join(line for line in imports.splitlines() if not line.startswith(("from qassim_analysis import","from audit_national_sources import","from verify_source_pairs import")))
    imports+="\n\nEXPECTED_COLUMNS = "+repr(q.EXPECTED_COLUMNS)+"\n"
    code(imports)
    code('''ROOT=project_root()
REQUIRE_ALL_REGIONS=True  # نطلب ملفات المناطق الـ13؛ هذا لا يعني اكتمال الأرقام الوطنية.
rules=json.loads((ROOT/"config/national_mappings.json").read_text(encoding="utf-8"))
pd.set_option("display.max_colwidth",100)
print("Project:",ROOT.name)''')
    md("""## 2. المصدر والرخصة وتوافق التاريخ

الناشر: **المركز الوطني لتنمية القطاع غير الربحي**. حُصرت المصادر من [فهرس المنصة الوطنية](https://open.data.gov.sa/ar/datasets) بالبحث «الكيانات غير الربحية». جميع البطاقات الـ13 تربط [رخصة البيانات المفتوحة](https://open.data.gov.sa/ar/pages/policies/license). توجد نسخة الرخصة في الحزمة، والروابط المفصلة والبصمات في `research/national_sources.json`.

تاريخ التحقق: **23 أكتوبر 2026**. تعرض الجوف فترة مرجعية لعام 2025 وتحديثاً في أغسطس 2025. عسير تعرض فترة ممتدة من نوفمبر 2025 إلى نهاية 2026. أغلب بقية الملفات تعرض عام 2026 وتحديثاً في مارس 2026. هذه بيانات وصفية للمجموعات، ولا يحتوي CSV تاريخ ملاحظة لكل كيان.

نستبعد مجموعة الرياض القديمة البديلة من الدمج؛ نستخدم المصدر الإقليمي الأحدث فقط. لا نخلط دليل نوى مع هذه الملفات المرخصة.

عسير وتبوك ونجران بترميز Windows-1256؛ ظهور الحروف كطلاسم في برنامج آخر لا يعني تلف المصدر. الجوف UTF-8 وتحتوي 7 أعمدة دون الرقم الوطني، بينما بقية المناطق 8 أعمدة.

القارئ التالي يرفض HTML حتى لو كان امتداد الملف CSV، ويفحص البصمة ورأس الأعمدة. يقبل مخطط الجوف ذي الأعمدة السبعة صراحةً، ويترك المعرّف غير المنشور فارغاً في النسخة الموحدة. لا يملأه باسم الكيان أو بمفتاح الصف.""")
    code(inspect.getsource(verify_source_pairs)+'''\n\ndisplay(pd.DataFrame(verify_source_pairs(ROOT)))''')
    code(inspect.getsource(read_regional_source)+"\n\n"+sections["load"])
    code('''raw,inventory,manifest=load_sources(ROOT,REQUIRE_ALL_REGIONS)
columns=["region","status","records","column_count","identifier_column_present","encoding","updated_at_as_displayed","reference_period_as_displayed"]
display(inventory[columns].astype(object).where(pd.notna(inventory[columns]),"غير متاح"))
print("Readable regions:",inventory.status.eq("readable").sum(),"/13; records:",len(raw))
display(raw.head(5))''')
    md("""## 3. قرارات التوحيد والمراجعة

- المواقع: خريطة صريحة توحد المسافات وأخطاء إملائية محددة، وتحفظ «مدينة/محافظة/مركز». لا دمج بالتشابه، ولا استنتاج للمقر من اسم الكيان.
- المجموعات الرئيسية: اعتماد الرقم والاسم المنشورين مع إبقاء الأوصاف الأصلية. البيئة تتضمن أوصافاً متعارضة تحتاج مراجعة.
- `منشأة بأمر ملكي` و`HMS_Check`: خارج المجموعات العشر؛ تظهران منفصلتين ولا تُحوّلان إلى تخصص مفترض.
- **مكة:** التصنيف الفرعي الأول يطابق الثاني في 1,365/1,365 سجلاً. نحتفظ بالعمودين لكن لا نستخدم المستوى الأول للمقارنة بين المناطق.
- سجلات مواقع تحمل أسماء تظهر في ملفات مناطق أخرى: تُعلّم للمراجعة، ولا ننقلها بين المناطق.
- الخلايا الأصلية الفارغة تبقى فارغة؛ لا ملء بتخمين.
- الجوف: حقل المعرّف الوطني غير منشور، ونوع الوحدة الجغرافية غير مذكور. يبقى الأصل محفوظاً دون افتراض مدينة أو محافظة. سجل المشكلات يرتبط بمفتاح صف، لا بالمعرّف الوطني الفارغ.

هذه قرارات تحليل موثقة في `config/national_mappings.json`، وليست تصحيحات اعتمدها الناشر.""")
    code('''display(raw.groupby("source_region").apply(lambda g:pd.Series({
    "السجلات":len(g),
    "تطابق التصنيفين الفرعيين":int(g["التصنيف الفرعي الاول"].eq(g["التصنيف الفرعي الثاني"]).sum())
})))
display(pd.DataFrame([{"القيمة الأصلية":value,**rule} for value,rule in rules["main_groups"].items()]))
display(pd.DataFrame(rules["location_cross_file_review"]))''')
    helpers="\n\n".join(inspect.getsource(function) for function in [q.normalize_text,q.clean_entities])
    code(helpers+"\n\n"+sections["normalize"])
    code('''cleaned,changes,issues=normalize_national(raw,rules)
display(cleaned[["record_key","entity_id","has_national_id","entity_name","region","location_label","main_group_code","main_group_name","entity_type","needs_review"]].head(10))
display(cleaned.loc[~cleaned.has_national_id,["record_key","entity_id","entity_name","region"]].head())
display(issues.groupby("issue_code").size().to_frame("عدد الحالات"))
display(issues[issues.issue_code.isin(["NONSTANDARD_MAIN_CLASSIFICATION","SOURCE_CELL_BLANK","LOCATION_CROSS_FILE_REVIEW"])].head(30))''')
    md("""## 4. فحوص الحفظ والتغطية

يجب حفظ كل سجل وخلاياه المنشورة، وتفرّد الأرقام الوطنية المنشورة ومفاتيح الصفوف وتطابق بصمات الملفات. الأرقام الوطنية الفارغة لا تدخل في فحص التكرار ولا تُحسب كمعرّف واحد مشترك.

**فحص التغطية منفصل عن اكتمال المعرّفات:** الوضع الصارم للمناطق ينجح حالياً 13/13. لكن فحص اعتماد إزالة التكرار الوطني الكامل يرفض الاستنتاج بسبب 62 سجلًا بلا معرّف. لا يثبت نجاح الفحوص اكتمال سجل المملكة أو نطاق الخدمة.""")
    code(sections["validate"])
    code('''checks=check_national(ROOT,raw,cleaned,inventory,manifest)
display(pd.Series(checks,name="اجتاز").to_frame())
load_sources(ROOT,require_all_regions=True)
print("اجتاز فحص توفر ملفات المناطق 13/13.")
try:
    require_complete_national_identifiers(cleaned)
except ValueError as error:
    print("حدود فحص التكرار كما هو متوقع:",error)
else:
    print("جميع السجلات تحمل أرقاماً وطنية منشورة.")''')
    md("""## 5. الجداول الأولى

المقام 6,403 سجلات من المناطق الـ13، منها 62 بلا معرّف. نعرض الجمعيات والمؤسسات معاً في الجداول الأساسية، وجداول مستقلة لكل نوع. لا نصف المجموع بأنه عدد جهات فريدة تم التحقق منه وطنياً.

التصنيف الأول لمكة مستبعد من جدول `subcategories_1_comparable` وحده؛ سجلات مكة موجودة في مجاميع المناطق والتصنيف الرئيسي. القيم الرئيسية غير القياسية معروضة منفصلة ومشمولة في مجموع السجلات.""")
    code(inspect.getsource(q.count_table)+"\n\n"+sections["summarize"])
    code('''tables=summarize_national(cleaned,inventory)
display(tables["regions"])
display(tables["entity_types"])
display(tables["main_groups"])
display(tables["identifier_coverage_by_region"])
display(tables["main_groups_within_region"].head(15))''')
    md("""## 6. الرسوم واختيار منطقة

الرسوم تعرض ملفات المناطق الـ13 ولا تمثل إحصاءً وطنياً متزامناً. الصفر في مصفوفة تخصصات منطقة يعني غياب سجل في ملفها فقط، وليس غياب الخدمة أو إثبات الاحتياج. لا يوجد مقام سكاني في هذه المرحلة.

استخدم متغير `SELECTED_REGION` لعرض أي منطقة؛ القيمة الحالية الجوف لقراءة البيانات التي أضيفت. نوع الموقع فيها غير مذكور في المصدر.""")
    code(inspect.getsource(q.configure_charts)+"\n\n"+sections["figures"])
    code('''figures=national_figures(ROOT,tables,inventory,manifest)
from IPython.display import Image,display
for path in figures:
    display(Image(filename=str(path),width=1100))
SELECTED_REGION="الجوف"
if SELECTED_REGION not in set(cleaned.region):
    print("لا يوجد ملف مقروء لهذه المنطقة:",SELECTED_REGION)
else:
    display(tables["locations"].query("region == @SELECTED_REGION"))
    display(tables["main_groups_within_region"].query("region == @SELECTED_REGION"))''')
    md("""## 7. حفظ المخرجات

النسخة الجديدة في `data_clean/national_entities_available.csv` و`outputs/national/`. مخرجات القصيم السابقة تبقى مستقلة.

نحفظ سجل التغييرات والمشكلات ونتائج الفحوص والروابط والمقام المستخدم. ملفات CSV تحفظ المعرّفات نصوصاً؛ يُفضّل استيرادها كنص عند فتحها في برنامج جداول.""")
    code(sections["export"])
    code('''report=export_national(ROOT,raw,cleaned,changes,issues,inventory,tables,checks,manifest)
display(pd.Series(report["coverage"],name="التغطية").to_frame())
print("NATIONAL_AVAILABLE_NOTEBOOK_OK")
print("التغطية الجغرافية 13/13؛ فحص التكرار بالأرقام الوطنية يشمل السجلات التي نشرت معرّفاتها فقط.")''')
    md("""## 8. القراءة والمرحلة التالية

أضيفت عسير بـ536 سجلًا والجوف بـ62 بعد مقارنة الصيغتين بالكامل. أصبح التحليل يغطي منشورات المناطق الـ13، مع 6,341 معرّفاً منشوراً فريداً و62 سجلًا بلا معرّف. هذه تغطية للمنشورات الإقليمية وليست دليلاً على اكتمال سجل وطني متزامن.

تبقى مراجعة تصنيفي مكة والقيم التقنية والمواقع المتعارضة، والبحث عن معرّفات الجوف من مصدر رسمي إذا أردنا إزالة تكرار وطنية شاملة. لم نربط الكيانات اعتماداً على تشابه الأسماء.

لا نقترح ترتيباً للاحتياج أو توقعاً زمنياً من هذه اللقطات. الخطوة التالية تحديد تخصص وقرار قابل للقياس، ثم البحث عن بيانات سكان ومؤشرات مناسبة قبل توصيات التوسع.""")
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"},"title":"بوصلة العطاء — حصر 13 منطقة ومقارنة الملفات المتاحة"})
    nbf.validate(notebook)
    nbf.write(notebook,ROOT/"analysis_national.ipynb")
    print("NATIONAL_NOTEBOOK_BUILT",len(cells),"cells")


if __name__=="__main__":
    build()
