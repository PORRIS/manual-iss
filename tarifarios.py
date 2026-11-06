"""Tarifarios distintos del Manual ISS 2001: SOAT 2026 y tarifas propias (tablas aparte).

Fuentes (se leen tal cual, sin modificarlas):
- soat/SOAT A SALARIO MINIMO_UVT_UVB.xlsx: hoja TABLA (código SOAT, descripción, factores SMLV,
  UVT y UVB 2026) y hoja TD (valor de la UVB, UVT y SMLV 2026 con su norma).
- soat/CUPS A SOAT_ANDER_OKANDER.xlsb: relación CUPS -> código SOAT (un CUPS puede tener varios).
Las tarifas propias no están aquí: son manuales versionados que se suben desde la web o la
consola (tarifas_propias.py) y se guardan en su propia base (TARIFAS_DB_URL).

Tablas (prefijo soat_, con llaves primarias y foráneas):
    tarifarios(id PK)                         catálogo: iss, soat, propia
    soat_parametros(concepto PK)              UVB, UVT, SMLV, SMLDV 2026
    soat_procedimientos(codigo PK)            todos los códigos SOAT (de la tabla y de la relación)
    soat_tarifas(codigo PK -> soat_procedimientos)          factores y valor 2026 = factor UVB x UVB
    soat_relacion_cups(cups, codigo_soat -> soat_procedimientos; PK cups+codigo_soat)

Cirugía SOAT (Decreto 780 de 2016, anexo técnico 1): cada procedimiento quirúrgico tiene un grupo
(02 a 13 y especiales 20 a 23) y su valor es la suma de los componentes de ese grupo:
    soat_grupos(codigo PK -> soat_procedimientos, grupo)   soat/soat_grupos.csv (extraer_soat_grupos.py)
    soat_grupo_componentes(grupo, componente; codigo_tarifa -> soat_tarifas)
        cirujano 39000-39015, anestesiologo 39100-39115, ayudante 39117-39128 (grupo 06 en
        adelante), sala 39204-39219, materiales 39301-39304 (grupos 02 a 13; en 20 a 23 se pagan a
        precio de catálogo, num. 54.2)
    soat_reglas_cirugia(regla PK): porcentajes de bilaterales y cirugías múltiples (num. 48.2,
        54.5, 69 a 72)
"""
import re
import warnings

import pandas as pd

from rutas import BASE

SOAT_TABLA = BASE / "soat" / "SOAT A SALARIO MINIMO_UVT_UVB.xlsx"
SOAT_RELACION = BASE / "soat" / "CUPS A SOAT_ANDER_OKANDER.xlsb"
SOAT_GRUPOS = BASE / "soat" / "soat_grupos.csv"
# Series de la tabla SOAT 2026 con la tarifa de cada componente por grupo (num. 47, 48 y 54)
SERIES_CIRUGIA = {"cirujano": (39000, 39015), "anestesiologo": (39100, 39115),
                  "ayudante": (39117, 39128), "sala": (39204, 39219), "materiales": (39301, 39304)}
GRUPOS_SOAT = list(range(2, 14)) + list(range(20, 24))
UVB_REFERENCIA = 12110.0  # UVB 2026: los índices de auditoría guardan los valores a esta UVB
# Tarifas de los componentes de cirugía en el Decreto 780 de 2016 (SMLDV), leídas del PDF
# (tablas 47.1.1, 47.1.2, 47.1.4, 48.1.1 y 54.1.1, págs. 116-121). Sirven para completar un
# componente que falte en una tabla SOAT: factor UVB = SMLDV x (UVB/SMLDV de esa misma tabla).
_G = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13",
      "especial 20", "especial 21", "especial 22", "especial 23"]
DECRETO_SMLDV = {
    **{str(39000 + i): (f"Grupo {g}", v) for i, (g, v) in enumerate(zip(_G, (
        2.93, 3.57, 4.31, 5.86, 7.68, 9.00, 10.44, 12.76, 15.71, 17.62, 19.63, 21.48, 25.43, 33.10,
        38.67, 60.73)))},
    **{str(39100 + i): (f"Grupo {g}", v) for i, (g, v) in enumerate(zip(_G, (
        2.09, 2.53, 3.10, 3.83, 4.56, 5.30, 6.17, 7.30, 9.02, 10.08, 11.44, 12.72, 14.85, 20.12,
        26.82, 37.95)))},
    **{str(39117 + i): (f"Grupo {g}", v) for i, (g, v) in enumerate(zip(_G[4:], (
        2.01, 2.37, 2.74, 3.49, 4.28, 4.83, 5.36, 6.17, 6.94, 9.03, 10.55, 16.57)))},
    **{str(39204 + i): (f"Grupo {g}", v) for i, (g, v) in enumerate(zip(_G, (
        4.84, 5.97, 7.61, 10.45, 15.13, 16.88, 18.51, 21.10, 28.08, 29.95, 31.47, 33.16, 34.82,
        36.51, 38.34, 48.07)))},
    "39301": ("GRUPOS 02 - 03", 2.28), "39302": ("GRUPOS 04 - 05 - 06", 4.27),
    "39303": ("GRUPOS 07 - 08 - 09", 9.92), "39304": ("GRUPOS 10 - 11 - 12 - 13", 15.72),
}


def completar_componentes(tar):
    """Agrega a la tabla SOAT los componentes de cirugía que le falten (p. ej. la sala del grupo 03,
    39205, que no trae la tabla 2026), calculados con la proporción UVB/SMLDV de la misma tabla
    (mediana sobre los componentes que sí tiene). Columna origen: 'tabla' o 'calculado'."""
    tar = tar.copy()
    if "origen" not in tar.columns:
        tar["origen"] = "tabla"
    tiene = dict(zip(tar.codigo, tar.factor_uvb))
    razones = sorted(tiene[k] / v for k, (_, v) in DECRETO_SMLDV.items() if k in tiene and tiene[k])
    if not razones:
        return tar, []
    razon = razones[len(razones) // 2]
    nuevas = [dict(codigo=k, descripcion=d, factor_uvb=round(v * razon, 2), factor_uvt=None,
                   factor_smlv=None, origen=f"calculado: {v:g} SMLDV (Decreto 780) x {razon:.4f} UVB/SMLDV")
              for k, (d, v) in DECRETO_SMLDV.items() if k not in tiene]
    if nuevas:
        tar = pd.concat([tar, pd.DataFrame(nuevas)], ignore_index=True)
    return tar, [n["codigo"] for n in nuevas]
REGLAS_CIRUGIA = [  # regla, numeral, página PDF, componente, porcentaje, texto
    ("BIL_HON", "69", 130, "honorarios", 75, "Intervención bilateral: +75% en servicios profesionales de cirujano, anestesiólogo y ayudante"),
    ("BIL_SALA", "48.2", 120, "sala", 50, "Intervención bilateral: +50% en derechos de sala"),
    ("BIL_MAT", "54.5", 122, "materiales", 75, "Intervención bilateral: +75% en materiales"),
    ("MUL_MISMA_VIA", "70", 131, "honorarios", 50, "Múltiples, mismo cirujano, igual vía: 100% de la mayor + 50% de cada adicional (honorarios)"),
    ("MUL_OTRA_VIA", "71", 131, "honorarios", 75, "Múltiples, mismo cirujano, diferente vía: 100% de la mayor + 75% de cada adicional (honorarios)"),
    ("MUL_ESPECIALIDAD", "72", 131, "honorarios", 50, "Múltiples, distinta especialidad: cada cirujano 100% de su mayor + 50% de las adicionales; anestesiólogo +75% (72.1); ayudante +50% solo de la adicional de mayor grupo (72.2)"),
    ("MUL_SALA", "48.2", 120, "sala", 50, "Múltiples en distinta región operatoria o de distinta especialidad: sala 100% de la mayor + 50% de cada adicional"),
    ("MUL_MAT", "54.5", 122, "materiales", 75, "Múltiples en diferente región operatoria: materiales 100% de la mayor + 75% de cada adicional"),
    ("MAT_ESPECIALES", "54.2", 121, "materiales", None, "Grupos especiales 20 a 23: materiales a precio comercial de catálogo (no tienen tarifa fija)"),
    ("AYUDANTE", "47.1.4", 117, "ayudante", None, "Ayudantía solo cuando la cirugía lo requiera (tabla desde el grupo 06)"),
]

DDL = """
CREATE TABLE tarifarios (
    id TEXT PRIMARY KEY, nombre TEXT NOT NULL, vigencia TEXT, unidad TEXT, fuente TEXT,
    descripcion TEXT);
CREATE TABLE soat_parametros (
    concepto TEXT PRIMARY KEY, valor REAL, valor_texto TEXT, equivalencia TEXT, uso TEXT,
    norma TEXT, entidad TEXT, observacion TEXT);
CREATE TABLE soat_procedimientos (
    codigo TEXT PRIMARY KEY, descripcion TEXT, fuente TEXT NOT NULL);
CREATE TABLE soat_tarifas (
    codigo TEXT PRIMARY KEY REFERENCES soat_procedimientos(codigo),
    descripcion TEXT, factor_smlv REAL, factor_uvt REAL, factor_uvb REAL NOT NULL,
    valor_2026 REAL NOT NULL, origen TEXT);
CREATE TABLE soat_grupos (
    codigo TEXT PRIMARY KEY REFERENCES soat_procedimientos(codigo), grupo INTEGER NOT NULL,
    pagina_pdf INTEGER, confianza TEXT);
CREATE TABLE soat_grupo_componentes (
    grupo INTEGER NOT NULL, componente TEXT NOT NULL,
    codigo_tarifa TEXT NOT NULL REFERENCES soat_tarifas(codigo), PRIMARY KEY (grupo, componente));
CREATE TABLE soat_reglas_cirugia (
    regla TEXT PRIMARY KEY, numeral TEXT, pagina_pdf INTEGER, componente TEXT, porcentaje REAL,
    texto TEXT);
CREATE TABLE soat_relacion_cups (
    cups TEXT NOT NULL, nombre_cups TEXT,
    codigo_soat TEXT NOT NULL REFERENCES soat_procedimientos(codigo), descripcion_soat TEXT,
    PRIMARY KEY (cups, codigo_soat));
CREATE INDEX ix_soat_rel_soat ON soat_relacion_cups(codigo_soat);
"""


def _codigo(v):
    """Texto del código sin '.0' de Excel ni espacios."""
    s = re.sub(r"\.0$", "", str(v).strip()) if v is not None and str(v).strip() not in ("", "nan") else ""
    return s.upper()


def _cups(v):
    """El Excel guarda los CUPS como número y pierde los ceros a la izquierda: se completan a 6."""
    s = _codigo(v)
    return s.zfill(6) if s.isdigit() else s


def _pesos(texto):
    """'$12.110' -> 12110.0; '$58.363,50' -> 58363.5"""
    s = re.sub(r"[^\d,.]", "", str(texto or ""))
    return float(s.replace(".", "").replace(",", ".")) if s else None


def leer_tabla_soat(fuente):
    """Excel con el formato del maestro SOAT (hoja TABLA: código, descripción, factores SMLV, UVT y
    UVB; hoja TD: valor de la UVB y demás parámetros) -> (parámetros, tarifas, uvb).
    fuente: ruta o bytes. La UVB es None si la hoja TD no la trae."""
    import io
    src = io.BytesIO(fuente) if isinstance(fuente, (bytes, bytearray)) else fuente
    xl = pd.ExcelFile(src, engine="openpyxl")
    hojas = {h.strip().upper(): h for h in xl.sheet_names}
    if "TABLA" not in hojas:
        raise ValueError("El Excel no tiene la hoja TABLA (código, descripción, % SMLV, factor UVT, factor UVB)")
    par = pd.DataFrame(columns=["concepto", "valor", "valor_texto", "equivalencia", "uso", "norma",
                                "entidad", "observacion"])
    uvb = None
    if "TD" in hojas:
        td = pd.read_excel(xl, sheet_name=hojas["TD"], header=None, dtype=str)
        cab = td.index[td[0].fillna("").str.strip().str.upper() == "CONCEPTO"]
        if len(cab):
            params = []
            for f in td.iloc[cab[0] + 1:].itertuples(index=False):
                f = list(f) + [None] * 7
                concepto = str(f[0] or "").strip()
                if not concepto or concepto == "nan" or concepto.upper().startswith(("CÓMO", "COMO")):
                    if params:
                        break
                    continue
                params.append(dict(concepto=concepto, valor=_pesos(f[1]), valor_texto=f[1],
                                   equivalencia=f[2], uso=f[3], norma=f[4], entidad=f[5], observacion=f[6]))
            par = pd.DataFrame(params)
            u = par[par.concepto.str.upper() == "UVB"]
            uvb = float(u.valor.iloc[0]) if len(u) and u.valor.iloc[0] else None
    t = pd.read_excel(xl, sheet_name=hojas["TABLA"], header=None, dtype=str)
    fila = next((i for i, v in enumerate(t[0].fillna("")) if str(v).strip().upper().startswith("CÓDIGO")
                 or str(v).strip().upper().startswith("CODIGO")), None)
    t = t.iloc[(fila + 1) if fila is not None else 4:, :5]
    t.columns = ["codigo", "descripcion", "factor_smlv", "factor_uvt", "factor_uvb"]
    t["codigo"] = t.codigo.map(_codigo)
    t = t[t.codigo.str.fullmatch(r"\d{3,6}")].copy()
    for c in ("factor_smlv", "factor_uvt", "factor_uvb"):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    t = t[t.factor_uvb.notna()].drop_duplicates("codigo")
    t["descripcion"] = t.descripcion.fillna("").str.strip()
    if t.empty:
        raise ValueError("La hoja TABLA no trae códigos con factor UVB")
    return par, t.reset_index(drop=True), uvb


def leer_soat():
    par, t, uvb = leer_tabla_soat(SOAT_TABLA)
    t, calculados = completar_componentes(t)
    t["valor_2026"] = (t.factor_uvb * uvb).round(2)
    with warnings.catch_warnings():  # pandas avisa que el motor pyxlsb cambiará; sigue sirviendo
        warnings.simplefilter("ignore")
        r = pd.read_excel(SOAT_RELACION, sheet_name=0, dtype=str, engine="pyxlsb").iloc[:, :4]
    r.columns = ["cups", "nombre_cups", "codigo_soat", "descripcion_soat"]
    r["cups"] = r.cups.map(_cups)
    r["codigo_soat"] = r.codigo_soat.map(_codigo)
    r = r[(r.cups != "") & (r.codigo_soat != "")].drop_duplicates(["cups", "codigo_soat"])
    for c in ("nombre_cups", "descripcion_soat"):
        r[c] = r[c].fillna("").str.strip()

    g = (pd.read_csv(SOAT_GRUPOS, dtype=str) if SOAT_GRUPOS.exists()
         else pd.DataFrame(columns=["codigo", "grupo", "pagina", "confianza"]))
    g = g.rename(columns={"pagina": "pagina_pdf"})[["codigo", "grupo", "pagina_pdf", "confianza"]]
    g["grupo"] = g.grupo.astype(int)
    procs = pd.concat([
        t[["codigo", "descripcion"]].assign(fuente="tabla SOAT 2026"),
        r.drop_duplicates("codigo_soat")[["codigo_soat", "descripcion_soat"]]
        .rename(columns={"codigo_soat": "codigo", "descripcion_soat": "descripcion"})
        .assign(fuente="relación CUPS-SOAT"),
        g[["codigo"]].assign(descripcion=None, fuente="Decreto 780 (grupo quirúrgico)"),
    ]).drop_duplicates("codigo").reset_index(drop=True)
    return par, procs, t.reset_index(drop=True), r.reset_index(drop=True), uvb, g, calculados


def componentes_grupo(tar):
    """(grupo, componente, codigo_tarifa) desde las series de la tabla SOAT 2026."""
    filas = []
    por_codigo = dict(zip(tar.codigo, tar.descripcion))
    for comp, (ini, fin) in SERIES_CIRUGIA.items():
        for k in range(ini, fin + 1):
            d = por_codigo.get(str(k))
            if d is None or "GRUPO" not in d.upper():
                continue
            for n in map(int, re.findall(r"\d+", d)):
                if n in GRUPOS_SOAT:
                    filas.append(dict(grupo=n, componente=comp, codigo_tarifa=str(k)))
    return pd.DataFrame(filas).drop_duplicates(["grupo", "componente"])


def crear(con):
    """Crea y llena las tablas soat_* (y el catálogo tarifarios) en la conexión."""
    con.executescript(DDL)
    resumen = []
    catalogo = [dict(id="iss", nombre="Manual Tarifario ISS 2001", vigencia="2001",
                     unidad="pesos y UVR", fuente="MANUAL-ISS-2001.pdf (Acuerdo 256 de 2001)",
                     descripcion="Tarifa del Manual, con los recargos y descuentos de sus artículos; "
                                 "los CUPS se llevan a código ISS con la relación CUPS 2026")]
    if SOAT_TABLA.exists() and SOAT_RELACION.exists():
        par, procs, tar, rel, uvb, grp, calculados = leer_soat()
        par.to_sql("soat_parametros", con, if_exists="append", index=False)
        procs.to_sql("soat_procedimientos", con, if_exists="append", index=False)
        tar.to_sql("soat_tarifas", con, if_exists="append", index=False)
        rel.to_sql("soat_relacion_cups", con, if_exists="append", index=False)
        grp.to_sql("soat_grupos", con, if_exists="append", index=False)
        comp = componentes_grupo(tar)
        comp.to_sql("soat_grupo_componentes", con, if_exists="append", index=False)
        pd.DataFrame(REGLAS_CIRUGIA, columns=["regla", "numeral", "pagina_pdf", "componente",
                                              "porcentaje", "texto"]) \
            .to_sql("soat_reglas_cirugia", con, if_exists="append", index=False)
        faltan = [f"{c} grupo {g:02d}" for g in GRUPOS_SOAT for c in SERIES_CIRUGIA
                  if not ((comp.grupo == g) & (comp.componente == c)).any()
                  and not (c == "ayudante" and g < 6) and not (c == "materiales" and g >= 20)]
        resumen.append(f"SOAT cirugía: {len(grp)} procedimientos con grupo, {len(comp)} tarifas de "
                       f"componentes" + (f"; calculados con el decreto: {', '.join(calculados)}" if calculados else "")
                       + (f"; faltan: {', '.join(faltan)}" if faltan else ""))
        catalogo.append(dict(id="soat", nombre="Manual Tarifario SOAT 2026", vigencia="2026",
                             unidad="UVB", fuente=f"{SOAT_TABLA.name}; {SOAT_RELACION.name}",
                             descripcion=f"Valor = factor UVB x ${uvb:,.0f} (UVB 2026). Los CUPS se "
                                         "llevan a código SOAT con la relación CUPS-SOAT; la cirugía "
                                         "por grupo quirúrgico aún no se liquida".replace(",", ".")))
        con_valor = rel.codigo_soat.isin(set(tar.codigo)).sum()
        resumen.append(f"SOAT: {len(tar)} tarifas (UVB ${uvb:,.0f})".replace(",", ".") + f", {len(procs)} códigos, "
                       f"relación CUPS {len(rel)} filas ({con_valor} con tarifa)")
    catalogo.append(dict(id="propia", nombre="Tarifas propias", vigencia="según el manual",
                         unidad="pesos o factor sobre SOAT/ISS",
                         fuente="Manuales versionados (tarifas_propias.py, base TARIFAS_DB_URL)",
                         descripcion="Manual de tarifas propias pactado con el pagador: valor fijo "
                                     "por código (CUPS, CUM, insumo, material) o factor sobre SOAT o "
                                     "ISS; el auditor elige el manual y la versión"))
    pd.DataFrame(catalogo).to_sql("tarifarios", con, if_exists="append", index=False)
    malos = con.execute("PRAGMA foreign_key_check").fetchall()
    if malos:
        raise SystemExit(f"tarifarios: {len(malos)} filas violan llaves foráneas: {malos[:5]}")
    return resumen


# ---------------------------------------------------------------- consulta (auditoría)
def cargar(con):
    """Índices para auditar con SOAT:
    {'soat': {cups: [(codigo_soat, descripcion, valor|None)]}, 'soat_directo': {codigo: (...)},
     'catalogo': {id: nombre}}"""
    def existe(t):
        return con.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (t,)).fetchone()
    d = dict(soat={}, soat_directo={}, catalogo={}, soat_grupos={}, soat_comp={}, soat_comp_codigo={})
    if existe("tarifarios"):
        d["catalogo"] = dict(con.execute("SELECT id, nombre FROM tarifarios"))
    if existe("soat_relacion_cups"):
        for cups, cod, desc, valor in con.execute(
                "SELECT r.cups, r.codigo_soat, COALESCE(t.descripcion, p.descripcion), t.valor_2026 "
                "FROM soat_relacion_cups r JOIN soat_procedimientos p ON p.codigo = r.codigo_soat "
                "LEFT JOIN soat_tarifas t ON t.codigo = r.codigo_soat ORDER BY r.cups, r.codigo_soat"):
            d["soat"].setdefault(cups, []).append((cod, desc, valor))
        for cod, desc, valor in con.execute(
                "SELECT p.codigo, COALESCE(t.descripcion, p.descripcion), t.valor_2026 "
                "FROM soat_procedimientos p LEFT JOIN soat_tarifas t ON t.codigo = p.codigo"):
            d["soat_directo"][cod] = (cod, desc, valor)
    if existe("soat_grupos"):
        d["soat_grupos"] = dict(con.execute("SELECT codigo, grupo FROM soat_grupos"))
        for g, comp, cod, valor in con.execute(
                "SELECT c.grupo, c.componente, c.codigo_tarifa, t.valor_2026 FROM soat_grupo_componentes c "
                "JOIN soat_tarifas t ON t.codigo = c.codigo_tarifa"):
            d["soat_comp"][(g, comp)] = valor
            d["soat_comp_codigo"][(g, comp)] = cod
    return d


if __name__ == "__main__":
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    for linea in crear(con):
        print(linea)
