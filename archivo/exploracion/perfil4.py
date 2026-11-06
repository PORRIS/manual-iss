import pandas as pd

raw = pd.read_excel("manual_iss.xls", header=None, engine="calamine").iloc[:, :5]
c0 = raw[0].astype(str)
txt = raw.fillna("").astype(str).agg(" | ".join, axis=1)

# 1) cualquier fila "ARTI..." en col 0 que NO haya sido leída como artículo
raro = c0.str.contains(r"^\s*ART", case=False) & ~c0.str.match(r"(?i)^ART[IÍ]CULO\s*\d+")
print("## filas ART* no reconocidas:", int(raro.sum()))
for i in raw.index[raro][:10]:
    print(i, txt[i][:140])

# 2) dónde aparece el 15 y el 83 en cualquier columna
for n in (15, 83):
    m = txt.str.contains(rf"ART\S*\W*{n}\b", case=False, regex=True)
    print(f"\n## 'ART..{n}' en filas:", list(raw.index[m][:5]))
    for i in raw.index[m][:3]:
        print(i, txt[i][:140])

# 3) artículo 83: el hueco entre el 82 y el 84 (filas 7903-7918)
print("\n## filas 7903-7918")
print(raw.iloc[7903:7919].to_string(max_colwidth=60))

# 4) sin_valor del artículo 95: 3 casos con contexto
p = pd.read_csv("salida/procedimientos.csv")
sv = p[(p.tipo == "sin_valor") & (p.articulo == 95)]
print("\n## sin_valor art 95:", len(sv))
for f in sv.fila_excel.head(3):
    print(raw.iloc[f - 5:f + 2].to_string(max_colwidth=50))
    print("---")

# 5) artículo 59 completo (filas 7636-7644)
print("\n## art 59")
print(raw.iloc[7636:7645].to_string(max_colwidth=130))