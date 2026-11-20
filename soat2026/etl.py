"""Construye la base nueva del Manual Tarifario SOAT 2026 (UVB) desde soat2026/salida/items.csv.

Base: soat2026/salida/manual_soat_2026.db (SQLite, independiente de salida/manual_iss.db).

Estructura (normalizada):
  capitulos      I, II, III... con su título
  articulos      número, capítulo, nombre corto, texto, tipo de tarifa
  agrupadores    títulos y subtítulos de cada artículo (padre_id / nivel = ruta con sus hijos)
  procedimientos código, descripción, artículo, agrupador; grupo quirúrgico (cap. III) o
                 factores y valores en SMLDV, UVT y UVB (cap. IV y V)
  notas          parágrafos, notas, literales, textos y títulos de sección
  parametros     SMLMV, SMLDV, UVT y UVB que trae el PDF
  tarifas_grupo  por grupo quirúrgico: código y valor de cirujano, anestesiólogo, ayudante,
                 derechos de sala y materiales (arts. 48, 49 y 55), para el cotizador
  observaciones_pdf  valores del PDF que no cuadran (factor x unidad <> valor), para revisar
  validacion     resumen de controles; si alguno falla el ETL termina con error

Los ajustes manuales (clasificación de un texto, nivel de un agrupador...) van en
soat2026/ajustes.csv y quedan registrados en la tabla `ajustes`.

Uso: uv run soat2026/etl.py
"""
import csv
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import pdfplumber

BASE = Path(__file__).resolve().parent
SALIDA = BASE / "salida"
ITEMS = SALIDA / "items.csv"
AJUSTES = BASE / "ajustes.csv"
DB = SALIDA / "manual_soat_2026.db"
PDF = BASE.parent / "manual tarifario sota" / "Manual-Tarifario-SOAT-2026-uvb.pdf"
REF_GRUPOS = BASE.parent / "soat" / "soat_grupos.csv"        # control externo (Decreto 780, OCR)
REF_ISS_DB = BASE.parent / "salida" / "manual_iss.db"          # control externo (tabla SOAT 2026 .xlsb)

RE_ART = re.compile(r"^ART[IÍí]CULO\s*(\d+)\s*(?::-|:+|\.-|\.|-)?\s*-?\s*(.*)$", re.S)
RE_PAR = re.compile(r"^PAR[AÁ]GRAFO\s*(\d*)\s*[:.]?\s*(.*)$", re.S)
RE_NOTA = re.compile(r"^NOTA\s*:?\s*(.*)$", re.S)
RE_LIT = re.compile(r"^([a-j])\s*[.)]\s+(.*)$", re.S)
RE_NUM = re.compile(r"^(\d{1,2})\s*(?:\.-|\.|-)?\s+(\D.*)$", re.S)
RE_GRUPO_DESC = re.compile(r"^Grupos?\s+(?:especial\s+)?((?:\d{1,2}[\s-]*)+)$", re.I)   # "Grupo 02", "GRUPOS 04 - 05 - 06"
# Piezas que la relectura en flujo de texto no puede comprobar, revisadas a ojo en el PDF
RELECTURA_EXCEPCIONES = {
    ("1161", "Craniectomía"): "pág. 4: la descripción de 1161 se superpone con la de 1162 en el PDF "
                              "y el flujo de texto las mezcla; por coordenadas se leen bien",
}
RE_CITA = re.compile(r"^\d{5}\s+[A-ZÁÉÍÓÚ]")                                          # "02501 Extracción..."
RE_ENCABEZADO = re.compile(r"^C[ÓO]DIGO\s+DESCRIPCI[ÓO]N", re.I)                  # rótulos de tabla
GRUPOS_VALIDOS = set(range(1, 14)) | {20, 21, 22, 23}

# Nombre corto de los artículos cuyo texto no lo deja sacar con las reglas de nombre_articulo()
NOMBRES = {
    1: "Campo de aplicación", 2: "Definiciones", 22: "Anatomía patológica",
    3: "Neurocirugía", 7: "Cardiovascular", 8: "Tórax", 9: "Abdomen", 17: "Cirugía plástica",
    18: "Cirugía oral, maxilofacial y dental", 24: "Medicina nuclear", 25: "Nefrología y urología",
    33: "Ecografía, vasculares no invasivos y resonancia magnética",
    39: "Procedimientos diagnósticos y terapéuticos",
    40: "Estancia: servicios básicos", 41: "Estancia paciente crónico somático",
    42: "Estancia unidad de trasplante", 43: "Estancia unidad de cuidado intensivo",
    44: "Estancia unidad de cuidado intermedio", 45: "Estancia unidad de quemados",
    46: "Clasificación de instituciones por nivel", 47: "Tarifas de estancia",
    48: "Servicios profesionales", 49: "Derechos de sala de cirugía", 50: "Derechos de sala de parto",
    51: "Derechos de sala de recuperación", 52: "Intervenciones incruentas en sala",
    53: "Derechos de sala de yesos", 54: "Derechos de sala en urgencias y consulta externa",
    55: "Materiales de sutura y curación, medicamentos y gases", 56: "Drogas y medicamentos",
    57: "Prótesis, ortesis y otros suministros", 58: "Hemodiálisis y diálisis peritoneal",
    59: "Oxígeno", 60: "Unidades móviles de urgencias", 61: "Programas de grupos específicos",
    62: "Hospital de día psiquiátrico", 63: "Traslado en ambulancia", 64: "Conjuntos de atención integral",
    65: "Complicaciones de una intervención o procedimiento",
    66: "Municipios sin psicología, optometría, trabajo social o nutrición",
    67: "Examen anatomopatológico de la pieza quirúrgica", 68: "Suturas concomitantes con lesiones mayores",
    69: "Vía de acceso", 70: "Intervenciones bilaterales",
    71: "Intervenciones múltiples: mismo cirujano, igual vía", 72: "Intervenciones múltiples: mismo cirujano, diferente vía",
    73: "Intervenciones múltiples: cirujanos de distinta especialidad", 74: "Donante vivo o cadáver",
    75: "Consulta preanestésica, prequirúrgica y controles", 76: "Interconsulta",
    77: "Complicación médica del paciente quirúrgico", 78: "Fototerapia del recién nacido", 79: "Equipo de rayos láser",
    80: "Biopsias y endoscopias: servicios profesionales", 81: "Alcance de las tarifas de diagnóstico y tratamiento",
    82: "Especialistas en la unidad de quemados", 83: "Unidad de cuidado intermedio", 84: "Atención de urgencias",
    85: "Horas nocturnas, dominicales y festivos", 86: "Incremento por departamento o región",
    87: "Procedimientos sin tarifa definida", 88: "Vigencia", 89: "Ajuste a la centena",
}


# ------------------------------------------------------------------------------------- utilidades
def sin_tildes(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


def mayusculas(s):
    letras = [c for c in s if c.isalpha()]
    return bool(letras) and sum(c.isupper() for c in letras) / len(letras) >= 0.85


def num(v, tipo=float):
    return tipo(float(v)) if v not in ("", None) else None


def leer_items():
    with open(ITEMS, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["pagina"], r["top"], r["orden"] = int(r["pagina"]), float(r["top"]), int(r["orden"])
    return filas


def leer_ajustes():
    if not AJUSTES.exists():
        return []
    with open(AJUSTES, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("pagina")]


# ------------------------------------------------------------------- 1) líneas de texto -> bloques
def es_marcador(t):
    return bool(RE_ART.match(t) or RE_PAR.match(t) or RE_NOTA.match(t) or RE_LIT.match(t)
                or RE_NUM.match(t) or re.match(r"^CAP[IÍ]TULO", re.sub(r"\s", "", t)))


def bloques(items):
    """Une las líneas de texto consecutivas de un mismo párrafo o título."""
    out = []
    for it in items:
        if it["tipo"] != "texto":
            out.append(dict(it))
            continue
        t = it["texto"].strip()
        prev = out[-1] if out and out[-1]["tipo"] == "texto" else None
        unir = False
        if prev and not es_marcador(t) and not re.sub(r"\s", "", prev["texto"]).upper().startswith(("CAPITULO", "CAPÍTULO")):
            misma_pag = prev["pagina"] == it["pagina"]
            gap = it["top"] - prev["_ultimo_top"] if misma_pag else None
            if misma_pag and gap <= 7.6:
                unir = True                                   # mismo párrafo
            elif misma_pag and gap <= 11.5 and mayusculas(t) and mayusculas(prev["texto"]) \
                    and not prev["texto"].rstrip().endswith(":"):
                unir = True                                   # título en dos líneas
            elif not misma_pag and it["pagina"] == prev["pagina"] + 1 and it["top"] < 140 and not RE_CITA.match(t) \
                    and prev["_ultimo_top"] > 690 and not mayusculas(t) \
                    and not prev["texto"].rstrip().endswith((".", ":")):
                unir = True                                   # párrafo que sigue en la página siguiente
        if prev and not unir and (not es_marcador(t) or re.match(r"^\d{1,2}\s+[a-záéíóúñ]", t)):
            cerca = (prev["pagina"] == it["pagina"] and it["top"] - prev["_ultimo_top"] <= 20) or \
                    (it["pagina"] == prev["pagina"] + 1 and it["top"] < 140)
            if cerca and re.match(r"^(\d{1,2}\s+)?[a-záéíóúñ]", t) and not prev["texto"].rstrip().endswith("."):
                unir = True                                   # continuación en minúscula
            elif cerca and RE_CITA.match(t) and (prev["texto"].rstrip().endswith(":") or prev.get("_citas")):
                prev["texto"] = prev["texto"].rstrip() + ("\n" if not prev.get("_citas") else "; ") + t
                prev["_citas"], prev["_ultimo_top"] = True, it["top"]
                continue                                      # códigos citados en un parágrafo
        if unir:
            prev["texto"] = prev["texto"].rstrip() + " " + t
            prev["_ultimo_top"] = it["top"]
        else:
            b = dict(it)
            b["texto"], b["_ultimo_top"] = t, it["top"]
            out.append(b)
    return out


# ------------------------------------------------------------- 2) clasificación y jerarquía
def nombre_articulo(n, texto):
    if n in NOMBRES:
        return NOMBRES[n]
    m = re.search(r"(?:intervenciones|procedimientos)[^,]*?(?:especialidad(?:es)? de|de)\s+(?:la |las |los )?"
                  r"(.+?)\s*,?\s*la\s+siguiente", texto, re.I)
    if m:
        nombre = m.group(1)
    else:
        m = re.search(r"para\s+(?:los |las |el |la )?(?:estudios y |exámenes y |procedimientos de |"
                      r"procedimientos |exámenes de |estudios de |los )*(.+?)\s*,?\s*(?:son|tendrán)\b", texto, re.I)
        if m:
            nombre = m.group(1)
        else:
            m = re.match(r"^([A-ZÁÉÍÓÚÑ ,]{4,}):", texto)
            nombre = m.group(1).title() if m else texto[:70]
    m = re.match(r"^Los exámenes y procedimientos de (\w+)", texto)
    if m:
        nombre = m.group(1)
    nombre = re.sub(r"\s+", " ", nombre).strip(" .,:")
    return nombre[:1].upper() + nombre[1:]


def construir(items, ajustes):
    bl = bloques(items)
    # índice del siguiente elemento (para saber si a un título le siguen procedimientos)
    siguiente_es_proc = {}
    for i, b in enumerate(bl):
        j = i + 1
        while j < len(bl) and bl[j]["tipo"] == "texto" and bl[j]["texto"].startswith("("):
            j += 1
        siguiente_es_proc[i] = j < len(bl) and bl[j]["tipo"] == "procedimiento"
    # ¿el artículo tiene procedimientos después de la posición i?
    tiene_proc_despues = {}
    hay = False
    for i in range(len(bl) - 1, -1, -1):
        b = bl[i]
        if b["tipo"] == "procedimiento":
            hay = True
        tiene_proc_despues[i] = hay
        if b["tipo"] == "texto" and RE_ART.match(b["texto"]):
            hay = False
    siguiente_es_art = {i: i + 1 < len(bl) and bl[i + 1]["tipo"] == "texto" and bool(RE_ART.match(bl[i + 1]["texto"]))
                        for i in range(len(bl))}

    aj = {}   # (pagina, inicio del texto) -> ajuste
    for a in ajustes:
        aj.setdefault((int(a["pagina"]), a["texto_inicio"].strip()), []).append(a)
    usados = set()

    def ajustes_de(b):
        for (pag, ini), lista in aj.items():
            if pag == b["pagina"] and b["texto"].startswith(ini):
                usados.add((pag, ini))
                return lista
        return []

    capitulos, articulos, agrupadores, procs, notas, registro = [], {}, [], [], [], []
    cap = art = None
    pila = []            # agrupadores abiertos del artículo: [(rango, id)]
    orden = 0
    RANGO = {"literal": 1, "numerado": 2, "mayusculas": 3, "dos_puntos": 4}

    def nota(tipo, texto, b, numero=None, en_agrupador=True):
        if tipo in ("texto", "literal") and notas and notas[-1]["articulo"] == (art["numero"] if art else None) \
                and notas[-1]["tipo"] in ("paragrafo", "inciso", "literal") and notas[-1].get("_seguido") == orden - 1 \
                and (notas[-1]["tipo"] != "literal" or notas[-1].get("_de_paragrafo")):
            par = notas[-1].get("_paragrafo")
            if tipo == "texto":
                tipo, numero = "inciso", par
            en_agrupador = False
        else:
            par = numero if tipo == "paragrafo" else None
        notas.append({"id": len(notas) + 1, "tipo": tipo, "numero": numero, "texto": texto,
                      "capitulo_id": cap["id"] if cap else None, "articulo": art["numero"] if art else None,
                      "agrupador_id": pila[-1][1] if (pila and en_agrupador) else None,
                      "pagina": b["pagina"], "orden": orden, "_seguido": orden, "_paragrafo": par,
                      "_de_paragrafo": par is not None or tipo == "paragrafo"})

    titulo_seccion = None
    for i, b in enumerate(bl):
        orden += 1
        if b["tipo"] == "procedimiento":
            if art is None:
                raise SystemExit(f"procedimiento {b['codigo']} antes del primer artículo")
            procs.append({**b, "articulo": art["numero"], "agrupador_id": pila[-1][1] if pila else None,
                          "orden": orden})
            continue
        t = b["texto"]
        if RE_ENCABEZADO.match(t):
            continue
        forzado = None
        for a in ajustes_de(b):
            if a["accion"] == "tipo":
                forzado = a["valor"]
            registro.append({"pagina": b["pagina"], "texto_inicio": a["texto_inicio"], "accion": a["accion"],
                             "valor": a["valor"], "motivo": a["motivo"]})
        if forzado == "ignorar":
            continue
        compacto = re.sub(r"\s", "", t)
        m = re.match(r"^CAP[IÍ]TULO([IVX]+)$", compacto, re.I)
        if m:
            cap = {"id": len(capitulos) + 1, "numero": m.group(1).upper(), "titulo": "", "pagina": b["pagina"],
                   "orden": orden}
            capitulos.append(cap)
            art, pila = None, []
            continue
        m = RE_ART.match(t)
        if m and forzado is None:
            n = int(m.group(1))
            if n in articulos:
                raise SystemExit(f"artículo {n} repetido (pág. {b['pagina']})")
            art = {"numero": n, "capitulo_id": cap["id"] if cap else None, "texto": m.group(2).strip(),
                   "pagina": b["pagina"], "orden": orden}
            art["nombre"] = nombre_articulo(n, art["texto"])
            articulos[n] = art
            pila = []
            if titulo_seccion:
                tb, tt = titulo_seccion
                notas.append({"id": len(notas) + 1, "tipo": "titulo_seccion", "numero": None, "texto": tt,
                              "capitulo_id": cap["id"] if cap else None, "articulo": n, "agrupador_id": None,
                              "pagina": tb["pagina"], "orden": tb["_orden"]})
                titulo_seccion = None
            continue
        if cap and art is None and forzado is None and mayusculas(t):
            cap["titulo"] = (cap["titulo"] + " " + t).strip()     # título del capítulo
            continue
        if art is None:
            nota("preambulo", t, b, en_agrupador=False)
            continue
        m = RE_PAR.match(t)
        if m and forzado is None:
            nota("paragrafo", t, b, numero=m.group(1) or None, en_agrupador=False)
            continue
        if RE_NOTA.match(t) and forzado is None:
            nota("nota", t, b)
            continue
        # ¿título (agrupador)?
        clase = None
        ml, mn = RE_LIT.match(t), RE_NUM.match(t)
        if forzado in RANGO:
            clase = forzado
        elif forzado:
            clase = None
        elif t.startswith("(") and agrupadores and agrupadores[-1]["_i"] == i - 1:
            agrupadores[-1]["nombre"] += " " + t                  # "(Sin disección Ganglionar)"
            agrupadores[-1]["_i"] = i
            continue
        elif ml:
            if t.rstrip().endswith(":") and tiene_proc_despues[i]:
                clase = "literal"
        elif mn and len(t) <= 160:
            if (mayusculas(mn.group(2)) and tiene_proc_despues[i]) or t.rstrip().endswith(":") or siguiente_es_proc[i]:
                clase = "numerado"
        elif mayusculas(t) and len(t) <= 160:
            if siguiente_es_art[i]:
                titulo_seccion = (dict(b, _orden=orden), t)        # título de sección antes de un artículo
                continue
            if tiene_proc_despues[i]:
                clase = "mayusculas"
        elif t.rstrip().endswith(":") and siguiente_es_proc[i]:
            clase = "dos_puntos"
        if clase is None:
            tipo = forzado or ("literal" if ml else "titulo" if mayusculas(t) else "texto")
            nota(tipo, t, b, numero=ml.group(1) if ml else None)
            continue
        rango = RANGO[clase]
        while pila and pila[-1][0] >= rango:
            pila.pop()
        numeral = (ml.group(1) if ml and clase == "literal" else mn.group(1) if mn and clase == "numerado" else None)
        nombre = (ml.group(2) if numeral and ml else mn.group(2) if numeral and mn else t).strip()
        g = {"id": len(agrupadores) + 1, "articulo": art["numero"], "padre_id": pila[-1][1] if pila else None,
             "nivel": len(pila) + 1, "numeral": numeral, "nombre": nombre, "texto_pdf": t, "pagina": b["pagina"],
             "orden": orden, "clase": clase, "_i": i}
        agrupadores.append(g)
        pila.append((rango, g["id"]))
    sin_usar = [k for k in aj if k not in usados]
    return capitulos, list(articulos.values()), agrupadores, procs, notas, registro, sin_usar


# --------------------------------------------------------------------------------- 3) parámetros
def parametros():
    with pdfplumber.open(PDF) as pdf:
        t = pdf.pages[0].extract_text() or ""
    def busca(rx):
        m = re.search(rx, t)
        if not m:
            raise SystemExit(f"no se encontró en la portada: {rx}")
        return int(m.group(1).replace(".", ""))
    return [
        ("SMLMV", busca(r"SMLV\s*\$\s*([\d.]+)"), "Salario mínimo legal mensual vigente 2026", "Decreto 1469 de 2025 (portada del PDF)"),
        ("SMLDV", busca(r"VALOR DIARIO\s*\$\s*([\d.]+)"), "Salario mínimo legal diario vigente 2026", "Portada del PDF"),
        ("UVT", busca(r"UVT 20\d\d\s*\$\s*([\d.]+)"), "Unidad de valor tributario (columna «UVT 2026» del PDF)", "Portada del PDF"),
        ("UVB", busca(r"UVB 20\d\d\s*\$\s*([\d.]+)"), "Unidad de valor básico 2026: tarifa oficial SOAT 2026", "Portada del PDF; Decreto 2644 de 2022"),
    ]


# ------------------------------------------------------------------------------ 4) base de datos
ESQUEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE parametros (concepto TEXT PRIMARY KEY, valor REAL NOT NULL, descripcion TEXT, fuente TEXT);
CREATE TABLE capitulos (
    id INTEGER PRIMARY KEY, numero TEXT NOT NULL UNIQUE, titulo TEXT, pagina INTEGER, orden INTEGER);
CREATE TABLE articulos (
    numero INTEGER PRIMARY KEY, capitulo_id INTEGER NOT NULL REFERENCES capitulos(id),
    nombre TEXT NOT NULL, texto TEXT, tipo_tarifa TEXT CHECK (tipo_tarifa IN ('grupo_quirurgico','smldv_uvt_uvb')),
    n_procedimientos INTEGER NOT NULL DEFAULT 0, pagina INTEGER, orden INTEGER);
CREATE TABLE agrupadores (
    id INTEGER PRIMARY KEY, articulo INTEGER NOT NULL REFERENCES articulos(numero),
    padre_id INTEGER REFERENCES agrupadores(id), nivel INTEGER NOT NULL, numeral TEXT, nombre TEXT NOT NULL,
    texto_pdf TEXT, pagina INTEGER, orden INTEGER);
CREATE TABLE procedimientos (
    id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, descripcion TEXT NOT NULL, descripcion_busqueda TEXT,
    articulo INTEGER NOT NULL REFERENCES articulos(numero), agrupador_id INTEGER REFERENCES agrupadores(id),
    grupo_quirurgico INTEGER,
    factor_smldv REAL, valor_smldv INTEGER, factor_uvt REAL, valor_uvt INTEGER, factor_uvb REAL, valor_uvb INTEGER,
    pagina INTEGER, orden INTEGER,
    CHECK (grupo_quirurgico IS NOT NULL OR factor_uvb IS NOT NULL OR valor_uvb IS NOT NULL OR factor_smldv IS NOT NULL));
CREATE TABLE notas (
    id INTEGER PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('preambulo','paragrafo','inciso','nota','literal','texto','titulo','titulo_seccion')),
    numero TEXT, texto TEXT NOT NULL, capitulo_id INTEGER REFERENCES capitulos(id),
    articulo INTEGER REFERENCES articulos(numero), agrupador_id INTEGER REFERENCES agrupadores(id),
    pagina INTEGER, orden INTEGER);
CREATE TABLE tarifas_grupo (
    concepto TEXT NOT NULL, grupo INTEGER NOT NULL, procedimiento_id INTEGER NOT NULL REFERENCES procedimientos(id),
    PRIMARY KEY (concepto, grupo));
CREATE TABLE observaciones_pdf (
    id INTEGER PRIMARY KEY, codigo TEXT, pagina INTEGER, campo TEXT, valor_pdf TEXT, esperado TEXT, detalle TEXT);
CREATE TABLE ajustes (id INTEGER PRIMARY KEY, pagina INTEGER, texto_inicio TEXT, accion TEXT, valor TEXT, motivo TEXT);
CREATE TABLE validacion (control TEXT PRIMARY KEY, resultado TEXT NOT NULL, detalle TEXT);
CREATE INDEX ix_proc_articulo ON procedimientos(articulo);
CREATE INDEX ix_proc_agrupador ON procedimientos(agrupador_id);
CREATE INDEX ix_agr_padre ON agrupadores(padre_id);
CREATE INDEX ix_notas_articulo ON notas(articulo);
"""

VISTAS = """
CREATE VIEW v_agrupadores_ruta AS
WITH RECURSIVE r(id, articulo, nivel, nombre, ruta, raiz_id) AS (
    SELECT id, articulo, nivel, nombre, nombre, id FROM agrupadores WHERE padre_id IS NULL
    UNION ALL
    SELECT a.id, a.articulo, a.nivel, a.nombre, r.ruta || ' > ' || a.nombre, r.raiz_id
    FROM agrupadores a JOIN r ON a.padre_id = r.id)
SELECT r.id AS agrupador_id, r.articulo, r.nivel, r.nombre, r.ruta, r.raiz_id,
       (SELECT COUNT(*) FROM agrupadores h WHERE h.padre_id = r.id) AS n_hijos,
       (SELECT COUNT(*) FROM procedimientos p WHERE p.agrupador_id = r.id) AS n_procedimientos
FROM r;

CREATE VIEW v_tarifas AS
SELECT c.numero AS capitulo, a.numero AS articulo, a.nombre AS articulo_nombre, ar.ruta AS agrupador_ruta,
       p.codigo, p.descripcion, p.grupo_quirurgico,
       p.factor_smldv, p.valor_smldv, p.factor_uvt, p.valor_uvt, p.factor_uvb, p.valor_uvb,
       p.pagina, p.id AS procedimiento_id, p.agrupador_id, p.descripcion_busqueda, p.orden
FROM procedimientos p
JOIN articulos a ON a.numero = p.articulo
JOIN capitulos c ON c.id = a.capitulo_id
LEFT JOIN v_agrupadores_ruta ar ON ar.agrupador_id = p.agrupador_id;

CREATE VIEW v_cirugias AS
SELECT t.capitulo, t.articulo, t.articulo_nombre, t.agrupador_ruta, t.codigo, t.descripcion, t.grupo_quirurgico,
       (SELECT q.valor_uvb FROM tarifas_grupo g JOIN procedimientos q ON q.id = g.procedimiento_id
         WHERE g.grupo = t.grupo_quirurgico AND g.concepto = 'cirujano') AS cirujano_uvb,
       (SELECT q.valor_uvb FROM tarifas_grupo g JOIN procedimientos q ON q.id = g.procedimiento_id
         WHERE g.grupo = t.grupo_quirurgico AND g.concepto = 'anestesiologo') AS anestesiologo_uvb,
       (SELECT q.valor_uvb FROM tarifas_grupo g JOIN procedimientos q ON q.id = g.procedimiento_id
         WHERE g.grupo = t.grupo_quirurgico AND g.concepto = 'ayudante') AS ayudante_uvb,
       (SELECT q.valor_uvb FROM tarifas_grupo g JOIN procedimientos q ON q.id = g.procedimiento_id
         WHERE g.grupo = t.grupo_quirurgico AND g.concepto = 'sala') AS sala_uvb,
       (SELECT q.valor_uvb FROM tarifas_grupo g JOIN procedimientos q ON q.id = g.procedimiento_id
         WHERE g.grupo = t.grupo_quirurgico AND g.concepto = 'materiales') AS materiales_uvb,
       t.pagina
FROM v_tarifas t WHERE t.grupo_quirurgico IS NOT NULL;

CREATE VIEW v_tarifas_grupo AS
SELECT g.grupo, g.concepto, p.codigo, p.descripcion, p.factor_uvb, p.valor_uvb, p.valor_smldv, p.articulo, p.pagina
FROM tarifas_grupo g JOIN procedimientos p ON p.id = g.procedimiento_id;

CREATE VIEW v_notas AS
SELECT n.id, n.tipo, n.numero, c.numero AS capitulo, n.articulo, a.nombre AS articulo_nombre,
       ar.ruta AS agrupador_ruta, n.texto, n.pagina
FROM notas n LEFT JOIN capitulos c ON c.id = n.capitulo_id
LEFT JOIN articulos a ON a.numero = n.articulo
LEFT JOIN v_agrupadores_ruta ar ON ar.agrupador_id = n.agrupador_id;

CREATE VIEW v_articulos AS
SELECT c.numero AS capitulo, c.titulo AS capitulo_titulo, a.numero AS articulo, a.nombre, a.tipo_tarifa,
       a.n_procedimientos,
       (SELECT COUNT(*) FROM agrupadores g WHERE g.articulo = a.numero) AS n_agrupadores,
       (SELECT COUNT(*) FROM notas n WHERE n.articulo = a.numero AND n.tipo = 'paragrafo') AS n_paragrafos,
       a.texto, a.pagina
FROM articulos a JOIN capitulos c ON c.id = a.capitulo_id;

CREATE VIEW v_manual_completo AS
SELECT orden, 'capitulo' AS elemento, numero AS capitulo, NULL AS articulo, NULL AS nivel, NULL AS codigo,
       'CAPÍTULO ' || numero || COALESCE(' - ' || NULLIF(titulo, ''), '') AS texto,
       NULL AS grupo_quirurgico, NULL AS factor_uvb, NULL AS valor_uvb, pagina
FROM capitulos
UNION ALL
SELECT a.orden, 'articulo', c.numero, a.numero, NULL, NULL, 'ARTÍCULO ' || a.numero || ': ' || a.texto,
       NULL, NULL, NULL, a.pagina
FROM articulos a JOIN capitulos c ON c.id = a.capitulo_id
UNION ALL
SELECT g.orden, 'agrupador', c.numero, g.articulo, g.nivel, NULL,
       COALESCE(g.numeral || '. ', '') || g.nombre, NULL, NULL, NULL, g.pagina
FROM agrupadores g JOIN articulos a ON a.numero = g.articulo JOIN capitulos c ON c.id = a.capitulo_id
UNION ALL
SELECT p.orden, 'procedimiento', c.numero, p.articulo, NULL, p.codigo, p.descripcion,
       p.grupo_quirurgico, p.factor_uvb, p.valor_uvb, p.pagina
FROM procedimientos p JOIN articulos a ON a.numero = p.articulo JOIN capitulos c ON c.id = a.capitulo_id
UNION ALL
SELECT n.orden, n.tipo, c.numero, n.articulo, NULL, NULL, n.texto, NULL, NULL, NULL, n.pagina
FROM notas n LEFT JOIN capitulos c ON c.id = n.capitulo_id;

CREATE VIEW v_validacion AS SELECT * FROM validacion;
CREATE VIEW v_observaciones_pdf AS SELECT * FROM observaciones_pdf;
"""


def concepto_de(articulo, ruta):
    if articulo == 49:
        return "sala"
    if articulo == 55:
        return "materiales"
    if articulo != 48:
        return None
    r = sin_tildes(ruta)
    if "CIRUJANO" in r:
        return "cirujano"
    if "ANESTESIOLOGO" in r and "EXAMENES" not in r:
        return "anestesiologo"
    if "AYUDANTIA" in r:
        return "ayudante"
    return None


def escribir(capitulos, articulos, agrupadores, procs, notas, registro, params):
    SALIDA.mkdir(exist_ok=True)
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript(ESQUEMA)
    con.executemany("INSERT INTO parametros VALUES (?,?,?,?)", params)
    con.executemany("INSERT INTO capitulos VALUES (:id,:numero,:titulo,:pagina,:orden)", capitulos)
    for a in articulos:
        ps = [p for p in procs if p["articulo"] == a["numero"]]
        a["n_procedimientos"] = len(ps)
        a["tipo_tarifa"] = ("grupo_quirurgico" if ps and all(p["grupo"] for p in ps)
                            else "smldv_uvt_uvb" if ps else None)
    con.executemany("INSERT INTO articulos VALUES (:numero,:capitulo_id,:nombre,:texto,:tipo_tarifa,"
                    ":n_procedimientos,:pagina,:orden)", articulos)
    con.executemany("INSERT INTO agrupadores VALUES (:id,:articulo,:padre_id,:nivel,:numeral,:nombre,:texto_pdf,"
                    ":pagina,:orden)", agrupadores)
    filas = []
    for i, p in enumerate(procs, 1):
        p["id"] = i
        filas.append((i, p["codigo"], p["descripcion"], sin_tildes(p["descripcion"]), p["articulo"], p["agrupador_id"],
                      num(p["grupo"], int), num(p["f_smldv"]), num(p["v_smldv"], int), num(p["f_uvt"]),
                      num(p["v_uvt"], int), num(p["f_uvb"]), num(p["v_uvb"], int), p["pagina"], p["orden"]))
    con.executemany("INSERT INTO procedimientos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", filas)
    con.executemany("INSERT INTO notas VALUES (:id,:tipo,:numero,:texto,:capitulo_id,:articulo,:agrupador_id,"
                    ":pagina,:orden)", notas)
    con.executemany("INSERT INTO ajustes (pagina,texto_inicio,accion,valor,motivo) VALUES "
                    "(:pagina,:texto_inicio,:accion,:valor,:motivo)", registro)
    con.executescript(VISTAS)
    # tarifas por grupo quirúrgico (descripciones "Grupo 02" ... "Grupo especial 23")
    for pid, art, desc, ruta in con.execute(
            "SELECT p.id, p.articulo, p.descripcion, COALESCE(r.ruta,'') FROM procedimientos p "
            "LEFT JOIN v_agrupadores_ruta r ON r.agrupador_id = p.agrupador_id").fetchall():
        m = RE_GRUPO_DESC.match(desc.strip())
        c = concepto_de(art, ruta) if m else None
        if c:
            for g in re.findall(r"\d+", m.group(1)):
                con.execute("INSERT INTO tarifas_grupo VALUES (?,?,?)", (c, int(g), pid))
    con.commit()
    return con, tmp


# ------------------------------------------------------------------------------- 5) validaciones
def validar(con, sin_usar):
    p = dict(con.execute("SELECT concepto, valor FROM parametros").fetchall())
    obs, ctl = [], []

    def control(nombre, ok, detalle):
        ctl.append((nombre, "OK" if ok else "FALLA", detalle))

    # aritmética del PDF: factor x unidad, redondeado a la centena (art. 89), contra el valor impreso
    # proporción factor UVB / factor SMLDV: es la misma en toda la tabla (mediana)
    props = sorted(fb / fs for fs, fb in con.execute(
        "SELECT factor_smldv, factor_uvb FROM procedimientos WHERE factor_smldv >= 1 AND factor_uvb > 0"))
    esperada = props[len(props) // 2]
    revisados = 0
    for cod, pag, *v in con.execute("SELECT codigo, pagina, factor_smldv, valor_smldv, factor_uvt, valor_uvt, "
                                    "factor_uvb, valor_uvb, grupo_quirurgico FROM procedimientos"):
        fs, vs, fu, vu, fb, vb, grupo = v
        if grupo is not None:
            continue
        revisados += 1
        for campo, f, val, unidad in (("smldv", fs, vs, p["SMLDV"]), ("uvt", fu, vu, p["UVT"]), ("uvb", fb, vb, p["UVB"])):
            if f is None or val is None:
                obs.append((cod, pag, campo, f"factor={f} valor={val}", "", "sin factor o sin valor en el PDF"))
                continue
            esperado = round(f * unidad, -2)
            if abs(esperado - val) > 100 + 0.005 * unidad:      # el factor impreso va redondeado a 2 decimales
                obs.append((cod, pag, campo, f"{val}", f"{esperado:.0f}", f"factor {f} x {unidad} no da el valor impreso"))
        if fs is not None and fb is not None and fs >= 1:
            prop = fb / fs
            if abs(prop - esperada) / esperada > 0.02:
                obs.append((cod, pag, "uvb/smldv", f"{prop:.3f}", f"{esperada:.3f}",
                            "el factor UVB no corresponde al factor SMLDV"))
    con.executemany("INSERT INTO observaciones_pdf (codigo,pagina,campo,valor_pdf,esperado,detalle) VALUES (?,?,?,?,?,?)", obs)

    n = lambda sql: con.execute(sql).fetchone()[0]
    control("procedimientos", n("SELECT COUNT(*) FROM procedimientos") > 3000,
            f"{n('SELECT COUNT(*) FROM procedimientos')} procedimientos, códigos únicos")
    arts = [r[0] for r in con.execute("SELECT numero FROM articulos ORDER BY numero")]
    faltan = sorted(set(range(1, 90)) - set(arts))
    control("articulos 1-89", not faltan, f"{len(arts)} artículos" + (f"; faltan {faltan}" if faltan else ""))
    malos = n(f"SELECT COUNT(*) FROM procedimientos WHERE grupo_quirurgico IS NOT NULL AND grupo_quirurgico NOT IN "
              f"({','.join(map(str, sorted(GRUPOS_VALIDOS)))})")
    control("grupos quirúrgicos válidos", malos == 0, f"{n('SELECT COUNT(*) FROM procedimientos WHERE grupo_quirurgico IS NOT NULL')} "
            f"con grupo; {malos} fuera de 1-13 y 20-23")
    mezcla = n("SELECT COUNT(*) FROM procedimientos WHERE grupo_quirurgico IS NOT NULL AND valor_uvb IS NOT NULL")
    control("grupo o valor, no ambos", mezcla == 0, f"{mezcla} con grupo y valor a la vez")
    cap3 = n("SELECT COUNT(*) FROM procedimientos p JOIN articulos a ON a.numero=p.articulo "
             "WHERE a.numero BETWEEN 3 AND 20 AND p.grupo_quirurgico IS NULL")
    control("cap. III con grupo", cap3 == 0, f"{cap3} procedimientos de los arts. 3-20 sin grupo")
    sin_agr = n("SELECT COUNT(*) FROM procedimientos WHERE agrupador_id IS NULL")
    control("procedimientos con agrupador", True, f"{sin_agr} sin agrupador (cuelgan directo del artículo)")
    otro_art = n("SELECT COUNT(*) FROM procedimientos p JOIN agrupadores g ON g.id=p.agrupador_id WHERE g.articulo<>p.articulo")
    control("agrupador del mismo artículo", otro_art == 0, f"{otro_art} inconsistentes")
    vacios = n("SELECT COUNT(*) FROM v_agrupadores_ruta WHERE n_hijos = 0 AND n_procedimientos = 0")
    control("agrupadores con contenido", vacios == 0, f"{vacios} agrupadores sin hijos ni procedimientos")
    tg = n("SELECT COUNT(*) FROM tarifas_grupo")
    conceptos = dict(con.execute("SELECT concepto, COUNT(*) FROM tarifas_grupo GROUP BY concepto").fetchall())
    control("tarifas por grupo", all(conceptos.get(c, 0) >= 12 for c in ("cirujano", "anestesiologo", "ayudante", "sala", "materiales")),
            f"{tg} filas: {conceptos}")
    control("ajustes aplicados", not sin_usar, "todos" if not sin_usar else f"sin coincidencia: {sin_usar}")
    control("proporción UVB/SMLDV", True, f"mediana {esperada:.4f}")
    control("aritmética del PDF", True, f"{revisados} procedimientos con valores; {len(obs)} observaciones "
            "(diferencias del propio PDF, ver v_observaciones_pdf)")

    # controles externos (opcionales): grupos del Decreto 780 y tabla SOAT 2026 del proyecto ISS
    if REF_GRUPOS.exists():
        with open(REF_GRUPOS, encoding="utf-8") as f:
            ref = {r["codigo"]: int(r["grupo"]) for r in csv.DictReader(f)}
        bd = dict(con.execute("SELECT codigo, grupo_quirurgico FROM procedimientos WHERE grupo_quirurgico IS NOT NULL"))
        comunes = set(ref) & set(bd)
        dif = sorted(c for c in comunes if ref[c] != bd[c])
        for c in dif:
            con.execute("INSERT INTO observaciones_pdf (codigo,pagina,campo,valor_pdf,esperado,detalle) "
                        "SELECT codigo, pagina, 'grupo', ?, ?, 'grupo distinto al del Decreto 780 (soat/soat_grupos.csv)' "
                        "FROM procedimientos WHERE codigo=?", (bd[c], ref[c], c))
        control("grupos vs Decreto 780", True, f"{len(comunes)} códigos en común, {len(dif)} con grupo distinto; "
                f"{len(set(bd) - set(ref))} solo en este PDF, {len(set(ref) - set(bd))} solo en el decreto")
    if REF_ISS_DB.exists():
        ext = sqlite3.connect(f"file:{REF_ISS_DB}?mode=ro", uri=True)
        try:
            ref = dict(ext.execute("SELECT codigo, factor_uvb FROM soat_tarifas"))
        except sqlite3.Error:
            ref = {}
        ext.close()
        if ref:
            bd = dict(con.execute("SELECT codigo, factor_uvb FROM procedimientos WHERE factor_uvb IS NOT NULL"))
            comunes = set(ref) & set(bd)
            dif = sorted(c for c in comunes if abs((ref[c] or 0) - bd[c]) > 0.011)
            for c in dif:
                con.execute("INSERT INTO observaciones_pdf (codigo,pagina,campo,valor_pdf,esperado,detalle) "
                            "SELECT codigo, pagina, 'factor_uvb', ?, ?, 'factor UVB distinto al de la tabla SOAT 2026 (.xlsb)' "
                            "FROM procedimientos WHERE codigo=?", (bd[c], ref[c], c))
            control("factor UVB vs tabla SOAT 2026", True, f"{len(comunes)} códigos en común, {len(dif)} distintos; "
                    f"{len(set(bd) - set(ref))} solo en este PDF, {len(set(ref) - set(bd))} solo en la tabla")
    # control independiente: el texto de cada página leído de otra forma (flujo de texto, sin
    # coordenadas) debe contener el código, el inicio de la descripción y los valores de la BD
    with pdfplumber.open(PDF) as pdf:
        paginas = {i: re.sub(r"\s", "", pg.extract_text() or "") for i, pg in enumerate(pdf.pages, 1)}
        tokens = [w["text"] for pg in pdf.pages for w in pg.extract_words()
                  if re.fullmatch(r"\d{4,6}", w["text"]) and w["x0"] < 66 and 112 < w["top"] < 776]
    # cobertura: todo código del margen izquierdo es un procedimiento o está citado en una nota
    codigos_bd = {r[0] for r in con.execute("SELECT codigo FROM procedimientos")}
    citas = " ".join(r[0] for r in con.execute("SELECT texto FROM notas"))
    sueltos = [t for t in tokens if t not in codigos_bd and t not in citas]
    control("cobertura de códigos", not sueltos and len(tokens) >= len(codigos_bd),
            f"{len(tokens)} códigos en el margen izquierdo del PDF: {len(codigos_bd)} procedimientos y "
            f"{len(tokens) - len(codigos_bd)} citados en notas" + (f"; sin ubicar: {sueltos}" if sueltos else ""))
    fallas = []
    for cod, desc, pag, fb, vb, fs in con.execute(
            "SELECT codigo, descripcion, pagina, factor_uvb, valor_uvb, factor_smldv FROM procedimientos"):
        txt = paginas[pag]
        piezas = [cod, re.sub(r"\s", "", desc)[:12]]
        if vb:
            piezas.append(f"{vb:,}".replace(",", "."))
        falta = [x for x in piezas if x not in txt and (cod, x) not in RELECTURA_EXCEPCIONES]
        if fb:
            formas = {f"{fb:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".") for d in (0, 1, 2, 3)}
            if not any(f in txt for f in formas):
                falta.append(sorted(formas)[0])
        if falta:
            fallas.append(f"{cod} (pág {pag}): {falta}")
    control("relectura del PDF", not fallas, f"{len(paginas)} páginas releídas; "
            + (f"{len(fallas)} procedimientos con piezas que no aparecen: {fallas[:5]}" if fallas else
               "código, descripción, factor y valor UVB de todos los procedimientos aparecen en su página"))
    con.executemany("INSERT INTO validacion VALUES (?,?,?)", ctl)
    con.commit()
    return ctl


def main():
    if not ITEMS.exists():
        sys.exit("Falta soat2026/salida/items.csv: ejecute primero uv run soat2026/extraer.py")
    items = leer_items()
    capitulos, articulos, agrupadores, procs, notas, registro, sin_usar = construir(items, leer_ajustes())
    con, tmp = escribir(capitulos, articulos, agrupadores, procs, notas, registro, parametros())
    ctl = validar(con, sin_usar)
    con.close()
    tmp.replace(DB)
    ancho = max(len(c[0]) for c in ctl)
    for nombre, res, det in ctl:
        print(f"  {res:5s} {nombre:{ancho}s}  {det}")
    print(f"BD: {DB}")
    print(f"capítulos {len(capitulos)}, artículos {len(articulos)}, agrupadores {len(agrupadores)}, "
          f"procedimientos {len(procs)}, notas {len(notas)}")
    if any(r == "FALLA" for _, r, _ in ctl):
        sys.exit("Hay controles con FALLA")


if __name__ == "__main__":
    main()
