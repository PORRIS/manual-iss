"""Pruebas de auditar.py con las facturas ficticias de ejemplos/ (resultados calculados a mano).
Uso: uv run pruebas_auditar.py"""
from auditar import auditar, leer_factura
from cotizar import cargar
from rutas import BASE, al_proyecto

al_proyecto()
D = cargar()
OP0 = {"solo-muestra": None, "biopsia-multiple": [], "portatil-rx": {}, "portatil-eco": [],
       "tecnecio": False, "bilateral": [], "mismo-acto": None, "region-134": None}


def leer(nombre):
    return leer_factura(nombre, (BASE / "ejemplos" / nombre).read_bytes())


def lineas(res):
    return {(x["codigo"], x["estado"]) for x in res["lineas"]}


rips = leer("rips_ejemplo.json")
xml = leer("factura_ejemplo.xml")
u1 = auditar(rips["grupos"][0]["lineas"], OP0, D)
u2 = auditar(rips["grupos"][1]["lineas"], OP0, D)
x_igual = auditar(xml["grupos"][0]["lineas"], {**OP0, "mismo-acto": "igual"}, D)
choco = auditar(rips["grupos"][0]["lineas"], {**OP0, "region-134": "CHOCO:Quibdó"}, D)
tipos = lambda res, cod: {a["tipo"] for x in res["lineas"] if x["codigo"] == cod for a in x["alertas"]}  # noqa: E731

contrato = auditar(rips["grupos"][0]["lineas"], OP0, D, contrato_pct=30)
mismo_momento = auditar([dict(codigo="903801", cantidad=1, valor_unitario=3315, fecha="2026-10-01 08:00"),
                         dict(codigo="903801", cantidad=1, valor_unitario=3315, fecha="2026-10-01 08:00"),
                         dict(codigo="903801", cantidad=1, valor_unitario=3315, fecha="2026-10-01 14:00")], OP0, D)
otros = leer_factura("x.json", b'{"numDocumentoIdObligado": "1", "numFactura": "F1", "usuarios": [{"tipoDocumentoIdentificacion": "CC", "numDocumentoIdentificacion": "123456", "fechaNacimiento": "1980-05-02", "consecutivo": 1, "servicios": {"otros_servicios": [{"codTecnologiaSalud": "X1", "tipoOS": "01", "cantidadOS": 2, "vrUnitOS": 100, "fechalnicioAtencion": "2026-01-01 10:00"}, {"codTecnologiaSalud": "S31301", "tipoOS": "02", "cantidadOS": 1, "vrUnitOS": 50855}], "hospitalizacion": [{"fechaInicioAtencion": "2026-01-01 09:00", "codDiagnosticoPrincipal": "K359", "codDiagnosticoPrincipalCIE11": "DB10"}]}}]}')["grupos"][0]

homo_rips = auditar([dict(codigo="903883", cantidad=1, valor_unitario=3125, seccion="procedimientos"),
                     dict(codigo="028302", cantidad=1, valor_unitario=227340, seccion="procedimientos")], OP0, D)
sin_pdf = auditar([dict(codigo="783001", cantidad=1, valor_unitario=1000, seccion="procedimientos")], OP0, D)
homo_dig = auditar([dict(codigo="028302", cantidad=1, valor_unitario=227340)], OP0, D)

CASOS = [
    ("RIPS: 2 usuarios, 6 líneas + 1 medicamento no tarifado (art. 87)",
     [len(rips["grupos"]), len(rips["grupos"][0]["lineas"]), len(rips["grupos"][0]["no_tarifadas"])], [2, 6, 1]),
    ("RIPS: otrosServicios con cantidad", [(x["codigo"], x["cantidad"]) for x in rips["grupos"][0]["lineas"]][-1], ("871112", 2)),
    ("RIPS: documento enmascarado", rips["grupos"][0]["etiqueta"], "Usuario 1 · CC ****0001"),
    ("XML: número y líneas", (xml["factura"], len(xml["grupos"][0]["lineas"])), ("FE-EJEMPLO-2", 2)),
    ("sobrecobro 903801: 4.000 - 3.315 = 685", round(next(x["glosa"] for x in u1["lineas"] if x["codigo"] == "903801"), 2), 685),
    ("estados usuario 1", lineas(u1), {("890201", "Conforme"), ("903801", "Glosa"), ("C40402", "Conforme"),
                                       ("512104", "Revisar"), ("999999", "Revisar"), ("871112", "Conforme")}),
    ("doble cobro: 512104 es componente de C40402 (art. 95)", "Doble cobro" in tipos(u1, "512104"), True),
    ("código inexistente", "Código" in tipos(u1, "999999"), True),
    ("radioaerosoles por paciente dentro de la línea: 81.735 + 103.225", (u2["lineas"][0]["esperado"], u2["lineas"][0]["estado"]),
     (184960, "Conforme")),
    ("mismo acto igual vía: C40403 al 25 % -> glosa 590.670", round(x_igual["resumen"]["glosa_sugerida"], 2), 590670),
    ("contrato ISS + 30 %: 903801 = 3.315 x 1,3", next(x["esperado"] for x in contrato["lineas"] if x["codigo"] == "903801"), 4309.5),
    ("misma fecha y hora = posible doble registro; otra hora no",
     [any(a["tipo"] == "Repetido" for a in x["alertas"]) for x in mismo_momento["lineas"]], [True, True, False]),
    ("otros_servicios (alias): insumo tipoOS 01 a 'sin tarifa' (art. 88), traslado se compara",
     ([o["codigo"] for o in otros["no_tarifadas"]], [x["codigo"] for x in otros["lineas"]]), (["X1"], ["S31301"])),
    ("episodio de hospitalización con CIE-11 (Res. 948) y edad calculada",
     (otros["episodios"][0]["datos"].get("codDiagnosticoPrincipalCIE11"), otros["usuario"]["edad_en_la_atencion"],
      otros["usuario"]["numDocumentoIdentificacion"]), ("DB10", 45, "**3456")),
    ("RIPS: CUPS 903883 se compara como ISS 903840 y CUPS 028302 como ISS 377800 (relación CUPS 2026)",
     [(x["codigo_factura"], x["manual"]["codigo"], x["estado"]) for x in homo_rips["lineas"]],
     [("903883", "903840", "Revisar"), ("028302", "377800", "Revisar")]),
    ("glucometría: relación en revisión (sugerido M19275, no aplicado)",
     [a["tipo"] for a in homo_rips["lineas"][0]["alertas"] if a["tipo"] == "Relación dudosa"], ["Relación dudosa"]),
    ("CUPS cuyo código ISS no está en el PDF: Revisar con la novedad",
     (sin_pdf["lineas"][0]["estado"], "novedad registrada" in sin_pdf["lineas"][0]["alertas"][0]["texto"]),
     ("Revisar", True)),
    ("línea digitada: el código se toma como ISS, sin homologar", homo_dig["lineas"][0]["manual"]["codigo"], "028302"),
    ("región art. 134: 903801 = 3.315 + 15 %", next(x["esperado"] for x in choco["lineas"] if x["codigo"] == "903801"), 3812.25),
]
fallas = 0
for desc, obtenido, esperado in CASOS:
    ok = obtenido == esperado or (isinstance(esperado, (int, float)) and abs(obtenido - esperado) < 0.01)
    fallas += not ok
    print(f"{'OK ' if ok else 'MAL'} {desc}: {obtenido}" + ("" if ok else f" (esperado {esperado})"))
print(f"\n{len(CASOS) - fallas}/{len(CASOS)} pruebas correctas")
raise SystemExit(1 if fallas else 0)
