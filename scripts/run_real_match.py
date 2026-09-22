"""
run_real_match.py

Core entity-resolution pipeline:
  - normalizer with word-boundary suffix stripping (international suffixes included)
  - corrupted-row filter (rows with garbage in "size")
  - Workday tenant-label stripping ("Company (TenantLabel)" -> "Company")
  - generic trailing-word stripping ("careers", "jobs", etc.)
  - prefix-match + max-size-bucket function, with short-slug and
    large-candidate-set review flagging
  - now also carries "industry" through for matched companies
"""

import os
from pathlib import Path
import pandas as pd
import time

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------
# Project root is one level up from scripts/ -- makes paths work no matter
# what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_CACHE = ROOT / "data" / "cache"
DATA_RESULTS = ROOT / "data" / "results"

PDL_PATH = DATA_RAW / "free_company_dataset.csv"
PDL_NAME_COLUMN = "name"
JOB_POSTINGS_PATH = DATA_RAW / "job_sample_scaled_v4.csv"
JOB_POSTINGS_COMPANY_COLUMN = "company"

SAMPLE_ROWS = None
CACHE_PATH = DATA_CACHE / "pdl_prefix_cache.csv"

# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------
SUFFIX_PATTERN = (
    r"\b(inc|llc|ltd|corp|corporation|incorporated|limited|co|company|"
    r"gmbh|ag|sarl|plc|bv|nv|sa|pty|pte|kk)\.?\s*$"
)

GENERIC_TRAILING_WORDS = [
    "careers", "candidateportal", "jobs", "recruiting",
    "hiring", "careersite", "external", "externalcareers",
]

def strip_generic_trailing_words(slug) -> str:
    if not isinstance(slug, str):
        return ""
    for word in GENERIC_TRAILING_WORDS:
        if slug.endswith(word) and len(slug) > len(word) + 2:
            return slug[: -len(word)]
    return slug

def strip_tenant_label(raw: str) -> str:
    """Workday names often look like 'Acxiom (AcxiomMEX)' -- the parenthetical
    is a tenant/site label, not part of the company name. Keep only what's
    before the first '('."""
    return raw.split("(")[0].strip()

def normalize(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.lower()
    s = s.str.replace(SUFFIX_PATTERN, "", regex=True).str.strip()
    s = s.str.replace(r"[^\w\s]", "", regex=True)
    s = s.str.replace(r"\s+", "", regex=True)
    s = s.apply(strip_generic_trailing_words)
    return s

# ---------------------------------------------------------------------------
# Size ordering
# ---------------------------------------------------------------------------
SIZE_ORDER = [
    "1-10", "11-50", "51-200", "201-500",
    "501-1000", "1001-5000", "5001-10000", "10001+",
]
SIZE_RANK = {size: i for i, size in enumerate(SIZE_ORDER)}
VALID_SIZES = set(SIZE_ORDER)

SHORT_SLUG_LENGTH = 6
MAX_CANDIDATES_BEFORE_REVIEW = 20

def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose size isn't one of the real 8 buckets."""
    return df[df["size"].isin(VALID_SIZES)]

def prefix_match(slug: str, pdl_clean: pd.DataFrame) -> dict:
    result = {
        "slug": slug,
        "matched_count": 0,
        "chosen_size": None,
        "chosen_industry": None,
        "candidates": [],
        "flag": None,
        "needs_review": False,
    }

    if not slug or pd.isna(slug) or len(slug) == 0:
        result["flag"] = "empty slug after normalization -- skipped, NOT auto-resolved"
        result["needs_review"] = True
        return result

    candidates = pdl_clean[pdl_clean["norm_name"].str.startswith(slug)]
    result["matched_count"] = len(candidates)
    result["candidates"] = candidates["norm_name"].tolist()

    if len(candidates) == 0:
        result["flag"] = "no match -- genuinely unmatched"
        return result

    is_short_slug = len(slug) < SHORT_SLUG_LENGTH
    is_multi_candidate = len(candidates) > 1

    if is_short_slug and is_multi_candidate:
        result["flag"] = (
            f"short slug ({len(slug)} chars) matched {len(candidates)} candidates "
            "-- likely false positives, needs manual review, NOT auto-resolved"
        )
        result["needs_review"] = True
        return result

    best_idx = candidates["size"].map(SIZE_RANK).idxmax()
    result["chosen_size"] = candidates.loc[best_idx, "size"]
    result["chosen_industry"] = candidates.loc[best_idx, "industry"]  # NEW

    if len(candidates) > MAX_CANDIDATES_BEFORE_REVIEW:
        result["flag"] = "large candidate set -- worth manual review"
        result["needs_review"] = True

    return result

# ---------------------------------------------------------------------------
# Load and prep PDL -- cached
# ---------------------------------------------------------------------------
if os.path.exists(CACHE_PATH):
    print("Loading cached normalized PDL...")
    pdl_clean = pd.read_csv(CACHE_PATH)
    print(f"Loaded {len(pdl_clean):,} cached rows.")
else:
    print("No cache found -- loading full PDL file (this may take a while)...")
    pdl = pd.read_csv(PDL_PATH, usecols=[PDL_NAME_COLUMN, "size", "industry"], nrows=SAMPLE_ROWS)
    pdl = pdl.rename(columns={PDL_NAME_COLUMN: "name"})

    print(f"Loaded {len(pdl):,} PDL rows. Filtering corrupted rows...")
    pdl_clean = clean_candidates(pdl)
    print(f"{len(pdl_clean):,} rows remain after dropping corrupted-size rows.")

    print("Normalizing PDL company names...")
    pdl_clean = pdl_clean.copy()
    pdl_clean["norm_name"] = normalize(pdl_clean["name"])

    pdl_clean.to_csv(CACHE_PATH, index=False)
    print("Cached for next time.")

# ---------------------------------------------------------------------------
# Load job postings, strip tenant labels, run match
# ---------------------------------------------------------------------------
postings = pd.read_csv(JOB_POSTINGS_PATH)
raw_companies = postings[JOB_POSTINGS_COMPANY_COLUMN].dropna().unique().tolist()
print(f"\n{len(raw_companies)} unique companies found in job postings file.")

stripped_companies = [strip_tenant_label(c) for c in raw_companies]
normalized_companies = normalize(pd.Series(stripped_companies)).tolist()

results = []
for raw, stripped, slug in zip(raw_companies, stripped_companies, normalized_companies):
    r = prefix_match(slug, pdl_clean)
    r["raw_company"] = raw
    r["stripped_company"] = stripped
    results.append(r)

results_df = pd.DataFrame(results)

matched = results_df[
    (results_df["chosen_size"].notna()) & (results_df["needs_review"] == False)
]
unmatched = results_df[
    results_df["chosen_size"].isna() & (results_df["needs_review"] == False)
]
needs_review = results_df[results_df["needs_review"] == True]

total = len(results_df)
print("\n" + "=" * 60)
print(f"TOTAL companies checked: {total}")
print(f"Cleanly auto-matched:    {len(matched)}  ({len(matched)/total:.1%})")
print(f"Genuinely unmatched:     {len(unmatched)}")
print(f"Needs manual review:     {len(needs_review)}")
print("=" * 60)

RESULTS_PATH = DATA_RESULTS / "match_results_scaled_v4_full.csv"
results_df.to_csv(RESULTS_PATH, index=False)
print(f"\nFull results saved to {RESULTS_PATH}")