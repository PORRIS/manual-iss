"""Manuales de tarifas propias: parametrización, versionamiento y aplicación.

Cada manual tiene un código propio (ej. TAR-PROPIA-2026-01), un nombre (ej. «Tarifario
Preferencial Convenio X») y una o más versiones. Cada versión guarda:
- tipo de liquidación base: valor fijo en pesos, o factor (% de recargo o descuento) sobre SOAT o ISS;
- vigencia (fecha de inicio y fin, según el contrato) y estado (borrador, activo, inactivo; se
  muestra «vencido» cuando la fecha de fin ya pasó);
- el Excel original (anexo de contratación) y sus filas: código (CUPS, CUM, insumo o material),
  descripción, tarifa pactada y, opcionalmente, su propio tipo de liquidación y factor.
Subir un Excel a un código existente crea una versión nueva: las anteriores se conservan para
atender glosas de vigencias anteriores.

Dónde se guarda: en la base de la variable de entorno TARIFAS_DB_URL (PostgreSQL, ej. Neon o
Supabase: postgresql://usuario:clave@servidor/base) o, si no está, en datos/tarifas_propias.db
(SQLite local, fuera de git). Es independiente de salida/manual_iss.db, que el ETL regenera.

Formato del Excel (ver plantilla()): una hoja por tipo (CUPS, CUMS o MEDICAMENTOS, INSUMOS,
MATERIALES) con las columnas Código, Descripción, Tarifa y, opcionales, «Tipo liquidación» (valor
fijo, SOAT o ISS) y «Factor %».

Uso:
    uv run tarifas_propias.py cargar "tarifas propias/TARIFAS PROPIAS.xlsx" --codigo TAR-PROPIA-2026-01 \\
        --nombre "Tarifario ejemplo" --inicio 2026-01-01 --fin 2026-12-31 --estado activo
    uv run tarifas_propias.py listar
"""
import argparse
import hashlib
import io
import os
import re
import unicodedata
from datetime import date, datetime

import openpyxl
from sqlalchemy import (Column, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer,
                        LargeBinary, MetaData, String, Table, Text, UniqueConstraint, create_engine,
                        func, select)

from rutas import BASE

ESTADOS = ("borrador", "activo", "inactivo")
TIPOS_BASE = ("valor_fijo", "soat", "iss")
TIPOS_ITEM = ("cups", "cum", "insumo", "material")
HOJAS = {"CUPS": "cups", "PROCEDIMIENTOS": "cups", "SERVICIOS": "cups", "CUMS": "cum",
         "CUM": "cum", "MEDICAMENTOS": "cum", "INSUMOS": "insumo", "MATERIALES": "material"}
MAX_ARCHIVO = 10_000_000
RE_CODIGO_MANUAL = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,49}$")

meta = MetaData()
manuales = Table(
    "tarifa_manuales", meta,
    Column("codigo", String(50), primary_key=True),
    Column("nombre", String(200), nullable=False),
    Column("pagador", String(200)),
    Column("creado_en", DateTime, nullable=False, server_default=func.now()))
versiones = Table(
    "tarifa_versiones", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("manual", String(50), ForeignKey("tarifa_manuales.codigo"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("tipo_base", String(20), nullable=False),
    Column("factor_pct", Float, nullable=False, default=0),
    Column("vigencia_inicio", Date),
    Column("vigencia_fin", Date),
    Column("estado", String(20), nullable=False),
    Column("observacion", Text),
    Column("archivo", String(300)),
    Column("sha256", String(64)),
    Column("filas", Integer, nullable=False, default=0),
    Column("cargado_en", DateTime, nullable=False, server_default=func.now()),
    UniqueConstraint("manual", "version", name="uq_tarifa_version"))
archivos = Table(
    "tarifa_archivos", meta,
    Column("version_id", Integer, ForeignKey("tarifa_versiones.id"), primary_key=True),
    Column("contenido", LargeBinary, nullable=False))
items = Table(
    "tarifa_items", meta,
    Column("version_id", Integer, nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("codigo", String(60), nullable=False),
    Column("descripcion", Text),
    Column("tarifa", Float),
    Column("tipo_liquidacion", String(20)),
    Column("factor_pct", Float),
    ForeignKeyConstraint(["version_id"], ["tarifa_versiones.id"]),
    UniqueConstraint("version_id", "tipo", "codigo", name="pk_tarifa_item"))

_motores = {}


def url_base():
    url = os.getenv("TARIFAS_DB_URL", "").strip()
    if not url:
        (BASE / "datos").mkdir(exist_ok=True)
        return f"sqlite:///{BASE / 'datos' / 'tarifas_propias.db'}"
    # Neon/Supabase entregan postgres:// o postgresql://; SQLAlchemy usa el driver psycopg 3
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", url)


def motor(url=None):
    url = url or url_base()
    if url not in _motores:
        eng = create_engine(url, pool_pre_ping=True)
        meta.create_all(eng)
        _motores[url] = eng
    return _motores[url]


def destino():
    """Texto para mostrar dónde se guardan los manuales (sin la clave)."""
    url = url_base()
    return f"SQLite local ({url.split(':///', 1)[1]})" if url.startswith("sqlite") else \
        "PostgreSQL " + re.sub(r"//[^@]*@", "//", url).split("?")[0].split("//", 1)[-1]


# ---------------------------------------------------------------- lectura del Excel
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9%]+", " ", s.upper()).strip()


def _num(v):
    """Número de una celda: 79000, '79.000', '$ 1.234.567,50', '12,5', '-5'."""
    if v is None or str(v).strip() == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if "," in s and "." in s:  # el último separador es el decimal
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", ".") if s.count(",") == 1 and len(s.split(",")[1]) != 3 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")  # 79.000 = setenta y nueve mil (formato colombiano)
    try:
        return float(s)
    except ValueError:
        return None


def _tipo_liq(v):
    n = _norm(v)
    if not n:
        return None
    if "SOAT" in n:
        return "soat"
    if "ISS" in n:
        return "iss"
    if "FIJ" in n or "PESO" in n or n == "VALOR":
        return "valor_fijo"
    return "?"


def _codigo(v, tipo):
    s = re.sub(r"\.0$", "", str(v).strip()).upper() if v is not None else ""
    return s.zfill(6) if tipo == "cups" and s.isdigit() and len(s) < 6 else s


def leer_excel(contenido):
    """Excel -> (filas, avisos). filas: [dict(tipo, codigo, descripcion, tarifa, tipo_liquidacion,
    factor_pct, hoja, fila)]. No guarda nada: sirve para la vista previa."""
    if len(contenido) > MAX_ARCHIVO:
        raise ValueError("El archivo pasa de 10 MB")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - cualquier archivo que no sea xlsx
        raise ValueError(f"No es un Excel .xlsx válido ({e.__class__.__name__})") from e
    filas, avisos, vistos = [], [], {}
    for ws in wb.worksheets:
        tipo = HOJAS.get(_norm(ws.title))
        if not tipo:
            if _norm(ws.title) != "INSTRUCCIONES":
                avisos.append(f"Hoja «{ws.title}» ignorada: use CUPS, CUMS/MEDICAMENTOS, INSUMOS o MATERIALES")
            continue
        it = ws.iter_rows(values_only=True)
        col, n_cab = None, 0
        for n_cab, fila in enumerate(it, start=1):  # la cabecera puede no estar en la fila 1
            cab = [_norm(c) for c in fila]
            if any(c.startswith("COD") for c in cab) and any("TARIFA" in c or "VALOR" in c for c in cab):
                col = {
                    "codigo": next(i for i, c in enumerate(cab) if c.startswith("COD")),
                    "descripcion": next((i for i, c in enumerate(cab) if c.startswith("DESC")
                                         or c.startswith("NOMBRE")), None),
                    "tarifa": next(i for i, c in enumerate(cab) if "TARIFA" in c and "TIPO" not in c
                                   or c in ("VALOR", "VALOR PACTADO")),
                    "tipo_liquidacion": next((i for i, c in enumerate(cab) if "LIQUID" in c
                                              or c == "TIPO TARIFA"), None),
                    "factor_pct": next((i for i, c in enumerate(cab) if "FACTOR" in c
                                        or c in ("%", "PORCENTAJE")), None),
                }
                break
            if n_cab > 15:
                break
        if col is None:
            avisos.append(f"Hoja «{ws.title}»: no encontré la cabecera (Código, Descripción, Tarifa)")
            continue
        for n, fila in enumerate(it, start=n_cab + 1):
            g = (lambda k: fila[col[k]] if col[k] is not None and col[k] < len(fila) else None)
            cod = _codigo(g("codigo"), tipo)
            if not cod:
                continue
            liq = _tipo_liq(g("tipo_liquidacion"))
            r = dict(tipo=tipo, codigo=cod, descripcion=str(g("descripcion") or "").strip(),
                     tarifa=_num(g("tarifa")), tipo_liquidacion=None if liq == "?" else liq,
                     factor_pct=_num(g("factor_pct")), hoja=ws.title, fila=n)
            if liq == "?":
                avisos.append(f"{ws.title} fila {n} ({cod}): tipo de liquidación «{g('tipo_liquidacion')}» "
                              "no reconocido (use valor fijo, SOAT o ISS); se toma el del manual")
            if (tipo, cod) in vistos:
                avisos.append(f"{ws.title} fila {n} ({cod}): código repetido (ya en la fila "
                              f"{vistos[(tipo, cod)]}); se usa la última")
                filas = [f for f in filas if (f["tipo"], f["codigo"]) != (tipo, cod)]
            vistos[(tipo, cod)] = n
            filas.append(r)
    if not filas:
        raise ValueError("El Excel no trae filas válidas. " + " ".join(avisos[:3]))
    return filas, avisos


def validar(filas, tipo_base):
    """Errores que impiden guardar: filas que no tienen cómo calcular su valor."""
    errores = []
    for f in filas:
        liq = f["tipo_liquidacion"] or tipo_base
        if liq == "valor_fijo" and (f["tarifa"] is None or f["tarifa"] < 0):
            errores.append(f"{f['hoja']} fila {f['fila']} ({f['codigo']}): sin tarifa en pesos "
                           "(el tipo de liquidación es valor fijo)")
    return errores


def _estilo_cabecera(ws, color="1DBB99"):
    from openpyxl.styles import Font, PatternFill
    for c in ws[1]:
        c.fill = PatternFill("solid", fgColor=color)
        c.font = Font(bold=True, color="FFFFFF")
    ws.freeze_panes = "A2"


def plantilla():
    """Excel para llenar y subir: una hoja de datos vacía por tipo (CUPS, CUMS, INSUMOS,
    MATERIALES) y la hoja INSTRUCCIONES con ejemplos (se ignora al cargar)."""
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = openpyxl.Workbook()
    ins = wb.active
    ins.title = "INSTRUCCIONES"
    texto = [
        ("Plantilla de tarifas propias", True),
        ("1. Llene una fila por tecnología en la hoja que corresponda: CUPS (procedimientos y servicios), "
         "CUMS (medicamentos), INSUMOS y MATERIALES. Puede dejar vacías las hojas que no use.", False),
        ("2. Columnas obligatorias: Código, Descripción y Tarifa (valor pactado en pesos, sin decimales "
         "o con coma decimal).", False),
        ("3. Columnas opcionales, solo si esa fila se liquida distinto al resto del manual: «Tipo "
         "liquidación» (valor fijo, SOAT o ISS) y «Factor %» (recargo o descuento sobre SOAT o ISS, "
         "ej. -5 o 10). Si las deja vacías se usa lo que indique al subir el manual.", False),
        ("4. Con tipo SOAT o ISS la Tarifa puede quedar vacía: el valor sale de esa tarifa más el factor.", False),
        ("5. No cambie los nombres de las hojas ni de las columnas. Esta hoja no se carga.", False),
        ("6. Al subir el archivo indique el código del manual (ej. TAR-PROPIA-2026-01), el nombre, el "
         "pagador, la vigencia y el estado. Si el código ya existe se crea una versión nueva.", False),
        ("", False),
        ("Ejemplos (no los copie como tarifas reales):", True),
    ]
    for t, negrita in texto:
        ins.append([t])
        ins.cell(ins.max_row, 1).font = Font(bold=negrita, size=13 if ins.max_row == 1 else 11)
        ins.cell(ins.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ins.append(["Hoja", "Código", "Descripción", "Tarifa", "Tipo liquidación", "Factor %"])
    for c in ins[ins.max_row]:
        c.font = Font(bold=True)
    for ej in (("CUPS", "890202", "CONSULTA DE PRIMERA VEZ POR OTRAS ESPECIALIDADES", 79000, "", ""),
               ("CUPS", "903841", "GLUCOSA EN SUERO", "", "SOAT", -10),
               ("CUMS", "19933174-1", "ACETAMINOFEN 500 MG TABLETA", 120, "", ""),
               ("INSUMOS", "INS-0001", "EQUIPO DE VENOCLISIS", 4500, "", ""),
               ("MATERIALES", "MAT-0001", "GASA ESTERIL 10 X 10", "", "ISS", 30)):
        ins.append(list(ej))
    ins.column_dimensions["A"].width = 110
    for c, w in zip("BCDEF", (14, 46, 12, 16, 10)):
        ins.column_dimensions[c].width = w
    lista = DataValidation(type="list", formula1='"valor fijo,SOAT,ISS"', allow_blank=True,
                           showErrorMessage=True, errorTitle="Tipo de liquidación",
                           error="Use valor fijo, SOAT o ISS (o déjelo vacío)")
    for hoja in ("CUPS", "CUMS", "INSUMOS", "MATERIALES"):
        ws = wb.create_sheet(hoja)
        ws.append(["Código", "Descripción", "Tarifa", "Tipo liquidación", "Factor %"])
        _estilo_cabecera(ws)
        for c, w in zip("ABCDE", (18, 60, 14, 18, 11)):
            ws.column_dimensions[c].width = w
        v = DataValidation(type="list", formula1=lista.formula1, allow_blank=True, showErrorMessage=True,
                           errorTitle=lista.errorTitle, error=lista.error)
        v.add("D2:D5000")
        ws.add_data_validation(v)
        for fila in range(2, 5001):  # códigos como texto: conservan los ceros a la izquierda
            ws.cell(fila, 1).number_format = "@"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- guardar y consultar
def estado_vigente(v, hoy=None):
    hoy = hoy or date.today()
    if v["estado"] == "activo" and v["vigencia_fin"] and v["vigencia_fin"] < hoy:
        return "vencido"
    return v["estado"]


def _fecha(v):
    if v in (None, ""):
        return None
    return v if isinstance(v, date) else datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def guardar(contenido, nombre_archivo, codigo, nombre, tipo_base="valor_fijo", factor_pct=0.0,
            inicio=None, fin=None, estado="borrador", pagador="", observacion="", eng=None):
    """Crea el manual si no existe y guarda una versión nueva. Devuelve dict de la versión."""
    eng = eng or motor()
    codigo = (codigo or "").strip().upper()
    if not RE_CODIGO_MANUAL.match(codigo):
        raise ValueError("Código del manual no válido: use letras, números, guion o punto (ej. TAR-PROPIA-2026-01)")
    if not (nombre or "").strip():
        raise ValueError("Falta el nombre del manual")
    if tipo_base not in TIPOS_BASE:
        raise ValueError(f"Tipo de liquidación base no válido: {tipo_base}")
    if estado not in ESTADOS:
        raise ValueError(f"Estado no válido: {estado} ({', '.join(ESTADOS)})")
    inicio, fin = _fecha(inicio), _fecha(fin)
    if inicio and fin and fin < inicio:
        raise ValueError("La fecha de fin de la vigencia es anterior a la de inicio")
    filas, avisos = leer_excel(contenido)
    errores = validar(filas, tipo_base)
    if errores:
        raise ValueError(f"{len(errores)} fila(s) sin valor: " + "; ".join(errores[:5]))
    with eng.begin() as con:
        if con.execute(select(manuales.c.codigo).where(manuales.c.codigo == codigo)).first() is None:
            con.execute(manuales.insert().values(codigo=codigo, nombre=nombre.strip(),
                                                 pagador=(pagador or "").strip()))
        else:
            con.execute(manuales.update().where(manuales.c.codigo == codigo)
                        .values(nombre=nombre.strip(), pagador=(pagador or "").strip()))
        n = con.execute(select(func.coalesce(func.max(versiones.c.version), 0))
                        .where(versiones.c.manual == codigo)).scalar() + 1
        vid = con.execute(versiones.insert().values(
            manual=codigo, version=n, tipo_base=tipo_base, factor_pct=float(factor_pct or 0),
            vigencia_inicio=inicio, vigencia_fin=fin, estado=estado, observacion=observacion,
            archivo=nombre_archivo, sha256=hashlib.sha256(contenido).hexdigest(), filas=len(filas),
            cargado_en=datetime.now())).inserted_primary_key[0]
        con.execute(archivos.insert().values(version_id=vid, contenido=contenido))
        con.execute(items.insert(), [dict(version_id=vid, **{k: f[k] for k in (
            "tipo", "codigo", "descripcion", "tarifa", "tipo_liquidacion", "factor_pct")})
            for f in filas])
    return dict(id=vid, manual=codigo, version=n, filas=len(filas), avisos=avisos)


def listar(eng=None):
    """Manuales con sus versiones (la más reciente primero)."""
    eng = eng or motor()
    with eng.connect() as con:
        ms = {m.codigo: dict(m._mapping, versiones=[]) for m in
              con.execute(select(manuales).order_by(manuales.c.codigo))}
        for v in con.execute(select(versiones).order_by(versiones.c.manual, versiones.c.version.desc())):
            d = dict(v._mapping)
            d["estado_vigente"] = estado_vigente(d)
            ms[d["manual"]]["versiones"].append(d)
    return list(ms.values())


def cambiar_estado(version_id, estado, eng=None):
    if estado not in ESTADOS:
        raise ValueError(f"Estado no válido: {estado}")
    eng = eng or motor()
    with eng.begin() as con:
        r = con.execute(versiones.update().where(versiones.c.id == version_id).values(estado=estado))
        if r.rowcount == 0:
            raise ValueError("Versión no encontrada")


def archivo(version_id, eng=None):
    eng = eng or motor()
    with eng.connect() as con:
        r = con.execute(select(versiones.c.archivo, archivos.c.contenido)
                        .join(archivos, archivos.c.version_id == versiones.c.id)
                        .where(versiones.c.id == version_id)).first()
    if r is None:
        raise ValueError("Versión no encontrada")
    return r.archivo, r.contenido


def cargar_version(version_id, eng=None):
    """dict(version: {...}, items: {(tipo, codigo): {...}}) para auditar."""
    eng = eng or motor()
    with eng.connect() as con:
        v = con.execute(select(versiones, manuales.c.nombre)
                        .join(manuales, manuales.c.codigo == versiones.c.manual)
                        .where(versiones.c.id == version_id)).first()
        if v is None:
            raise ValueError("Versión del manual de tarifas propias no encontrada")
        its = {(r.tipo, r.codigo): dict(r._mapping) for r in
               con.execute(select(items).where(items.c.version_id == version_id))}
    v = dict(v._mapping)
    v["estado_vigente"] = estado_vigente(v)
    return dict(version=v, items=its)


def items_version(version_id, eng=None):
    eng = eng or motor()
    with eng.connect() as con:
        return [dict(r._mapping) for r in con.execute(
            select(items).where(items.c.version_id == version_id)
            .order_by(items.c.tipo, items.c.codigo))]


# ---------------------------------------------------------------- consola
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cargar", help="sube un Excel como versión nueva de un manual")
    c.add_argument("archivo")
    c.add_argument("--codigo", required=True)
    c.add_argument("--nombre", required=True)
    c.add_argument("--pagador", default="")
    c.add_argument("--tipo-base", choices=TIPOS_BASE, default="valor_fijo")
    c.add_argument("--factor", type=float, default=0, help="%% sobre SOAT o ISS (ej. -5)")
    c.add_argument("--inicio")
    c.add_argument("--fin")
    c.add_argument("--estado", choices=ESTADOS, default="borrador")
    sub.add_parser("listar", help="manuales y versiones guardados")
    sub.add_parser("plantilla", help="escribe plantilla_tarifas_propias.xlsx")
    a = ap.parse_args()
    print("base:", destino())
    if a.cmd == "cargar":
        with open(a.archivo, "rb") as fh:
            v = guardar(fh.read(), os.path.basename(a.archivo), a.codigo, a.nombre, a.tipo_base,
                        a.factor, a.inicio, a.fin, a.estado, a.pagador)
        print(f"guardado {v['manual']} versión {v['version']} (id {v['id']}): {v['filas']} filas")
        for x in v["avisos"]:
            print(" aviso:", x)
    elif a.cmd == "listar":
        for m in listar():
            print(f"{m['codigo']}  {m['nombre']}")
            for v in m["versiones"]:
                print(f"   v{v['version']} id={v['id']} {v['estado_vigente']:9} {v['tipo_base']} "
                      f"{v['factor_pct']:+g}%  {v['vigencia_inicio']} a {v['vigencia_fin']}  "
                      f"{v['filas']} filas  {v['archivo']}")
    else:
        with open("plantilla_tarifas_propias.xlsx", "wb") as fh:
            fh.write(plantilla())
        print("escrito plantilla_tarifas_propias.xlsx")


if __name__ == "__main__":
    main()
