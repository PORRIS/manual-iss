"""Auditoría de facturas contra el Manual Tarifario ISS 2001 (salida/manual_iss.db).

Lee una factura en RIPS JSON (Resolución 2275 de 2023) o en XML de factura electrónica DIAN
(UBL 2.1, también dentro de un AttachedDocument), y compara cada línea con la tarifa del Manual
calculada como en cotizar.py (con los recargos y descuentos que declare el auditor). Marca:

- diferencias de valor (sobrecobro o cobro inferior al Manual);
- posible doble cobro: un componente cobrado aparte junto con el conjunto que lo cubre (art. 95);
- notas del procedimiento que el auditor debe verificar (INCLUYE, EXCLUYE, APLICA, por sesión...);
- códigos que no están en el Manual, con varios valores o en UVR (no se comparan solos).

Cada línea sale con un estado sugerido: "Conforme", "Glosa" (solo diferencias de valor a favor
del prestador) o "Revisar". La decisión final es del auditor. Los RIPS se auditan por usuario
(paciente): una cotización/auditoría corresponde a un paciente.

Uso:
    uv run auditar.py factura_rips.json                 # todos los usuarios, uno por uno
    uv run auditar.py factura.xml --region-134 META:Granada
    uv run auditar.py factura_rips.json --usuario 2 --csv auditoria.csv
    uv run auditar.py factura_rips.json --contrato 30         # contrato ISS 2001 + 30%
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd

import cotizar as cz
from revision_relacion_cups import leer_homologacion
from rutas import BASE, DB, conectar

OPC_ITEM = ("solo-muestra", "biopsia-multiple", "portatil-rx", "portatil-eco", "bilateral")
HOMOLOGACION = BASE / "homologacion.csv"  # código de la factura (CUPS vigente) -> código del Manual
TOLERANCIA = 1.0  # pesos: diferencias menores se consideran redondeo
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
                r["alertas"].append(dict(tipo="UVR", cita="arts. 59-68", texto=(
                    f"Se liquida por UVR ({f['valor']:g} UVR): honorarios, sala y materiales "
                    "según cirugía múltiple; aún no se compara solo")))
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
    globales = dict(tecnecio=False, conjuntos=0)
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
        revisar = any(a["tipo"] in ("Código", "UVR", "Unidad", "Doble cobro", "Repetido",
                                    "Relación dudosa")
                      for a in r["alertas"])
        if r.get("doble_cobro") and r["facturado"] is not None:
            r["estado"], r["glosa"] = "Revisar", r["facturado"]
            r["motivo"] = "Posible doble cobro: componente de un conjunto facturado"
        elif dif is not None and dif > TOLERANCIA:
            r["estado"], r["glosa"] = "Glosa", dif
            r["motivo"] = "Valor facturado superior a la tarifa del Manual"
        elif revisar or r["facturado"] is None:
            r["estado"], r["glosa"] = "Revisar", 0.0
            r["motivo"] = "Sin valor facturado" if r["facturado"] is None else \
                "Ver alertas: no se pudo comparar o requiere verificación"
        else:
            r["estado"], r["glosa"] = "Conforme", 0.0
            r["motivo"] = "Cobro inferior al Manual" if dif is not None and dif < -TOLERANCIA \
                else "Igual a la tarifa del Manual"
        f = r.pop("fila")
        r["manual"] = None if f is None else dict(
            codigo=f["codigo"], descripcion=f["descripcion"], articulo=f["articulo"],
            unidad=f["unidad"], agrupador=f["agrupador"])

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


# ---------------------------------------------------------------- consola
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.split("\n")[14:]))
    ap.add_argument("archivo", help="RIPS .json o factura electrónica .xml")
    ap.add_argument("--usuario", help="solo este usuario del RIPS (1, 2, ...)")
    ap.add_argument("--region-134", metavar="DEPTO:MUNICIPIO")
    ap.add_argument("--mismo-acto", choices=["igual", "diferente"])
    ap.add_argument("--contrato", type=float, default=0, metavar="PCT",
                    help="porcentaje pactado sobre el Manual (contrato ISS 2001 + PCT%%)")
    ap.add_argument("--csv", help="guarda el detalle en este CSV")
    a = ap.parse_args()

    with open(a.archivo, "rb") as fh:
        fac = leer_factura(a.archivo, fh.read())
    d = cz.cargar()
    op = {"solo-muestra": None, "biopsia-multiple": [], "portatil-rx": {}, "portatil-eco": [],
          "tecnecio": False, "bilateral": [], "mismo-acto": a.mismo_acto,
          "region-134": a.region_134}
    print(f"{fac['formato']} · factura {fac['factura'] or '(sin número)'} · "
          f"{len(fac['grupos'])} grupo(s)")
    detalle = []
    for g in fac["grupos"]:
        if a.usuario and g["id"] != a.usuario:
            continue
        r = auditar(g["lineas"], op, d, a.contrato)
        s = r["resumen"]
        print(f"\n== {g['etiqueta']}: {s['lineas']} líneas | facturado {cz.pesos(s['facturado'])} | "
              f"Manual {cz.pesos(s['esperado'])} | glosa sugerida {cz.pesos(s['glosa_sugerida'])} | "
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
