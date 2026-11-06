"""Propone la jerarquía de agrupadores (título / subtítulo / ...) a partir del PDF y la
escribe en jerarquia_agrupadores.csv, para revisarla. etl.py la aplica como
agrupadores.padre_id y agrupadores.nivel.

Regla de niveles en el PDF (dentro de cada artículo):
  - títulos seguidos, sin filas de tabla entre ellos (p. ej. "CRANEO" / "MALFORMACIONES
    CONGENITAS"): cada uno es hijo del anterior;
  - un título suelto toma el nivel del título previo con el mismo estilo (negrita, tamaño y
    alineación); si hay varios, el más profundo. Si el estilo no se vio antes, es nivel 1.
Luego cada agrupador de la BD se empareja con su título del PDF por nombre (en orden).
"""
import csv
import difflib
import re

import pandas as pd

from rutas import al_proyecto, conectar

al_proyecto()
from validar_completo import fuerte

t = pd.read_csv("pdf_textos.csv", keep_default_na=False)
b = pd.read_csv("pdf_tablas.csv", keep_default_na=False)
bl = (t.sort_values(["pagina", "orden_en_pagina"]).groupby("bloque", sort=False)
        .agg(pagina=("pagina", "first"), orden=("orden_en_pagina", "first"),
             tipo=("tipo", "first"), texto=("texto", " ".join), negrita=("negrita", "first"),
             tamano=("tamano", "first"), x0=("x0", "first"), x1=("x1", "first"))
        .reset_index())


def estilo(r):
    return (bool(r.negrita), round(float(r.tamano), 0))  # la alineación varía entre páginas


ev = [(r.pagina, r.orden_en_pagina, "fila", None) for r in b.itertuples()] + \
     [(r.pagina, r.orden, "texto", r) for r in bl.itertuples()]
ev.sort(key=lambda e: (e[0], e[1]))

# ¿el título tiene subtítulos justo debajo (otro título antes de la siguiente fila)?
tiene_hijo, pendiente = {}, None
for _, _, clase, r in ev:
    if clase == "fila":
        pendiente = None
    elif r.tipo == "agrupador":
        if pendiente is not None:
            tiene_hijo[pendiente] = True
        pendiente = r.Index
    elif r.tipo in ("articulo", "capitulo"):
        pendiente = None

# Ajustes revisados a mano (2026-11-05) donde la regla automática falla; cada uno con la
# evidencia del PDF. (página, título) -> nivel. Los hijos se recalculan solos.
#   - Formato: en los arts. 1-18 el título de región va en negrita y sus subtítulos sin ella.
#   - REF: la numeración interna agrupa las secciones (21xxxx radiología, incluida la TAC;
#     31xxxx ecografía y RM; 22xxx medicina nuclear).
AJUSTES = {
    (13, "OPERACIONES EN LA RETINA"):
        (2, "subtítulo sin negrita de CAMARA ANTERIOR Y RETINA (en negrita)"),
    (43, "RESECCIONES EN LA MAMA"):
        (2, "subtítulo sin negrita de MAMA (en negrita), igual que INCISIONES EN OVARIO"),
    (119, "MEDICINA NUCLEAR"):
        (1, "sección propia: REF 22xxx, distinta de ecografía y RM (31xxxx)"),
    (148, "INTERNACION ESPECIAL"):
        (2, "mismo formato que INTERNACION GENERAL (negrita, x=191): hermanas"),
    (169, "Servicio Intermunicipal"):
        (3, "mismo formato que Servicio Urbano (negrita, x=152): hermanos"),
}
AJUSTES = {(p, fuerte(t)): v for (p, t), v in AJUSTES.items()}

titulos = []  # dict(articulo, texto, pagina, nivel, padre(idx en titulos), dudoso)
art, pila, vistos, tras_fila = None, [], [], True
# pila: títulos abiertos [(nivel, idx)]; vistos: todos los del artículo [(estilo, nivel, hijo)]
for _, _, clase, r in ev:
    if clase == "fila":
        tras_fila = True
        continue
    if r.tipo == "articulo":
        m = re.match(r"ARTICULO\s*(\d+)", r.texto)
        if m and int(m.group(1)) == (art or 0) + 1:
            art, pila, vistos = int(m.group(1)), [], []
        continue
    if r.tipo == "capitulo":
        pila = []
        continue
    if r.tipo != "agrupador" or art is None:
        continue
    st, hijo, dudoso = estilo(r), tiene_hijo.get(r.Index, False), ""
    if not tras_fila and pila:  # sigue a otro título: es su hijo
        nivel = pila[-1][0] + 1
    else:
        # nivel de los títulos anteriores del artículo con el mismo estilo; si este tiene
        # subtítulos, solo cuentan los que también los tuvieron ("UNIDAD DE SALUD MENTAL
        # ESPECIAL" es hermana de "...GENERAL", no hija de "SERVICIO DE COMPLEJIDAD ...")
        niveles = sorted({n for e, n, h in vistos if e == st and (h or not hijo)
                          and n <= (pila[-1][0] + 1 if pila else 1)})
        nivel = niveles[-1] if niveles else 1
        # revisados en lista el 2026-11-05; los incorrectos están en AJUSTES
        if len(niveles) > 1:
            dudoso = f"Revisado: el mismo formato aparece en los niveles {niveles}"
        elif not niveles and pila:
            dudoso = "Revisado: formato nuevo en el artículo; nivel 1"
    ajuste = AJUSTES.get((r.pagina, fuerte(r.texto)))
    if ajuste:
        nivel, dudoso = ajuste[0], f"Ajustado a mano: {ajuste[1]}"
    pila = [p for p in pila if p[0] < nivel]
    padre = pila[-1][1] if pila else None
    titulos.append(dict(articulo=art, texto=r.texto, pagina=r.pagina, nivel=nivel,
                        padre=padre, dudoso=dudoso))
    pila.append((nivel, len(titulos) - 1))
    vistos.append((st, nivel, hijo))
    tras_fila = False

tp = pd.DataFrame(titulos)
con = conectar()
ag = pd.read_sql("SELECT id, articulo, nombre, fila_excel FROM agrupadores ORDER BY fila_excel", con)
con.close()

filas, sin_pdf = [], []
pdf_a_bd = {}
for a in sorted(set(ag.articulo)):
    ga = ag[ag.articulo == a]
    ta = tp[tp.articulo == a]
    sm = difflib.SequenceMatcher(a=[fuerte(x) for x in ga.nombre],
                                 b=[fuerte(x) for x in ta.texto], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                pdf_a_bd[ta.index[j]] = ga.index[i]
        else:
            sin_pdf += [ga.index[i] for i in range(i1, i2)]

for j, i in pdf_a_bd.items():
    tj = tp.loc[j]
    pj = tj.padre
    pi = pdf_a_bd.get(pj) if pj is not None and not pd.isna(pj) else None
    filas.append(dict(fila_excel=int(ag.at[i, "fila_excel"]), nombre=ag.at[i, "nombre"],
                      nivel=int(tj.nivel),
                      fila_excel_padre=int(ag.at[pi, "fila_excel"]) if pi is not None else "",
                      nombre_padre=ag.at[pi, "nombre"] if pi is not None else "",
                      pagina_pdf=int(tj.pagina),
                      observacion=tj.dudoso if pj is None or pd.isna(pj) or pi is not None
                      else f"el título padre del PDF no está en la BD: {tp.at[pj, 'texto']}"))
for i in sin_pdf:
    filas.append(dict(fila_excel=int(ag.at[i, "fila_excel"]), nombre=ag.at[i, "nombre"],
                      nivel="", fila_excel_padre="", nombre_padre="", pagina_pdf="",
                      observacion="agrupador de la BD sin título equivalente en el PDF"))

out = pd.DataFrame(filas).sort_values("fila_excel")
out.to_csv("jerarquia_agrupadores.csv", index=False, quoting=csv.QUOTE_MINIMAL)
print(f"títulos en el PDF: {len(tp)} | agrupadores en la BD: {len(ag)} | emparejados: "
      f"{len(pdf_a_bd)} | sin pareja en el PDF: {len(sin_pdf)}")
print("agrupadores por nivel:", out.nivel.value_counts().to_dict())
print("ajustados a mano:", out.observacion.str.startswith("Ajustado").sum(),
      "| nivel dudoso (revisado):", out.observacion.str.startswith("Revisado").sum(),
      "| sin título en el PDF:", out.nivel.eq("").sum())
