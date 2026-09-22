"""
fuzzy_match_leftovers.py (v2)
"""

from pathlib import Path

import pandas as pd
from rapidfuzz import process, fuzz

# Project root is one level up from scripts/ -- makes paths work no matter
# what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_CACHE = ROOT / "data" / "cache"
DATA_RESULTS = ROOT / "data" / "results"

PDL_PATH = DATA_RAW / "free_company_dataset.csv"
MATCH_RESULTS_PATH = DATA_RESULTS / "match_results_scaled_v4.csv"   # CHANGED

FUZZY_THRESHOLD = 85

KNOWN_JUNK_SLUGS = {
    "externaljobboards",
    "2bc11c2c7us",
}

def looks_like_hash(slug: str) -> bool:
    if len(slug) < 8:
        return False
    digit_count = sum(c.isdigit() for c in slug)
    return digit_count / len(slug) > 0.3

def strip_slug_suffixes(slug: str) -> str:
    """Strip common suffixes even without a space boundary -- catches
    cases like 'arxroboticsgmbh' that the main normalize() regex misses."""
    for suffix in ["gmbh", "gmb", "inc", "llc", "ltd", "corp", "co"]:
        if slug.endswith(suffix) and len(slug) > len(suffix) + 2:
            slug = slug[: -len(suffix)]
            break
    return slug

# ---------------------------------------------------------------------------
# Step 1: pull ONLY genuinely-unmatched companies, filter out known junk
# ---------------------------------------------------------------------------
results = pd.read_csv(MATCH_RESULTS_PATH)
leftovers = results[
    results["chosen_size"].isna() & (results["needs_review"] == False)
].copy()

is_junk = leftovers["slug"].isin(KNOWN_JUNK_SLUGS) | leftovers["slug"].apply(
    lambda s: looks_like_hash(str(s))
)
junk = leftovers[is_junk]
leftovers = leftovers[~is_junk]

print(f"Filtered out {len(junk)} known/suspected junk slugs -- REVIEW THESE:")
print(junk[["raw_company", "slug"]].to_string(index=False))
print(f"\n{len(leftovers)} real candidates remain for fuzzy matching.")

# ---------------------------------------------------------------------------
# Step 2: load PDL names+size once (reuse cache if present)
# ---------------------------------------------------------------------------
import os
CACHE_PATH = DATA_CACHE / "pdl_prefix_cache.csv"
if os.path.exists(CACHE_PATH):
    print("Loading cached normalized PDL...")
    pdl = pd.read_csv(CACHE_PATH)
else:
    print("Loading PDL names (one pass)...")
    pdl = pd.read_csv(PDL_PATH, usecols=["name", "size"])
    pdl["norm_name"] = (
        pdl["name"].astype(str).str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
    )

# ---------------------------------------------------------------------------
# Step 3: fuzzy match, with tighter blocking + slug-side suffix stripping
# ---------------------------------------------------------------------------
def fuzzy_match_one(raw_slug: str):
    slug = strip_slug_suffixes(str(raw_slug))          # CHANGED -- Fix 2
    prefix = slug[:4]                                   # CHANGED -- Fix 1 (was slug[:2])
    candidates = pdl[
        pdl["norm_name"].str.startswith(prefix)
        & pdl["norm_name"].str.len().between(len(slug) - 2, len(slug) + 2)  # CHANGED -- tighter window
    ]

    if len(candidates) == 0:
        return {"slug": slug, "best_match": None, "score": 0, "size": None, "pool_size": 0}

    top2 = process.extract(slug, candidates["norm_name"], scorer=fuzz.ratio, limit=2)  # CHANGED -- Fix 4

    if not top2 or top2[0][1] < FUZZY_THRESHOLD:
        return {
            "slug": slug, "best_match": None,
            "score": top2[0][1] if top2 else 0,
            "size": None, "pool_size": len(candidates),
        }

    best_name, best_score, best_idx = top2[0]
    gap = best_score - top2[1][1] if len(top2) > 1 else best_score   # NEW -- confidence gap

    return {
        "slug": slug, "best_match": best_name, "score": best_score,
        "size": candidates.loc[best_idx, "size"], "pool_size": len(candidates),
        "confidence_gap": gap,
    }

print("\nFuzzy matching leftovers against narrowed candidate pools...")
fuzzy_results = [fuzzy_match_one(slug) for slug in leftovers["slug"]]
fuzzy_df = pd.DataFrame(fuzzy_results)

recovered = fuzzy_df[fuzzy_df["best_match"].notna()]
still_unmatched = fuzzy_df[fuzzy_df["best_match"].isna()]

print("\n" + "=" * 60)
print(f"Leftover companies checked: {len(fuzzy_df)}")
print(f"Recovered via fuzzy match:  {len(recovered)}")
print(f"Still unmatched:            {len(still_unmatched)}")
print("=" * 60)
print("\n--- Recovered (check confidence_gap before trusting!) ---")
print(recovered.sort_values("confidence_gap").to_string(index=False))
print("\n--- Still unmatched ---")
print(still_unmatched[["slug", "score", "pool_size"]].to_string(index=False))

FUZZY_RESULTS_PATH = DATA_RESULTS / "fuzzy_match_results_v4.csv"
fuzzy_df.to_csv(FUZZY_RESULTS_PATH, index=False)
print(f"\nSaved to {FUZZY_RESULTS_PATH}")