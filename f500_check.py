from ats_scrapers import get_scraper_for_url
import pandas as pd

scraper = get_scraper_for_url("https://nvidia.wd5.myworkdayjobs.com/nvidiaexternalcareersite")
jobs = scraper.fetch()



df = pd.DataFrame([
    {"title": j.title, "company": j.company, "location": j.location, "description": j.description}
    for j in jobs
])
print(df.head())
print(df.shape)
df.to_csv("nvidia_postings.csv", index=False)