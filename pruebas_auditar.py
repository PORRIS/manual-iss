"""Pruebas de auditar.py con las facturas ficticias de ejemplos/ (resultados calculados a mano).
Uso: uv run pruebas_auditar.py"""
import io

import openpyxl

import soat_versiones as sv
import tarifas_propias as tp
from auditar import auditar, auditar_tarifa, cargar_tarifas, leer_factura
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

T = cargar_tarifas()


def tarifa(t, lineas, **k):
    return auditar_tarifa(lineas, t, T, **k)["lineas"]


P = "procedimientos"
soat = tarifa("soat", [dict(codigo="903841", valor_unitario=22887.9, seccion=P),
                       dict(codigo="903841", valor_unitario=30000, seccion=P),
                       dict(codigo="890202", valor_unitario=79078.3, seccion="consultas"),
                       dict(codigo="890202", valor_unitario=50000, seccion="consultas"),
                       dict(codigo="010101", valor_unitario=100000, seccion=P)])
# Cirugía SOAT (grupo quirúrgico): CUPS 541701 -> SOAT 7144, grupo 07; valores reales de un RIPS
# liquidado con la UVB 2025 ($11.552)
cir = [auditar_tarifa([dict(codigo="541701", valor_unitario=u, seccion=P)], "soat", T, uvb=11552)["lineas"][0]
       for u in (1893200, 363100, 2500000, 5000000)]
cir_g3 = auditar_tarifa([dict(codigo="10101", valor_unitario=1)], "soat", T)["lineas"][0]
soat_uvb = tarifa("soat", [dict(codigo="903841", valor_unitario=21833.28, seccion=P)], uvb=11552)
soat_contrato = tarifa("soat", [dict(codigo="903841", valor_unitario=23803.42, seccion=P)], contrato_pct=4)


def excel(hojas):
    """Excel en memoria: {hoja: [filas]} (la primera fila es la cabecera)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, filas in hojas.items():
        ws = wb.create_sheet(nombre)
        for f in filas:
            ws.append(f)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# Manuales de tarifas propias en una base temporal (en memoria)
ENG = tp.motor("sqlite://")
CAB = ["Código", "Descripción", "Tarifa", "Tipo liquidación", "Factor %"]
va = tp.guardar(excel({
    "CUPS": [["Tarifario de prueba"], [], CAB, ["890202", "CONSULTA ESPECIALISTA", "$ 79.000", "", ""],
             ["903841", "GLUCOSA", "", "SOAT", "-10"], ["903883", "GLUCOMETRIA", "", "ISS", ""],
             ["890202", "CONSULTA ESPECIALISTA", 79000, "", ""]],
    "CUMS": [CAB, ["MED-001", "ACETAMINOFEN", 58000]],
    "INSUMOS": [CAB, [50010194, "PROTESIS FACIAL", "11.292.000"]],
    "OTRA HOJA": [["x"]]}), "a.xlsx", "tar-prueba-01", "Tarifario de prueba", "valor_fijo",
    estado="activo", inicio="2026-01-01", fin="2026-12-31", eng=ENG)
vb = tp.guardar(excel({"CUPS": [CAB, ["890202", "CONSULTA", 79000]]}), "b.xlsx", "TAR-PRUEBA-01",
                "Tarifario de prueba", "soat", -5, estado="borrador", eng=ENG)
PA, PB = tp.cargar_version(va["id"], ENG), tp.cargar_version(vb["id"], ENG)
# Versión SOAT subida (misma tabla, UVB 12.600): se elige al auditar
vs = sv.guardar((BASE / "soat" / "SOAT A SALARIO MINIMO_UVT_UVB.xlsx").read_bytes(), "soat.xlsx", 2027,
                "SOAT 2027 prueba", 12600, eng=ENG)
T27, uvb27, _ = sv.aplicar(T, vs["id"], eng=ENG)
glu = [auditar_tarifa([dict(codigo="903841", valor_unitario=23814, seccion=P)], "soat", t, uvb=u)["lineas"][0]["estado"]
       for t, u in ((T, 12110), (T27, uvb27))]
# Plantillas: se descargan, se llenan y se vuelven a subir con el mismo cargador
from rutas import conectar  # noqa: E402

pl_soat, _ = sv.plantilla(conectar())
wb = openpyxl.load_workbook(io.BytesIO(pl_soat))
for fila in wb["TD"].iter_rows(min_row=4):
    if fila[0].value == "UVB":
        fila[1].value = 12600  # la persona escribe la UVB nueva como número
buf = io.BytesIO()
wb.save(buf)
tar_pl, uvb_pl, calc_pl = sv.leer_excel(buf.getvalue())
pl_prop = openpyxl.load_workbook(io.BytesIO(tp.plantilla()))
pl_prop["CUPS"].append(["010101", "PUNCION CISTERNAL", 150000])
pl_prop["CUMS"].append(["19933174-1", "ACETAMINOFEN", "1.200"])
buf = io.BytesIO()
pl_prop.save(buf)
filas_pl, avisos_pl = tp.leer_excel(buf.getvalue())

# Cirugías ISS en UVR (líneas digitadas: el código es ISS)
def uvr_linea(cod, valor, **op):
    return auditar([dict(codigo=cod, cantidad=1, valor_unitario=valor)], {**OP0, **op}, D,
                   op.pop("contrato", 0) if "contrato" in op else 0)["lineas"][0]


u_completa = uvr_linea("487702", 1178015)   # 300 UVR: 381.000 + 288.000 + 108.000 + sala S23311 401.015
u_adicional = uvr_linea("386100", 126057.5)  # 55 UVR: 60% x 142.450 + 50% x sala S23203 81.175
u_bilateral = uvr_linea("386100", 1.75 * (142450 + 81175 + 57410))  # +75% honorarios, sala y materiales S55105
u_unibi = uvr_linea("797501", 1)            # «UNI Ó BILATERAL»: sin escenario bilateral
u_region = uvr_linea("386100", 1.3 * 142450 + 1.3 * 81175 + 57410, **{"region-134": "META:Granada"})
u_contrato = auditar([dict(codigo="386100", cantidad=1, valor_unitario=1.2 * (142450 + 81175 + 57410))],
                     OP0, D, 20)["lineas"][0]
u_caro = uvr_linea("386100", 2_000_000)

# SOAT: perfusionista (47.2), incruenta (51, 54.3), otra especialidad (72, 48.2), anestesia de
# diagnóstico (47.1.3); ISS UVR: descuento de sala (77 par. 4), recuperación (84), art. 67
def soat_linea(cod, valor, **k):
    return auditar_tarifa([dict(codigo=cod, valor_unitario=valor, seccion=P)], "soat", T, **k)["lineas"][0]


s_perf = soat_linea("525301", 3744654 + 379406.3)   # grupo 20: completa + perfusionista 39129
s_incr = soat_linea("541701", 1104947)              # grupo 07: cir + anest + 45% sala + 39305
s_esp = soat_linea("541701", 1031651)               # grupo 07: cir + 75% anest + 50% ayud + 50% sala
s_anest = [soat_linea("881201", 288823.5, anestesia_diag=m)["estado"] for m in ({"881201"}, set())]
i_dto = auditar([dict(codigo="386100", cantidad=1, valor_unitario=245000)],
                {**OP0, "descuento-sala": "instrumentacion"}, D)["lineas"][0]
i_rec = uvr_linea("386100", 329480)  # completa con ayudante 281.035 + recuperación alta S24103 48.445
i_esp = uvr_linea("386100", 200525)   # 69.850 + 75% x 52.800 + 50% x 19.800 + sala 81.175

lp = [dict(codigo="890202", valor_unitario=80000, seccion="consultas"),
      dict(codigo="50010194", valor_unitario=11292000, seccion="otrosServicios", datos={"tipoOS": "01"}),
      dict(codigo="MED-001", valor_unitario=58000, seccion="medicamentos"),
      dict(codigo="903841", valor_unitario=20599.11, seccion=P),
      dict(codigo="903883", valor_unitario=3125, seccion=P),
      dict(codigo="903801", valor_unitario=5000, seccion=P)]
propia_a = auditar_tarifa(lp, "propia", T, propia=PA, d=D)
propia_b = auditar_tarifa([dict(codigo="903841", valor_unitario=21743.51, seccion=P)], "propia", T,
                          propia=PB, d=D)

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
    ("SOAT: 903841 -> 19490 (1,89 UVB x 12.110 = 22.887,9): igual Conforme, 30.000 Glosa 7.112,1",
     [(x["manual"]["codigo"], x["estado"], round(x["glosa"], 1)) for x in soat[:2]],
     [("19490", "Conforme", 0), ("19490", "Glosa", 7112.1)]),
    ("SOAT con varias opciones: coincide con una -> Conforme; entre opciones -> Revisar",
     [(x["estado"], x["alertas"][0]["tipo"]) for x in soat[2:4]], [("Conforme", "Varias opciones"), ("Revisar", "Varias opciones")]),
    ("SOAT cirugía grupo 07 (UVB 2025): completa 1.893.200 y adicional igual vía 363.100 Conforme; "
     "entre opciones Revisar; por encima de la bilateral Glosa",
     [(x["estado"], round(x["esperado"])) for x in cir],
     [("Conforme", 1893026), ("Conforme", 362906), ("Revisar", 1893026), ("Glosa", 3128975)]),
    ("SOAT cirugía: el escenario elegido queda explicado por componente",
     ("Cirugía completa (grupo 07)" in cir[0]["manual"]["descripcion"], "cirujano" in cir[0]["ajustes"][0]["texto"]),
     (True, True)),
    ("SOAT cirugía grupo 03: la sala 39205 se calcula con el decreto (22,5 UVB) y la cirugía completa sale",
     ([a["tipo"] for a in cir_g3["alertas"] if a["tipo"] == "Tarifa incompleta"],
      round(T["soat_comp"][(3, "sala")])), ([], 272475)),
    ("versión SOAT 2027 (UVB 12.600): la misma glucosa es Glosa con la 2026 y Conforme con la 2027; "
     "la versión también calcula la 39205",
     (glu, vs["calculados"], uvb27), (["Glosa", "Conforme"], ["39205", "39305"], 12600.0)),
    ("SOAT con otra UVB (11.552): 1,89 x 11.552 = 21.833,28", (round(soat_uvb[0]["esperado"], 2), soat_uvb[0]["estado"]), (21833.28, "Conforme")),
    ("SOAT + 4 %: 22.887,9 x 1,04 = 23.803,42", round(soat_contrato[0]["esperado"], 2), 23803.42),
    ("plantilla SOAT prellenada: 1.426 códigos de la tabla, UVB escrita como número, 39205 se calcula",
     (len(tar_pl) - len(calc_pl), uvb_pl, calc_pl), (1426, 12600.0, ["39205", "39305"])),
    ("plantilla de tarifas propias: hojas vacías + INSTRUCCIONES (no se carga ni avisa); filas llenadas",
     ([(f["tipo"], f["codigo"], f["tarifa"]) for f in filas_pl], avisos_pl),
     ([("cups", "010101", 150000.0), ("cum", "19933174-1", 1200.0)], [])),
    ("ISS UVR: 487702 (300 UVR) completa en quirófano = 1.178.015 (materiales según consumo, >170 UVR)",
     (u_completa["estado"], round(u_completa["esperado"]), any("170 UVR" in a["texto"] for a in u_completa["alertas"])),
     ("Conforme", 1178015, True)),
    ("ISS UVR: adicional igual vía (60% honorarios + 50% sala) y bilateral (+75%) Conforme",
     (u_adicional["estado"], u_bilateral["estado"], "Bilateral" in u_bilateral["manual"]["descripcion"]),
     ("Conforme", "Conforme", True)),
    ("ISS UVR: «UNI Ó BILATERAL» no tiene escenario bilateral",
     any("Bilateral" in a["texto"] for a in u_unibi["alertas"] if a["tipo"] == "Varias opciones"), False),
    ("ISS UVR: región art. 134 a (+30% honorarios y sala) y contrato ISS + 20%",
     (u_region["estado"], u_contrato["estado"]), ("Conforme", "Conforme")),
    ("ISS UVR: por encima de todos los escenarios -> Glosa sobre el mayor (bilateral)",
     (u_caro["estado"], round(u_caro["glosa"])), ("Glosa", round(2_000_000 - 1.75 * (142450 + 81175 + 57410)))),
    ("SOAT: completa con perfusionista (g20), incruenta (g07) y cirugía de otra especialidad (g07) Conforme",
     [(x["estado"], w in x["manual"]["descripcion"]) for x, w in
      ((s_perf, "perfusionista"), (s_incr, "Incruenta"), (s_esp, "otra especialidad"))],
     [("Conforme", True)] * 3),
    ("SOAT: anestesia de diagnóstico +50% solo si se declara (num. 47.1.3)", s_anest, ["Conforme", "Glosa"]),
    ("ISS UVR: descuento de sala por instrumentación de la EPS, recuperación > 6 h y mayor de otro especialista",
     [x["estado"] for x in (i_dto, i_rec, i_esp)], ["Conforme"] * 3),
    ("manual propio: versiones 1 y 2 del mismo código; 5 códigos (repetido y hoja ajena avisados)",
     (va["version"], vb["version"], va["filas"], len(va["avisos"])), (1, 2, 5, 2)),
    ("manual propio v1: valor fijo (glosa 1.000), insumo, CUM, fila SOAT -10 %, fila ISS (vía relación), "
     "código fuera del manual",
     [(x["manual"]["codigo"] if x["manual"] else x["codigo"], x["estado"], round(x["glosa"], 2))
      for x in propia_a["lineas"]],
     [("890202", "Glosa", 1000.0), ("50010194", "Conforme", 0.0), ("MED-001", "Conforme", 0.0),
      ("19490", "Conforme", 0.0), ("903840", "Conforme", 0.0), ("903801", "Revisar", 0.0)]),
    ("manual propio v2 (base SOAT -5 %, borrador): código fuera del manual usa la base y avisa el estado",
     (round(propia_b["lineas"][0]["esperado"], 2), propia_b["lineas"][0]["estado"], len(propia_b["avisos"])),
     (21743.51, "Conforme", 1)),
    ("región art. 134: 903801 = 3.315 + 15 %", next(x["esperado"] for x in choco["lineas"] if x["codigo"] == "903801"), 3812.25),
]
fallas = 0
for desc, obtenido, esperado in CASOS:
    ok = obtenido == esperado or (isinstance(esperado, (int, float)) and abs(obtenido - esperado) < 0.01)
    fallas += not ok
    print(f"{'OK ' if ok else 'MAL'} {desc}: {obtenido}" + ("" if ok else f" (esperado {esperado})"))
print(f"\n{len(CASOS) - fallas}/{len(CASOS)} pruebas correctas")
raise SystemExit(1 if fallas else 0)
