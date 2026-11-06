import pandas as pd

df = pd.read_excel("manual_iss.xls", header=None, engine="calamine", dtype=object)
df.to_csv("manual_iss_crudo.csv", index=False, header=False, sep=";", encoding="utf-8-sig")
print("OK ->", df.shape)