# Project Notes

File-by-file purpose and the reasoning behind decisions that aren't obvious from
the code alone. See [README.md](README.md) for the research question, data
sources, and current status/roadmap — this file is the "what does each script
do and why is it built this way" companion to that.

Note: the repo is currently flat (no `src/`/`tests/`/`scripts/` split yet,
despite the README's aspirational "Project structure" section) — the file list
below is what actually exists today.

## Pipeline scripts

Roughly in the order data flows through them:

- **`pull_data.py`** — Pulls job postings via `ats-scrapers` across multiple
  ATS platforms (Greenhouse, Workday) and multiple search terms (engineer,
  sales, marketing, operations, designer), tagging each row with
  `search_term`/`ats_platform`. Skips the pull entirely if the output file
  already exists, since re-pulling live ATS data is slow and rate-limit-prone.
- **`website_testing.py`** — One-off pull of a single named company (Nvidia)
  directly through `ats_scrapers.get_scraper_for_url`, for the case-study
  companies that need to be fetched individually rather than through a
  keyword search.
- **`run_real_match.py`** — The core entity-resolution pipeline: normalizes
  both PDL company names and job-posting company slugs, then **prefix-matches**
  postings against the full PDL file and picks the largest size bucket among
  matching candidates (see "Why prefix-match" below). Caches the normalized
  PDL file (`pdl_prefix_cache.csv`) since normalizing a multi-GB file is the
  slow part and the PDL data doesn't change between runs. Outputs
  `match_results_scaled_v2.csv` split into auto-matched / needs-review /
  unmatched.
- **`fuzzy_match_leftovers.py`** — Second pass, fuzzy-matches (via `rapidfuzz`)
  only the genuinely-unmatched leftovers from `run_real_match.py` — not the
  whole dataset. Filters out known junk/hash-like slugs first
  (`looks_like_hash`, `KNOWN_JUNK_SLUGS`) so fuzzy matching isn't wasted on
  unrecoverable ATS aggregator noise. Outputs `fuzzy_match_results_v2.csv`
  with a `confidence_gap` column (best score minus second-best) so
  low-confidence matches are visible before being trusted.
- **`ai_detection.py`** — The AI-mention classification logic: a deliberately
  wide net of positive terms (technical + casual business phrasing) and a
  deliberately narrow, evidence-based set of exclusions (see "Why the
  exclusion list is narrow" below). Includes a regression check
  (`KNOWN_SOFT_POSITIVES`) and documented real examples
  (`NON_TECHNICAL_AI_EXAMPLES`) that any future scoring logic must not filter
  out, plus a weak-signal detector (`ai_mention_near_boilerplate`) that
  down-weights AI mentions found inside generic "About Us" company-mission
  copy rather than actual role content.
- **`tests.py`** — Validates the detection signals in `ai_detection.py`
  (`title_hit`, `mention_count`, `density`) against a small hand-labeled set
  of real postings scored 1–5 by the author, to sanity-check that the
  automated signals track human judgment before trusting them at scale.

## Diagnostic / one-off scripts

- **`normalize_check.py`** — Standalone sanity check for the name normalizer,
  run *before* pointing it at the full 9M-row PDL file. Deliberately includes
  adversarial cases (`Cisco`, `Sysco`, `Geico`, `Tesco` — all end in letters
  that look like the `co` suffix but aren't) so a bad regex change is caught
  in seconds instead of silently corrupting a full run.
- **`f500_check.py`** — Ad-hoc inspector: builds a slim PDL cache
  (`name`/`size`/`website`) and lets you eyeball all candidate rows for a
  given slug (e.g. `inspect("walmart")`) to manually verify prefix-match
  behavior on specific companies before trusting it in bulk.
- **`explore.py`** — Earlier, simpler matching attempt: exact-match only
  (`isin`), streamed over the PDL file in 500k-row chunks. Superseded by
  `run_real_match.py`'s prefix-match approach once it became clear large
  companies are fragmented across many PDL rows rather than missing (see
  README's "Current status"). Kept as a record of the earlier approach, not
  part of the active pipeline.
- **`Check_postings.py`** — Manual-review sampling tool: pulls a random batch
  of not-yet-seen postings for eyeballing, and appends their IDs to
  `postings_already_read.txt` so re-running it never resurfaces the same
  postings twice.
- **`plot_size_distribution.py`** — Reads `size_counts.csv` and plots the PDL
  company-size distribution on a log scale (a linear scale makes every bucket
  but `1-10` invisible). Filters to the 8 real size buckets first, since the
  underlying counts file was built from the unfiltered `size` column and
  includes the ~834 corrupted rows mentioned in the README.

## Data / state files (mostly gitignored)

`*.csv`, `*.zip`, and `*.png` are gitignored (see `.gitignore`) — they're
either multi-GB source data, reproducible caches, or regenerable chart output.
Kept in the working directory but not pushed:

- `free_company_dataset.csv` — PDL's raw bulk company dataset.
- `pdl_prefix_cache.csv`, `pdl_slim_cache.csv` — normalized-PDL caches used by
  `run_real_match.py`/`fuzzy_match_leftovers.py` and `f500_check.py`
  respectively, so the slow full-file normalize only happens once.
- `job_sample*.csv` — successive job-posting pulls (`job_sample.csv` was the
  original single-term Greenhouse pull; `_scaledv1`/`_scaledv2` are later,
  broader pulls across more platforms/terms).
- `match_results*.csv`, `fuzzy_match_results*.csv`, `matched_companies.csv` —
  pipeline outputs from the matching scripts above.
- `postings_already_read.txt` — the only plain-text state file (not
  gitignored); tracks `global_id`s already shown by `Check_postings.py`.
- `manual_classification_batch.csv` — hand-labeled postings used for
  validating `ai_detection.py` against human judgment.
- `size_counts.csv` / `size_distribution.png` — input/output of
  `plot_size_distribution.py`.

## Why these decisions

### Why prefix-match + fuzzy, instead of just fuzzy matching everything

Fuzzy-matching every job-posting company slug against all ~35.8M PDL rows
would mean scoring millions of candidate pairs per slug — far too slow to be
practical. The pipeline instead does matching in three cheap-to-expensive
tiers:

1. **Exact/prefix match first** (`run_real_match.py`) — cheap, and correct
   for the large majority of cases, including the common case where a large
   company is fragmented across many PDL rows (regional subsidiaries,
   business units) that all share a name prefix.
2. **Junk filtering** (`fuzzy_match_leftovers.py`) — strip out slugs that are
   unrecoverable ATS noise (hashes, known aggregator containers) *before*
   spending fuzzy-match cycles on them.
3. **Fuzzy match only the genuine leftovers**, and even then only against a
   tightly *blocked* candidate pool (same 4-char prefix + length within ±2 of
   the slug) — not the full PDL file. Blocking keeps the fuzzy comparison set
   small enough to be fast while still catching real naming-format mismatches
   (e.g. `ambiqmicroinc` vs. PDL's shorter brand name).

Running fuzzy matching everywhere would also raise the false-positive rate —
short or generic slugs would drift toward whatever happens to be
lexically close in a 35.8M-row pool. Reserving fuzzy matching for a small,
pre-filtered leftover set keeps both the compute cost and the false-positive
surface area small.

### Why the exclusion list in `ai_detection.py` is deliberately narrow

The research question is whether/how AI is discussed differently across
company size and industry — including in **non-technical** roles, where a
plain-language AI mention (e.g. a marketing role using "AI-powered
speed-to-lead integrations") is itself the phenomenon being measured, not
noise to be filtered out. A broad, heuristic exclusion list (e.g. stripping
any posting that mentions AI outside a tech-sounding title) would silently
delete exactly the "AI divide" evidence the project is trying to surface —
a false negative here doesn't just lose a data point, it biases the whole
size/industry comparison toward already-tech-coded companies.

So exclusions are kept to a minimum and each one is required to be
**traceable to a specific false positive actually found in real data** (the
one current exclusion, `is_game_dev_ai_mention`, exists because game-dev
postings' "AI" almost always means classical pathfinding/NPC-behavior AI, not
ML/LLM AI — a pattern found by inspection, not assumed). Every exclusion is
checked against `KNOWN_SOFT_POSITIVES` (phrases like "comfortable using AI
tools in daily workflow") to catch the exclusion being too aggressive before
it ships, and `NON_TECHNICAL_AI_EXAMPLES` documents confirmed real cases the
final scoring logic must keep classifying as genuine hits.

### Other non-obvious decisions worth knowing

- **Normalizer order matters**: suffix stripping happens *before* whitespace
  collapse, because collapsing whitespace first destroys the word boundary
  the suffix regex depends on (`normalize_check.py`'s docstring calls this
  out as "the `thewaltdisneyco` problem" — collapse-then-strip would fail to
  recognize `Co.` as a separate trailing word).
- **Max-size-bucket, not first-match**: when a slug prefix-matches multiple
  PDL rows (a fragmented multinational), `run_real_match.py` picks the
  *largest* size bucket among candidates rather than an arbitrary one — the
  assumption being that for a size-tier analysis, the parent/global
  company's scale is the more meaningful signal than whichever regional
  subsidiary happens to sort first.
- **Short slugs are flagged, not auto-resolved**: slugs under 6 characters
  that prefix-match more than one PDL candidate (e.g. `2k`, `2u`) are routed
  to manual review instead of auto-matched, because short prefixes collide
  with many unrelated company names — auto-resolving them would trade
  coverage for silently wrong matches.
- **Pull-once caching is a repeated pattern**, not just an optimization in
  one file: `pull_data.py`, `run_real_match.py`, and `f500_check.py` all skip
  re-doing expensive work (a live scrape, a full-file normalize) if a cached
  output already exists on disk. This is deliberate given the PDL file is
  several GB and ATS pulls are rate-limited/slow — but it also means deleting
  the wrong cache file silently changes what a script does on its next run
  (e.g. `pdl_prefix_cache.csv` needs to be deleted manually after changing
  `normalize()`, or the cache will serve stale normalization).
