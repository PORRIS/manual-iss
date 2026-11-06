"""Rutas del proyecto, independientes de la carpeta desde la que se ejecute el script.

- al_proyecto(): cambia a la carpeta del proyecto (para los scripts sin argumentos de archivo).
- conectar(): abre salida/manual_iss.db y falla con un mensaje claro si no existe
  (sqlite3.connect a una ruta inexistente crea en silencio una BD vacía, sin tablas ni vistas).
"""
import os
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "salida" / "manual_iss.db"


def al_proyecto():
    os.chdir(BASE)


def conectar(db=DB):
    db = Path(db)
    if not db.is_absolute():
        db = BASE / db
    if not db.exists():
        sys.exit(f"ERROR: no existe la base {db}. Genérela con: ./actualizar.sh (o uv run etl.py)")
    return sqlite3.connect(db)
