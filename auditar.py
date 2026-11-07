"""Auditoría de facturas contra el Manual Tarifario ISS 2001 (salida/manual_iss.db).

Lee una factura en RIPS JSON (Resolución 2275 de 2023) o en XML de factura electrónica DIAN
(UBL 2.1, también dentro de un AttachedDocument), y compara cada línea con la tarifa del Manual
calculada como en cotizar.py (con los recargos y descuentos que declare el auditor). Marca:

- diferencias de valor (sobrecobro o cobro inferior al Manual);
- posible doble cobro: un componente cobrado aparte junto con el conjunto que lo cubre (art. 95);
- notas del procedimiento que el auditor debe verificar (INCLUYE, EXCLUYE, APLICA, por sesión...);
- códigos que no están en el Manual o con varios valores (no se comparan solos);
- cirugías en UVR (Capítulo I): se comparan contra los escenarios de la norma (uvr.py): completa en
  quirófano u otra sala, adicional del mismo acto, bilateral o un solo componente.

Cada línea sale con un estado sugerido: "Conforme", "Glosa" (solo diferencias de valor a favor
del prestador) o "Revisar". La decisión final es del auditor. Los RIPS se auditan por usuario
(paciente): una cotización/auditoría corresponde a un paciente.

Uso:
    uv run auditar.py factura_rips.json                 # todos los usuarios, uno por uno
    uv run auditar.py factura.xml --region-134 META:Granada
    uv run auditar.py factura_rips.json --usuario 2 --csv auditoria.csv
    uv run auditar.py factura_rips.json --contrato 30         # contrato ISS 2001 + 30%
    uv run auditar.py factura_rips.json --tarifario soat --contrato -5   # SOAT 2026 - 5 %
    uv run auditar.py factura_rips.json --tarifario soat --uvb 11552     # SOAT con otra UVB
    uv run auditar.py factura_rips.json --tarifario propia --version-propia 1   # manual propio
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd

import cotizar as cz
import tarifarios
import tarifas_propias as tp
import uvr as uvr_iss
from revision_relacion_cups import leer_homologacion
from rutas import BASE, DB, conectar

OPC_ITEM = ("solo-muestra", "biopsia-multiple", "portatil-rx", "portatil-eco", "bilateral")
HOMOLOGACION = BASE / "homologacion.csv"  # código de la factura (CUPS vigente) -> código del Manual
TOLERANCIA = 1.0  # pesos: diferencias menores se consideran redondeo
TOLERANCIA_UVR = 100.0  # pesos: suma de varios componentes de una cirugía en UVR
# Secciones del RIPS (Res. 2275 de 2023 y Res. 948 de 2026): (campo código, cantidad, valor unitario)
SECCIONES_RIPS = {
    "consultas": ("codConsulta", None, "vrServicio"),
    "procedimientos": ("codProcedimiento", None, "vrServicio"),
    "otrosServicios": ("codTecnologiaSalud", "cantidadOS", "vrUnitOS"),
    "medicamentos": ("codTecnologiaSalud", "cantidadMedicamento", "vrUnitMedicamento"),
}
EPISODIOS_RIPS = ("urgencias", "hospitalizacion", "recienNacidos")  # sin valor: se muestran
ALIAS_SECCION = {"otros_servicios": "otrosServicios", "otrosservicios": "otrosServicios",
                 "recien_nacidos": "recienNacidos", "reciennacidos": "recienNacidos"}
MOTIVO_MEDICAMENTO = ("Medicamento: se paga por el precio de adquisición más un porcentaje según el "
                      "tipo de prestador (art. 87); no tiene tarifa por código en el Manual")
MOTIVO_TIPO_OS = {
    "01": ("Dispositivo médico o insumo: se paga según consumo, hasta el precio de adquisición "
           "más el 12% (art. 88); verifique con la factura de compra"),
    "04": "Servicio complementario (MIPRES): no tiene tarifa por código en el Manual",
}
TIPO_OS = {"01": "Dispositivos médicos e insumos", "02": "Traslados", "03": "Estancias",
           "04": "Servicios complementarios", "05": "Honorarios"}
PRIVADOS = {"numDocumentoIdentificacion"}  # no se devuelven: se enmascaran
RE_NOTA = [  # (tipo, patrón al inicio de la nota, qué debe verificar el auditor)
    ("Incluye", r"^INCLUYE", "lo incluido no se cobra aparte"),
    ("Excluye", r"^EXCLUYE", "lo excluido se cobra con su propio código"),
    ("No aplica", r"^NO APLICA", "verifique que el caso no esté excluido"),
    ("Aplica", r"^APLICA", "verifique que se cumpla la condición"),
    ("Unidad de cobro", r"^TARIFA|POR SESI[OÓ]N|POR PACIENTE|DIARIA|MENSUAL|POR CADA",
     "verifique la cantidad facturada"),
]


# ---------------------------------------------------------------- lectura de facturas
def _num(x, defecto=None):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return defecto


def _enmascarar(doc):
    doc = str(doc or "")
    return ("*" * max(len(doc) - 4, 0)) + doc[-4:] if doc else "sin documento"


def _clave(k):
    """Nombre de campo comparable: sin mayúsculas, sin '_' y con la 'l' por '1' de los errores
    tipográficos de la norma (fechalnicioAtencion, codDiagnosticoRelacionadol...)."""
    return str(k).replace("_", "").lower().translate(str.maketrans("li", "11"))


def _campos(d):
    """dict con claves normalizadas -> valor (para leer con cualquier variante del nombre)."""
    return {_clave(k): v for k, v in (d or {}).items()} if isinstance(d, dict) else {}


def _get(c, *nombres):
    for n in nombres:
        v = c.get(_clave(n))
        if v not in (None, ""):
            return v
    return None


def _datos(registro):
    """Todos los campos del registro tal como llegan (incluidos los nuevos de la Res. 948),
    con los documentos enmascarados."""
    privados = {_clave(x) for x in PRIVADOS}
    return {k: (_enmascarar(v) if _clave(k) in privados else v)
            for k, v in (registro or {}).items() if not isinstance(v, (dict, list))}


def _edad(fecha_nac, referencia):
    m1 = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(fecha_nac or ""))
    m2 = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(referencia or ""))
    if not (m1 and m2):
        return None
    a1, a2 = tuple(map(int, m1.groups())), tuple(map(int, m2.groups()))
    return a2[0] - a1[0] - ((a2[1], a2[2]) < (a1[1], a1[2]))


def leer_rips(datos):
    """RIPS JSON -> dict(factura, grupos=[dict(id, etiqueta, usuario, episodios, lineas,
    no_tarifadas)]). Lee todos los campos de cada registro (quedan en 'datos')."""
    if isinstance(datos, (str, bytes)):
        datos = json.loads(datos)
    raiz = _campos(datos)
    usuarios = _get(raiz, "usuarios")
    if not isinstance(usuarios, list):
        raise ValueError("No parece un RIPS JSON: falta la lista 'usuarios'")
    grupos = []
    for n, u in enumerate(usuarios, start=1):
        cu = _campos(u)
        serv = {ALIAS_SECCION.get(_clave(k), k): v for k, v in (_get(cu, "servicios") or {}).items()}
        serv = {next((s for s in list(SECCIONES_RIPS) + list(EPISODIOS_RIPS)
                      if _clave(s) == _clave(k)), k): v for k, v in serv.items()}
        lineas, otras, fechas = [], [], []
        for sec, (f_cod, f_cant, f_val) in SECCIONES_RIPS.items():
            for i, reg in enumerate(serv.get(sec) or [], start=1):
                c = _campos(reg)
                cant = _num(_get(c, f_cant), 1) if f_cant else 1
                cant = cant or 1
                unit = _num(_get(c, f_val))
                total = _num(_get(c, "vrServicio"))
                if (unit is None or (unit == 0 and total)) and total is not None:
                    unit = total / cant
                fecha = str(_get(c, "fechaInicioAtencion", "fechaSuministroTecnologia",
                                 "fechaDispensAdmon") or "")
                fechas.append(fecha)
                tipo_os = str(_get(c, "tipoOS") or "").zfill(2) if sec == "otrosServicios" else ""
                linea = dict(codigo=str(_get(c, f_cod) or "").strip(), cantidad=cant,
                             valor_unitario=unit, descripcion=_get(c, "nomTecnologiaSalud") or "",
                             fecha=fecha, seccion=sec,
                             origen=f"{sec}{' ' + TIPO_OS.get(tipo_os, tipo_os) if tipo_os else ''}"
                                    f" #{_get(c, 'consecutivo') or i}",
                             datos=_datos(reg))
                motivo = MOTIVO_MEDICAMENTO if sec == "medicamentos" else MOTIVO_TIPO_OS.get(tipo_os)
                if motivo:
                    otras.append(dict(motivo=motivo, **linea))
                else:
                    lineas.append(linea)
        episodios = [dict(tipo=sec, datos=_datos(reg)) for sec in EPISODIOS_RIPS
                     for reg in serv.get(sec) or []]
        fechas += [str(_get(_campos(e["datos"]), "fechaInicioAtencion") or "") for e in episodios]
        primera = min((f for f in fechas if f), default="")
        usuario = _datos(u)
        usuario.pop("fechaNacimiento", None)
        usuario["edad_en_la_atencion"] = _edad(_get(cu, "fechaNacimiento"), primera)
        etiqueta = (f"Usuario {_get(cu, 'consecutivo') or n} · {_get(cu, 'tipoDocumentoIdentificacion') or ''} "
                    f"{_enmascarar(_get(cu, 'numDocumentoIdentificacion'))}").strip()
        grupos.append(dict(id=str(n), etiqueta=etiqueta, usuario=usuario, episodios=episodios,
                           lineas=lineas, no_tarifadas=otras))
    return dict(formato="RIPS JSON", factura=_get(raiz, "numFactura") or "",
                prestador=_get(raiz, "numDocumentoIdObligado") or "",
                nota=" ".join(str(x) for x in (_get(raiz, "tipoNota"), _get(raiz, "numNota")) if x),
                grupos=grupos)


def _sin_ns(e):
    return e.tag.rsplit("}", 1)[-1]


def _hijo(e, *ruta):
    for nombre in ruta:
        if e is None:
            return None
        e = next((h for h in e if _sin_ns(h) == nombre), None)
    return e


def _texto(e, *ruta):
    h = _hijo(e, *ruta)
    return (h.text or "").strip() if h is not None and h.text else ""


def leer_xml(contenido):
    """Factura electrónica DIAN (Invoice UBL 2.1 o AttachedDocument que la contiene)."""
    if isinstance(contenido, bytes):
        contenido = contenido.decode("utf-8-sig", errors="replace")
    if re.search(r"<!DOCTYPE|<!ENTITY", contenido, re.I):
        raise ValueError("El XML trae DOCTYPE/ENTITY; por seguridad no se procesa")
    raiz = ET.fromstring(contenido.encode("utf-8"))
    if _sin_ns(raiz) == "AttachedDocument":
        interno = next((d.text for d in raiz.iter() if _sin_ns(d) == "Description"
                        and d.text and "<Invoice" in d.text), None)
        if not interno:
            raise ValueError("AttachedDocument sin la factura (Invoice) adentro")
        return leer_xml(interno)
    if _sin_ns(raiz) not in ("Invoice", "CreditNote", "DebitNote"):
        raise ValueError(f"XML no reconocido: raíz <{_sin_ns(raiz)}> (se espera Invoice)")
    lineas = []
    for i, ln in enumerate((e for e in raiz if _sin_ns(e).endswith("InvoiceLine")), start=1):
        cant = _num(next((h.text for h in ln if _sin_ns(h).endswith("Quantity")), None), 1)
        total = _num(_texto(ln, "LineExtensionAmount"))
        unit = _num(_texto(ln, "Price", "PriceAmount"))
        if unit is None and total is not None and cant:
            unit = total / cant
        codigo = (_texto(ln, "Item", "StandardItemIdentification", "ID")
                  or _texto(ln, "Item", "SellersItemIdentification", "ID"))
        lineas.append(dict(codigo=codigo, cantidad=cant or 1, valor_unitario=unit,
                           descripcion=_texto(ln, "Item", "Description"), fecha="", seccion="",
                           origen=f"línea {_texto(ln, 'ID') or i}", datos={}))
    return dict(formato="Factura electrónica XML", factura=_texto(raiz, "ID"), nota="",
                total=_num(_texto(raiz, "LegalMonetaryTotal", "PayableAmount")),
                prestador=_texto(raiz, "AccountingSupplierParty", "Party", "PartyTaxScheme",
                                 "CompanyID"),
                grupos=[dict(id="1", etiqueta="Factura completa", usuario={}, episodios=[],
                             lineas=lineas, no_tarifadas=[])],
                aviso=("La factura electrónica suele traer el código interno del prestador, no "
                       "el CUPS: para comparar con el Manual cargue el RIPS JSON de la misma "
                       "factura. El XML sirve para cuadrar el total."))


def leer_factura(nombre, contenido):
    texto = contenido.decode("utf-8-sig", errors="replace") if isinstance(contenido, bytes) \
        else contenido
    if nombre.lower().endswith(".json") or texto.lstrip().startswith("{"):
        return leer_rips(texto)
    if nombre.lower().endswith(".xml") or texto.lstrip().startswith("<"):
        return leer_xml(texto)
    raise ValueError("Formato no reconocido: use RIPS .json o factura .xml")


# ---------------------------------------------------------------- auditoría
def clasificar_nota(texto):
    t = cz.norm(texto)
    for tipo, pat, verificar in RE_NOTA:
        if re.search(cz.norm(pat), t):
            return tipo, verificar
    return "Nota", "revise la nota"


def homologacion(db=DB):
    """({codigo_factura: (codigo_manual, fuente)}, {cups: (sugerido, observación)}).
    Relación CUPS 2026 -> ISS 2001 de la base (tabla homologacion_cups) y, encima, las filas
    "aprobada" de homologacion.csv; las "por_revisar" solo generan una alerta."""
    homo = {}
    con = conectar(db)
    if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'homologacion_cups'").fetchone():
        for cups, iss in con.execute("SELECT cups, codigo_iss FROM homologacion_cups "
                                     "WHERE codigo_iss <> ''"):
            homo[cups.upper()] = (iss, "Relación Manual ISS - CUPS 2026")
    con.close()
    dudosas = {}
    for r in leer_homologacion().itertuples():
        cod, iss = r.codigo_factura.strip().upper(), r.codigo_manual.strip()
        if not (cod and iss):
            continue
        estado = (r.estado or "aprobada").strip().lower()
        if estado == "aprobada":
            homo[cod] = (iss, "homologacion.csv" + (f": {r.observacion}" if r.observacion else ""))
        elif estado == "por_revisar":
            dudosas[cod] = (iss, r.observacion)
    return homo, dudosas


def auditar(lineas, op, d, contrato_pct=0.0):
    """lineas: [dict(codigo, cantidad, valor_unitario, ...)]. Devuelve dict con el detalle.

    El valor esperado de cada línea es la tarifa del Manual más los recargos y descuentos de su
    código (los de un código repetido en varias líneas se reparten según la cantidad).
    contrato_pct: porcentaje pactado sobre el valor del Manual (contrato "ISS 2001 + X%"); se
    aplica al final, sobre el valor de cada línea con sus recargos y descuentos."""
    res, filas = [], []
    if "homologacion" not in d:
        d["homologacion"] = homologacion()
    homo, dudosas = d["homologacion"]
    for i, ln in enumerate(lineas):
        cod = str(ln.get("codigo") or "").strip()
        cod_factura = cod
        # solo las líneas que vienen de un RIPS traen CUPS; las digitadas se toman como código ISS
        homologado = bool(ln.get("seccion")) and cod.upper() in homo and "@" not in cod
        if homologado:
            cod = homo[cod.upper()][0]
        cant = int(round(_num(ln.get("cantidad"), 1) or 1))
        item = cod if cant == 1 or "x" in cod.lower() else f"{cod}x{cant}" if "@" not in cod \
            else cod.replace("@", f"x{cant}@", 1)
        r = dict(linea=i, codigo=cod, cantidad=cant, valor_unitario=_num(ln.get("valor_unitario")),
                 descripcion_factura=ln.get("descripcion") or "", origen=ln.get("origen") or "",
                 fecha=ln.get("fecha") or "", seccion=ln.get("seccion") or "",
                 datos=ln.get("datos") or {}, alertas=[], fila=None)
        if homologado and cod_factura.upper() in dudosas:
            sug, obs = dudosas[cod_factura.upper()]
            r["alertas"].append(dict(tipo="Relación dudosa", cita="homologacion.csv", texto=(
                f"La relación del CUPS {cod_factura} está en revisión ({obs}). Si se aprueba, se "
                f"compararía como {sug}")))
        if cod != cod_factura:
            r["codigo_factura"] = cod_factura
            r["alertas"].append(dict(tipo="Homologado", cita=homo[cod_factura.upper()][1], texto=(
                f"CUPS {cod_factura} de la factura comparado como {cod} del Manual ISS 2001")))
        r["facturado"] = None if r["valor_unitario"] is None else r["valor_unitario"] * cant
        f, err, avisos = cz.resolver([item], d) if cod else ([], ["línea sin código"], [])
        if err:
            msg = err[0]
            if "no existe en el Manual" in msg and homologado:
                msg = (f"El CUPS {cod_factura} se relaciona con el código ISS {cod}, que no existe en "
                       "el Manual (PDF): novedad registrada en «Relación CUPS sin código en el PDF»")
            elif "no existe en el Manual" in msg:
                msg += (" (no está en la relación CUPS -> ISS: corrija el código en la línea o "
                        "agréguelo a homologacion.csv)")
            r["alertas"].append(dict(tipo="Código", texto=msg, cita=""))
        else:
            f = f[0]
            f["linea"] = i
            r["fila"] = f
            filas.append(f)
            if f["unidad"] == "UVR":
                r["uvr"] = f["valor"]  # se compara contra los escenarios de uvr.py
            elif f["unidad"] != "pesos":
                r["alertas"].append(dict(tipo="Unidad", cita="",
                                         texto=f"Unidad '{f['unidad']}': no se compara sola"))
            for n in d["notas"][d["notas"].procedimiento_id == f["id"]].texto:
                tipo, verificar = clasificar_nota(n)
                r["alertas"].append(dict(tipo=tipo, texto=f"{n} — {verificar}", cita=""))
        res.append(r)

    ajustes, errores, avisos_reg = cz.aplicar(filas, dict(op), d) if filas else ([], [], [])

    # valor esperado por línea
    cant_cod = {}
    for f in filas:
        if f["base"] is not None:
            cant_cod[f["codigo"]] = cant_cod.get(f["codigo"], 0) + f["cantidad"]
    for r in res:
        f = r["fila"]
        r["valor_manual"] = r["esperado"] = None
        r["ajustes"] = []
        if f is None or f["base"] is None:
            continue
        r["valor_manual"] = f["valor"]
        parte = f["cantidad"] / cant_cod[f["codigo"]]
        aj = [a for a in ajustes if a["codigo"] == f["codigo"]]
        r["ajustes"] = [dict(a, monto=a["monto"] * parte) for a in aj]
        r["esperado"] = f["base"] + sum(a["monto"] for a in r["ajustes"])

    # adicionales por paciente (sin código): se asignan a la primera línea a la que aplican
    R = d["reglas"]
    for a in [a for a in ajustes if not a["codigo"]]:
        m = re.search(r"\(sobre (\w+)\)", a["texto"])
        origen = R[R.regla == (m[1] if m else a["regla"])]
        alcance = origen.alcance.iloc[0] if len(origen) else f"art:{a['articulo']}"
        r = next((r for r in res if r["fila"] is not None and r["fila"]["base"] is not None
                  and cz.en_alcance(r["fila"], alcance)), None)
        if r is not None:
            r["ajustes"].append(dict(a, texto=a["texto"] + " (una vez por paciente)"))
            r["esperado"] += a["monto"]
            a["asignado"] = True

    # contrato "ISS + X%": sobre el valor de cada línea con sus recargos y descuentos
    factor = 1 + (contrato_pct or 0) / 100
    if factor != 1:
        for r in res:
            if r["esperado"] is not None:
                r["ajustes"].append(dict(regla="CONTRATO", codigo=r["codigo"], articulo="",
                                         cita="contrato", monto=r["esperado"] * (factor - 1),
                                         texto=f"Porcentaje pactado en el contrato: {contrato_pct:+g}%"))
                r["esperado"] *= factor

    # cirugías en UVR: escenarios de la norma (con el contrato y el +30 % regional del art. 134 a)
    if any(r.get("uvr") for r in res):
        if "uvr_tablas" not in d:
            con = conectar()
            d["uvr_tablas"] = uvr_iss.tablas(con)
            con.close()
        region = False
        if op.get("region-134"):
            depto, _, muni = op["region-134"].partition(":")
            depto = cz.ALIAS_134.get(cz.norm(depto), cz.norm(depto))
            region = depto in cz.DEPTOS_134 and bool(muni) and cz.norm(muni) not in cz.EXCEPTUADAS_134
        ftxt = f" {contrato_pct:+g}% (contrato)" if factor != 1 else ""
        for r in res:
            if not r.get("uvr"):
                continue
            f = r["fila"]
            esc, avisos_uvr = uvr_iss.escenarios(f["codigo"], f["valor"], f["descripcion"], d["uvr_tablas"],
                                                 factor, region, ftxt, op.get("descuento-sala"))
            for a in avisos_uvr:
                r["alertas"].append(dict(tipo="Cirugía UVR", cita="arts. 59-85", texto=a))
            if not esc:
                r["alertas"].append(dict(tipo="UVR", cita="arts. 59-85",
                                         texto=f"{f['valor']:g} UVR: no se pudo calcular ningún escenario"))
                continue
            unit, tol = r["valor_unitario"], TOLERANCIA_UVR
            ops = "; ".join(f"{n} {cz.pesos(v)}" for n, v, _ in esc)
            iguales = [e for e in esc if unit is not None and abs(unit - e[1]) <= tol]
            if iguales:
                elegido = iguales[0]
                nota = f"Lo facturado coincide con: {elegido[0]}"
            elif unit is not None and unit > max(e[1] for e in esc) + tol:
                elegido = max(esc, key=lambda e: e[1])
                nota = f"Lo facturado supera todos los escenarios; se compara con el mayor ({elegido[0]})"
            else:
                elegido = min(esc, key=lambda e: abs((unit or 0) - e[1]))
                nota = (f"Lo facturado no coincide con ningún escenario: elija el que corresponde. "
                        f"Se muestra el más cercano ({elegido[0]})")
                r["revisar_opciones"] = True
            r["alertas"].append(dict(tipo="Varias opciones", cita="arts. 59-85", texto=f"{nota}. Escenarios: {ops}"))
            nombre, v, detalle = elegido
            r["manual"] = None  # se rellena abajo con la fila; aquí se guarda el escenario
            r["escenario_uvr"] = nombre
            r["valor_manual"] = v
            r["esperado"] = v * r["cantidad"]
            r["ajustes"] = [dict(regla="UVR", codigo=r["codigo"], articulo=f["articulo"], monto=0.0,
                                 cita="arts. 59-85", texto=f"{detalle}: {cz.pesos(v)} por unidad")]

    # mismo código el mismo día (posible doble registro) y doble cobro conjunto/componente
    por_cod, por_dia = {}, {}
    for r in res:
        if r["fila"] is not None:
            por_cod.setdefault(r["fila"]["codigo"], []).append(r)
            if r["fecha"]:  # misma fecha y hora: varias tomas el mismo día son normales
                por_dia.setdefault((r["fila"]["codigo"], r["fecha"].strip()), []).append(r)
    for (cod, momento), rs in por_dia.items():
        if len(rs) > 1:
            for r in rs:
                r["alertas"].append(dict(tipo="Repetido", cita="", texto=(
                    f"El código se cobra {len(rs)} veces con la misma fecha y hora ({momento}): "
                    "verifique que no sea un doble registro")))
    paq = d["paq"]
    for r in res:
        if r["fila"] is None:
            continue
        cub = paq[(paq.componente_codigo == r["fila"]["codigo"])
                  & paq.paquete_codigo.isin(por_cod.keys())]
        for p in cub.itertuples():
            r["alertas"].append(dict(tipo="Doble cobro", cita="art. 95 par. 1 (pág. 187)", texto=(
                f"Cobrado aparte, pero lo cubre el conjunto {p.paquete_codigo} que también está en "
                "la factura: el valor del conjunto incluye sus componentes")))
            r["doble_cobro"] = True

    # opciones que el auditor puede declarar por línea y para toda la factura
    Ra = R[R.estado == "aprobada"]
    tec = Ra[Ra.opcion == "tecnecio"]
    globales = dict(tecnecio=False, conjuntos=0,
                    uvr=sum(r["cantidad"] for r in res if r.get("uvr")))
    for r in res:
        f = r["fila"]
        ok = f is not None and f["base"] is not None
        r["aplicables"] = sorted({x.opcion for x in Ra[Ra.opcion.isin(OPC_ITEM)].itertuples()
                                  if ok and cz.en_alcance(f, x.alcance)})
        if ok and len(tec) and cz.en_alcance(f, tec.alcance.iloc[0]):
            globales["tecnecio"] = True
        if ok and cz.en_alcance(f, "art:95"):
            globales["conjuntos"] += f["cantidad"]

    # estado sugerido
    for r in res:
        dif = None
        if r["esperado"] is not None and r["facturado"] is not None:
            dif = r["facturado"] - r["esperado"]
        r["diferencia"] = dif
        revisar = r.pop("revisar_opciones", False) or any(
            a["tipo"] in ("Código", "UVR", "Unidad", "Doble cobro", "Repetido", "Relación dudosa")
            for a in r["alertas"])
        tol = TOLERANCIA_UVR if r.get("uvr") else TOLERANCIA
        if r.get("doble_cobro") and r["facturado"] is not None:
            r["estado"], r["glosa"] = "Revisar", r["facturado"]
            r["motivo"] = "Posible doble cobro: componente de un conjunto facturado"
        elif dif is not None and dif > tol * r["cantidad"] and not revisar:
            r["estado"], r["glosa"] = "Glosa", dif
            r["motivo"] = "Valor facturado superior a la tarifa del Manual"
        elif revisar or r["facturado"] is None:
            r["estado"], r["glosa"] = "Revisar", 0.0
            r["motivo"] = "Sin valor facturado" if r["facturado"] is None else \
                "Ver alertas: no se pudo comparar o requiere verificación"
        else:
            r["estado"], r["glosa"] = "Conforme", 0.0
            r["motivo"] = "Cobro inferior al Manual" if dif is not None and dif < -tol * r["cantidad"] \
                else "Igual a la tarifa del Manual"
        f = r.pop("fila")
        esc_uvr = r.pop("escenario_uvr", None)
        r.pop("uvr", None)
        r["manual"] = None if f is None else dict(
            codigo=f["codigo"], descripcion=f["descripcion"] + (f" — {esc_uvr}" if esc_uvr else ""),
            articulo=f["articulo"], unidad=f["unidad"], agrupador=f["agrupador"])

    por_paciente = [a for a in ajustes if not a["codigo"] and not a.get("asignado")]
    por_paciente = [dict(a, monto=a["monto"] * factor) for a in por_paciente]
    suma = lambda k: sum(r[k] for r in res if r[k] is not None)  # noqa: E731
    return dict(
        lineas=res, errores=errores, avisos=avisos_reg, por_paciente=por_paciente,
        globales=globales,
        parrafos=cz.parrafos(filas, d),
        resumen=dict(lineas=len(res), facturado=suma("facturado"),
                     esperado=suma("esperado") + sum(a["monto"] for a in por_paciente),
                     comparables=sum(1 for r in res if r["diferencia"] is not None),
                     glosa_sugerida=sum(r["glosa"] for r in res if r["estado"] == "Glosa"),
                     en_revision=sum(1 for r in res if r["estado"] == "Revisar")))


# ---------------------------------------------------------------- SOAT y tarifa propia
TOLERANCIA_SOAT = 100.0  # pesos: el valor SOAT en UVB da decimales; se acepta el redondeo a la centena
UVB_2026 = tarifarios.UVB_REFERENCIA
ETQ_BASE = {"soat": "SOAT", "iss": "ISS 2001", "valor_fijo": "valor fijo"}


def _tipos_item(ln):
    """Tipos del manual propio en los que se busca la línea del RIPS (digitada: en todos)."""
    sec = ln.get("seccion")
    if sec == "medicamentos":
        return ["cum"]
    if sec == "otrosServicios" and str((ln.get("datos") or {}).get("tipoOS", "")).zfill(2) == "01":
        return ["insumo", "material"]
    if sec:
        return ["cups"]
    return ["cups", "cum", "insumo", "material"]


TOLERANCIA_CIRUGIA = 500.0  # pesos: cada componente se redondea a la centena (hasta 5 componentes)
COMPONENTES = (("cirujano", "cirujano"), ("anestesiologo", "anestesiólogo"), ("ayudante", "ayudante"),
               ("sala", "derechos de sala"), ("materiales", "materiales"))


def escenarios_cirugia(k, dsc, grupo, T, uvb):
    """Valores posibles de una cirugía SOAT de un grupo (Decreto 780 de 2016, anexo técnico 1):
    [(código, descripción, valor, cómo se calculó, tolerancia)]. La línea del RIPS puede traer la
    cirugía completa, una adicional del mismo acto (con su porcentaje), una bilateral o un solo
    componente."""
    f = uvb / UVB_2026
    c = {comp: (T["soat_comp"].get((grupo, comp)) or 0) * f for comp, _ in COMPONENTES}
    if grupo < 6:
        c["ayudante"] = 0.0  # la tabla de ayudantía empieza en el grupo 06 (num. 47.1.4)
    falta_sala = not c["sala"]
    hon = c["cirujano"] + c["anestesiologo"] + c["ayudante"]
    hon_sin = c["cirujano"] + c["anestesiologo"]
    g = f"grupo {grupo:02d}"
    mat_txt = " (materiales a precio de catálogo en grupos 20-23, num. 54.2)" if grupo >= 20 else ""
    det = lambda pares: " + ".join(f"{n} {cz.pesos(v)}" for n, v in pares if v)  # noqa: E731
    esc = []
    if not falta_sala:
        esc.append(("Cirugía completa", hon + c["sala"] + c["materiales"],
                    det([("cirujano", c["cirujano"]), ("anestesiólogo", c["anestesiologo"]),
                         ("ayudante", c["ayudante"]), ("sala", c["sala"]),
                         ("materiales", c["materiales"])]) + mat_txt))
        if c["ayudante"]:
            esc.append(("Cirugía completa sin ayudante", hon_sin + c["sala"] + c["materiales"],
                        det([("cirujano", c["cirujano"]), ("anestesiólogo", c["anestesiologo"]),
                             ("sala", c["sala"]), ("materiales", c["materiales"])])))
        esc.append(("Adicional en otra región operatoria (num. 71, 48.2, 54.5)",
                    0.75 * hon + 0.5 * c["sala"] + 0.75 * c["materiales"],
                    "75% honorarios + 50% sala + 75% materiales"))
        esc.append(("Bilateral (num. 69, 48.2, 54.5)",
                    1.75 * hon + 1.5 * c["sala"] + 1.75 * c["materiales"],
                    "honorarios +75%, sala +50%, materiales +75%"))
    # num. 47.2: perfusionista en los grupos especiales 20 a 23
    perf = (T["soat_directo"].get("39129") or (None, None, None))[2]
    if grupo >= 20 and perf and esc:
        esc.append(("Cirugía completa con perfusionista (num. 47.2)", esc[0][1] + perf * f,
                    esc[0][2] + f" + perfusionista 39129 {cz.pesos(perf * f)}"))
    # num. 72, 72.1, 72.2 y 48.2: la cirugía la hace un especialista de otra especialidad en el mismo acto
    if not falta_sala:
        esc.append(("Cirugía de otra especialidad en el mismo acto (num. 72, 48.2)",
                    c["cirujano"] + 0.75 * c["anestesiologo"] + 0.5 * c["ayudante"] + 0.5 * c["sala"],
                    "cirujano 100% (su mayor), anestesiólogo 75%, ayudante 50%, sala 50%"))
        # num. 51 y 54.3: intervención incruenta en sala (45% de la sala del grupo + materiales 39305)
        mat_inc = (T["soat_directo"].get("39305") or (None, None, None))[2]
        if mat_inc:
            esc.append(("Incruenta en sala quirúrgica o especial (num. 51, 54.3)",
                        hon_sin + 0.45 * c["sala"] + mat_inc * f,
                        f"cirujano + anestesiólogo + 45% de la sala del grupo + materiales 39305 {cz.pesos(mat_inc * f)}"))
            esc.append(("Incruenta en sala, sin anestesiólogo (num. 51, 54.3)",
                        c["cirujano"] + 0.45 * c["sala"] + mat_inc * f,
                        "cirujano + 45% de la sala del grupo + materiales 39305"))
    esc.append(("Adicional, mismo cirujano e igual vía (num. 70)", 0.5 * hon, "50% de los honorarios"))
    if c["ayudante"]:
        esc.append(("Adicional, igual vía, sin ayudante (num. 70)", 0.5 * hon_sin,
                    "50% de cirujano y anestesiólogo"))
    esc.append(("Adicional, mismo cirujano y diferente vía (num. 71)", 0.75 * hon, "75% de los honorarios"))
    for comp, nombre in COMPONENTES:
        if c[comp]:
            esc.append((f"Solo {nombre}", c[comp], f"{nombre} del {g}"))
    return [(k, f"{dsc or ''} — {nombre} ({g})", v, f"SOAT cirugía {g}: {txt} (UVB {cz.pesos(uvb)})",
             TOLERANCIA_CIRUGIA) for nombre, v, txt in esc if v], falta_sala


def _soat(cod, ln, T, uvb):
    """[(código SOAT, descripción, valor unitario|None, cómo se calculó, tolerancia)] y la
    explicación si no hay valor. Las cirugías (código con grupo quirúrgico) dan varios escenarios."""
    cups = cod.zfill(6) if cod.isdigit() else cod
    if not ln.get("seccion") and cod in T["soat_directo"]:  # digitado: primero el código SOAT exacto
        base = [T["soat_directo"][cod]]
    elif cups in T["soat"]:  # del RIPS (o digitado): CUPS -> SOAT con la relación
        base = T["soat"][cups]
    else:
        return [], f"El código {cod} no está en la relación CUPS-SOAT ni en la tabla SOAT"
    c, sin_sala = [], []
    for k, dsc, v in base:
        if v:
            c.append((k, dsc, v / UVB_2026 * uvb, f"SOAT {v / UVB_2026:g} UVB x {cz.pesos(uvb)}", None))
        elif k in T["soat_grupos"]:
            esc, falta = escenarios_cirugia(k, dsc, int(T["soat_grupos"][k]), T, uvb)
            c += esc
            if falta:
                sin_sala.append(k)
        else:
            c.append((k, dsc, None, "", None))
    porque = ""
    if not any(x[2] for x in c):
        porque = (f"El código {cod} se relaciona con códigos SOAT sin tarifa ni grupo quirúrgico "
                  f"({', '.join(k for k, *_ in base)})")
    if sin_sala:
        porque = (porque + "; " if porque else "") + (
            f"falta la tarifa de derechos de sala del grupo 03 (código 39205) en la tabla SOAT 2026: "
            f"no se calcula la cirugía completa de {', '.join(sin_sala)}")
    return c, porque


def _iss(cod, ln, d):
    """[(código ISS, descripción, valor en pesos)] usando la relación CUPS -> ISS."""
    if "homologacion" not in d:
        d["homologacion"] = homologacion()
    homo, _ = d["homologacion"]
    iss = homo[cod.upper()][0] if ln.get("seccion") and cod.upper() in homo else cod
    f, err, _ = cz.resolver([iss], d)
    if err:
        return [], err[0]
    f = f[0]
    if f["unidad"] != "pesos":
        return [], f"El código ISS {iss} está en {f['unidad']} ({f['valor']:g}): no se compara solo"
    return [(f["codigo"], f["descripcion"], f["valor"])], ""


def candidatos(ln, cod, tarifario, T, uvb, contrato_pct=0.0, propia=None, d=None):
    """[(código de referencia, descripción, valor unitario final, cómo se calculó, tolerancia)] y,
    si no hay, la explicación. El valor final ya incluye el factor del manual o del contrato."""
    def base(liq, factor, origen):
        if liq == "soat":
            c, porque = _soat(cod, ln, T, uvb)
        else:
            c, porque = _iss(cod, ln, d)
            c = [(k, dsc, v, f"ISS 2001 {cz.pesos(v)}", None) for k, dsc, v in c]
        f = 1 + (factor or 0) / 100
        return [(k, dsc, v * f if v else None,
                 calc + (f" {factor:+g}% ({origen})" if factor else "") if v else "", tol)
                for k, dsc, v, calc, tol in c], porque

    if tarifario == "soat":
        return base("soat", contrato_pct, "contrato")
    if tarifario != "propia" or propia is None:
        return [], "Tarifario no válido o sin manual de tarifas propias elegido"
    v = propia["version"]
    manual = f"{v['manual']} v{v['version']}"
    for tipo in _tipos_item(ln):
        clave = (tipo, cod.zfill(6) if tipo == "cups" and cod.isdigit() and len(cod) < 6 else cod)
        it = propia["items"].get(clave)
        if it is None:
            continue
        liq = it["tipo_liquidacion"] or v["tipo_base"]
        if liq == "valor_fijo":
            return [(clave[1], it["descripcion"], it["tarifa"], f"Valor fijo del manual {manual}", None)], ""
        factor = it["factor_pct"] if it["factor_pct"] is not None else v["factor_pct"]
        c, porque = base(liq, factor, f"manual {manual}")
        return [(k, (it["descripcion"] or dsc) if len(c) == 1 else dsc, val, txt, tol)
                for k, dsc, val, txt, tol in c], porque
    if v["tipo_base"] in ("soat", "iss"):
        c, porque = base(v["tipo_base"], v["factor_pct"], f"base del manual {manual}")
        return [(k, dsc, val, txt + " — el código no está en el manual: se usa su base", tol)
                for k, dsc, val, txt, tol in c], porque
    return [], f"El código {cod} no está en el manual {manual} ({'/'.join(_tipos_item(ln))})"


def anestesia_diag_aplica(cands):
    """La opción del num. 47.1.3 (anestesia general en exámenes y procedimientos de diagnóstico y
    tratamiento: +50 %) se ofrece en códigos SOAT con tarifa propia que no son laboratorio ni
    patología (19xxx, 20xxx), ni cirugía por grupo, ni los de valor propio 39150-39155."""
    return any(c[2] and not c[3].startswith("SOAT cirugía") and not c[0].startswith(("19", "20"))
               and c[0] not in {"39150", "39151", "39152", "39153", "39154", "39155"} for c in cands)


def auditar_tarifa(lineas, tarifario, T, contrato_pct=0.0, uvb=UVB_2026, propia=None, d=None,
                   anestesia_diag=()):
    """Auditoría contra SOAT ('soat') o un manual de tarifas propias ('propia').

    SOAT: el CUPS se lleva a código SOAT con la relación CUPS-SOAT; valor = factor UVB x uvb
    (por defecto la UVB 2026; para facturas de otro año use la UVB de ese año); contrato_pct es el
    porcentaje pactado (ej. -5 = SOAT - 5 %). Si el CUPS tiene varias opciones SOAT: si lo
    facturado coincide con una, Conforme; si supera a todas, Glosa sobre la de mayor valor; si no,
    Revisar.
    Propia: propia = tarifas_propias.cargar_version(id). Cada código usa su tipo de liquidación
    (o el del manual): valor fijo, o factor % sobre SOAT o ISS (d = datos de cotizar.cargar()).
    Los códigos que no están en el manual usan la base del manual si es SOAT o ISS."""
    if tarifario == "propia":
        v = propia["version"]
        nombre = f"manual {v['manual']} v{v['version']}"
    else:
        nombre = T["catalogo"].get(tarifario, tarifario)
    tol = TOLERANCIA_SOAT if tarifario == "soat" or (
        propia and propia["version"]["tipo_base"] == "soat") else TOLERANCIA
    res = []
    for i, ln in enumerate(lineas):
        cod = str(ln.get("codigo") or "").strip().upper()
        cant = int(round(_num(ln.get("cantidad"), 1) or 1))
        unit = _num(ln.get("valor_unitario"))
        r = dict(linea=i, codigo=cod, cantidad=cant, valor_unitario=unit,
                 descripcion_factura=ln.get("descripcion") or "", origen=ln.get("origen") or "",
                 fecha=ln.get("fecha") or "", seccion=ln.get("seccion") or "",
                 datos=ln.get("datos") or {}, alertas=[], ajustes=[], aplicables=[],
                 facturado=None if unit is None else unit * cant, manual=None,
                 valor_manual=None, esperado=None)
        cands, porque = candidatos(ln, cod, tarifario, T, uvb, contrato_pct, propia, d) \
            if cod else ([], "línea sin código")
        if tarifario == "soat" and anestesia_diag_aplica(cands):
            r["aplicables"] = ["anestesia-diag"]
            if cod in anestesia_diag:  # el auditor declara anestesia general (num. 47.1.3)
                cands = [(k, dsc, v * 1.5, calc + " + anestesiólogo 50% (num. 47.1.3)", tol)
                         if v and not calc.startswith("SOAT cirugía") else (k, dsc, v, calc, tol)
                         for k, dsc, v, calc, tol in cands]
        con_valor = [c for c in cands if c[2]]
        elegido = None
        tol_de = lambda c: c[4] if c[4] is not None else tol  # noqa: E731
        if not con_valor:
            r["alertas"].append(dict(tipo="Código", cita=nombre, texto=porque))
        elif porque:  # hay valores, pero algo no se pudo calcular (p. ej. sala del grupo 03)
            r["alertas"].append(dict(tipo="Tarifa incompleta", cita=nombre, texto=porque))
        if len(con_valor) == 1:
            elegido = con_valor[0]
        elif con_valor:
            ops = "; ".join(f"{k} {dsc[:60]} {cz.pesos(v)}" for k, dsc, v, *_ in con_valor)
            iguales = [c for c in con_valor if unit is not None and abs(unit - c[2]) <= tol_de(c)]
            if iguales:
                elegido = iguales[0]
                r["alertas"].append(dict(tipo="Varias opciones", cita=nombre, texto=(
                    f"El CUPS tiene {len(con_valor)} opciones; lo facturado coincide con {elegido[0]}. "
                    f"Opciones: {ops}")))
            elif unit is not None and unit > max(c[2] + tol_de(c) for c in con_valor):
                elegido = max(con_valor, key=lambda c: c[2])
                r["alertas"].append(dict(tipo="Varias opciones", cita=nombre, texto=(
                    f"Lo facturado supera todas las opciones; se compara con la de mayor valor "
                    f"({elegido[0]}). Opciones: {ops}")))
            else:
                elegido = min(con_valor, key=lambda c: abs((unit or 0) - c[2]))
                r["alertas"].append(dict(tipo="Varias opciones", cita=nombre, texto=(
                    f"El CUPS tiene {len(con_valor)} opciones y lo facturado no coincide con ninguna: "
                    f"elija la que corresponde. Se muestra la más cercana ({elegido[0]}). "
                    f"Opciones: {ops}")))
                r["revisar_opciones"] = True
        if elegido:
            k, dsc, v, calc, tol_e = elegido
            r["tolerancia"] = tol_de(elegido)
            r["manual"] = dict(codigo=k, descripcion=dsc, articulo=None, unidad="pesos", agrupador=nombre)
            r["valor_manual"] = v
            r["esperado"] = v * cant
            r["ajustes"].append(dict(regla="TARIFA", codigo=cod, articulo="", monto=0.0, cita=nombre,
                                     texto=f"{calc}: {cz.pesos(v)} por unidad"))
        res.append(r)

    momentos = {}
    for r in res:
        if r["manual"] and r["fecha"]:
            momentos.setdefault((r["codigo"], r["fecha"].strip()), []).append(r)
    for (cod, momento), rs in momentos.items():
        if len(rs) > 1:
            for r in rs:
                r["alertas"].append(dict(tipo="Repetido", cita="", texto=(
                    f"El código se cobra {len(rs)} veces con la misma fecha y hora ({momento}): "
                    "verifique que no sea un doble registro")))

    avisos = []
    if propia and propia["version"]["estado_vigente"] != "activo":
        v = propia["version"]
        avisos.append(f"El manual {v['manual']} versión {v['version']} está «{v['estado_vigente']}» "
                      f"(vigencia {v['vigencia_inicio'] or '—'} a {v['vigencia_fin'] or '—'})")
    for r in res:
        dif = None if r["esperado"] is None or r["facturado"] is None else r["facturado"] - r["esperado"]
        r["diferencia"] = dif
        revisar = r.pop("revisar_opciones", False) or any(
            a["tipo"] in ("Código", "Repetido") for a in r["alertas"])
        t = r.pop("tolerancia", tol) * r["cantidad"]
        if dif is not None and dif > t and not revisar:
            r["estado"], r["glosa"] = "Glosa", dif
            r["motivo"] = f"Valor facturado superior a la tarifa ({nombre})"
        elif revisar or dif is None:
            r["estado"], r["glosa"] = "Revisar", 0.0
            r["motivo"] = "Sin valor facturado" if r["facturado"] is None else \
                "Ver alertas: no se pudo comparar o requiere verificación"
        else:
            r["estado"], r["glosa"] = "Conforme", 0.0
            r["motivo"] = f"Cobro inferior a la tarifa ({nombre})" if dif < -t \
                else f"Igual a la tarifa ({nombre})"

    suma = lambda k: sum(r[k] for r in res if r[k] is not None)  # noqa: E731
    return dict(
        lineas=res, errores=[], avisos=avisos, por_paciente=[], parrafos=[],
        globales=dict(tecnecio=False, conjuntos=0), tarifario=tarifario,
        resumen=dict(lineas=len(res), facturado=suma("facturado"), esperado=suma("esperado"),
                     comparables=sum(1 for r in res if r["diferencia"] is not None),
                     glosa_sugerida=sum(r["glosa"] for r in res if r["estado"] == "Glosa"),
                     en_revision=sum(1 for r in res if r["estado"] == "Revisar")))


def cargar_tarifas():
    con = conectar()
    try:
        return tarifarios.cargar(con)
    finally:
        con.close()


# ---------------------------------------------------------------- consola
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.split("\n")[14:]))
    ap.add_argument("archivo", help="RIPS .json o factura electrónica .xml")
    ap.add_argument("--usuario", help="solo este usuario del RIPS (1, 2, ...)")
    ap.add_argument("--region-134", metavar="DEPTO:MUNICIPIO")
    ap.add_argument("--mismo-acto", choices=["igual", "diferente"])
    ap.add_argument("--descuento-sala", choices=["instrumentacion", "enfermeria", "ambos"],
                    help="ISS: la EPS aporta instrumentación, enfermería o ambas (art. 77 par. 4)")
    ap.add_argument("--contrato", type=float, default=0, metavar="PCT",
                    help="porcentaje pactado sobre la tarifa (ej. 30 = tarifa + 30%%, -5 = tarifa - 5%%)")
    ap.add_argument("--tarifario", choices=["iss", "soat", "propia"], default="iss",
                    help="contra qué se audita: Manual ISS 2001, SOAT 2026 o tarifas propias")
    ap.add_argument("--uvb", type=float, default=None,
                    help="valor de la UVB para el SOAT (por defecto, la de la versión: 2026 = 12110)")
    ap.add_argument("--soat-version", default="base", metavar="ID",
                    help="versión de la tarifa SOAT (soat_versiones.py listar); por defecto la 2026")
    ap.add_argument("--version-propia", type=int, metavar="ID",
                    help="id de la versión del manual de tarifas propias (tarifas_propias.py listar)")
    ap.add_argument("--csv", help="guarda el detalle en este CSV")
    a = ap.parse_args()

    with open(a.archivo, "rb") as fh:
        fac = leer_factura(a.archivo, fh.read())
    d = cz.cargar()
    T = cargar_tarifas()
    if a.tarifario == "soat":
        import soat_versiones as sv
        T, uvb_version, nombre_version = sv.aplicar(T, a.soat_version)
        if a.uvb is None:
            a.uvb = uvb_version or UVB_2026
        print(f"SOAT: {nombre_version or 'SOAT 2026 (por defecto)'}, UVB {a.uvb:g}")
    a.uvb = a.uvb or UVB_2026
    propia = None
    if a.tarifario == "propia":
        if not a.version_propia:
            sys.exit("Con --tarifario propia indique --version-propia ID (vea: uv run tarifas_propias.py listar)")
        propia = tp.cargar_version(a.version_propia)
    op = {"solo-muestra": None, "biopsia-multiple": [], "portatil-rx": {}, "portatil-eco": [],
          "tecnecio": False, "bilateral": [], "mismo-acto": a.mismo_acto,
          "descuento-sala": a.descuento_sala,
          "region-134": a.region_134}
    print(f"{fac['formato']} · factura {fac['factura'] or '(sin número)'} · "
          f"{len(fac['grupos'])} grupo(s)")
    detalle = []
    for g in fac["grupos"]:
        if a.usuario and g["id"] != a.usuario:
            continue
        if a.tarifario == "iss":
            r = auditar(g["lineas"], op, d, a.contrato)
        else:
            extra = g["no_tarifadas"] if a.tarifario == "propia" else []
            r = auditar_tarifa(g["lineas"] + extra, a.tarifario, T, a.contrato, a.uvb, propia, d)
        s = r["resumen"]
        print(f"\n== {g['etiqueta']}: {s['lineas']} líneas | facturado {cz.pesos(s['facturado'])} | "
              f"tarifa {cz.pesos(s['esperado'])} | glosa sugerida {cz.pesos(s['glosa_sugerida'])} | "
              f"a revisar {s['en_revision']}")
        for e in r["errores"]:
            print("  ERROR:", e)
        for x in r["lineas"]:
            if x["estado"] != "Conforme":
                print(f"  {x['estado']:8} {x['codigo']:8} {x['origen']:22} "
                      f"fact. {cz.pesos(x['facturado'] or 0):>13} "
                      f"Manual {cz.pesos(x['esperado']) if x['esperado'] is not None else '—':>13}  "
                      f"{x['motivo']}")
        for x in r["lineas"]:
            detalle.append(dict(grupo=g["etiqueta"], origen=x["origen"], codigo=x["codigo"],
                                cantidad=x["cantidad"], facturado=x["facturado"],
                                valor_manual=x["esperado"], diferencia=x["diferencia"],
                                estado=x["estado"], glosa=x["glosa"], motivo=x["motivo"],
                                alertas=" | ".join(f"{al['tipo']}: {al['texto']}"
                                                   for al in x["alertas"])))
        if g["no_tarifadas"]:
            from collections import Counter
            for motivo, n in Counter(o["motivo"].split(":")[0] for o in g["no_tarifadas"]).items():
                print(f"  ({n} sin tarifa por código en el Manual: {motivo})")
    if a.csv:
        pd.DataFrame(detalle).to_csv(a.csv, index=False, encoding="utf-8-sig")
        print(f"\ndetalle en {a.csv}")


if __name__ == "__main__":
    sys.exit(main())
