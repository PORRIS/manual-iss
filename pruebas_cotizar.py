"""Pruebas de cotizar.py con resultados calculados a mano (tarifas del PDF).
Uso: uv run pruebas_cotizar.py"""
from cotizar import cargar, cotizar
from rutas import al_proyecto

al_proyecto()

D = cargar()
OP0 = {"solo-muestra": None, "biopsia-multiple": [], "portatil-rx": {}, "portatil-eco": [],
       "tecnecio": False, "bilateral": [], "mismo-acto": None, "region-134": None}


def total(items, **op):
    o = {**OP0, **{k.replace("_", "-"): v for k, v in op.items()}}
    filas, ajustes, errores, _ = cotizar(items, o, D)
    assert not errores, errores
    return round(sum(f["base"] for f in filas if f["base"] is not None)
                 + sum(a["monto"] for a in ajustes), 2)


def errores(items, **op):
    o = {**OP0, **{k.replace("_", "-"): v for k, v in op.items()}}
    return cotizar(items, o, D)[2]


CASOS = [
    # (descripción, items, opciones, total esperado, cálculo a mano)
    ("solo toma de muestra, art. 25 par. 3", ["903801"], dict(solo_muestra=[]),
     397.8, "3.315 x 12%"),
    ("biopsia múltiple, art. 26 par. 1", ["898101"], dict(biopsia_multiple=["898101"]),
     34352, "21.470 + 60%"),
    ("radiología portátil con fluoroscopia x2, art. 27 par. 4", ["871112x2"],
     dict(portatil_rx={"871112": "fluoroscopia"}), 130360, "2 x 18.875 + 2 x 46.305"),
    ("ecografía portátil, art. 27 par. 12", ["951301"], dict(portatil_eco=["951301"]),
     65010, "55.915 + 9.095"),
    ("tecnecio 99 + radioaerosoles, art. 27 par. 16", ["920302", "920304"],
     dict(tecnecio=True), 333620, "81.735 + 135.540 + 13.120 + 103.225 (una vez)"),
    ("radioaerosoles automático, art. 27 par. 16", ["920302"], {},
     184960, "81.735 + 103.225"),
    ("conjunto bilateral, art. 95 par. 6", ["C40402"], dict(bilateral=["C40402"]),
     2800338.5, "1.806.670 + 55%"),
    # art. 95 par. 7: varios conjuntos en un mismo acto
    ("mismo acto, igual vía, art. 95 par. 7 b", ["C40403", "C40402"], dict(mismo_acto="igual"),
     2003560, "1.806.670 + 25% x 787.560"),
    ("mismo acto, igual vía, mismo conjunto x2", ["C40403x2"], dict(mismo_acto="igual"),
     984450, "787.560 + 25% x 787.560"),
    ("mismo acto, diferente vía, 3 conjuntos", ["C40402", "C40403", "C40404"],
     dict(mismo_acto="diferente"), 2824935.5, "1.806.670 + 70% x (787.560 + 667.105)"),
    ("mismo acto + región art. 134", ["C40402", "C40403"],
     dict(mismo_acto="diferente", region_134="La Guajira:Maicao"), 2688076.68,
     "(1.806.670 + 70% x 787.560) + 14%"),
    # cirugías en UVR (uvr.py): honorarios + derechos de sala + materiales
    ("UVR: 386100 (55 UVR) en quirófano", ["386100"], {}, 261235,
     "55 x (1.270 + 960) + sala S23203 81.175 + materiales S55105 57.410"),
    ("UVR: 386100 en sala especial con anestesia local", ["386100"],
     {"uvr_sala": {"386100": "especial"}, "sin_anestesia": ["386100"]}, 134710,
     "55 x 1.270 + sala S22205 40.590 + materiales S55114 24.270"),
    ("UVR: bilateral +75% (art. 64, 77 par. 5, 85 par. 5)", ["386100"], dict(bilateral=["386100"]),
     457161.25, "1,75 x (122.650 + 81.175 + 57.410)"),
    ("UVR: «UNI Ó BILATERAL» sin recargo aunque se declare", ["797501"], dict(bilateral=["797501"]),
     155430, "35 x 2.230 + sala S23201 44.270 + materiales S55103 33.110"),
    ("UVR: mismo acto igual vía con ayudante (art. 65, 77 par. 6)", ["487702", "386100"],
     dict(mismo_acto="igual", ayudante=["487702", "386100"]), 1304072.5,
     "487702: 300 x 2.590 + sala 401.015 (materiales por consumo) + 386100: 60% x 142.450 + 50% x 81.175"),
    ("UVR: mismo acto diferente vía (art. 66)", ["487702", "386100"], dict(mismo_acto="diferente"),
     1162002.5, "300 x 2.230 + 401.015 + 75% x 55 x 2.230"),
    ("UVR: región art. 134 a (+30% honorarios y sala)", ["386100"], dict(region_134="META:Granada"),
     1.3 * (122650 + 81175) + 57410, "1,3 x (122.650 + 81.175) + 57.410"),
    ("UVR: recuperación más de 6 horas, complejidad alta (art. 84)", ["386100"],
     {"recuperacion": {"386100": "alta"}}, 309680, "261.235 + S24103 48.445"),
    ("UVR: más de 170 UVR con hoja de gasto (art. 85 par. 1)", ["849501"],
     dict(ayudante=["849501"], materiales={"849501": 500000}), 2900000,
     "600 x (1.270 + 960 + 360 + 1.410) + hoja de gasto 500.000"),
    ("UVR: ayudante de igual especialidad desde 450 UVR (art. 63 par.)", ["849501"],
     dict(ayudante_especialista=["849501"]), 2760000, "600 x (1.270 + 960 + 960 + 1.410)"),
    ("UVR: ayudante de igual especialidad con menos de 450 UVR: a $360", ["487702"],
     dict(ayudante=["487702"], ayudante_especialista=["487702"]), 300 * 2590 + 401015,
     "300 x (1.270 + 960 + 360) + sala 401.015"),
    ("UVR: hoja de gasto sin recargo bilateral", ["849501"],
     dict(bilateral=["849501"], materiales={"849501": 500000}), 1.75 * 600 * (1270 + 960 + 1410) + 500000,
     "1,75 x 600 x (1.270 + 960 + 1.410) + 500.000"),
    ("UVR: hasta 170 UVR la hoja de gasto no se usa (tarifa fija)", ["386100"],
     dict(materiales={"386100": 100000}), 261235, "igual que sin hoja"),
    ("UVR: múltiples con hoja de gasto", ["487702", "386100"],
     dict(mismo_acto="igual", ayudante=["487702", "386100"], materiales={"487702": 300000}), 1604072.5,
     "1.304.072,5 + hoja de gasto 300.000"),
    # art. 85 par. 1 y 5: múltiples con todas de 170 UVR o menos: materiales por tabla, 100 % + 50 %
    ("UVR: múltiples igual vía, todas <= 170 UVR: materiales 100 % + 50 % (art. 85 par. 5)", ["386100", "797501"],
     dict(mismo_acto="igual"), 346755,
     "386100: 122.650 + 81.175 + 57.410; 797501: 60% x 78.050 + 50% x 44.270 + 50% x 33.110"),
    ("UVR: múltiples diferente vía, todas <= 170 UVR: adicional sin sala ni materiales (solo politrauma)",
     ["386100", "797501"], dict(mismo_acto="diferente"), 319772.5, "261.235 + 75% x 78.050"),
    # politrauma: art. 65 par., art. 77 par. 6 y art. 85 par. 5
    ("UVR: igual vía, tercera cirugía sin politrauma: no se paga (art. 65 par.)", ["386100", "797501x2"],
     dict(mismo_acto="igual"), 346755, "igual que con dos"),
    ("UVR: igual vía con politrauma: la tercera también al 60 % / 50 %", ["386100", "797501x2"],
     dict(mismo_acto="igual", politrauma=True), 432275, "346.755 + 46.830 + 22.135 + 16.555"),
    ("UVR: diferente vía con politrauma: sala y materiales 50 % hasta la tercera adicional", ["386100", "797501x4"],
     dict(mismo_acto="diferente", politrauma=True), 611455,
     "261.235 + 3 x (58.537,5 + 22.135 + 16.555) + 58.537,5"),
    # art. 77 par. 7: accesorios que se pagan aparte, por cada procedimiento
    ("UVR: colecistectomía laparoscópica + trocar de primera punción (art. 77 par. 7)", ["512104"],
     dict(accesorios={"512104": ["trocar"]}), 1018405, "714.410 + 303.995"),
    ("UVR: trocar por cada procedimiento (x2, actos distintos)", ["512104x2"],
     dict(accesorios={"512104": ["trocar"]}), 2036810, "2 x (714.410 + 303.995)"),
    ("UVR: cuchilla de artroscopio en artroscopia diagnóstica: no se suma (solo terapéuticas)", ["802501"],
     dict(accesorios={"802501": ["cuchilla"]}), 381840, "igual que sin cuchilla"),
    # art. 65: endoscópicos sin porcentaje adicional; artroscopias 60 % solo con grupos de complejidad distintos
    ("UVR: igual vía, cistoscopia adicional por vía endoscópica: sin porcentaje adicional (art. 65)",
     ["560100", "573201"], dict(mismo_acto="igual"), 692970, "solo la mayor: 254.000 + 192.000 + 246.970"),
    ("UVR: igual vía, dos artroscopias del mismo grupo (C40465): la adicional no se paga (art. 65)",
     ["806103", "807603"], dict(mismo_acto="igual"), 517155, "solo la mayor"),
    ("UVR: igual vía, artroscopias de grupos distintos (C40467 y C40465): 60 % / 50 % (art. 65)",
     ["814504", "806103"], dict(mismo_acto="igual"), 892122.5,
     "670.670 + 60% x (139.700 + 105.600) + 50% x 148.545 (materiales por consumo, >170)"),
    ("UVR: igual vía, mayor abierta + artroscopia adicional: 60 % normal", ["849501", "806103"],
     dict(mismo_acto="igual"), 2405452.5, "2.184.000 + 60% x 245.300 + 50% x 148.545"),
    # art. 80 par. 2: sala de endoscopia, una vez por paciente
    ("UVR: extracción endoscópica de cálculos biliares en endoscopia + papilótomo y litotripsia (art. 80 par. 2)",
     ["518801"], dict(uvr_sala={"518801": "endoscopia"}, sin_anestesia=["518801"],
                      accesorios={"518801": ["papilotomo", "litotripsia"]}),
     565400, "158.750 + sala S22234 61.230 + S55114 24.270 + 121.075 + 200.075 (sin anestesiólogo, art. 80)"),
    ("UVR: papilótomo en quirófano: no se suma (solo sala de endoscopia)", ["518801"],
     dict(accesorios={"518801": ["papilotomo"]}), 562940, "igual que sin papilótomo"),
    # art. 67: distinta especialidad
    ("UVR: distinta especialidad, cada uno su mayor (art. 67): anestesiólogo 75 % en la segunda",
     ["386100", "797501"], dict(mismo_acto="distinta", especialista={"386100": "1", "797501": "2"}), 408265,
     "261.235 + 35 x 1.270 + 75% x 35 x 960 + 44.270 + 33.110"),
    ("UVR: distinta especialidad, mismo especialista en las dos: cirujano 60 %, sala y materiales 50 %",
     ["386100", "797501"], dict(mismo_acto="distinta"), 351795,
     "261.235 + 60% x 44.450 + 75% x 33.600 + 50% x 44.270 + 50% x 33.110"),
    ("UVR: distinta especialidad con ayudante: 100 % + 50 % (art. 67 par. 2); materiales por consumo (>170)",
     ["487702", "386100"], dict(mismo_acto="distinta", ayudante=["487702", "386100"],
                                especialista={"487702": "1", "386100": "2"}), 1378540,
     "487702: 381.000 + 288.000 + 108.000 + 401.015; 386100: 69.850 + 75% x 52.800 + 50% x 19.800 + 81.175"),
    ("UVR: recuperación en UCI adulto menos de 24 h: 50 % de S12103 (art. 84 par.)", ["386100"],
     {"recuperacion": {"386100": "uci-adulto"}}, 261235 + 271480, "261.235 + 50% x 542.960"),
    ("UVR: recuperación en intermedios neonatal menos de 24 h: 50 % de S12201", ["386100"],
     {"recuperacion": {"386100": "intermedio-neonatal"}}, 261235 + 119405, "261.235 + 50% x 238.810"),
    ("UVR: la EPS aporta la instrumentación (art. 77 par. 4)", ["386100"],
     {"descuento_sala": "instrumentacion"}, 245000, "261.235 - 20% x sala 81.175"),
    ("UVR: la EPS aporta instrumentación y enfermería", ["386100"], {"descuento_sala": "ambos"},
     224706.25, "261.235 - 45% x 81.175"),
    # Capítulo II con anestesia general o regional (arts. 62 y 78) y materiales del art. 85 par. 3 y 4
    ("Cap. II con anestesia: renopunción, anestesiólogo 50 % (art. 62) y quirófano 80 % (art. 78)", ["559210"],
     dict(anestesia_cap2=["559210"]), 206091.5, "89.605 + 50% x 89.605 + 80% x 89.605"),
    ("Cap. II con anestesia, dos procedimientos: una vez, sobre el de tarifa superior", ["559210", "220100"],
     dict(anestesia_cap2=["559210", "220100"]), 216456.5, "89.605 + 10.365 + 44.802,5 + 71.684"),
    ("Cap. II con anestesia: resonancia, anestesiólogo S41233 + quirófano 80 % + materiales S55116", ["883101"],
     dict(anestesia_cap2=["883101"]), 743358, "366.035 + 60.225 + 292.828 + 24.270"),
    ("Cap. II con anestesia: TAC, anestesiólogo S41232 + quirófano 80 % + S55116", ["879111"],
     dict(anestesia_cap2=["879111"]), 228051, "97.045 + 29.100 + 77.636 + 24.270"),
    ("art. 27 par. 8: trombólisis intracraneal, quirófano o sala especial 60 % + S55116 (art. 85 par. 4)",
     ["380110"], {}, 3475566, "2.157.060 + 60% x 2.157.060 + 24.270"),
    ("art. 85 par. 3: terapia electroconvulsiva S41230 + materiales S55115", ["S41230"], {}, 39450,
     "29.100 + 10.350"),
    # art. 134: al final, sobre lo que efectivamente se paga por cada ítem
    ("región art. 134, laboratorio", ["903801"], dict(region_134="META:Granada"),
     3812.25, "3.315 + 15%"),
    ("región art. 134 + solo muestra", ["903801"],
     dict(solo_muestra=[], region_134="META:Granada"), 457.47, "(3.315 x 12%) + 15%"),
    ("región art. 134 + conjunto bilateral", ["C40402"],
     dict(bilateral=["C40402"], region_134="CHOCO:Quibdó"), 3192385.89,
     "(1.806.670 + 55%) + 14%"),
    ("región art. 134 + adicionales por paciente", ["920302"],
     dict(tecnecio=True, region_134="Chocó:Quibdó"), 227792,
     "(81.735 + 13.120 + 103.225) + 15%"),
    ("región art. 134 literal a: consulta (art. 75)", ["890201"],
     dict(region_134="META:Granada"), 11381.5, "8.755 + 30%"),
    ("región art. 134 literal a: perfusionista queda fuera (pendiente de consulta)", ["399601"],
     dict(region_134="META:Granada"), 105980, "105.980 sin incremento"),
    ("región art. 134 no aplica fuera del Cap. II (ambulancia, art. 93)", ["S31301"],
     dict(region_134="META:Granada"), 50855, "50.855 sin incremento"),
    ("región art. 134, ciudad exceptuada (par. 2)", ["903801"],
     dict(region_134="META:Villavicencio"), 3315, "3.315 sin incremento"),
]
ERRORES = [
    ("bilateral fuera de alcance", ["903801"], dict(bilateral=["903801"]), "no aplica"),
    ("región 134 sin municipio", ["903801"], dict(region_134="META"), "indique también el municipio"),
    ("región 134 departamento fuera de la lista", ["903801"],
     dict(region_134="ANTIOQUIA:Medellín"), "no está entre los departamentos"),
    ("mismo acto con un solo conjunto (literal a)", ["C40402", "903801"],
     dict(mismo_acto="igual"), "no procede su valor"),
    ("mismo acto igual vía con 3 conjuntos", ["C40402", "C40403", "C40404"],
     dict(mismo_acto="igual"), "pendiente de consulta"),
    ("mismo acto con bilateral", ["C40402", "C40403"],
     dict(mismo_acto="diferente", bilateral=["C40402"]), "pendiente de consulta"),
    ("mismo acto sin conjuntos", ["903801"], dict(mismo_acto="igual"), "no tiene conjuntos"),
    ("ayudante en un código que no es cirugía en UVR", ["903801"], dict(ayudante=["903801"]),
     "no tiene cirugías en UVR"),
    ("sala no válida para cirugía en UVR", ["386100"], {"uvr_sala": {"386100": "cocina"}}, "sala no válida"),
    ("descuento de sala no válido", ["386100"], {"descuento_sala": "todo"}, "no válido"),
    ("hoja de gasto con valor no numérico", ["849501"], {"materiales": {"849501": "mucho"}}, "hoja de gasto"),
    ("hoja de gasto de un código que no está", ["849501"], {"materiales": {"386100": 1000}}, "no es una cirugía en UVR"),
    ("politrauma sin mismo acto", ["386100", "797501"], {"politrauma": True}, "--politrauma"),
    ("accesorio no válido", ["512104"], {"accesorios": {"512104": ["grapadora"]}}, "--accesorio 512104:grapadora"),
    ("anestesia Cap. II en una cirugía en UVR", ["386100", "559210"], {"anestesia_cap2": ["386100"]},
     "es una cirugía en UVR"),
    ("anestesia Cap. II con un código S4123x ya agregado", ["559210", "S41234"], {"anestesia_cap2": ["559210"]},
     "use una sola forma"),
    ("recuperación con complejidad no válida", ["386100"], {"recuperacion": {"386100": "extrema"}},
     "complejidad no válida"),
    ("tecnecio sin medicina nuclear", ["903801"], dict(tecnecio=True), "ningún ítem"),
    ("TAC portátil no aplica", ["879111"], dict(portatil_rx={"879111": "simple"}), "no aplica"),
    ("código de la opción que no está en la cotización", ["898101"],
     dict(biopsia_multiple=["898102"]), "no está en la cotización"),
    ("variante portátil no válida", ["871112"], dict(portatil_rx={"871112": "otra"}),
     "variante no válida"),
]

fallas = 0
# suministros del art. 88 (pág. 161): compra + 12 %; tutor en préstamo 25 % de eso (par. 2)
from cotizar import liquidar_suministros
SUMI = [
    ("art. 88: 2 placas de $850.000 + 12 %", [dict(descripcion="placa", precio=850000, cantidad=2)], 1_904_000),
    ("art. 87 a: medicamento, prestador externo: 3 x $100.000 + 12 %",
     [dict(precio=100000, cantidad=3, tipo="med_externo")], 336_000),
    ("art. 87 b: medicamento, prestador interno: 3 x $100.000 + 5 %",
     [dict(precio=100000, cantidad=3, tipo="med_interno")], 315_000),
    ("art. 88 par. 2: tutor en préstamo de $2.000.000: 25 % de 2.240.000", [dict(precio=2_000_000, prestamo=True)], 560_000),
]
for desc, lista, esperado in SUMI:
    lineas, err = liquidar_suministros(lista)
    obtenido = sum(x["monto"] for x in lineas)
    ok = not err and abs(obtenido - esperado) < 0.01
    fallas += not ok
    print(f"{'OK ' if ok else 'MAL'} {desc}: {obtenido:,.2f} (esperado {esperado:,.2f})")
ok = bool(liquidar_suministros([dict(precio=0)])[1])
fallas += not ok
print(f"{'OK ' if ok else 'MAL'} error esperado - suministro con precio 0")
ok = bool(liquidar_suministros([dict(precio=1000, prestamo=True, tipo="med_externo")])[1])
fallas += not ok
print(f"{'OK ' if ok else 'MAL'} error esperado - préstamo en un medicamento")
for desc, items, op, esperado, calculo in CASOS:
    obtenido = total(items, **op)
    ok = abs(obtenido - esperado) < 0.01
    fallas += not ok
    print(f"{'OK ' if ok else 'MAL'} {desc}: {obtenido:,.2f} (esperado {esperado:,.2f} = {calculo})")
for desc, items, op, frase in ERRORES:
    e = errores(items, **op)
    ok = any(frase in x for x in e)
    fallas += not ok
    print(f"{'OK ' if ok else 'MAL'} error esperado - {desc}: {e[0][:90] if e else 'sin error'}")
n = len(CASOS) + len(ERRORES) + len(SUMI) + 2
print(f"\n{n - fallas}/{n} pruebas correctas")
raise SystemExit(1 if fallas else 0)
