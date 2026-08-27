from ats_scrapers import search

jobs = search(query="engineer", ats="greenhouse", limit=300)
jobs.to_csv("job_sample.csv", index=False)
print(f"Saved {len(jobs)} postings to job_sample.csv")