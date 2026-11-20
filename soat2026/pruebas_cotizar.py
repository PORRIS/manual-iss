"""Pruebas del cotizador SOAT 2026 con resultados calculados a mano (valores UVB 2026 del PDF).

Uso: uv run soat2026/pruebas_cotizar.py   (termina con error si alguna falla)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cotizar as cz  # noqa: E402

D = cz.cargar()

# (descripción, ítems, opciones, total esperado, comprobación extra o None)
PRUEBAS = [
    ("procedimiento con valor y cantidad: 71.800 + 2 x 77.000", ["19001", "21101x2"], {}, 225_800, None),
    ("cirugía 1101 grupo 09 completa: 582.400 + 333.100 + 159.200 + 963.400 + 452.800",
     ["1101"], {}, 2_490_900, None),
    ("grupo 04 sin ayudante por tabla (empieza en el 06): 196.800 + 141.600 + 347.200 + 195.200",
     ["1250"], {}, 880_800, lambda r: not any(ln["concepto"] == "ayudante" for ln in r["lineas"])),
    ("sin anestesiólogo y sin ayudante: 582.400 + 963.400 + 452.800",
     ["1101:sin_anestesiologo:sin_ayudante"], {}, 1_998_600, None),
    ("mayor grupo 20 (sin materiales: catálogo) + 1101 diferente vía: 3.744.600 + 436.800 + 249.800 + "
     "119.400 + 481.700 + 339.600", ["1102", "1101:diferente_via"], {}, 5_371_900,
     lambda r: any("catálogo" in a for a in r["avisos"])),
    ("adicionales igual vía (50 % honorarios, sin sala ni materiales): 3.744.600 + 537.400 + 441.700",
     ["1101", "1102", "1103:igual_via"], {}, 4_723_700, None),
    ("otra especialidad: cirujano 100 %, anestesiólogo 75 %, ayudante 50 % solo de la adicional de mayor grupo, "
     "sala 50 %", ["1110:perfusionista", "1101:otra_especialidad", "1103:otra_especialidad"], {}, 7_391_800,
     lambda r: sum(1 for ln in r["lineas"] if ln["concepto"] == "ayudante") == 2),
    ("bilateral con región META: honorarios x1,75 x1,25; sala x1,5; materiales x1,75",
     ["1101:bilateral"], dict(region="META"), 4_588_400, None),
    ("incruenta: sala 45 % (310.800) y materiales 39305 (105.600)", ["13350:incruenta"], {}, 1_067_000, None),
    ("perfusionista en grupo 09: no se cobra y avisa", ["1101:perfusionista"], {}, 2_490_900,
     lambda r: any("perfusionista" in a for a in r["avisos"])),
    ("anestesia general y bilateral en un examen: 77.000 x 1,75 + 50 % de 77.000",
     ["21101:anestesia:bilateral"], {}, 173_300, None),
    ("dos conjuntos, igual vía: mayor 100 % + 25 % del otro", ["502001", "503001"], {}, 2_863_500 + 552_300, None),
    ("dos conjuntos, diferente vía: mayor 100 % + 70 % del otro", ["502001:diferente_via", "503001"], {},
     2_863_500 + 1_546_500, None),
    ("art. 86 b: capítulo IV +15 % (71.800 -> 82.570 -> 82.600)", ["19001"], dict(region="META"), 82_600, None),
    ("art. 86 a: consulta especializada +25 % (79.100 -> 98.875 -> 98.900)", ["39143"], dict(region="META"), 98_900, None),
    ("art. 86: la estancia no se incrementa", ["38111"], dict(region="META"), 297_700, None),
    ("art. 86: municipio exceptuado", ["19001"], dict(region="META", exceptuado=True), 71_800, None),
    ("UVB 2025 (11.552): cirujano 48,09 -> 555.500; sala 79,55 -> 919.000; materiales 37,39 -> 431.900",
     ["1101:sin_anestesiologo:sin_ayudante"], dict(uvb=11552), 555_500 + 919_000 + 431_900, None),
    ("código inexistente da error", ["99999"], {}, 0, lambda r: r["errores"]),
]


def main():
    fallas = 0
    for desc, textos, op, esperado, extra in PRUEBAS:
        items, err = cz.leer_items(textos)
        r = cz.cotizar(items, D, **op) if not err else dict(total=None, errores=err)
        ok = r["total"] == esperado and (extra is None or bool(extra(r)))
        fallas += not ok
        print(f"  {'OK   ' if ok else 'FALLA'} {desc}" + ("" if ok else f"\n        esperado {esperado}, obtenido {r['total']}"))
    print(f"{len(PRUEBAS) - fallas}/{len(PRUEBAS)} pruebas correctas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
