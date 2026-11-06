"""Versiones de la tarifa SOAT (una por año o por resolución).

La versión por defecto es la SOAT 2026 del repositorio (soat/SOAT A SALARIO MINIMO_UVT_UVB.xlsx),
que el ETL carga en salida/manual_iss.db (tabla soat_tarifas). Las demás (2027, ...) se suben como
Excel con el mismo formato (hoja TABLA con código, descripción, % SMLV, factor UVT y factor UVB;
hoja TD con el valor de la UVB) y se guardan en la base de tarifas propias (TARIFAS_DB_URL o
datos/tarifas_propias.db):

    soat_versiones(id PK, anio, nombre, uvb, estado, archivo, sha256, filas, cargado_en, observacion)
    soat_version_archivos(version_id PK -> soat_versiones, contenido)      el Excel original
    soat_version_tarifas(version_id -> soat_versiones, codigo, descripcion, factor_uvb,
                         factor_uvt, factor_smlv, origen; PK version_id + codigo)

Lo que no cambia con el año se comparte: la relación CUPS-SOAT y el grupo quirúrgico de cada
procedimiento (Decreto 780). Si a una tabla le falta un componente de cirugía se calcula con el
decreto (tarifarios.completar_componentes).

Uso:
    uv run soat_versiones.py cargar tabla_soat_2027.xlsx --anio 2027 --nombre "SOAT 2027" [--uvb 12600]
    uv run soat_versiones.py listar
"""
import argparse
import hashlib
import os
from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer,
                        LargeBinary, MetaData, String, Table, Text, UniqueConstraint, func, select)

import tarifarios
import tarifas_propias as tp

BASE_ID = "base"  # la SOAT 2026 del repositorio
ESTADOS = ("activo", "inactivo")
meta = MetaData()
versiones = Table(
    "soat_versiones", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("anio", Integer, nullable=False),
    Column("nombre", String(200), nullable=False),
    Column("uvb", Float, nullable=False),
    Column("estado", String(20), nullable=False),
    Column("archivo", String(300)),
    Column("sha256", String(64)),
    Column("filas", Integer, nullable=False, default=0),
    Column("observacion", Text),
    Column("cargado_en", DateTime, nullable=False, server_default=func.now()))
archivos = Table(
    "soat_version_archivos", meta,
    Column("version_id", Integer, ForeignKey("soat_versiones.id"), primary_key=True),
    Column("contenido", LargeBinary, nullable=False))
tarifas = Table(
    "soat_version_tarifas", meta,
    Column("version_id", Integer, nullable=False),
    Column("codigo", String(10), nullable=False),
    Column("descripcion", Text),
    Column("factor_uvb", Float, nullable=False),
    Column("factor_uvt", Float),
    Column("factor_smlv", Float),
    Column("origen", Text),
    ForeignKeyConstraint(["version_id"], ["soat_versiones.id"]),
    UniqueConstraint("version_id", "codigo", name="pk_soat_version_tarifa"))
_listo = set()


def motor(eng=None):
    eng = eng or tp.motor()
    if id(eng) not in _listo:
        meta.create_all(eng)
        _listo.add(id(eng))
    return eng


def leer_excel(contenido):
    """Excel -> (tarifas DataFrame con origen, uvb de la hoja TD o None, códigos calculados)."""
    if len(contenido) > tp.MAX_ARCHIVO:
        raise ValueError("El archivo pasa de 10 MB")
    try:
        _, tar, uvb = tarifarios.leer_tabla_soat(contenido)
    except ValueError:
        raise
    except Exception as e:  # noqa: BLE001 - archivo que no es un Excel válido
        raise ValueError(f"No es un Excel .xlsx válido ({e.__class__.__name__})") from e
    tar, calculados = tarifarios.completar_componentes(tar)
    return tar, uvb, calculados


def guardar(contenido, nombre_archivo, anio, nombre, uvb=None, estado="activo", observacion="", eng=None):
    eng = motor(eng)
    anio = int(anio)
    if not 2000 <= anio <= 2100:
        raise ValueError("Año no válido")
    if estado not in ESTADOS:
        raise ValueError(f"Estado no válido: {estado}")
    tar, uvb_td, calculados = leer_excel(contenido)
    uvb = float(uvb) if uvb else uvb_td
    if not uvb or uvb <= 0:
        raise ValueError("Falta el valor de la UVB (no viene en la hoja TD): indíquelo")
    with eng.begin() as con:
        vid = con.execute(versiones.insert().values(
            anio=anio, nombre=(nombre or f"SOAT {anio}").strip(), uvb=uvb, estado=estado,
            archivo=nombre_archivo, sha256=hashlib.sha256(contenido).hexdigest(), filas=len(tar),
            observacion=observacion, cargado_en=datetime.now())).inserted_primary_key[0]
        con.execute(archivos.insert().values(version_id=vid, contenido=contenido))
        con.execute(tarifas.insert(), [
            dict(version_id=vid, codigo=r.codigo, descripcion=r.descripcion,
                 factor_uvb=float(r.factor_uvb),
                 factor_uvt=None if r.factor_uvt != r.factor_uvt else r.factor_uvt,
                 factor_smlv=None if r.factor_smlv != r.factor_smlv else r.factor_smlv,
                 origen=r.origen) for r in tar.itertuples()])
    return dict(id=vid, anio=anio, uvb=uvb, filas=len(tar), calculados=calculados)


def version_base(con_bd):
    """La SOAT 2026 del repositorio (salida/manual_iss.db)."""
    uvb = con_bd.execute("SELECT valor FROM soat_parametros WHERE UPPER(concepto) = 'UVB'").fetchone()
    filas = con_bd.execute("SELECT COUNT(*) FROM soat_tarifas").fetchone()[0]
    return dict(id=BASE_ID, anio=2026, nombre="SOAT 2026 (por defecto)", uvb=uvb[0] if uvb else 12110.0,
                estado="activo", archivo=tarifarios.SOAT_TABLA.name, filas=filas, cargado_en=None,
                observacion="Viene en el repositorio y se carga con el ETL", predeterminada=True)


def listar(con_bd, eng=None):
    """Versión por defecto y las subidas (la más reciente primero)."""
    res = [version_base(con_bd)]
    try:
        with motor(eng).connect() as con:
            res += [dict(r._mapping, predeterminada=False) for r in
                    con.execute(select(versiones).order_by(versiones.c.anio.desc(), versiones.c.id.desc()))]
    except Exception:  # noqa: BLE001 - sin base de versiones: solo la del repositorio
        pass
    return res


def cambiar_estado(version_id, estado, eng=None):
    if estado not in ESTADOS:
        raise ValueError(f"Estado no válido: {estado}")
    with motor(eng).begin() as con:
        if con.execute(versiones.update().where(versiones.c.id == int(version_id))
                       .values(estado=estado)).rowcount == 0:
            raise ValueError("Versión SOAT no encontrada")


def archivo(version_id, eng=None):
    with motor(eng).connect() as con:
        r = con.execute(select(versiones.c.archivo, archivos.c.contenido)
                        .join(archivos, archivos.c.version_id == versiones.c.id)
                        .where(versiones.c.id == int(version_id))).first()
    if r is None:
        raise ValueError("Versión SOAT no encontrada")
    return r.archivo, r.contenido


def tarifas_version(version_id, eng=None):
    with motor(eng).connect() as con:
        return [dict(r._mapping) for r in con.execute(
            select(tarifas).where(tarifas.c.version_id == int(version_id)).order_by(tarifas.c.codigo))]


def aplicar(T, version_id, eng=None):
    """Índices de auditoría (tarifarios.cargar) con los factores de otra versión SOAT.
    Devuelve (T de la versión, UVB de la versión, nombre). La versión base devuelve T tal cual."""
    if version_id in (None, "", BASE_ID):
        return T, None, None
    with motor(eng).connect() as con:
        v = con.execute(select(versiones).where(versiones.c.id == int(version_id))).first()
        if v is None:
            raise ValueError("Versión SOAT no encontrada")
        fac = {r.codigo: (r.descripcion, r.factor_uvb) for r in
               con.execute(select(tarifas).where(tarifas.c.version_id == v.id))}
    ref = tarifarios.UVB_REFERENCIA  # los índices guardan valores a la UVB 2026; auditar escala por la UVB
    valor = lambda k: fac[k][1] * ref if k in fac else None  # noqa: E731
    Tv = dict(T)
    Tv["soat"] = {cups: [(k, fac[k][0] if k in fac and fac[k][0] else dsc, valor(k)) for k, dsc, _ in lista]
                  for cups, lista in T["soat"].items()}
    Tv["soat_directo"] = {k: (k, fac[k][0] if k in fac and fac[k][0] else dsc, valor(k))
                          for k, (_, dsc, _) in T["soat_directo"].items()}
    for k, (dsc, f) in fac.items():
        Tv["soat_directo"].setdefault(k, (k, dsc, f * ref))
    Tv["soat_comp"] = {gc: valor(cod) for gc, cod in T["soat_comp_codigo"].items() if cod in fac}
    Tv["catalogo"] = dict(T["catalogo"], soat=v.nombre)
    return Tv, v.uvb, v.nombre


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cargar", help="sube una tabla SOAT (Excel con hojas TABLA y TD)")
    c.add_argument("archivo")
    c.add_argument("--anio", type=int, required=True)
    c.add_argument("--nombre", default="")
    c.add_argument("--uvb", type=float, help="valor de la UVB (si la hoja TD no lo trae)")
    c.add_argument("--estado", choices=ESTADOS, default="activo")
    sub.add_parser("listar", help="versiones SOAT disponibles")
    a = ap.parse_args()
    from rutas import conectar
    print("base de versiones:", tp.destino())
    if a.cmd == "cargar":
        with open(a.archivo, "rb") as fh:
            v = guardar(fh.read(), os.path.basename(a.archivo), a.anio, a.nombre, a.uvb, a.estado)
        print(f"guardada la versión {v['id']} (SOAT {v['anio']}, UVB {v['uvb']:g}): {v['filas']} códigos"
              + (f"; calculados con el decreto: {', '.join(v['calculados'])}" if v["calculados"] else ""))
    else:
        for v in listar(conectar()):
            print(f"{str(v['id']):>5}  {v['anio']}  {v['nombre']:30} UVB {v['uvb']:>9,.0f}  {v['estado']:8} "
                  f"{v['filas']} códigos  {v['archivo'] or ''}")


if __name__ == "__main__":
    main()
