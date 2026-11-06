"""Ejecuta consultas SQL contra salida/manual_iss.db y muestra el resultado
(útil si no tiene instalado el cliente sqlite3).

Uso:
    uv run consultar.py consultas_ver.sql                  # todas las consultas del archivo
    uv run consultar.py consultas_ver.sql --vertical       # una ficha por fila (columna: valor)
    uv run consultar.py "SELECT * FROM v_paquetes LIMIT 5"
    uv run consultar.py consultas_ver.sql --csv salida.csv # guarda la última consulta en CSV
"""
import argparse
import os
import sqlite3
import sys

import pandas as pd

from rutas import BASE, conectar


def sentencias(sql):
    """Separa el texto en sentencias completas; el título es el último '-- ##' anterior."""
    titulo, actual = "", []
    for ln in sql.splitlines():
        solo_comentarios = all(not x.strip() or x.strip().startswith("--") for x in actual)
        if ln.startswith("-- ##") and solo_comentarios:
            titulo, actual = ln[5:].strip(), []
            continue
        actual.append(ln)
        texto = "\n".join(actual)
        if sqlite3.complete_statement(texto):
            if texto.strip().strip(";").strip() and any(
                    not x.strip().startswith("--") and x.strip() for x in actual):
                yield titulo, texto
            titulo, actual = "", []


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sql", help="archivo .sql o una consulta entre comillas")
    ap.add_argument("--vertical", action="store_true", help="una ficha por fila")
    ap.add_argument("--max", type=int, default=50, help="máximo de filas a mostrar (50)")
    ap.add_argument("--csv", help="guarda el resultado de la última consulta en este CSV")
    a = ap.parse_args()

    archivo = a.sql if os.path.exists(a.sql) else BASE / a.sql  # también desde otra carpeta
    sql = open(archivo, encoding="utf-8").read() if os.path.exists(archivo) else a.sql
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 60)
    con = conectar()
    df = None
    for titulo, q in sentencias(sql if sql.rstrip().endswith(";") else sql + ";"):
        try:
            df = pd.read_sql(q, con)
        except Exception as e:  # noqa: BLE001
            print(f"ERROR en «{titulo or q[:60]}»: {e}")
            sys.exit(1)
        print(f"\n### {titulo or 'consulta'}  ({len(df)} filas)")
        ver = df.head(a.max)
        if a.vertical:
            for i, fila in ver.iterrows():
                print(f"--- fila {i + 1}")
                for col, val in fila.items():
                    if pd.notna(val) and val != "":
                        print(f"  {col:22} {val}")
        else:
            print(ver.to_string(index=False))
        if len(df) > a.max:
            print(f"... ({len(df) - a.max} filas más; use --max o --csv)")
    if a.csv and df is not None:
        df.to_csv(a.csv, index=False, encoding="utf-8-sig")
        print(f"\nguardado en {a.csv}")


if __name__ == "__main__":
    main()
