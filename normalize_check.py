"""
normalize_check.py

Sanity check for the fixed company-name normalizer BEFORE running it on the
full 9M-row PDL file. Mixes names that should survive untouched with names
that should get correctly suffix-stripped, so a false-positive strip (like
the "cisco" -> "cis" bug) shows up immediately instead of three steps later.

Run this, eyeball the "expected" vs "got" columns, fix anything that
doesn't match, THEN point the same normalize() function at the real data.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# The fixed normalizer
# ---------------------------------------------------------------------------
# Order matters here:
#   1. lowercase
#   2. strip legal-suffix TOKEN while word boundaries / spaces still exist
#   3. strip punctuation
#   4. collapse/remove whitespace
# Doing whitespace collapse before the suffix strip destroys the word
# boundary the suffix regex depends on (see: "thewaltdisneyco" problem).

SUFFIX_PATTERN = (
    r"\b(inc|llc|ltd|corp|corporation|incorporated|limited|co|company|"
    r"gmbh|ag|sarl|plc|bv|nv|sa|pty|pte|kk)\.?\s*$"
)


def normalize(series: pd.Series) -> pd.Series:
    s = series.str.lower()
    s = s.str.replace(SUFFIX_PATTERN, "", regex=True).str.strip()
    s = s.str.replace(r"[^\w\s]", "", regex=True)  # strip punctuation
    s = s.str.replace(r"\s+", "", regex=True)       # collapse whitespace last
    return s


# ---------------------------------------------------------------------------
# Test cases: (input, expected_output, note)
# ---------------------------------------------------------------------------
cases = [
    # --- names that LOOK like they end in a suffix but aren't one ---
    ("Cisco", "cisco", "ends in 'co' but is not Company Inc"),
    ("Sysco", "sysco", "same trap as Cisco"),
    ("Geico", "geico", "same trap"),
    ("Tesco", "tesco", "same trap"),
    ("Chicago", "chicago", "ends in 'go', not a suffix, just a control case"),

    # --- real legal suffixes that SHOULD be stripped ---
    ("The Walt Disney Co.", "thewaltdisney", "classic 'Co.' suffix, with space + period"),
    ("Intel Corp", "intel", "no period, still should strip"),
    ("Intel Corporation", "intel", "full word form"),
    ("1upHealth, Inc.", "1uphealth", "comma before suffix, from your own notes"),
    ("Arx Robotics GmbH", "arxrobotics", "German suffix, the original gap"),
    ("Some Company AG", "somecompany", "German AG suffix"),
    ("Edgewood Partners Insurance Center LLC", "edgewoodpartnersinsurancecenter", "long real name + LLC"),
    ("Acme Ltd", "acme", "UK Ltd"),
    ("Acme PLC", "acme", "UK Plc"),
    ("Nogent SARL", "nogent", "French suffix"),
    ("Vantage BV", "vantage", "Dutch suffix"),
    ("Nordic NV", "nordic", "Dutch/Belgian suffix"),
    ("Iberia SA", "iberia", "Spanish/French/Italian suffix"),
    ("Outback PTY", "outback", "Australian suffix"),
    ("Marina PTE", "marina", "Singapore suffix"),
    ("Tanaka KK", "tanaka", "Japanese suffix"),

    # --- edge cases worth knowing about either way ---
    ("10a Labs", "10alabs", "should pass through untouched, no suffix"),
    ("Walmart", "walmart", "no suffix at all, control case"),
    ("Ably30", "ably30", "ATS-slug noise, NOT fixed by suffix stripping - expected to still be wrong"),
]

df = pd.DataFrame(cases, columns=["input", "expected", "note"])
df["got"] = normalize(df["input"])
df["match"] = df["got"] == df["expected"]

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 140)

print(df[["input", "expected", "got", "match", "note"]].to_string(index=False))
print()
print(f"{df['match'].sum()}/{len(df)} passed")

failures = df[~df["match"]]
if len(failures):
    print("\nFAILURES:")
    print(failures[["input", "expected", "got", "note"]].to_string(index=False))
