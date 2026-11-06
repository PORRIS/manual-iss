"""Control de la tarea 1: compara pdf_tablas.csv (celdas, pdfplumber) contra
pdf_referencia.csv (pdftotext + regex) en ref, código y valor, página por página y en orden.
Escribe control_extraccion.csv con cada discrepancia."""
import difflib

import pandas as pd

ref = pd.read_csv("pdf_referencia.csv", dtype=str, encoding="utf-8-sig")
cel = pd.read_csv("pdf_tablas.csv", dtype=str, encoding="utf-8-sig").fillna("")
ref = ref.fillna("")
ref["pagina"] = ref.pagina.astype(int)
cel["pagina"] = cel.pagina.astype(int)
ref = ref.sort_values(["pagina", "linea"], key=lambda s: s.astype(int))
cel = cel.sort_values(["pagina", "orden_en_pagina"], key=lambda s: s.astype(int))
cel = cel[cel.codigo != ""]  # filas sin código (tablas de texto) no son procedimientos


def r5(r):
    return r.zfill(5) if r.isdigit() else r


def num(v):
    return "" if v == "" else f"{float(v):.4f}"


dif = []
for pag in sorted(set(ref.pagina) | set(cel.pagina)):
    a = ref[ref.pagina == pag]
    b = cel[cel.pagina == pag]
    ka = list(zip(a.ref_pdf.map(r5), a.codigo))
    kb = list(zip(b.ref.map(r5), b.codigo))
    sm = difflib.SequenceMatcher(a=ka, b=kb, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                ra, rb = a.iloc[i], b.iloc[j]
                if num(ra.valor_pdf) != num(rb.valor):
                    dif.append(dict(tipo="VALOR", pagina=pag, ref=ka[i][0], codigo=ka[i][1],
                                    referencia=ra.valor_txt, celdas=rb.valor_txt))
                if (ra.pb == "PB") != (rb.pb == "PB"):
                    dif.append(dict(tipo="PB", pagina=pag, ref=ka[i][0], codigo=ka[i][1],
                                    referencia=ra.pb, celdas=rb.pb))
        else:
            for i in range(i1, i2):
                dif.append(dict(tipo="SOLO_REFERENCIA", pagina=pag, ref=ka[i][0],
                                codigo=ka[i][1], referencia=a.iloc[i].valor_txt, celdas=""))
            for j in range(j1, j2):
                dif.append(dict(tipo="SOLO_CELDAS", pagina=pag, ref=kb[j][0], codigo=kb[j][1],
                                referencia="", celdas=b.iloc[j].valor_txt))

d = pd.DataFrame(dif, columns=["tipo", "pagina", "ref", "codigo", "referencia", "celdas"])
d.to_csv("control_extraccion.csv", index=False, encoding="utf-8-sig")
print(f"referencia: {len(ref)} | celdas (con código): {len(cel)}")
print("discrepancias:", d.tipo.value_counts().to_dict() if len(d) else "ninguna")
if len(d):
    print("páginas:", d.groupby("pagina").size().sort_values(ascending=False).head(15).to_dict())
    print(d.head(20).to_string(index=False))
