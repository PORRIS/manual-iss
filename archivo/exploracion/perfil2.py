import pandas as pd

d = pd.read_excel("manual_iss.xls", header=None, engine="calamine").dropna(how="all")
patron = d.notna().astype(int).astype(str).agg("".join, axis=1)

# 1) 4 filas de ejemplo por cada patrón frecuente
for p, n in patron.value_counts().head(10).items():
    print(f"\n=== {p}  ({n} filas) ===")
    print(d[patron == p].sample(min(4, n), random_state=1).sort_index()
          .to_string(max_colwidth=45))

# 2) palabras clave que delatan agrupadores y notas (columna 0)
col0 = d[0].astype(str).str.strip().str.upper()
print("\n=== palabras clave en col 0 ===")
for kw in ["CAPITULO", "SECCION", "SUBSECCION", "GRUPO", "ARTICULO", "NOTA", "PARAGRAFO", "TOTAL"]:
    m = col0.str.startswith(kw)
    print(kw, m.sum(), list(d.index[m][:5]))