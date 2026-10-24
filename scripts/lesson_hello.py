from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
print("HELLO_FROM_LOCAL_PYTHON")
print(ROOT)
print((ROOT / "data_clean").exists())
