from pathlib import Path

import pandas as pd

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_RESULTS = ROOT / "data" / "results"

jobs = pd.read_csv(DATA_RAW / "job_sample.csv")
target_companies = jobs["company"].dropna().unique()
print(f"Unique companies in job sample: {len(target_companies)}")

def normalize_fast(series):
    s = series.astype(str).str.lower().str.strip()
    s = s.str.replace(r"[^a-z0-9]", "", regex=True)
suffix_pattern = r"\b(inc|llc|ltd|corp|corporation|incorporated|limited|co|company|gmbh|ag|sarl|plc)\.?\s*$"
s = s.str.replace(suffix_pattern, "", regex=True).str.strip()

target_df = pd.DataFrame({"company": target_companies})
target_df["clean_name"] = normalize_fast(target_df["company"])
target_set = set(target_df["clean_name"])

matched_rows = []
chunks = pd.read_csv(DATA_RAW / "free_company_dataset.csv", usecols=["name", "website", "size", "industry"], chunksize=500_000)
for chunk in chunks:
    chunk["clean_name"] = normalize_fast(chunk["name"])
    hits = chunk[chunk["clean_name"].isin(target_set)]
    if not hits.empty:
        matched_rows.append(hits)

matched = pd.concat(matched_rows)
matched_companies = set(matched["clean_name"])

print(f"Matched: {len(matched_companies)} / {len(target_set)} = {len(matched_companies)/len(target_set):.1%}")

unmatched = target_set - matched_companies
print(f"Unmatched ({len(unmatched)}):")
for name in sorted(unmatched):
    print(" -", name)

matched.to_csv(DATA_RESULTS / "matched_companies.csv", index=False)