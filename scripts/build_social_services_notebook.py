"""Build an Arabic Notebook with embedded analysis code, runnable offline."""
from pathlib import Path
import inspect
import nbformat as nbf
import social_services_analysis as analysis

ROOT = Path(__file__).resolve().parents[1]


def build():
    cells = []
    def md(text):
        cells.append(nbf.v4.new_markdown_cell('<div dir="rtl">\n\n' + text + '\n\n</div>'))
    def code(text):
        cells.append(nbf.v4.new_code_cell(text.strip()))
    md("""# بوصلة العطاء — جمعيات الخدمات الاجتماعية والسكان

اختار صاحب المشروع **الخدمات الاجتماعية G04**. السؤال: كيف يختلف الحضور المسجل بين المناطق بعد مراعاة عدد السكان؟

النتيجة الأساسية: **سجلات جمعيات الخدمات الاجتماعية لكل 100 ألف من سكان 2022**. البسط 1,546 سجل جمعية، والمؤسسات الـ61 تعرض منفصلة. هذا مؤشر وصفي للحضور المسجل، وليس مقياس احتياج أو كفاية أو أثر.

المقام جميع السكان (سعوديون وغير سعوديين والجنسين). لا نعرف الفئة المستفيدة الفعلية أو نطاق خدمة كل جهة. بيانات الجهات منشورات مختلفة التواريخ (2025–2026)؛ لذا المقارنة مع **خط أساس 2022** وليست كثافة حالية في 2026.""")
    md("""## 1. المصادر والبيئة

المدخلات: النسخة المنظفة الناتجة من `analysis_national.ipynb` وJSON أصلي من API بيانات السعودية المنسوب للهيئة العامة للإحصاء. أُخذ رابط API من زر «نسخ API» وقورنت القيم بالجدول الظاهر. التفاصيل والبصمات في `research/population_sources.json`.

يمكن قراءة المخرجات المحفوظة دون تشغيل. في Colab ارفع حزمة المشروع وفكها، ثم افتح هذا الملف. خلية التثبيت وحدها تحتاج الإنترنت؛ بقية التحليل يقرأ الملفات المحلية، بلا نموذج ذكاء اصطناعي أو طلب مدفوع.

سياسة إعادة الاستخدام: https://www.stats.gov.sa/ar/use-policy — مع إسناد الهيئة وبيان التعديلات وعدم الإيحاء باعتماد نتائجنا. رخصة بيانات الجهات موثقة مستقلة في `DATA_LICENSE.md`.""")
    code('''import sys
if "google.colab" in sys.modules:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pandas==3.0.1", "numpy==2.5.4", "matplotlib==3.11.2"])
else:
    print("البيئة المحلية: requirements.txt؛ لا تنزيل أثناء الحساب.")''')
    source = (ROOT / "scripts/social_services_analysis.py").read_text(encoding="utf-8")
    code(source.split("def load_population")[0].split('"""')[-1].strip())
    code('''ROOT = Path.cwd()
if not (ROOT / "research/population_sources.json").exists():
    ROOT = ROOT / "bouslat-alataa-national"
assert (ROOT / "research/population_sources.json").exists(), "فك حزمة المشروع أولاً"
pd.set_option("display.max_columns", 12)
pd.set_option("display.max_colwidth", 90)
print("مجلد التحليل:", ROOT)''')
    md("""## 2. التحقق من المقام وسنة التغطية

نختار إجمالي الجنسية وإجمالي الجنس مرة واحدة؛ لا نجمع الإجماليات مع مكوناتها. نفصل صف المملكة قبل جمع المناطق. يفترض أن نحصل على 13 منطقة ومجموع 32,175,224 نسمة.

فحص كل السنوات في المجموعة يوضح أن 2023 و2024 إجمالي وطني فقط. لذلك استخدمنا 2022، ولم نوزع إجمالي 2024 على المناطق أو نستنتج نموها منه. فُحص ملف GASTAT Excel لعام 2024، لكنه وطني حسب العمر والجنس ولم يستخدم هنا.""")
    code(inspect.getsource(analysis.load_population))
    code('''population, population_coverage, population_meta = load_population(ROOT)
display(population_coverage)
display(population[["region", "population_2022", "population_year"]])''')
    md("""## 3. تصفية التخصص وربط المناطق

نختار G04 ثم نفصل نوعي الكيانات. الربط واحد إلى واحد باسم المنطقة الصريح؛ التغيير الوحيد في أسماء السكان «المنطقة الشرقية» ← «الشرقية»، مع حفظ الأصل. نستعمل منطقة مجموعة المصدر ولا ندعي تحقق مقر كل جهة.

مشكلة التصنيف الفرعي الأول لمكة لا تغير اختيار G04 الرئيسي. تبقى الجمعيات الثلاثون في الجوف بلا رقم وطني، ولا تخمّن هويتها أو تدمج أسماؤها آلياً.""")
    code(inspect.getsource(analysis.focus_comparison))
    code('''focus_records, comparison, identified_regions = focus_comparison(ROOT, population)
display(comparison[["region", "association_records", "foundation_records", "population_2022", "associations_per_100k_population_2022", "association_records_without_id"]].round(2))''')
    md("""## 4. المقارنة البصرية

المعدل = عدد سجلات الجمعيات ÷ جميع سكان المنطقة في 2022 × 100,000.

ترتيب المعدل يختلف عن ترتيب العدد. لا نستخدم ترتيباً آلياً للاحتياج: موقع التسجيل لا يحدد أين تصل الخدمة، ولا نملك حجم الجهة أو مستفيديها أو ميزانيتها. المعدل الوطني يحسب من مجموع البسط على مجموع المقام، وليس متوسط معدلات المناطق.""")
    code(inspect.getsource(analysis.draw_focus))
    code('''OUTPUT = ROOT / "outputs/national/focus"
OUTPUT.mkdir(parents=True, exist_ok=True)
chart = draw_focus(comparison, OUTPUT)
from IPython.display import Image, display
display(Image(filename=str(chart)))
print("معدل تجميع السجلات لكل 100 ألف من سكان 2022:", round(comparison.association_records.sum() / comparison.population_2022.sum() * 100000, 2))''')
    md("""## 5. حساسية غياب معرّفات الجوف

يعرض الجدول التالي المناطق الـ12 التي تنشر معرّفات كل الجمعيات. لم يتغير معدل المناطق الباقية، ولم نستبدل الجوف بصفر. هذه رؤية مراجعة محدودة وليست مجموعاً وطنياً جديداً. تاريخ منشور الجوف أقدم، ويتطلب أي استنتاج عنه تحققاً إضافياً.""")
    code('''display(identified_regions[["region", "association_records", "associations_per_100k_population_2022", "scope_note"]].round(2))''')
    md("""## 6. حفظ التقرير والأثر التحليلي

الجدول يحفظ البسط والمقام والسنة وروابط المصدر وملاحظات التفسير. CSV يحفظ المعدل بكامل الدقة؛ التقريب للعرض فقط. لا تتغير ملفات المصدر.

الخطوة البحثية التالية: اختيار منطقة وأسئلة محددة للتحقق من المستفيدين والطاقة التشغيلية ونطاق الخدمة، بعد قراءة اختلاف الأعداد والمعدلات. لا نبني تنبؤاً من لقطة الجهات أو نستعمل الفترات السابقة للمقام لتوقع أعداد الجهات.""")
    code(inspect.getsource(analysis.export_focus))
    code('''result = export_focus(ROOT, focus_records, comparison, identified_regions, population_coverage, population_meta, chart)
print(json.dumps(result, ensure_ascii=False, indent=2))
print("التقرير:", OUTPUT / "social_services_and_population.html")''')
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}})
    nbf.validate(nb)
    nbf.write(nb, ROOT / "analysis_social_services.ipynb")
    print("SOCIAL_NOTEBOOK_BUILT", len(cells), "cells")


if __name__ == "__main__":
    build()
