import pandas as pd

df = pd.read_csv("free_company_dataset.csv", nrows=2000)
print(df["size"].unique())
print(df["size"].value_counts(dropna=False))

sizes = pd.read_csv("free_company_dataset.csv", usecols=["size"])
sizes["size"].value_counts(dropna=False).rename_axis("size_bucket").reset_index(name="count").to_csv("size_counts.csv", index=False)
