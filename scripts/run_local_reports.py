"""Run the existing analysis and HTML reports without a Notebook frontend."""
from pathlib import Path
from national_analysis import run as run_national
from package_national import make_report
from social_services_analysis import run as run_focus

ROOT = Path(__file__).resolve().parents[1]
run_national(ROOT)
make_report()
run_focus(ROOT)
print("LOCAL_REPORTS_OK")
print(ROOT / "outputs/national/coverage_and_results.html")
print(ROOT / "outputs/national/focus/social_services_and_population.html")
