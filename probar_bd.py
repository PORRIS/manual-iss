"""Ejecuta consultas_prueba.sql contra salida/manual_iss.db y compara con el resultado esperado.

Uso:
    uv run probar_bd.py              # todas las pruebas (y ejemplos de uso abreviados)
    uv run probar_bd.py --ejemplos   # muestra también las primeras filas de los ejemplos
"""
import argparse
import sqlite3
import sys

DB = "salida/manual_iss.db"
SQL = "consultas_prueba.sql"


def texto(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return "NULL" if v is None else str(v)


def bloques(sql):
    for b in sql.split("-- @prueba")[1:]:
        lineas = b.splitlines()
        titulo = [lineas[0].strip()]
        esperado, consulta = None, []
        for ln in lineas[1:]:
            if ln.startswith("-- @esperado"):
                esperado = ln[len("-- @esperado"):].strip()
            elif ln.startswith("--") and esperado is None and not consulta:
                titulo.append(ln.lstrip("- ").strip())  # continuación del título
            elif not ln.startswith("--"):
                consulta.append(ln)
        yield " ".join(titulo), esperado, "\n".join(consulta).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ejemplos", action="store_true", help="muestra las filas de los ejemplos")
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    ok = fallas = 0
    for titulo, esperado, consulta in bloques(open(SQL, encoding="utf-8").read()):
        try:
            cur = con.execute(consulta)
            filas = cur.fetchall()
        except sqlite3.Error as e:
            fallas += 1
            print(f"ERROR  {titulo}\n       {e}")
            continue
        if esperado is None:
            print(f"EJEMPLO {titulo}: {len(filas)} filas")
            if a.ejemplos:
                print("       " + " | ".join(c[0] for c in cur.description))
                for f in filas[:8]:
                    print("       " + " | ".join(texto(v)[:60] for v in f))
            continue
        obtenido = texto(filas[0][0]) if filas else "(sin filas)"
        if obtenido == esperado:
            ok += 1
            print(f"OK     {titulo}")
        else:
            fallas += 1
            print(f"FALLA  {titulo}\n       esperado: {esperado}\n       obtenido: {obtenido}")
    print(f"\n{ok} pruebas correctas, {fallas} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
