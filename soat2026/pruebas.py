"""Pruebas de la base del Manual Tarifario SOAT 2026 con valores leídos a mano en el PDF.

Uso: uv run soat2026/pruebas.py   (termina con error si alguna falla)
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent / "salida" / "manual_soat_2026.db"

# (descripción, consulta, resultado esperado) — página del PDF entre paréntesis
PRUEBAS = [
    ("parámetros de la portada (pág. 1)",
     "SELECT group_concat(concepto || '=' || CAST(valor AS INT), ' ') FROM parametros",
     "SMLMV=1750905 SMLDV=58363 UVT=52374 UVB=12110"),
    ("1101 grupo 9, art. 3 (pág. 2)", "SELECT grupo_quirurgico || '|' || articulo FROM procedimientos WHERE codigo='1101'", "9|3"),
    ("1112 descripción en dos líneas (pág. 3)", "SELECT descripcion FROM procedimientos WHERE codigo='1112'",
     "Tratamiento de malformaciones arterio venosas de línea media e intraventricular"),
    ("1162 junto al texto superpuesto (pág. 4)", "SELECT descripcion || '|' || grupo_quirurgico FROM procedimientos WHERE codigo='1162'",
     "Craneoplastia para corrección de defecto por resección del tumor óseo o infección|20"),
    ("ruta de 1110 (pág. 3)", "SELECT agrupador_ruta FROM v_tarifas WHERE codigo='1110'",
     "ÓRGANOS INTRACRANEALES > CRANEOTOMÍAS PARA TRATAMIENTO DE LESIÓNES VASCULARES CONGÉNITAS O ADQUIRIDAS"),
    ("19001 Acetaminofén, todas las columnas (pág. 58)",
     "SELECT factor_smldv||'|'||valor_smldv||'|'||factor_uvt||'|'||valor_uvt||'|'||factor_uvb||'|'||valor_uvb "
     "FROM procedimientos WHERE codigo='19001'", "1.57|91600|1.38|72300|5.93|71800"),
    ("37508 colecistectomía laparoscópica (pág. 86)", "SELECT valor_uvb FROM procedimientos WHERE codigo='37508'", "10956800"),
    ("39116 parto, valores centrados en dos líneas (pág. 91)",
     "SELECT factor_smldv||'|'||valor_uvb FROM procedimientos WHERE codigo='39116'", "4.96|226500"),
    ("39205 sala grupo 03 (pág. 92)", "SELECT factor_uvb||'|'||valor_uvb FROM procedimientos WHERE codigo='39205'", "22.52|272700"),
    ("ayudante desde el grupo 6 (art. 48)", "SELECT MIN(grupo) || '|' || COUNT(*) FROM tarifas_grupo WHERE concepto='ayudante'", "6|12"),
    ("materiales grupos 04-05-06 = 39302 (pág. 93)",
     "SELECT group_concat(grupo) FROM v_tarifas_grupo WHERE concepto='materiales' AND codigo='39302'", "4,5,6"),
    ("502001 conjunto de 6 dígitos (pág. 97)", "SELECT valor_uvb FROM procedimientos WHERE codigo='502001'", "2209300"),
    ("art. 47: 9 numerales con hijos", "SELECT COUNT(*) FROM agrupadores WHERE articulo=47 AND nivel=1", "9"),
    ("art. 48: parágrafos 1 a 9", "SELECT group_concat(numero) FROM notas WHERE articulo=48 AND tipo='paragrafo'", "1,2,3,4,5,6,7,8,9"),
    ("art. 69 (ARTíCULO con í minúscula, pág. 99)", "SELECT COUNT(*) FROM articulos WHERE numero=69", "1"),
    ("códigos citados en el parágrafo 3 del art. 23 no son procedimientos",
     "SELECT COUNT(*) FROM notas WHERE articulo=23 AND numero='3' AND texto LIKE '%02501 Extracción%25139%'", "1"),
    ("23106 sin tarifa en el PDF (pág. 74)", "SELECT COALESCE(valor_smldv,'nulo')||'|'||valor_uvb FROM procedimientos WHERE codigo='23106'", "nulo|0"),
    ("vista de cirugías: 1102 grupo 20 sin materiales (art. 55)",
     "SELECT cirujano_uvb||'|'||sala_uvb||'|'||COALESCE(materiales_uvb,'consumo') FROM v_cirugias WHERE codigo='1102'",
     "1160600|1589400|consumo"),
]


def main():
    con = sqlite3.connect(DB)
    fallas = 0
    for desc, sql, esperado in PRUEBAS:
        r = con.execute(sql).fetchone()
        obtenido = str(r[0]) if r else None
        ok = obtenido == esperado
        fallas += not ok
        print(f"  {'OK   ' if ok else 'FALLA'} {desc}" + ("" if ok else f"\n        esperado {esperado!r}, obtenido {obtenido!r}"))
    print(f"{len(PRUEBAS) - fallas}/{len(PRUEBAS)} pruebas OK")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
