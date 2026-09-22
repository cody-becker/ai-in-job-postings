from ats_scrapers import get_scraper_for_url
import pandas as pd
from pathlib import Path

# Project root is two levels up from scripts/scratch/ -- makes paths work
# no matter what directory this is run from.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"

scraper = get_scraper_for_url("https://nvidia.wd5.myworkdayjobs.com/nvidiaexternalcareersite")
jobs = scraper.fetch()



df = pd.DataFrame([
    {"title": j.title, "company": j.company, "location": j.location, "description": j.description}
    for j in jobs
])
print(df.head())
print(df.shape)
df.to_csv(DATA_RAW / "nvidia_postings.csv", index=False)