# AI in Job Postings

Independent research project analyzing how AI is discussed in job postings, and whether/how that discussion differs across company size and industry.

## Research question

How is AI discussed in job postings, and does that differ by company "level" — where level is defined as the crossing of two axes:

1. **Company size** (PDL's size bucket: `1-10`, `51-200`, ... `10001+`)
2. **Industry** (PDL's industry field)

These are treated as *crossed* dimensions (`groupby(["size_tier", "industry"])`), not nested — a company's size and industry can independently affect how it talks about AI (e.g. Nvidia and Walmart are the same size tier but talk about AI completely differently; that's an industry effect, not a size effect).

Five named companies (Walmart, Intel, Google, Nvidia, a small regional bank) are used as illustrative case studies layered on top of the real evidence, not as the evidence itself.

## Why this matters

- **Diffusion of innovation** — firm size/resources shaping technology adoption is well-established IS theory.
- **Job postings as revealed preference** — a text signal of a firm's actual tech posture, as opposed to self-reported survey data.
- **"AI divide"** — whether AI-related opportunity concentrates at already-resourced employers, echoing digital divide research.

Not controlled for: geography, funding stage, company age. Disclosed as limitations / future work, not fixed in this version.

## Data sources

- **Job postings**: [`ats-scrapers`](https://github.com/kalil0321/ats-scrapers) (Greenhouse, Workday)
- **Firmographic data**: [People Data Labs](https://www.peopledatalabs.com/) free bulk company dataset (~35.8M rows) — company name, industry, size bucket, founded year, LinkedIn URL. Supplemented by PDL's Company Enrichment API for gap-filling genuine misses.

PDL aggregates from public web sources and third-party datasets rather than direct company verification. Company size is likely inferred substantially from public professional-profile data, which may under-represent companies or regions with lower presence on such platforms — a limitation carried into any size-based analysis built on this data.

## Current status

**Entity resolution (job posting company name → PDL company record) is the current focus.**

- Normalizer strips legal suffixes (`inc`, `llc`, `gmbh`, `ag`, `sarl`, etc.) using word-boundary matching, run *before* whitespace collapse (see `scripts/scratch/normalize_check.py`).
- ~834 PDL rows have corrupted `size` values due to a CSV quoting issue upstream; filtered out (`~0.002%` of the file — negligible).
- Large/multinational companies (e.g. Walmart) are *fragmented* across many PDL rows (regional subsidiaries, business units), not missing. Resolved via prefix-match + max-size-bucket across all matching candidates (see `prefix_match()` in `scripts/run_real_match.py`).
- Short slugs (e.g. `2k`, `2u`) that prefix-match many unrelated candidates are flagged for manual review rather than auto-resolved, to avoid false positives.

**Latest real match rate** (44 unique companies from an initial 300-posting Greenhouse "engineer" search, matched against the full PDL file):
- 28/44 (63.6%) auto-matched
- 6/44 flagged for manual review (ambiguous short-slug or large-candidate-set matches)
- 12/44 genuinely unmatched (mix of unfixable junk — ATS aggregator containers, hashed tokens — and real companies needing fuzzy matching not yet implemented)
- **34/44 (77.3%) resolvable** combining auto-matched + manual review

## Roadmap

1. Manually resolve the 6 flagged review cases
2. Run size-skew audit — check whether unmatched companies disproportionately skew toward small companies (now meaningful, since normalizer/prefix-match preprocessing bugs are fixed)
3. Add fuzzy matching for genuine naming-format mismatches (e.g. `ambiqmicroinc` vs. PDL's shorter brand name)
4. Scale the job postings pull — more ATS platforms (Workday specifically, for enterprise-tier companies), more search terms/job functions
5. Pull and cache the five named case-study companies
6. Build the actual AI-mention detection method — distinguishing AI-as-required-skill, AI-as-company-subject, and AI-in-hiring-process, not a flat keyword count
7. Join postings + AI-mention tags + company tier into one table
8. Run the crossed `groupby(["size_tier", "industry"])` comparison
9. Write up with an explicit limitations section
10. Consider submission venues (undergrad research symposium / journal)

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

You'll need your own copy of PDL's free bulk company dataset (signup required) and to run your own `ats-scrapers` pulls — these files are not included in this repo (see `.gitignore`) due to size and redistribution terms. Drop them into `data/raw/` (e.g. `data/raw/free_company_dataset.csv`, `data/raw/job_sample_scaled_v4.csv`) and the scripts will pick them up from there.

## Project structure

```
data/raw/         original pulled datasets (PDL bulk company file, ATS job-posting pulls)
data/cache/       PDL/matching cache files, rebuilt automatically if deleted
data/results/     matching and classification outputs
scripts/          the real pipeline: pull_data.py, run_real_match.py, ai_detection.py,
                  classify_and_join.py, fuzzy_match_leftovers.py
scripts/scratch/  one-off exploratory/diagnostic scripts
```

All scripts resolve paths relative to the project root (via `Path(__file__)`), so they can be run either from the repo root (`python scripts/run_real_match.py`) or from within their own directory.
