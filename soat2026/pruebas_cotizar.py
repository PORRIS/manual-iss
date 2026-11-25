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
    ("art. 64 par. 4 a: conjunto + cirugía: el conjunto es la mayor y la cirugía adicional igual vía (50 % "
     "honorarios, sin sala ni materiales): 2.209.300 + 291.200 + 166.600 + 79.600",
     ["502001", "1101"], {}, 2_746_700, lambda r: [x["mayor"] for x in r["items"]] == [True, False]),
    ("art. 64 par. 4 a: conjunto + cirugía de otra especialidad: 2.209.300 + 582.400 + 75 % 333.100 + "
     "50 % 159.200 + 50 % 963.400", ["502001", "1101:otra_especialidad"], {},
     2_209_300 + 582_400 + 249_800 + 79_600 + 481_700, None),
    ("parto: ginecoobstetra grupo 07 410.700 + anestesiólogo 39116 226.500 (art. 48 a.2) + ayudante 108.300 + "
     "sala de parto 39220 774.000 (art. 50), sin materiales (art. 55 par. 3)",
     ["12101"], {}, 1_519_500, lambda r: not any(ln["concepto"] == "materiales" for ln in r["lineas"])),
    ("art. 55 par. 3: legrado obstétrico sin materiales: 196.800 + 141.600 + 347.200", ["12111"], {}, 685_600,
     lambda r: not any(ln["concepto"] == "materiales" for ln in r["lineas"])),
    ("cesárea 12110: sala y materiales de su grupo 08 (par. del art. 50): 476.800 + 281.600 + 124.900 + "
     "845.300 + 452.800", ["12110"], {}, 2_181_400, None),
    ("art. 73: dos cirugías del mismo especialista de otra especialidad: la segunda con cirujano al 50 %",
     ["1110", "1101:otra_especialidad:esp2", "1103:otra_especialidad:esp2"], {}, 6_774_000,
     lambda r: any("segunda cirugía del especialista 2" in ln["regla"] for ln in r["lineas"])),
    ("art. 73 sin especialista: cada cirugía de otra especialidad es de un especialista distinto (cirujano 100 %)",
     ["1110", "1101:otra_especialidad", "1103:otra_especialidad"], {}, 6_774_000 + 238_400, None),
    ("art. 52 y 55 par. 2: incruenta en un procedimiento del capítulo IV: 80.200 + 45 % (36.100) + 39305 105.600",
     ["37201:incruenta"], {}, 221_900, None),
    ("art. 70 par. 1: el bilateral avisa los órganos en que procede", ["1101:bilateral"], {}, 4_118_200,
     lambda r: any("art. 70 par. 1" in a for a in r["avisos"])),
    ("art. 55 par. 1: grupo 20 con materiales a precio de catálogo (exacto, sin centena): 3.744.600 + 850.000",
     ["1102"], dict(campos={"1102": dict(catalogo=850000)}), 4_594_600, None),
    ("art. 51: recuperación de más de 6 horas, 50 % de la estancia 38123 (325.800): 2.490.900 + 162.900",
     ["1101"], dict(campos={"1101": dict(recuperacion="media:38123")}), 2_653_800, None),
    ("art. 51: cirugía ambulatoria nivel 2, estancia de tres camas 38123: 2.490.900 + 325.800",
     ["1101"], dict(campos={"1101": dict(recuperacion="ambulatoria:2")}), 2_816_700, None),
    ("art. 51: grupo especial en UCI menos de 24 h, 50 % de 38525 (2.269.200): 3.744.600 + 1.134.600",
     ["1102"], dict(campos={"1102": dict(recuperacion="uci")}), 4_879_200, None),
    ("art. 51: UCI en un grupo 09 no procede (se ignora y avisa)", ["1101"],
     dict(campos={"1101": dict(recuperacion="uci")}), 2_490_900, lambda r: any("grupos especiales" in a for a in r["avisos"])),
    ("arts. 56 y 57: suministros y medicamentos a precio de catálogo: 2.490.900 + 2 x 850.000 + 3 x 30.000",
     ["1101"], dict(suministros=[dict(tipo="suministro", precio=850000, cantidad=2, descripcion="Placa"),
                                 dict(tipo="medicamento", precio=30000, cantidad=3)]), 4_280_900, None),
    ("art. 23 par. 1: radiografía sin lectura del radiólogo: 77.000 x 75 % = 57.750 -> 57.800", ["21101:sin_lectura"], {},
     57_800, None),
    ("art. 23 par. 3: embolización (ítem 5) + especialista igual a la tarifa: 2 x 925.900", ["21501:especialista"], {},
     1_851_800, None),
    ("art. 23 par. 3: aortograma (21434) tiene su propio código de especialista: no suma y avisa", ["21434:especialista"],
     {}, 587_100, lambda r: any("propio código" in a for a in r["avisos"])),
    ("art. 27 par. 2: registros en película +9,09 SMLDV = 9,09 x 3,7695 UVB x 12.110 -> 415.000", ["25100:pelicula"],
     {}, 882_700 + 415_000, None),
    ("art. 27 par. 2 en SMLDV: 9,09 x 58.363 = 530.519 -> 530.500", ["25100:pelicula"], dict(unidad="smldv"),
     1_128_700 + 530_500, None),
    ("art. 33: doppler color +30 %: 576.700 x 1,3 = 749.710 -> 749.700", ["31201:doppler"], {}, 749_700, None),
    ("art. 33: resonancia + adicional con contraste al 25 %: 1.570.200 + 392.550 -> 392.600",
     ["31301", "31301:rm_adicional"], {}, 1_962_800, None),
    ("art. 35 par. 3: acelerador lineal +30 % y simulación +8,84 SMLDV: 3.682.120 -> 3.682.100 + 403.500",
     ["33101:acelerador:simulacion"], {}, 4_085_600, None),
    ("opción del capítulo IV fuera de su artículo: se ignora y avisa", ["21101:doppler"], {}, 77_000,
     lambda r: any("no aplica" in a for a in r["avisos"])),
    ("art. 86 b: el especialista del art. 23 par. 3 también recibe +15 %: 2 x 925.900 x 1,15 -> 2 x 1.064.800",
     ["21501:especialista"], dict(region="META"), 2_129_600, None),
    ("art. 86 b: capítulo IV +15 % (71.800 -> 82.570 -> 82.600)", ["19001"], dict(region="META"), 82_600, None),
    ("art. 86 a: consulta especializada +25 % (79.100 -> 98.875 -> 98.900)", ["39143"], dict(region="META"), 98_900, None),
    ("art. 86: la estancia no se incrementa", ["38111"], dict(region="META"), 297_700, None),
    ("art. 86: municipio exceptuado", ["19001"], dict(region="META", exceptuado=True), 71_800, None),
    ("UVB 2025 (11.552): cirujano 48,09 -> 555.500; sala 79,55 -> 919.000; materiales 37,39 -> 431.900",
     ["1101:sin_anestesiologo:sin_ayudante"], dict(valor_unidad=11552), 555_500 + 919_000 + 431_900, None),
    ("SMLDV: 19001 1,57 x 58.363 = 91.629,91 -> 91.600 (igual al valor impreso)", ["19001"], dict(unidad="smldv"),
     91_600, lambda r: r["unidad_nombre"] == "SMLDV"),
    ("UVT: 19001 1,38 x 52.374 = 72.276,12 -> 72.300 (igual al impreso)", ["19001"], dict(unidad="uvt"), 72_300, None),
    ("UVT: 19016 0,74 x 52.374 = 38.756,76 -> 38.800 (el PDF imprime 38.600: factor con más decimales)",
     ["19016"], dict(unidad="uvt"), 38_800, None),
    ("SMLDV cirugía 1101 grupo 09: suma de las columnas SMLDV impresas 744.700 + 426.000 + 203.700 + "
     "1.231.500 + 579.000", ["1101"], dict(unidad="smldv"), 744_700 + 426_000 + 203_700 + 1_231_500 + 579_000, None),
    ("UVT sin factor en el PDF (25123) da error y sugiere otra unidad", ["25123"], dict(unidad="uvt"), 0,
     lambda r: "otra unidad" in r["errores"][0]),
    ("SMLDV con región: capítulo IV +15 % (91.600 -> 105.340 -> 105.300)", ["19001"],
     dict(unidad="smldv", region="META"), 105_300, None),
    ("código inexistente da error", ["99999"], {}, 0, lambda r: r["errores"]),
    ("contrato 0 %: valores del PDF tal cual, sin ajuste", ["1101"], dict(contrato_pct=0), 2_490_900,
     lambda r: r["ajuste_contrato"] == 0 and r["total_manual"] == r["total"]),
    ("contrato +4 % por línea: 605.700 + 346.400 + 165.600 + 1.001.900 + 470.900 (ajuste +99.600)",
     ["1101"], dict(contrato_pct=4), 2_590_500, lambda r: r["ajuste_contrato"] == 99_600 and r["total_manual"] == 2_490_900),
    ("contrato -5 %: 553.300 + 316.400 + 151.200 + 915.200 + 430.200", ["1101"], dict(contrato_pct=-5), 2_366_300, None),
    ("contrato después del art. 86: 71.800 -> +15 % 82.600 -> +4 % 85.904 -> 85.900", ["19001"],
     dict(region="META", contrato_pct=4), 85_900, None),
    ("contrato de -100 % o menos da error", ["19001"], dict(contrato_pct=-100), 0, lambda r: r["errores"]),
]


def main():
    fallas = 0
    for desc, textos, op, esperado, extra in PRUEBAS:
        items, err = cz.leer_items(textos)
        op = dict(op)
        for it in items:
            it.update((op.get("campos") or {}).get(it["codigo"], {}))
        op.pop("campos", None)
        r = cz.cotizar(items, D, **op) if not err else dict(total=None, errores=err)
        ok = r["total"] == esperado and (extra is None or bool(extra(r)))
        fallas += not ok
        print(f"  {'OK   ' if ok else 'FALLA'} {desc}" + ("" if ok else f"\n        esperado {esperado}, obtenido {r['total']}"))
    print(f"{len(PRUEBAS) - fallas}/{len(PRUEBAS)} pruebas correctas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
