import pandas as pd
import os
from pathlib import Path

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_CACHE = ROOT / "data" / "cache"

PDL_PATH = DATA_RAW / "free_company_dataset.csv"
CACHE_PATH = DATA_CACHE / "pdl_slim_cache.csv"

if os.path.exists(CACHE_PATH):
    print("Loading cached slim version...")
    pdl = pd.read_csv(CACHE_PATH)
else:
    print("No cache found — reading full PDL file (this is the slow part)...")
    pdl = pd.read_csv(PDL_PATH, usecols=["name", "size", "website"])
    pdl["norm_name"] = pdl["name"].astype(str).str.lower().str.replace(r"[^\w\s]", "", regex=True).str.replace(r"\s+", "", regex=True)
    pdl.to_csv(CACHE_PATH, index=False)
    print("Cached for next time.")

def inspect(slug):
    rows = pdl[pdl["norm_name"].str.startswith(slug)]
    print(f"\n=== '{slug}' — {len(rows)} candidates ===")
    print(rows[["name", "website", "size"]].to_string(index=False))
    print(f"\nUnique websites: {rows['website'].nunique()} out of {len(rows)} rows")
    print(f"Null/missing websites: {rows['website'].isna().sum()}")

inspect("walmart")
inspect("entera")
# add more inspect(...) calls here freely -- second run onward is fast