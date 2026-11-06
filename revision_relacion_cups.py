"""Posibles inconsistencias en la relación CUPS 2026 -> ISS 2001 («Relación Manual ISS - CUPS 2026»).

Compara la descripción de cada CUPS con la del código ISS al que apunta y busca en el Manual un
código cuya descripción se parezca más. Un caso se marca solo si cumple una de estas reglas:

1. Mismo código en el Manual: el código CUPS existe en el Manual con una descripción equivalente
   (parecido >= 0,6 y al menos 0,2 mayor que el del código actual), pero la relación lo lleva a otro.
2. Descripción del Manual contenida en la CUPS: todas las palabras de la descripción de otro código
   del Manual están en la descripción CUPS y las del código actual no (ej. «GLUCOSA SEMIAUTOMATIZADA
   [GLUCOMETRÍA]» -> M19275 GLUCOMETRÍA y no 903840 GLUCOSA EN ORINA).
3. Grupo de procedimiento distinto: los dos primeros dígitos del CUPS y del código actual difieren,
   el parecido actual es bajo (< 0,3) y hay un candidato del mismo grupo del CUPS mucho mejor.
4. Descripción muy distinta: parecido actual < 0,2 y un candidato con >= 0,55 (0,35 más).

Parecido: coseno entre las palabras de las dos descripciones (sin tildes ni palabras vacías),
ponderadas por lo poco comunes que son en el Manual (IDF). No se sugieren conjuntos (códigos C):
llevar un CUPS a un paquete integral cambia la forma de pago.

Son sugerencias para revisar, no correcciones: proponer_homologaciones() las agrega a
homologacion.csv con estado "por_revisar" y solo las "aprobada" se usan en la auditoría.

Uso: uv run revision_relacion_cups.py     (muestra el resumen y actualiza homologacion.csv)
"""
import math
import re
import unicodedata
from collections import Counter

import pandas as pd

from rutas import BASE

HOMOLOGACION = BASE / "homologacion.csv"
COLUMNAS_HOMOLOGACION = ["codigo_factura", "codigo_manual", "estado", "observacion"]
VACIAS = set("DE DEL LA LAS EL LOS Y O EN POR CON SIN A AL U OTRO OTRA OTROS OTRAS PARA SOD NCOC "
             "VIA SU SE UN UNA".split())
MOTIVOS = {
    "Mismo código en el Manual": "el código CUPS también existe en el Manual con una descripción "
                                 "equivalente, pero la relación lo lleva a otro código",
    "Descripción del Manual contenida en la CUPS": "la descripción de otro código del Manual está "
                                                   "completa en la descripción CUPS y la del código "
                                                   "actual no",
    "Grupo de procedimiento distinto": "el código actual es de otro grupo (dos primeros dígitos) y "
                                       "se parece poco; hay un código del grupo del CUPS mucho más "
                                       "parecido",
    "Descripción muy distinta": "la descripción del código actual casi no se parece a la CUPS y hay "
                                "otro código del Manual claramente más parecido",
}


def palabras(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return {t for t in re.findall(r"[A-Z0-9]+", s) if t not in VACIAS and len(t) > 1}


def revisar(relacion, procedimientos):
    """relacion: DataFrame (cups, descripcion_cups, codigo_iss).
    procedimientos: DataFrame (codigo, descripcion) con los códigos del Manual que tienen tarifa.
    Devuelve un DataFrame con una fila por posible inconsistencia."""
    desc = (procedimientos.dropna(subset=["codigo"]).drop_duplicates("codigo")
            .set_index("codigo").descripcion.to_dict())
    docs = {c: palabras(d) for c, d in desc.items()}
    df = Counter(t for s in docs.values() for t in s)
    n = len(docs)

    def idf(t):
        return math.log((n + 1) / (df.get(t, 0) + 1)) + 1

    def sim(a, b):
        if not a or not b:
            return 0.0
        return sum(idf(t) for t in a & b) / math.sqrt(sum(idf(t) for t in a) * sum(idf(t) for t in b))

    indice = {}
    for c, s in docs.items():
        for t in s:
            indice.setdefault(t, set()).add(c)
    sugeribles = {c for c in docs if not c.startswith("C")}  # sin conjuntos del art. 95

    def candidatos(a, excluir):
        return {c for t in a for c in indice.get(t, ())} & sugeribles - {excluir}

    filas = []
    for cups, dc, iss in relacion[["cups", "descripcion_cups", "codigo_iss"]].itertuples(index=False):
        if iss not in docs:
            continue  # sin tarifa en el Manual: es otra novedad (v_novedades_relacion_cups)
        a, b = palabras(dc), docs[iss]
        s = sim(a, b)
        cand = candidatos(a, iss)
        hallazgo = None
        if cups != iss and cups in sugeribles:
            sc = sim(a, docs[cups])
            if sc >= 0.6 and sc >= s + 0.2:
                hallazgo = ("Mismo código en el Manual", cups, sc)
        if not hallazgo and not b <= a:
            dentro = [c for c in cand if docs[c] and docs[c] <= a
                      and sum(idf(t) for t in docs[c]) >= 5]
            if dentro:
                sc, c = max((sim(a, docs[c]), c) for c in dentro)
                if sc >= s + 0.15:
                    hallazgo = ("Descripción del Manual contenida en la CUPS", c, sc)
        if (not hallazgo and cups[:2].isdigit() and iss[:2].isdigit() and cups[:2] != iss[:2]
                and s < 0.3):
            mismo = [c for c in cand if c[:2] == cups[:2]]
            if mismo:
                sc, c = max((sim(a, docs[c]), c) for c in mismo)
                if sc >= 0.5 and sc >= s + 0.25:
                    hallazgo = ("Grupo de procedimiento distinto", c, sc)
        if not hallazgo and s < 0.2 and cand:
            sc, c = max((sim(a, docs[c]), c) for c in cand)
            if sc >= 0.55 and sc - s >= 0.35:
                hallazgo = ("Descripción muy distinta", c, sc)
        if hallazgo:
            tipo, c, sc = hallazgo
            filas.append(dict(cups=cups, descripcion_cups=dc, codigo_iss=iss,
                              descripcion_iss=desc[iss], parecido_actual=round(s, 2),
                              codigo_sugerido=c, descripcion_sugerida=desc[c],
                              parecido_sugerido=round(sc, 2), tipo=tipo, motivo=MOTIVOS[tipo]))
    return pd.DataFrame(filas, columns=[
        "cups", "descripcion_cups", "codigo_iss", "descripcion_iss", "parecido_actual",
        "codigo_sugerido", "descripcion_sugerida", "parecido_sugerido", "tipo", "motivo"])


def leer_homologacion():
    if not HOMOLOGACION.exists():
        return pd.DataFrame(columns=COLUMNAS_HOMOLOGACION)
    h = pd.read_csv(HOMOLOGACION, dtype=str, keep_default_na=False)
    for c in COLUMNAS_HOMOLOGACION:
        if c not in h.columns:
            h[c] = "aprobada" if c == "estado" else ""
    return h[COLUMNAS_HOMOLOGACION]


def proponer_homologaciones(revision):
    """Agrega a homologacion.csv las sugerencias que aún no estén (estado "por_revisar").
    No toca las filas existentes: así se conservan las aprobadas o rechazadas a mano."""
    h = leer_homologacion()
    ya = set(h.codigo_factura.str.upper())
    nuevas = [dict(codigo_factura=r.cups, codigo_manual=r.codigo_sugerido, estado="por_revisar",
                   observacion=f"{r.tipo}: hoy la relación lo lleva a {r.codigo_iss} "
                               f"({r.descripcion_iss[:60]}); sugerido {r.codigo_sugerido} "
                               f"({r.descripcion_sugerida[:60]})")
              for r in revision.itertuples() if r.cups.upper() not in ya]
    if nuevas:
        h = pd.concat([h, pd.DataFrame(nuevas)], ignore_index=True)
        h.to_csv(HOMOLOGACION, index=False)
    return len(nuevas)


if __name__ == "__main__":
    from rutas import conectar
    con = conectar()
    rel = pd.read_sql("SELECT cups, descripcion_cups, codigo_iss FROM homologacion_cups", con)
    pr = pd.read_sql("SELECT codigo, descripcion FROM procedimientos WHERE tipo = 'con_valor' "
                     "ORDER BY id", con)
    rev = revisar(rel, pr)
    print(rev.tipo.value_counts().to_string())
    print(f"total: {len(rev)}; agregadas a homologacion.csv: {proponer_homologaciones(rev)}")
