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

El SOAT de cirugía se liquida por grupo quirúrgico (Decreto 780 de 2016, anexo técnico 1): esos
códigos están en soat_procedimientos y en la relación, pero no tienen valor en soat_tarifas.
"""
import re
import warnings

import pandas as pd

from rutas import BASE

SOAT_TABLA = BASE / "soat" / "SOAT A SALARIO MINIMO_UVT_UVB.xlsx"
SOAT_RELACION = BASE / "soat" / "CUPS A SOAT_ANDER_OKANDER.xlsb"

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
    valor_2026 REAL NOT NULL);
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


def leer_soat():
    td = pd.read_excel(SOAT_TABLA, sheet_name="TD", header=None, dtype=str, engine="openpyxl")
    i = td.index[td[0].fillna("").str.strip().str.upper() == "CONCEPTO"][0]
    params = []
    for f in td.iloc[i + 1:].itertuples(index=False):
        concepto = str(f[0] or "").strip()
        if not concepto or concepto.upper().startswith(("CÓMO", "COMO")) or concepto == "nan":
            if params:
                break
            continue
        params.append(dict(concepto=concepto, valor=_pesos(f[1]), valor_texto=f[1],
                           equivalencia=f[2], uso=f[3], norma=f[4], entidad=f[5], observacion=f[6]))
    par = pd.DataFrame(params)
    uvb = float(par[par.concepto.str.upper() == "UVB"].valor.iloc[0])

    t = pd.read_excel(SOAT_TABLA, sheet_name="TABLA", header=None, dtype=str, skiprows=4,
                      engine="openpyxl").iloc[:, :5]
    t.columns = ["codigo", "descripcion", "factor_smlv", "factor_uvt", "factor_uvb"]
    t["codigo"] = t.codigo.map(_codigo)
    t = t[t.codigo != ""].copy()
    for c in ("factor_smlv", "factor_uvt", "factor_uvb"):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    t["descripcion"] = t.descripcion.fillna("").str.strip()
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

    procs = pd.concat([
        t[["codigo", "descripcion"]].assign(fuente="tabla SOAT 2026"),
        r.drop_duplicates("codigo_soat")[["codigo_soat", "descripcion_soat"]]
        .rename(columns={"codigo_soat": "codigo", "descripcion_soat": "descripcion"})
        .assign(fuente="relación CUPS-SOAT"),
    ]).drop_duplicates("codigo").reset_index(drop=True)
    return par, procs, t.reset_index(drop=True), r.reset_index(drop=True), uvb


def crear(con):
    """Crea y llena las tablas soat_* (y el catálogo tarifarios) en la conexión."""
    con.executescript(DDL)
    resumen = []
    catalogo = [dict(id="iss", nombre="Manual Tarifario ISS 2001", vigencia="2001",
                     unidad="pesos y UVR", fuente="MANUAL-ISS-2001.pdf (Acuerdo 256 de 2001)",
                     descripcion="Tarifa del Manual, con los recargos y descuentos de sus artículos; "
                                 "los CUPS se llevan a código ISS con la relación CUPS 2026")]
    if SOAT_TABLA.exists() and SOAT_RELACION.exists():
        par, procs, tar, rel, uvb = leer_soat()
        par.to_sql("soat_parametros", con, if_exists="append", index=False)
        procs.to_sql("soat_procedimientos", con, if_exists="append", index=False)
        tar.to_sql("soat_tarifas", con, if_exists="append", index=False)
        rel.to_sql("soat_relacion_cups", con, if_exists="append", index=False)
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
    d = dict(soat={}, soat_directo={}, catalogo={})
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
    return d


if __name__ == "__main__":
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    for linea in crear(con):
        print(linea)
