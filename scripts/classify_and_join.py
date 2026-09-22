"""
classify_and_join.py

Dry-run step 2 & 3: classify every posting's AI tier, then join to the
matched company size/industry data from run_real_match.py's output.
"""

import time
from pathlib import Path

import pandas as pd
from ai_detection import classify_posting

# Project root is one level up from scripts/ -- makes paths work no matter
# what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_RESULTS = ROOT / "data" / "results"

# ---------------------------------------------------------------------------
# Step 1: classify every posting by AI tier
# ---------------------------------------------------------------------------
start_time = time.time()
postings = pd.read_csv(DATA_RAW / "job_sample_scaled_v4.csv")

print("Classifying postings by AI tier...")
postings["ai_tier"] = postings.apply(
    lambda row: classify_posting(row["title"], row["description"]), axis=1
)

print("\nAI tier distribution across all postings:")
print(postings["ai_tier"].value_counts().sort_index())

postings.to_csv(DATA_RESULTS / "postings_with_ai_tier.csv", index=False)

# ---------------------------------------------------------------------------
# Step 2: join to matched company size/industry
# ---------------------------------------------------------------------------
match_results = pd.read_csv(DATA_RESULTS / "match_results_scaled_v4.csv")

# Only keep cleanly-matched companies for this dry run -- review/unmatched
# companies don't have a trustworthy size/industry yet
matched = match_results[
    (match_results["chosen_size"].notna()) & (match_results["needs_review"] == False)
][["raw_company", "chosen_size", "chosen_industry"]]

joined = postings.merge(
    matched, left_on="company", right_on="raw_company", how="inner"
)

print(f"\n{len(postings)} total postings -> {len(joined)} postings from cleanly-matched companies")

joined.to_csv(DATA_RESULTS / "postings_matched_with_tier.csv", index=False)

# ---------------------------------------------------------------------------
# Step 3 (sanity check): does the groupby run and produce something sane?
# ---------------------------------------------------------------------------
summary = joined.groupby(["chosen_size", "ai_tier"]).size().unstack(fill_value=0)
print("\nPostings by size tier x AI tier:")
print(summary)

elapsed = time.time() - start_time
print(f"\nElapsed time: {elapsed:.1f} seconds")