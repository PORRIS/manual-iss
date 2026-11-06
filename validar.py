"""Compara la BD generada desde el Excel (salida/manual_iss.db) contra el PDF del
Acuerdo 256 de 2001, ya extraído en pdf_referencia.csv. Escribe validacion.csv."""
import re
import sqlite3
import unicodedata

import pandas as pd

DB = "salida/manual_iss.db"
REF_PDF = "pdf_referencia.csv"
SALIDA = "validacion.csv"


def norm_txt(s):
    if s is None or pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\(\d+\)|[*+]", "", s)
    return re.sub(r"[^A-Z0-9]", "", s)


def norm_ref(r):
    if r is None or pd.isna(r):
        return ""
    r = str(r).strip()
    if r.endswith(".0"):
        r = r[:-2]
    return r.zfill(5) if r.isdigit() else r  # el xls pierde el cero: 5101 -> 05101


# ---- datos ----
con = sqlite3.connect(DB)
x = pd.read_sql("SELECT fila_excel, articulo, codigo_manual, codigo, descripcion, valor, tipo "
                "FROM procedimientos ORDER BY fila_excel", con)
con.close()
p = pd.read_csv(REF_PDF, dtype={"ref_pdf": str, "codigo": str}).sort_values("linea")

x["ref"] = x.codigo_manual.map(norm_ref)
p["ref"] = p.ref_pdf.map(norm_ref)
x["k"] = x.groupby(["ref", "codigo"]).cumcount()
p["k"] = p.groupby(["ref", "codigo"]).cumcount()

m = x.merge(p, on=["ref", "codigo", "k"], how="outer", indicator=True)
hallazgos = []


def add(tipo, r, detalle=""):
    hallazgos.append(dict(
        tipo=tipo, fila_excel=r.get("fila_excel"), pagina_pdf=r.get("pagina"),
        articulo=r.get("articulo"), ref=r.get("ref"), codigo=r.get("codigo"),
        descripcion_excel=r.get("descripcion"), descripcion_pdf=r.get("descripcion_pdf"),
        valor_excel=r.get("valor"), valor_pdf=r.get("valor_pdf"), detalle=detalle))


for _, r in m.iterrows():
    r = r.to_dict()
    if r["_merge"] == "left_only":
        add("SOLO_EN_EXCEL", r)
        continue
    if r["_merge"] == "right_only":
        add("SOLO_EN_PDF", r)
        continue
    vx, vp = r["valor"], r["valor_pdf"]
    if r["tipo"] == "con_valor":
        if pd.isna(vp):
            add("PDF_SIN_VALOR", r, "revisar la página a mano")
        else:
            d = abs(vx - vp)
            if d > 5:
                add("VALOR_DISTINTO", r, f"diferencia {d:,.2f}")
            elif d > 0.001:
                add("REDONDEO", r, f"diferencia {d:,.2f}")
    nx, np_ = norm_txt(r["descripcion"]), norm_txt(r["descripcion_pdf"])
    if np_ and not nx.startswith(np_[:max(10, len(np_) - 3)]):
        add("DESCRIPCION_DISTINTA", r)

# valores con decimales que el formato del Excel puede estar ocultando
for _, r in x[(x.tipo == "con_valor") & (x.valor % 1 != 0) & (x.valor > 100)].iterrows():
    add("VALOR_CON_DECIMALES", r.to_dict(), "el Excel guarda decimales que no se ven")

h = pd.DataFrame(hallazgos)
h.to_csv(SALIDA, index=False, encoding="utf-8-sig")

emp = (m._merge == "both").sum()
print(f"filas Excel: {len(x)} | filas PDF: {len(p)} | emparejadas: {emp} ({emp / len(x):.1%})")
cv = m[(m._merge == "both") & (m.tipo == "con_valor")]
print(f"valores comparados: {cv.valor_pdf.notna().sum()}")
print("hallazgos por tipo:")
print(h.tipo.value_counts().to_string() if len(h) else "  ninguno")
print(f"detalle en {SALIDA}")
