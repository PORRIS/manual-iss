import pandas as pd

df = pd.read_excel("manual_iss.xls", header=None, sheet_name=None)
for hoja, d in df.items():
    print(hoja, d.shape)
    print(d.head(40).to_string(max_colwidth=40))   # muestra
    # patrón de columnas llenas: revela tipos de fila
    patron = d.notna().astype(int).astype(str).agg("".join, axis=1)
    print(patron.value_counts().head(10))