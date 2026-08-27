"""
run_real_match.py

Combines everything built so far:
  - the fixed normalizer (word-boundary suffix stripping)
  - the corrupted-row filter (~834 bad rows with garbage in "size")
  - the prefix-match + max-size-bucket function, with short-slug review flagging

...and runs it against the REAL PDL file and your REAL Greenhouse company list,
to get an actual updated match rate vs. the original 68.2% (30/44).

*** ADJUST THE PATHS BELOW BEFORE RUNNING ***
"""

import pandas as pd

# ---------------------------------------------------------------------------
# !!! EDIT THESE THREE LINES to match your actual files !!!
# ---------------------------------------------------------------------------
PDL_PATH = "free_company_dataset.csv"          # the real PDL bulk file
PDL_NAME_COLUMN = "name"                       # confirm this is the right column
JOB_POSTINGS_PATH = "job_sample.csv"      # your 300-posting Greenhouse pull
JOB_POSTINGS_COMPANY_COLUMN = "company"        # confirm this is the right column

# Set this to a number (e.g. 500_000) to test the code quickly on a partial
# file first. Set to None for the real, full-file run once you've confirmed
# the code works correctly -- a sample CANNOT give you a trustworthy match
# rate, since a fragmented company's matching rows could be scattered
# anywhere across the full 35.8M rows in no particular order.
SAMPLE_ROWS = None   # <-- start here to validate quickly; set to None for the real run


# ---------------------------------------------------------------------------
# Normalizer (from normalize_check.py)
# ---------------------------------------------------------------------------
SUFFIX_PATTERN = (
    r"\b(inc|llc|ltd|corp|corporation|incorporated|limited|co|company|"
    r"gmbh|ag|sarl|plc|bv|nv|sa|pty|pte|kk)\.?\s*$"
)


def normalize(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.lower()
    s = s.str.replace(SUFFIX_PATTERN, "", regex=True).str.strip()
    s = s.str.replace(r"[^\w\s]", "", regex=True)
    s = s.str.replace(r"\s+", "", regex=True)
    return s


# ---------------------------------------------------------------------------
# Size ordering (confirmed against the real PDL file's 8 buckets)
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
    """Drop rows whose size isn't one of the real 8 buckets -- catches the
    ~834 corrupted rows before they ever reach matching."""
    return df[df["size"].isin(VALID_SIZES)]


def prefix_match(slug: str, pdl_clean: pd.DataFrame) -> dict:
    """
    pdl_clean is expected to ALREADY be filtered via clean_candidates()
    and have a normalized "norm_name" column -- passed in pre-cleaned here
    since we don't want to re-filter the whole PDL file on every call when
    looping over many slugs (that would be extremely slow at ~35.8M rows).
    """
    result = {
        "slug": slug,
        "matched_count": 0,
        "chosen_size": None,
        "candidates": [],
        "flag": None,
        "needs_review": False,
    }

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

    if len(candidates) > MAX_CANDIDATES_BEFORE_REVIEW:
        result["flag"] = "large candidate set -- worth manual review"
        result["needs_review"] = True

    return result


# ---------------------------------------------------------------------------
# Load and prep the real PDL file
# ---------------------------------------------------------------------------
print("Loading PDL file" + (f" (sample of {SAMPLE_ROWS:,} rows)" if SAMPLE_ROWS else " (full file, this may take a while at ~35.8M rows)") + "...")
pdl = pd.read_csv(PDL_PATH, usecols=[PDL_NAME_COLUMN, "size"], nrows=SAMPLE_ROWS)
pdl = pdl.rename(columns={PDL_NAME_COLUMN: "name"})

print(f"Loaded {len(pdl):,} PDL rows. Filtering corrupted rows...")
pdl_clean = clean_candidates(pdl)
print(f"{len(pdl_clean):,} rows remain after dropping corrupted-size rows.")

print("Normalizing PDL company names (this is the slow step -- vectorized, but 35.8M rows)...")
pdl_clean = pdl_clean.copy()
pdl_clean["norm_name"] = normalize(pdl_clean["name"])

# ---------------------------------------------------------------------------
# Load your real job-postings company list
# ---------------------------------------------------------------------------
postings = pd.read_csv(JOB_POSTINGS_PATH)
raw_companies = postings[JOB_POSTINGS_COMPANY_COLUMN].dropna().unique().tolist()
print(f"\n{len(raw_companies)} unique companies found in job postings file.")

normalized_companies = normalize(pd.Series(raw_companies)).tolist()

# ---------------------------------------------------------------------------
# Run the match
# ---------------------------------------------------------------------------
results = []
for raw, slug in zip(raw_companies, normalized_companies):
    r = prefix_match(slug, pdl_clean)
    r["raw_company"] = raw
    results.append(r)

results_df = pd.DataFrame(results)

matched = results_df[results_df["chosen_size"].notna()]
unmatched = results_df[
    results_df["chosen_size"].isna() & (results_df["needs_review"] == False)
]
needs_review = results_df[results_df["needs_review"] == True]

total = len(results_df)
print("\n" + "=" * 60)
print(f"TOTAL companies checked: {total}")
print(f"Auto-matched:            {len(matched)}  ({len(matched)/total:.1%})")
print(f"Genuinely unmatched:     {len(unmatched)}")
print(f"Needs manual review:     {len(needs_review)}")
print("=" * 60)

print("\n--- Auto-matched ---")
print(matched[["raw_company", "slug", "matched_count", "chosen_size"]].to_string(index=False))

print("\n--- Needs manual review ---")
if len(needs_review):
    print(needs_review[["raw_company", "slug", "matched_count", "flag"]].to_string(index=False))
else:
    print("(none)")

print("\n--- Genuinely unmatched ---")
if len(unmatched):
    print(unmatched[["raw_company", "slug"]].to_string(index=False))
else:
    print("(none)")

results_df.to_csv("match_results.csv", index=False)
print("\nFull results saved to match_results.csv")