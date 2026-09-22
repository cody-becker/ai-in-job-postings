import os
from pathlib import Path
import pandas as pd
from ats_scrapers import search
import time

# Project root is one level up from scripts/ -- makes paths work no matter
# what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"

OUTPUT_PATH = DATA_RAW / "job_sample_scaled_v4.csv"   # NEW filename -- don't overwrite job_sample.csv

# NEW: multiple platforms, not just greenhouse
ATS_PLATFORMS = ["greenhouse", "workday"]

SEARCH_TERMS = [
    "engineer", "sales", "marketing", "operations", "designer",
    "manager", "analyst", "product", "finance", "hr",
    "data", "developer", "consultant", "specialist", "coordinator",
]  # expanded from 10 to 15 -- broader functional coverage

LIMIT_PER_PULL = 1000 # NEW: pull up to 1000 postings per ATS per search term

# ---------------------------------------------------------------------------
# Pull-once-cache: skip the whole thing if you already have a saved result
# ---------------------------------------------------------------------------
start_time = time.time()

if os.path.exists(OUTPUT_PATH):
    print(f"{OUTPUT_PATH} already exists -- skipping pull. Delete it manually if you want to re-pull.")
else:
    all_results = []

    for ats in ATS_PLATFORMS:
        for term in SEARCH_TERMS:
            print(f"Pulling: ats={ats}, query='{term}'...")
            try:
                jobs = search(query=term, ats=ats, limit=LIMIT_PER_PULL)
                jobs["search_term"] = term
                jobs["ats_platform"] = ats
                all_results.append(jobs)
                print(f"  -> got {len(jobs)} postings")
            except Exception as e:
                print(f"  -> FAILED for ats={ats}, query='{term}': {e}")

    combined = pd.concat(all_results, ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(combined)} total postings to {OUTPUT_PATH}")

elapsed = time.time() - start_time
print(f"Elapsed time: {elapsed:.1f} seconds")
 