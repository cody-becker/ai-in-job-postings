from pathlib import Path

import pandas as pd

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RESULTS = ROOT / "data" / "results"

results = pd.read_csv(DATA_RESULTS / "match_results_scaled_v4_full.csv")
matched = results[(results["chosen_size"].notna()) & (results["needs_review"] == False)]

print(f"Total cleanly matched: {len(matched)}")

print("\nTop industries overall:")
print(matched["chosen_industry"].value_counts().head(15))

large_tier = matched[matched["chosen_size"] == "10001+"]
print(f"\n10001+ companies: {len(large_tier)}")
print(large_tier["chosen_industry"].value_counts())

print("\nFull size x industry cell counts:")
density = matched.groupby(["chosen_size", "chosen_industry"]).size().unstack(fill_value=0)
print(density)

# Worth adding this time: how many cells actually clear a reasonable minimum
cell_counts = density.values.flatten()
print(f"\nCells with 5+ companies: {(cell_counts >= 5).sum()} out of {len(cell_counts)}")
print(f"Cells with 10+ companies: {(cell_counts >= 10).sum()} out of {len(cell_counts)}")