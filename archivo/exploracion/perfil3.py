import pandas as pd

d = pd.read_excel("manual_iss.xls", header=None, engine="calamine").iloc[:, :5]
d.columns = ["c0", "pb", "cod", "desc", "val"]
d = d.dropna(how="all")
p = d.notna().astype(int).astype(str).agg("".join, axis=1)
t = d["c0"].astype(str)

# 1) filas sin valor: 2 ejemplos por patrón, con 6 filas antes y 1 después
for pat in ["01110", "10110", "00110"]:
    idx = d.index[p == pat]
    print(f"\n##### {pat}: {len(idx)} filas")
    for i in [idx[len(idx) // 3], idx[2 * len(idx) // 3]]:
        pos = d.index.get_loc(i)
        print(d.iloc[max(pos - 6, 0):pos + 2].to_string(max_colwidth=40))
        print("---")

# 2) artículos: título corto y estadísticas del valor (para deducir la unidad)
es_art = t.str.upper().str.match(r"^ARTICULO")
print("\n##### ARTICULOS")
for i in d.index[es_art]:
    print(i, t[i][:70])

d["art"] = t.where(es_art).str.upper().str.extract(r"(ARTICULO\s*\d+)")[0].ffill()
d["v"] = pd.to_numeric(d["val"], errors="coerce")
print("\n##### VALOR POR ARTICULO (n, mediana, máximo)")
print(d.dropna(subset=["v"]).groupby("art", sort=False)["v"]
      .agg(["count", "median", "max"]).to_string())