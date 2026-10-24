from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_national_sources import read_regional_source

manifest = json.loads(
    (ROOT / "research/national_sources.json")
    .read_text(encoding="utf-8")
)
source = next(s for s in manifest["sources"]
              if s["slug"] == "asir")
rows, details = read_regional_source(ROOT, source)
print(source["local_file"])
print(details["encoding"], len(rows))
