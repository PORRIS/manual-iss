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
    ("tecnecio sin medicina nuclear", ["903801"], dict(tecnecio=True), "ningún ítem"),
    ("TAC portátil no aplica", ["879111"], dict(portatil_rx={"879111": "simple"}), "no aplica"),
    ("código de la opción que no está en la cotización", ["898101"],
     dict(biopsia_multiple=["898102"]), "no está en la cotización"),
    ("variante portátil no válida", ["871112"], dict(portatil_rx={"871112": "otra"}),
     "variante no válida"),
]

fallas = 0
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
print(f"\n{len(CASOS) + len(ERRORES) - fallas}/{len(CASOS) + len(ERRORES)} pruebas correctas")
raise SystemExit(1 if fallas else 0)
