"""Exporta la base del Manual Tarifario SOAT 2026 a un Excel organizado por hojas.

Salida: soat2026/salida/manual_soat_2026.xlsx
Hojas: Resumen, Artículos, Agrupadores (ruta con sus hijos), Tarifas (todos los procedimientos),
Cirugías (cap. III con honorarios, sala y materiales de su grupo), Tarifas por grupo, Notas,
Manual completo (en el orden del PDF), Observaciones del PDF y Validación.

Uso: uv run soat2026/exportar_excel.py
"""
import sqlite3
from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

BASE = Path(__file__).resolve().parent
DB = BASE / "salida" / "manual_soat_2026.db"
XLSX = BASE / "salida" / "manual_soat_2026.xlsx"

HOJAS = [
    ("Parámetros", "SELECT concepto, valor, descripcion, fuente FROM parametros"),
    ("Artículos", "SELECT capitulo, articulo, nombre, tipo_tarifa, n_procedimientos, n_agrupadores, n_paragrafos, "
                  "pagina, texto FROM v_articulos ORDER BY articulo"),
    ("Agrupadores", "SELECT g.articulo, a.nombre AS articulo_nombre, g.id AS agrupador_id, g.padre_id, g.nivel, "
                    "g.numeral, g.nombre, r.ruta, r.n_hijos, r.n_procedimientos, g.pagina "
                    "FROM agrupadores g JOIN v_agrupadores_ruta r ON r.agrupador_id = g.id "
                    "JOIN articulos a ON a.numero = g.articulo ORDER BY g.orden"),
    ("Tarifas", "SELECT capitulo, articulo, articulo_nombre, agrupador_ruta, codigo, descripcion, grupo_quirurgico, "
                "factor_smldv, valor_smldv, factor_uvt, valor_uvt, factor_uvb, valor_uvb, pagina "
                "FROM v_tarifas ORDER BY orden"),
    ("Cirugías", "SELECT articulo, articulo_nombre, agrupador_ruta, codigo, descripcion, grupo_quirurgico, "
                 "cirujano_uvb, anestesiologo_uvb, ayudante_uvb, sala_uvb, materiales_uvb, pagina FROM v_cirugias"),
    ("Tarifas por grupo", "SELECT grupo, concepto, codigo, descripcion, factor_uvb, valor_uvb, valor_smldv, articulo, "
                          "pagina FROM v_tarifas_grupo ORDER BY grupo, concepto"),
    ("Notas", "SELECT capitulo, articulo, articulo_nombre, tipo, numero, agrupador_ruta, texto, pagina "
              "FROM v_notas ORDER BY id"),
    ("Manual completo", "SELECT elemento, capitulo, articulo, nivel, codigo, texto, grupo_quirurgico, factor_uvb, "
                        "valor_uvb, pagina FROM v_manual_completo ORDER BY orden"),
    ("Observaciones PDF", "SELECT codigo, pagina, campo, valor_pdf, esperado, detalle FROM observaciones_pdf"),
    ("Validación", "SELECT control, resultado, detalle FROM validacion"),
]
MONEDA = {"valor_smldv", "valor_uvt", "valor_uvb", "cirujano_uvb", "anestesiologo_uvb", "ayudante_uvb",
          "sala_uvb", "materiales_uvb"}
ANCHO_MAX = {"texto": 90, "descripcion": 60, "agrupador_ruta": 60, "ruta": 70, "detalle": 80}


def escribir(destino, db=DB, informar=lambda hoja, n: None):
    """Escribe el Excel en `destino` (ruta o BytesIO). La web lo usa para la descarga."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        for hoja, sql in HOJAS:
            df = pd.read_sql_query(sql, con)
            df.to_excel(xw, sheet_name=hoja, index=False)
            ws = xw.sheets[hoja]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for celda in ws[1]:
                celda.font = Font(bold=True, color="FFFFFF")
                celda.fill = PatternFill("solid", fgColor="1DBB99")
            for i, col in enumerate(df.columns, 1):
                largo = max([len(str(col))] + [len(str(v)) for v in df[col].head(500).tolist()])
                ws.column_dimensions[get_column_letter(i)].width = min(max(8, largo + 2), ANCHO_MAX.get(col, 40))
                if col in MONEDA:
                    for (c,) in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                        c.number_format = '"$"#,##0'
            informar(hoja, len(df))
    con.close()


def main():
    if not DB.exists():
        raise SystemExit(f"No existe {DB}: ejecute uv run soat2026/etl.py")
    escribir(XLSX, informar=lambda hoja, n: print(f"  {hoja}: {n} filas"))
    print(f"Excel: {XLSX}")


if __name__ == "__main__":
    main()
