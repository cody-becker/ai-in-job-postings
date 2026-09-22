import pandas as pd
import os
from pathlib import Path

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_CACHE = ROOT / "data" / "cache"

SEEN_LOG = DATA_CACHE / "postings_already_read.txt"

postings = pd.read_csv(DATA_RAW / "job_sample_scaledv2.csv")

def get_unseen_sample(postings_df, n=8, filter_condition=None):
    if os.path.exists(SEEN_LOG):
        with open(SEEN_LOG) as f:
            seen_ids = set(line.strip() for line in f)
    else:
        seen_ids = set()

    pool = postings_df[~postings_df["global_id"].isin(seen_ids)]
    if filter_condition is not None:
        pool = pool[filter_condition]

    sample = pool.sample(min(n, len(pool)))

    with open(SEEN_LOG, "a") as f:
        for gid in sample["global_id"]:
            f.write(f"{gid}\n")

    return sample

# Load whatever's already been marked as seen (empty set on first run)
if os.path.exists(SEEN_LOG):
    with open(SEEN_LOG) as f:
        seen_ids = set(line.strip() for line in f)
else:
    seen_ids = set()

available = postings[~postings["global_id"].isin(seen_ids)]

# ... your sampling logic, e.g.:
non_tech_sample = available.sample(min(8, len(available)), random_state=None)

# Print them same as before
for _, row in non_tech_sample.iterrows():
    print(f"\n{'='*60}\n{row['company']} — {row['title']}\n{'='*60}")
    print(row["description"][:800])

# Mark these as seen for next time
with open(SEEN_LOG, "a") as f:
    for gid in non_tech_sample["global_id"]:
        f.write(f"{gid}\n")

    