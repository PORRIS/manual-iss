"""Tarea 5: auditoría visual por muestreo (reproducible).

Elige 10 páginas al azar entre las que tienen tablas (semilla fija), las renderiza en
salida/auditoria/pag_NNN_{a,b}.png (mitad superior e inferior, legibles) y escribe
auditoria_filas.csv con las filas de la BD de esas páginas, en el orden del PDF, para
compararlas a ojo contra la imagen. El resultado de la revisión va en auditoria_visual.csv.
"""
import os
import random
import sqlite3

import pandas as pd
import pdfplumber

from validar_completo import ref5

SEMILLA = 256  # Acuerdo 256 de 2001
N = 10
DIR = "salida/auditoria"

pt = pd.read_csv("pdf_tablas.csv", dtype=str, keep_default_na=False)
pt["pagina"] = pt.pagina.astype(int)
pt["orden_en_pagina"] = pt.orden_en_pagina.astype(int)
paginas = sorted(set(pt.pagina))
muestra = sorted(random.Random(SEMILLA).sample(paginas, N))
print(f"páginas con tablas: {len(paginas)} | semilla {SEMILLA} | muestra: {muestra}")

con = sqlite3.connect("salida/manual_iss.db")
pr = pd.read_sql("SELECT fila_excel, codigo_manual, marca, codigo, descripcion, ref_nota, "
                 "valor FROM procedimientos ORDER BY fila_excel", con)
con.close()
pr["ref"] = pr.codigo_manual.map(ref5)
pr["k"] = pr.groupby(["ref", "codigo"]).cumcount()
pt = pt.sort_values(["pagina", "orden_en_pagina"])
pt["ref5"] = pt.ref.map(ref5)
pt["k"] = pt.groupby(["ref5", "codigo"]).cumcount()
m = pt.merge(pr, left_on=["ref5", "codigo", "k"], right_on=["ref", "codigo", "k"],
             how="left", suffixes=("_pdf", ""))
filas = m[m.pagina.isin(muestra)][["pagina", "orden_en_pagina", "fila_excel", "codigo_manual",
                                   "marca", "codigo", "descripcion", "ref_nota", "valor"]]
filas.to_csv("auditoria_filas.csv", index=False, encoding="utf-8-sig")
print(f"auditoria_filas.csv: {len(filas)} filas de la BD en {N} páginas")

os.makedirs(DIR, exist_ok=True)
with pdfplumber.open("MANUAL-ISS-2001.pdf") as pdf:
    for n in muestra:
        p = pdf.pages[n - 1]
        mitad = p.height / 2
        for sufijo, caja in (("a", (0, 0, p.width, mitad + 20)),
                             ("b", (0, mitad - 20, p.width, p.height))):
            p.crop(caja).to_image(resolution=110).save(f"{DIR}/pag_{n:03d}_{sufijo}.png")
print(f"imágenes en {DIR}/")
