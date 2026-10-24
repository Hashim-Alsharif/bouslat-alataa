"""Register already-downloaded official API responses without changing them."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.datasaudi.sa/tesseract/data.jsonrecords?cube=gastat_population_province_sex_nationality&locale=ar&drilldowns=Province%2CSex%2CYear%2CNationality&measures=Population&include=Sex%3A3%3BYear%3A2022%3BNationality%3A3&limit=100%2C0"
EXPLORER = "https://datasaudi.sa/ar/data-explorer?cube=gastat_population_province_sex_nationality&locale=ar&drilldowns=Province%2CSex%2CYear%2CNationality&measures=Population&include=Sex%3A3%3BYear%3A2022%3BNationality%3A3&limit=100%2C0&panel=table"


def register():
    files = []
    for name in ["datasaudi_population_2022.json", "datasaudi_population_years.json"]:
        path = ROOT / "data_raw/population" / name
        payload = path.read_bytes()
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    source = {"title": "إحصاءات السكان حسب المناطق الإدارية والجنس والجنسية - سنوي", "publisher": "الهيئة العامة للإحصاء", "access_platform": "بيانات السعودية — وزارة الاقتصاد والتخطيط", "retrieved_on": "2026-10-23", "download_method": "Public API URL obtained using the explorer Copy API button; visible regional values cross-checked against JSON", "api_url": API, "explorer_url": EXPLORER, "publisher_link_as_provided": "https://www.stats.gov.sa/en/statistics-tabs?tab=436327&category=127396", "years_api_url": API.replace("Sex%3A3%3BYear%3A2022%3BNationality%3A3", "Sex%3A3%3BNationality%3A3").replace("limit=100%2C0", "limit=10000%2C0"), "selected_file": files[0]["path"], "selected_year": 2022, "population_definition": "جميع السكان، سعودي وغير سعودي، الجنسين؛ إجمالي واحد لكل منطقة", "scope": "13 administrative regions, plus one national total row excluded before regional aggregation", "year_selection": "Latest complete regional year in this checked cube is 2022; 2023 and 2024 contain national total rows only. This does not establish the latest year in all possible official sources.", "license_policy_url": "https://www.stats.gov.sa/ar/use-policy", "license_policy_checked_on": "2026-10-23", "license_policy_sections": ["1.2.2", "1.4.1", "1.4.2"], "license_note": "Official policy permits reuse with GASTAT attribution and clear disclosure of changes. Derived calculations must not be presented as official GASTAT statistics or imply endorsement. No logo reused.", "files": files, "examined_rejected_candidate": {"title": "Population Estimates Publication 2024.xlsx", "sha256": "4dc73233b7aa5ec64eb68c92a765245b13b58ec25c27a84128da8a86f7276212", "reason": "National age/sex/nationality sheet only; no regional table. Not used for regional rates."}, "entity_input_sha256": hashlib.sha256((ROOT / "data_clean/national_entities_available.csv").read_bytes()).hexdigest()}
    (ROOT / "research/population_sources.json").write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")
    print("POPULATION_SOURCES_REGISTERED", len(files))


if __name__ == "__main__":
    register()
