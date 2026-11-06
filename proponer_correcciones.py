"""Tarea 4: genera correcciones_propuestas.csv (mismo formato que correcciones.csv) a partir
de validacion_completa.csv. NO modifica correcciones.csv: hay que revisarlo y aprobarlo.

Criterios:
  - descripción / nota_ref / textos con equivalente en el PDF -> cambiar al texto del PDF
    (la BD guarda la última nota en ref_nota y las anteriores al final de la descripción)
  - textos de la BD que no están en el PDF o están duplicados -> eliminar
  - falsos positivos de la extracción del PDF -> aceptar (se mantiene la BD)
  - lo que es decisión del usuario -> motivo empieza con "DECIDIR:" (acción sugerida)
"""
import csv
import re

import pandas as pd

from rutas import al_proyecto, conectar

al_proyecto()
from validar_completo import RE_NOTAS_FINAL, espacios, fuerte, notas_de

DB = "salida/manual_iss.db"
COLS = ["fila_excel", "codigo_esperado", "accion", "campo", "valor_nuevo", "pagina_pdf",
        "motivo"]

d = pd.read_csv("validacion_completa.csv", dtype=str, keep_default_na=False)
con = conectar()
pr = pd.read_sql("SELECT fila_excel, codigo, descripcion, ref_nota FROM procedimientos", con)
con.close()
pr["fila_excel"] = pr.fila_excel.astype(str)
pr = pr.set_index("fila_excel")
pt = pd.read_csv("pdf_tablas.csv", dtype=str, keep_default_na=False)

prop = []


def P(fila, cod, accion, campo, valor, pag, motivo):
    prop.append(dict(fila_excel=fila, codigo_esperado=cod, accion=accion, campo=campo,
                     valor_nuevo=valor, pagina_pdf=pag, motivo=motivo))


# ---------------------------------------------------------------- procedimientos
DECISION_DESC = {
    "903046": "DECIDIR: el PDF deja vacía la primera línea y solo trae 'POR NEFELOMETRÍA' "
              "(falta 'TRANSFERRINA', error evidente del PDF). Se sugiere mantener la BD",
}
proc = d[d.campo.isin(["descripcion", "nota_ref"])]
for f, g in proc.groupby("fila_excel"):
    r = pr.loc[f]
    cod, pag = g.codigo.iloc[0], g.pagina_pdf.iloc[0]
    tipos = "/".join(sorted(set(g.tipo)))
    if cod in DECISION_DESC:
        for _, x in g.iterrows():
            P(f, cod, "aceptar", x.campo, x.valor_pdf, pag, DECISION_DESC[cod])
        continue
    d_bd = espacios(r.descripcion)
    core_bd = RE_NOTAS_FINAL.sub("", d_bd).strip()
    gd = g[g.campo == "descripcion"]
    core = gd.valor_pdf.iloc[0] if len(gd) else core_bd
    gn = g[g.campo == "nota_ref"]
    if len(gn):
        notas = [n for n in gn.valor_pdf.iloc[0].split(",") if n]
    else:
        notas = [n for n in (notas_de(RE_NOTAS_FINAL.search(d_bd).group(0))
                             if RE_NOTAS_FINAL.search(d_bd) else "").split(",") if n]
        notas += [espacios(r.ref_nota).removesuffix(".0")] if espacios(r.ref_nota) else []
    desc_obj = core + "".join(f" ({n})" for n in notas[:-1])
    ref_obj = notas[-1] if notas else ""
    if desc_obj != d_bd:
        P(f, cod, "cambiar", "descripcion", desc_obj, pag, f"[{tipos}] Texto del PDF")
    if ref_obj != espacios(r.ref_nota).removesuffix(".0"):
        P(f, cod, "cambiar", "ref_nota", ref_obj, pag, f"[{tipos}] Nota del PDF "
          f"({'sin nota' if not ref_obj else '(' + ref_obj + ')'})")

# ---------------------------------------------------------------- textos de la BD
CAMPO_TXT = {"texto_agrupador": "nombre"}
ELIMINAR = {
    "45": "Cabecera de tabla del Excel ('ISS CODIGO DESCRIPCION UVR'); no es texto del PDF",
    "1954": "Nota (362) de M09181, procedimiento que no existe en el PDF (ya eliminado)",
    "8506": "Nota (362) de M09181, procedimiento que no existe en el PDF (ya eliminado)",
    "4942": "Título que no aparece en el PDF (buscado en el texto completo)",
}
for _, x in d[d.campo.str.startswith("texto_") & (d.campo != "texto_solo_pdf")].iterrows():
    campo = CAMPO_TXT.get(x.campo, "texto")
    if x.valor_pdf:
        P(x.fila_excel, "", "cambiar", campo, x.valor_pdf, x.pagina_pdf,
          f"[{x.tipo}] Texto del PDF")
    elif x.detalle.startswith("duplicado"):
        P(x.fila_excel, "", "eliminar", "", "", x.pagina_pdf, f"[MAYOR] {x.detalle}")
    elif x.fila_excel in ELIMINAR:
        P(x.fila_excel, "", "eliminar", "", "", x.pagina_pdf, f"[MAYOR] {ELIMINAR[x.fila_excel]}")
    else:
        P(x.fila_excel, "", "aceptar", x.campo, "", x.pagina_pdf,
          "DECIDIR: texto de la BD sin pareja en el PDF")

# ---------------------------------------------------------------- textos solo en el PDF
for _, x in d[d.campo == "texto_solo_pdf"].iterrows():
    if x.detalle.startswith("leyenda"):
        m = "DECIDIR: leyenda de abreviaturas al pie de tabla; la BD no guarda leyendas. " \
            "Se sugiere aceptar (no agregarlas)"
    elif x.pagina_pdf == "173":
        continue  # se resuelve con AGREGAR (notas de implante coclear)
    elif x.pagina_pdf == "207":
        m = "DECIDIR: fórmula de cierre y firmas del Acuerdo; la BD no la guarda. " \
            "Se sugiere aceptar"
    else:
        m = "DECIDIR: nota del PDF que falta en la BD. Se sugiere agregarla " \
            "(requiere acción 'agregar' en etl.py); mientras tanto, aceptar"
    P("", "", "aceptar", x.campo, x.valor_pdf, x.pagina_pdf, m)

# notas del PDF que faltan en el Excel (pág. 173), después de su procedimiento
AGREGAR = [
    ("8592", "C40147", "INCLUYE: evaluación por psicología, audiología y terapia de lenguaje."),
    ("8596", "C40148", "INCLUYE: instrucción a paciente y familia; encendido (decisión sobre "
     "tipo de parámetro de estimulación a utilizar, medición de la respuesta electrofísica del "
     "paciente a los electródos, elaboración y ajustes de mapeos, balanceo de electródos, "
     "revisión de umbrales, evaluación de pruebas audiométricas y primera fase del "
     "entrenamiento). Tarifa por paciente."),
    ("8597", "C40149", "INCLUYE: ajustes de programación, revisión electroacústica del mapeo, "
     "evaluación de pruebas audiométricas, etc. Tarifa por paciente."),
]
for f, cod, txt in AGREGAR:
    P(f, cod, "agregar", "texto", txt, "173", "[MAYOR] Nota del PDF que falta en el Excel")

# título de dos líneas que el Excel partió en dos agrupadores (pág. 73)
P("3868", "", "cambiar", "nombre", "TRATAMIENTO EN QUEMADURAS (Incluye quemadura por fricción)",
  "73", "[MAYOR] En el PDF es un solo título de dos líneas")
P("3869", "", "eliminar", "", "", "73", "[MAYOR] Segunda línea del título 'TRATAMIENTO EN "
  "QUEMADURAS'; sus procedimientos pasan a ese agrupador")

# ---------------------------------------------------------------- agrupador por procedimiento
# títulos que la BD tiene como nota y en el PDF son agrupador (centrados sobre la tabla)
NOTA_A_AGRUPADOR = {"2594": "48", "2932": "55"}
for f, pag in NOTA_A_AGRUPADOR.items():
    P(f, "", "cambiar", "tipo", "agrupador", pag,
      "[MAYOR] En el PDF es un título (agrupador) y la BD lo tiene como nota; las filas "
      "siguientes quedan bajo el agrupador anterior")
PDF_FALSO = {  # líneas que la extracción tomó como título y no lo son
    "EQUIPO O ELEMENTO M3 / HORA O": "cabecera de columna fuera de la tabla (pág. 167)",
}
for _, x in d[d.campo == "agrupador"].iterrows():
    if x.valor_pdf in PDF_FALSO or (x.pagina_pdf == "173" and x.valor_bd == "Actividades postimplante"):
        motivo = ("Falso positivo de la extracción: " +
                  PDF_FALSO.get(x.valor_pdf, "líneas en negrita de una nota (pág. 173)") +
                  "; el agrupador de la BD es correcto")
    elif re.search(r"EXTRAÑO INTRA ?OSEO", x.valor_pdf):
        continue  # se resuelve con NOTA_A_AGRUPADOR
    elif fuerte(x.valor_pdf) == fuerte("Trasplante de médula ósea"):
        continue  # se resuelve al corregir el nombre del agrupador (texto_agrupador)
    elif x.valor_bd == "(Incluye quemadura por fricción)":
        continue  # se resuelve uniendo los dos agrupadores (filas 3868 y 3869)
    else:
        motivo = ("DECIDIR: jerarquía de títulos (título + subtítulo); la BD tiene un solo "
                  f"nivel de agrupador. Títulos del PDF: {x.detalle.split('[', 1)[-1].rstrip(']')}")
    P(x.fila_excel, x.codigo, "aceptar", "agrupador", x.valor_pdf, x.pagina_pdf, motivo)

out = pd.DataFrame(prop, columns=COLS)
# decisiones aprobadas por el usuario (2026-11-05): se dejan como "Aprobado:"
out["motivo"] = out.motivo.str.replace(r"^DECIDIR: ", "Aprobado: ", regex=True)
out.to_csv("correcciones_propuestas.csv", index=False, quoting=csv.QUOTE_MINIMAL)
print(f"correcciones_propuestas.csv: {len(out)} filas")
out["clase"] = out.motivo.str.extract(r"^\[(\w+(?:/\w+)?)\]")[0].fillna(
    out.motivo.str.extract(r"^(Aprobado|Falso positivo)")[0])
print(out.pivot_table(index=["accion", "campo"], columns="clase", values="motivo",
                      aggfunc="size", fill_value=0).to_string())
