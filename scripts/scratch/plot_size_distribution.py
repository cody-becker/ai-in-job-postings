"""
plot_size_distribution.py

Reads size_counts.csv (produced earlier via value_counts().to_csv(...))
and plots the PDL company size distribution as a bar chart.

NOTE: size_counts.csv was built from the UNFILTERED size column, so it
also contains hundreds of garbage rows from the ~834 corrupted PDL rows
(city names, LinkedIn URLs, stray text fragments that landed in the size
column due to a CSV quoting/escaping issue elsewhere in the source file).
This script filters those out before plotting, keeping only the 8 real
size buckets.

Run:
    pip install matplotlib --break-system-packages   # if not already installed
    python scripts/scratch/plot_size_distribution.py
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RESULTS = ROOT / "data" / "results"

# The real bucket order, smallest to largest -- same ordering used
# elsewhere in the project for SIZE_ORDER/SIZE_RANK.
SIZE_ORDER = [
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1001-5000",
    "5001-10000",
    "10001+",
]

df = pd.read_csv(DATA_RESULTS / "size_counts.csv")

# size_counts.csv was built from the unfiltered size column, so it's full
# of corrupted-row garbage (city names, LinkedIn URLs, text fragments).
# Keep only rows whose size_bucket is one of the real 8 buckets.
df = df[df["size_bucket"].isin(SIZE_ORDER)]

# Re-order by real size (smallest -> largest) instead of value_counts()'s
# default "most common first" ordering.
df["size_bucket"] = pd.Categorical(df["size_bucket"], categories=SIZE_ORDER, ordered=True)
df = df.sort_values("size_bucket")

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(df["size_bucket"], df["count"])

ax.set_yscale("log")  # linear scale would make every bucket but 1-10 invisible
ax.set_xlabel("Company size bucket")
ax.set_ylabel("Number of companies (log scale)")
ax.set_title("PDL company size distribution")

# annotate each bar with its real count, since a log-scale y-axis makes
# it hard to eyeball actual numbers at a glance
for i, count in enumerate(df["count"]):
    ax.text(i, count, f"{count:,}", ha="center", va="bottom", fontsize=8)

plt.xticks(rotation=30, ha="right")
plt.tight_layout()
CHART_PATH = DATA_RESULTS / "size_distribution.png"
plt.savefig(CHART_PATH, dpi=150)
plt.show()

print(f"Saved chart to {CHART_PATH}")