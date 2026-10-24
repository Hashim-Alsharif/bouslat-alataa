from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data_clean/national_entities_available.csv"
df = pd.read_csv(
    source, encoding="utf-8-sig",
    dtype=str, keep_default_na=False,
)
print(df.shape)
print(df.columns.tolist())
print(df[["region", "main_group_code"]].head(5))
print(df["entity_type"].value_counts())
