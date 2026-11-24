"""Cotizador de servicios con tarifas del Manual ISS 2001 (salida/manual_iss.db).

Suma las tarifas en pesos de los códigos dados y aplica SOLO las reglas de recargo o
descuento que se piden con una opción explícita (el código no dice si un estudio fue
portátil o un conjunto bilateral; eso lo declara quien cotiza). Las cifras y el alcance
de cada regla están en reglas_tarifas.csv, con artículo, parágrafo y página del PDF; las
que tienen estado distinto de "aprobada" no se aplican.

Lo demás que puede cambiar el valor (contrato, insumos según consumo, ...) solo se
avisa. Las cirugías en UVR (arts. 1-18) se liquidan con uvr.py: honorarios de cirujano y
anestesiólogo (y ayudante si se declara), derechos de sala y materiales; la sala, la anestesia
local, el ayudante y la bilateralidad se declaran por código, y --mismo-acto aplica los arts. 65
(igual vía) y 66 (diferente vía). Una cotización corresponde a un paciente.

Uso:
    uv run cotizar.py 903801 871112x2 C40402
    uv run cotizar.py 903801 --solo-muestra                 # 12% (art. 25 par. 3)
    uv run cotizar.py 898101 --biopsia-multiple 898101       # +60% (art. 26 par. 1)
    uv run cotizar.py 871112 --portatil-rx 871112:fluoroscopia   # simple | fluoroscopia
    uv run cotizar.py 951301 --portatil-eco 951301          # +$9.095 (art. 27 par. 12)
    uv run cotizar.py 920302 --tecnecio                     # +$13.120 por paciente
    uv run cotizar.py C40402 --bilateral C40402             # +55% (art. 95 par. 6)
    uv run cotizar.py C40402 C40403 --mismo-acto igual      # 100% + 25% (art. 95 par. 7)
    uv run cotizar.py C40402 C40403 --mismo-acto diferente  # 100% + 70% de los demás
    uv run cotizar.py 903801 C40402 --region-134 META:Granada   # +15% / +14% (art. 134)
    uv run cotizar.py 697100@41501                          # CODIGO@REF si hay varios valores
    uv run cotizar.py 487702 --ayudante 487702              # cirugía en UVR con ayudante
    uv run cotizar.py 487702 386100 --mismo-acto igual      # UVR: 100% + 60% (art. 65)
    uv run cotizar.py 386100 --uvr-sala 386100:especial --sin-anestesia 386100
    uv run cotizar.py 903801 --csv cotizacion.csv
"""
import argparse
import re
import sys
import unicodedata

import pandas as pd

import uvr
from rutas import BASE, conectar

DB = BASE / "salida" / "manual_iss.db"
REGLAS = BASE / "reglas_tarifas.csv"
REGIONES = BASE / "regiones_134.csv"
RE_ITEM = re.compile(r"^(?P<codigo>[A-Za-z]?\d{4,6})(?:x(?P<cant>\d+))?(?:@(?P<ref>\w+))?$")
# Art. 134 (pág. 204): departamentos y región con incremento; par. 2 (pág. 205): ciudades
# donde no aplica. Están en regiones_134.csv. "URABA" = municipios de la región de Urabá
# (el Manual no los enumera).
_REG = pd.read_csv(REGIONES, dtype=str, keep_default_na=False)
ALIAS_134 = {"LA GUAJIRA": "GUAJIRA", "SAN ANDRES Y PROVIDENCIA": "SAN ANDRES"}
DEPTOS_134 = set(_REG[_REG.clase != "ciudad_exceptuada"].clave)
EXCEPTUADAS_134 = set(_REG[_REG.clase == "ciudad_exceptuada"].clave)
RE_MODIFICA = re.compile(r"\d+\s*%|por ciento|adicional|se incrementa|incremento|"
                         r"se pagará el|descuento", re.I)


def pesos(v):
    s = f"${abs(v):,.0f}".replace(",", ".")
    return f"-{s}" if v < 0 else s


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return s.upper().strip()


def parte(p):
    """'3' -> 'par. 3'; 'b' -> 'literal b' (art. 134 b)."""
    return f"par. {p}" if p.isdigit() else f"literal {p}"


def normcod(c):
    c = c.upper()
    return c.zfill(6) if c.isdigit() else c


# ---------------------------------------------------------------- datos
def cargar(db=DB, reglas=REGLAS):
    con = conectar(db)
    d = dict(
        t=pd.read_sql("SELECT * FROM v_tarifas", con),
        notas=pd.read_sql("SELECT procedimiento_id, texto FROM notas "
                          "WHERE procedimiento_id IS NOT NULL", con),
        parr=pd.read_sql("SELECT articulo, texto FROM notas WHERE tipo = 'paragrafo'", con),
        paq=pd.read_sql("SELECT * FROM v_paquete_componentes", con),
        uvr=uvr.tablas(con),
    )
    con.close()
    d["reglas"] = pd.read_csv(reglas, dtype=str, keep_default_na=False)
    return d


def en_alcance(f, alcance):
    """alcance: condiciones separadas por ';' (todas deben cumplirse)."""
    for cond in alcance.split(";"):
        k, v = cond.split(":", 1)
        if k == "art":
            arts = set()
            for parte in v.split(","):
                a, _, b = parte.partition("-")
                arts |= set(range(int(a), int(b or a) + 1))
            if f["articulo"] not in arts:
                return False
        elif k == "titulo" and norm(f["titulo"]) != norm(v):
            return False
        elif k == "no_ruta" and norm(v) in norm(f["agrupador_ruta"]):
            return False
        elif k == "agrupador_contiene" and norm(v) not in norm(f["agrupador"]):
            return False
        elif k == "codigos" and f["codigo"] not in {normcod(x) for x in v.split(",")}:
            return False
        elif k == "no_codigos" and f["codigo"] in {normcod(x) for x in v.split(",")}:
            return False
    return True


# ---------------------------------------------------------------- ítems
def resolver(items, d):
    t, paq = d["t"], d["paq"]
    filas, errores, avisos = [], [], []
    for it in items:
        m = RE_ITEM.match(it.strip())
        if not m:
            errores.append(f"{it}: formato no válido (use CODIGO, CODIGOx2 o CODIGO@REF)")
            continue
        cod, cant, ref = normcod(m["codigo"]), int(m["cant"] or 1), m["ref"]
        c = t[(t.codigo == cod) & (t.tipo == "con_valor")]
        if ref:
            c = c[c.ref.fillna("").str.lstrip("0") == ref.lstrip("0")]
        if c.empty:
            otro = t[t.codigo == cod]
            if otro.empty:
                errores.append(f"{cod}: no existe en el Manual")
            else:
                cub = paq[paq.componente_codigo == cod]
                donde = "; ".join(f"{r.paquete_codigo} {pesos(r.paquete_valor)}"
                                  for r in cub.itertuples())
                errores.append(f"{cod}: no tiene tarifa propia ({otro.tipo.iloc[0]})"
                               + (f"; está cubierto por el conjunto {donde}" if donde else ""))
            continue
        if c.valor.nunique() > 1:
            ops = "; ".join(f"@{r.ref} art. {r.articulo} {pesos(r.valor)} [{r.agrupador}]"
                            for r in c.itertuples())
            errores.append(f"{cod}: tiene varios valores, elija con CODIGO@REF -> {ops}")
            continue
        r = c.iloc[0]
        en_pesos = r.unidad == "pesos"
        filas.append(dict(id=int(r.id), codigo=cod, descripcion=r.descripcion,
                          articulo=int(r.articulo), titulo=r.titulo or "",
                          agrupador=r.agrupador or "", agrupador_ruta=r.agrupador_ruta or "",
                          unidad=r.unidad, valor=float(r.valor), cantidad=cant,
                          base=float(r.valor) * cant if en_pesos else None))
        if r.unidad == "UVR":
            pass  # se liquida en cotizar() con uvr.py
        elif not en_pesos:
            avisos.append(f"{cod}: unidad '{r.unidad}', no se suma")
        if len(c) > 1:
            avisos.append(f"{cod}: aparece {len(c)} veces en el Manual con el mismo valor")
        for n in d["notas"][d["notas"].procedimiento_id == r.id].texto:
            avisos.append(f"{cod}: {n}")
        for p in paq[paq.componente_codigo == cod].itertuples():
            avisos.append(f"{cod}: también lo cubre el conjunto {p.paquete_codigo} "
                          f"({p.paquete_descripcion[:50]}, {pesos(p.paquete_valor)}), art. 95")
    return filas, errores, avisos


# ---------------------------------------------------------------- reglas
def aplicar(filas, op, d):
    """op: dict con las opciones pedidas (ver argumentos). Devuelve (ajustes, errores)."""
    R = d["reglas"]
    ajustes, errores = [], []
    pesos_ = [f for f in filas if f["base"] is not None]

    def regla(rid):
        return R[R.regla == rid].iloc[0]

    def ajuste(r, f, monto):
        ajustes.append(dict(regla=r.regla, codigo=f["codigo"] if f else "",
                            articulo=f["articulo"] if f else int(r.articulo),
                            cita=f"art. {r.articulo} {parte(r.paragrafo)} (pág. {r.pagina_pdf})",
                            texto=r.texto, monto=monto,
                            # en la auditoría un código puede repetirse en varias líneas
                            **({"linea": f["linea"]} if f and "linea" in f else {})))

    def por_item(r, f):
        v, n = float(r.valor), f["cantidad"]
        if r.tipo == "factor":
            return f["valor"] * n * (v - 1)
        if r.tipo == "porcentaje":
            return f["valor"] * n * v
        return v * (n if r.base == "por_estudio" else 1)

    def objetivos(r, codigos, opcion):
        """Ítems a los que se aplica una opción con lista de códigos (vacía = todos)."""
        sel = [f for f in pesos_ if en_alcance(f, r.alcance)]
        if codigos:
            pedidos = {normcod(c) for c in codigos}
            faltan = pedidos - {f["codigo"] for f in pesos_}
            fuera = {f["codigo"] for f in pesos_ if f["codigo"] in pedidos} - \
                {f["codigo"] for f in sel}
            for c in sorted(faltan):
                errores.append(f"--{opcion} {c}: el código no está en la cotización")
            for c in sorted(fuera):
                errores.append(f"--{opcion} {c}: no aplica ({r.texto})")
            sel = [f for f in sel if f["codigo"] in pedidos]
        elif not sel:
            errores.append(f"--{opcion}: ningún ítem de la cotización está en su alcance "
                           f"({r.texto})")
        return sel

    # reglas pendientes de aprobación: no se aplican
    for opcion in {k for k, v in op.items() if v not in (None, False, [], {}) and not k.startswith("_")}:
        pend = R[(R.opcion == opcion) & (R.estado != "aprobada")]
        if len(pend):
            errores.append(f"--{opcion}: la regla {', '.join(pend.regla)} está "
                           f"'{pend.estado.iloc[0]}' en {REGLAS}; no se aplica")
            op[opcion] = None

    if op.get("solo-muestra") is not None:
        r = regla("R25P3")
        for f in objetivos(r, op["solo-muestra"], "solo-muestra"):
            ajuste(r, f, por_item(r, f))
    for opcion, rid in (("biopsia-multiple", "R26P1"), ("portatil-eco", "R27P12"),
                        ("bilateral", "R95P6")):
        if op.get(opcion):
            r = regla(rid)
            for f in objetivos(r, op[opcion], opcion):
                ajuste(r, f, por_item(r, f))
    if op.get("mismo-acto"):
        mismo_acto(op, pesos_, R, regla, ajuste, errores)
    for cod, variante in (op.get("portatil-rx") or {}).items():
        rr = R[(R.opcion == "portatil-rx") & (R.variante == variante)]
        if rr.empty:
            errores.append(f"--portatil-rx {cod}:{variante}: variante no válida "
                           "(simple | fluoroscopia)")
            continue
        r = rr.iloc[0]
        for f in objetivos(r, [cod], "portatil-rx"):
            ajuste(r, f, por_item(r, f))
    if op.get("tecnecio"):
        r = regla("R27P16T")
        if objetivos(r, [], "tecnecio"):
            ajuste(r, None, float(r.valor))  # una vez por paciente
    for _, r in R[(R.opcion == "automatica") & (R.estado == "aprobada")].iterrows():
        if any(en_alcance(f, r.alcance) for f in pesos_):
            ajuste(r, None, float(r.valor))  # una vez por paciente

    # Art. 134: va al final, sobre lo que efectivamente se paga por cada ítem (tarifa + sus
    # ajustes): el +14% de los conjuntos incluye el +55% bilateral (par. 23: "tarifa total del
    # conjunto") y el +15% de la toma de muestra se calcula sobre el 12%. Los adicionales por
    # paciente del Capítulo II (tecnecio, radioaerosoles) también reciben el +15%.
    avisos = []
    if op.get("region-134"):
        depto, _, muni = op["region-134"].partition(":")
        depto, muni = norm(depto), norm(muni)
        depto = ALIAS_134.get(depto, depto)
        if depto not in DEPTOS_134:
            errores.append(f"--region-134 {op['region-134']}: '{depto}' no está entre los "
                           f"departamentos y regiones del art. 134 ({', '.join(sorted(DEPTOS_134))})")
        elif not muni:
            errores.append("--region-134: indique también el municipio (DEPARTAMENTO:MUNICIPIO); "
                           "en " + ", ".join(sorted(EXCEPTUADAS_134)) + " no aplica el incremento")
        elif muni in EXCEPTUADAS_134:
            avisos.append(f"art. 134 par. 2 (pág. 205): en {muni.title()} no aplica el "
                          "incremento regional")
        else:
            previos = list(ajustes)
            for _, r in R[(R.opcion == "region-134") & (R.estado == "aprobada")].iterrows():
                for f in [f for f in pesos_ if en_alcance(f, r.alcance)]:
                    pagado = f["base"] + sum(x["monto"] for x in previos
                                             if x["codigo"] == f["codigo"]
                                             and x.get("linea") == f.get("linea"))
                    ajuste(r, f, pagado * float(r.valor))
                for x in previos:
                    if not x["codigo"] and en_alcance({"articulo": x["articulo"]}, r.alcance):
                        ajustes.append(dict(regla=r.regla, codigo="",
                                            articulo=x["articulo"],
                                            cita=f"art. {r.articulo} {parte(r.paragrafo)} "
                                                 f"(pág. {r.pagina_pdf})",
                                            texto=f"{r.texto} (sobre {x['regla']})",
                                            monto=x["monto"] * float(r.valor)))
    return ajustes, errores, avisos


def mismo_acto(op, pesos_, R, regla, ajuste, errores):
    """Art. 95 par. 7 (pág. 188): varios procedimientos en un mismo acto, alguno de Conjunto.
    Cada unidad (CODIGOx2 = dos conjuntos) cuenta por separado; el de mayor tarifa es el
    principal. Los casos que el texto no resuelve con claridad no se calculan."""
    via = op["mismo-acto"]
    if via == "distinta":  # par. 7 literal b: distinta especialidad = la regla de diferente vía (70 %)
        via = "diferente"
    rr = R[(R.opcion == "mismo-acto") & (R.variante == via) & (R.estado == "aprobada")]
    if via not in ("igual", "diferente") or rr.empty:
        errores.append(f"--mismo-acto {via}: vía no válida (igual | diferente)")
        return
    r = rr.iloc[0]
    conj = [f for f in pesos_ if en_alcance(f, r.alcance)]
    unidades = sorted(((f["valor"], f) for f in conj for _ in range(f["cantidad"])),
                      key=lambda x: -x[0])
    cita = f"art. 95 par. 7 (pág. {r.pagina_pdf})"
    if not unidades:
        if not op.get("_hay_uvr"):  # con cirugías en UVR el mismo acto se aplica a ellas
            errores.append(f"--mismo-acto: la cotización no tiene conjuntos del art. 95 ({cita})")
    elif len(unidades) == 1:
        errores.append(f"--mismo-acto: con un solo conjunto en el acto no procede su valor; "
                       f"cobre cada actividad por su tarifa (las de UVR, sin el conjunto) "
                       f"({cita}, literal a: {regla('R95P7A').texto})")
    elif via == "igual" and len(unidades) > 2:
        errores.append(f"--mismo-acto igual con {len(unidades)} conjuntos: el Manual dice que el "
                       f"25% se adiciona «por una sola vez» y no aclara qué pasa con el tercero "
                       f"y siguientes; caso pendiente de consulta ({cita})")
    elif {normcod(c) for c in op.get("bilateral") or []} & {f["codigo"] for f in conj}:
        errores.append(f"--mismo-acto con --bilateral: el Manual no dice si el +55% bilateral "
                       f"se calcula antes o después de los porcentajes del par. 7; caso "
                       f"pendiente de consulta ({cita})")
    else:
        rebaja = {}
        for v, f in unidades[1:]:
            rebaja.setdefault(id(f), [f, 0.0])[1] -= v * (1 - float(r.valor))
        for f, monto in rebaja.values():
            ajuste(r, f, monto)


def parrafos(filas, d):
    """Parágrafos de los artículos cotizados que pueden modificar el valor."""
    arts = {f["articulo"] for f in filas}
    pa = d["parr"][d["parr"].articulo.isin(arts) & d["parr"].texto.str.contains(RE_MODIFICA)]
    salida = []
    for p in pa.itertuples():
        rr = d["reglas"][(d["reglas"].articulo == str(p.articulo)) & d["reglas"].paragrafo.map(
            lambda n, t=p.texto: t.startswith((f"PARAGRAFO {n}.", f"PARAGRAFO {n} ")))]
        opcion = None
        if len(rr):
            opcion = rr.opcion.iloc[0] if (rr.estado == "aprobada").all() else "pendiente"
        salida.append(dict(articulo=int(p.articulo), opcion=opcion, texto=p.texto))
    return salida


def region_valida(op):
    """True si se declaró una región del art. 134 donde aplica el incremento."""
    if not op.get("region-134"):
        return False
    depto, _, muni = op["region-134"].partition(":")
    depto = ALIAS_134.get(norm(depto), norm(depto))
    return depto in DEPTOS_134 and bool(muni) and norm(muni) not in EXCEPTUADAS_134


def liquidar_uvr(filas, op, d):
    """Cirugías en UVR: valor con uvr.liquidar_acto según lo declarado. Devuelve (errores, avisos)."""
    cir = [f for f in filas if f["unidad"] == "UVR"]
    errores, avisos = [], []
    if not cir:
        for opcion in ("uvr-sala", "sin-anestesia", "ayudante", "ayudante-especialista", "recuperacion", "materiales",
                       "especialista", "accesorios", "politrauma", "descuento-sala"):
            if op.get(opcion):
                errores.append(f"--{opcion}: la cotización no tiene cirugías en UVR")
        return errores, avisos
    codigos = {f["codigo"] for f in cir}
    for opcion in ("uvr-sala", "sin-anestesia", "ayudante", "ayudante-especialista", "recuperacion", "materiales",
                   "especialista", "accesorios"):
        for c in (op.get(opcion) or []):
            if normcod(c) not in codigos:
                errores.append(f"--{opcion} {c}: no es una cirugía en UVR de la cotización")
    sala = {normcod(k): v for k, v in (op.get("uvr-sala") or {}).items()}
    for c, v in sala.items():
        if v not in uvr.SALA_ART:
            errores.append(f"--uvr-sala {c}:{v}: sala no válida ({' | '.join(uvr.SALA_ART)})")
    recup = {normcod(k): v for k, v in (op.get("recuperacion") or {}).items() if v}
    for c, v in recup.items():
        if v not in uvr.RECUPERACION and v not in uvr.RECUP_UCI:
            errores.append(f"--recuperacion {c}:{v}: complejidad no válida "
                           f"({' | '.join([*uvr.RECUPERACION, *uvr.RECUP_UCI])})")
    mat = {}
    for c, v in (op.get("materiales") or {}).items():
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = -1
        if v < 0:
            errores.append(f"--materiales {c}: el valor de la hoja de gasto debe ser un número en pesos")
        elif v:
            mat[normcod(c)] = v
    dto = op.get("descuento-sala") or None
    if dto and dto not in uvr.DESCUENTO_SALA:
        errores.append(f"--descuento-sala {dto}: no válido ({' | '.join(uvr.DESCUENTO_SALA)})")
        dto = None
    sin_anest = {normcod(c) for c in op.get("sin-anestesia") or []}
    ayud = {normcod(c) for c in op.get("ayudante") or []}
    ayud_esp = {normcod(c) for c in op.get("ayudante-especialista") or []}
    bil = {normcod(c) for c in op.get("bilateral") or []}
    via = op.get("mismo-acto") if op.get("mismo-acto") in ("igual", "diferente", "distinta") else None
    espec = {normcod(k): str(v) for k, v in (op.get("especialista") or {}).items() if v}
    acces = {}
    for c, ks in (op.get("accesorios") or {}).items():
        ks = [ks] if isinstance(ks, str) else list(ks or [])
        for k in ks:
            if k not in uvr.ACCESORIOS:
                errores.append(f"--accesorio {c}:{k}: no válido ({' | '.join(uvr.ACCESORIOS)})")
            else:
                acces.setdefault(normcod(c), []).append(k)
    items = [dict(codigo=f["codigo"], uvr=f["valor"], descripcion=f["descripcion"], cantidad=f["cantidad"],
                  sala=sala.get(f["codigo"], "quirofano"), anestesia=f["codigo"] not in sin_anest,
                  ayudante=f["codigo"] in ayud,
                  ayudante_especialista=f["codigo"] in ayud_esp, bilateral=f["codigo"] in bil,
                  recuperacion=recup.get(f["codigo"]), materiales_consumo=mat.get(f["codigo"]),
                  especialista=espec.get(f["codigo"], "1"), accesorios=acces.get(f["codigo"], [])) for f in cir]
    if via is None and sum(f["cantidad"] for f in cir) > 1:
        avisos.append("Varias cirugías en UVR sin --mismo-acto: se liquidan como actos distintos (cada una "
                      "al 100%). Si fueron en el mismo acto, declare igual o diferente vía (arts. 65-66)")
    politrauma = bool(op.get("politrauma"))
    if politrauma and via not in ("igual", "diferente"):
        errores.append("--politrauma: aplica a varias cirugías del mismo especialista en un mismo acto; "
                       "use --mismo-acto igual o diferente (arts. 65 par. y 77 par. 6)")
        politrauma = False
    res, av = uvr.liquidar_acto(items, d["uvr"], via, region_valida(op), dto, politrauma)
    avisos += av
    for f in cir:
        r = res[f["codigo"]]
        f["base"] = r["total"]
        f["uvr_detalle"] = [dict(concepto=c, monto=m, cita=ci) for c, m, ci in r["componentes"]]
    return errores, avisos


SUMINISTRO_PCT = 12   # art. 88: precio de adquisición + 12 % (pág. 161)
TUTOR_PCT = 25        # art. 88 par. 2: tutores en préstamo, 25 % por paciente
# tipo -> (porcentaje sobre el precio de adquisición, texto, cita)
TIPOS_SUMINISTRO = {
    "suministro": (SUMINISTRO_PCT, "Suministro", "art. 88 (pág. 161)"),
    "med_externo": (12, "Medicamento, prestador externo", "art. 87 literal a (pág. 160)"),
    "med_interno": (5, "Medicamento, prestador interno", "art. 87 literal b (pág. 160)"),
}


def liquidar_suministros(lista):
    """Suministros del art. 88 (prótesis, órtesis, placas, tornillos, clavos, mallas, stents, catéteres,
    cemento óseo...): se pagan según consumo, hasta por el precio de adquisición + 12 %. Los tutores
    (fijación externa) en préstamo: 25 % de ese valor por paciente, cualquiera sea el número y el
    periodo de uso, sin los tornillos de fijación (par. 2).
    Medicamentos y soluciones (art. 87): precio de adquisición + 12 % si el prestador es externo
    (literal a) o + 5 % si es interno (literal b).
    lista: [dict(descripcion, precio, cantidad=1, prestamo=False, tipo="suministro")]. Devuelve (lineas, errores)."""
    lineas, errores = [], []
    for k, s in enumerate(lista, 1):
        desc = (s.get("descripcion") or "").strip() or f"Suministro {k}"
        try:
            precio, cant = float(s.get("precio")), float(s.get("cantidad") or 1)
        except (TypeError, ValueError):
            precio, cant = -1, 1
        if precio <= 0 or cant <= 0:
            errores.append(f"Suministro «{desc}»: el precio de compra y la cantidad deben ser mayores que 0")
            continue
        tipo = s.get("tipo") or "suministro"
        if tipo not in TIPOS_SUMINISTRO:
            errores.append(f"Suministro «{desc}»: tipo no válido ({' | '.join(TIPOS_SUMINISTRO)})")
            continue
        pct, nombre, cita = TIPOS_SUMINISTRO[tipo]
        prestamo = bool(s.get("prestamo"))
        if prestamo and tipo != "suministro":
            errores.append(f"«{desc}»: el préstamo (25 %) es solo para tutores de fijación externa (art. 88 par. 2)")
            continue
        compra = precio * cant
        margen = compra * pct / 100
        monto = (compra + margen) * (TUTOR_PCT / 100 if prestamo else 1)
        lineas.append(dict(
            descripcion=desc, precio=precio, cantidad=cant, prestamo=prestamo, tipo=tipo, pct=pct,
            compra=compra, margen=margen, monto=monto,
            texto=(f"Tutor en préstamo: {TUTOR_PCT} % de (compra + {pct} %)" if prestamo
                   else f"{nombre}: precio de compra + {pct} %"),
            cita="art. 88 par. 2 (pág. 161)" if prestamo else cita))
    return lineas, errores


def ajuste_contrato(total, pct):
    """Ajuste del contrato (ej. «ISS + 4 %» o «ISS - 5 %») sobre el valor total ya liquidado, al peso."""
    return round(total * pct / 100) if pct else 0


# ---------------------------------------------------------------- Capítulo II con anestesia
NEURO_27P8 = {"380110", "385120", "395010", "382301", "380210", "385220", "385401", "395200"}  # art. 27 par. 6-9
MAT_85P3 = {"S41230", "S41231", "S41234", "S41235"}                    # art. 85 par. 3: S55115
MAT_85P4 = {"380110", "385120", "380210", "382301", "385220", "386301", "395010", "395200", "874133",
            "S41232", "S41233", "S41236"}                                # art. 85 par. 4: S55116
RE_HEMODINAMIA = re.compile(r"CATETERISMO|HEMODINAM|ELECTROFISIOL|ABLACION|CORONARIOGRAF", re.I)


def valor_codigo(d, codigo):
    v = d["t"][(d["t"].codigo == codigo) & (d["t"].tipo == "con_valor")].valor
    return float(v.iloc[0]) if len(v) else None


def capitulo2_anestesia(pesos_, op, d, cod_uvr):
    """Exámenes y procedimientos del Capítulo II (arts. 19-41) que necesitan anestesia general o
    regional (opción «anestesia-cap2» por código), y materiales con valor fijo del art. 85 par. 3 y 4.
    - Anestesiólogo (art. 62, pág. 150): 50 % de la tarifa del procedimiento (en los múltiples, de la
      superior), salvo los de valor fijo: radiología convencional y TAC S41232, resonancia S41233. En
      intervencionismo y hemodinamia es un porcentaje del «valor operativo» (par.), que el Manual no
      separa de la tarifa: se avisa y no se suma.
    - Quirófano (art. 78, pág. 156): 80 % de la tarifa (de la superior si son varios), si no es
      complementario de una cirugía del Capítulo I. Los 8 intervencionistas del art. 27 par. 8 pagan
      siempre quirófano o sala especial al 60 %, una vez (en los múltiples, sobre la tarifa superior).
    - Materiales: S55115 con S41230, S41231, S41234, S41235 (art. 85 par. 3); S55116 con los códigos
      del art. 85 par. 4 y con S41232, S41233, S41236 (también cuando se liquidan por esta opción).
    Devuelve (ajustes, errores, avisos); no reciben el incremento regional del art. 134."""
    ajustes, errores, avisos = [], [], []
    cods = {f["codigo"] for f in pesos_}
    hay_uvr = bool(cod_uvr)

    def aj(regla, f, monto, texto, cita, articulo):
        ajustes.append(dict(regla=regla, codigo=f["codigo"] if f else "", articulo=articulo,
                            cita=cita, texto=texto, monto=monto,
                            **({"linea": f["linea"]} if f and "linea" in f else {})))

    pedidos = {normcod(c) for c in op.get("anestesia-cap2") or []}
    for c in sorted(pedidos - cods):
        errores.append(f"--anestesia-cap2 {c}: " + ("es una cirugía en UVR, no un examen o procedimiento del "
                                                     "Capítulo II (arts. 19-41)" if c in cod_uvr
                                                     else "el código no está en la cotización"))
    marc = [f for f in pesos_ if f["codigo"] in pedidos]
    for f in marc:
        if not 19 <= f["articulo"] <= 41:
            errores.append(f"--anestesia-cap2 {f['codigo']}: no es un examen o procedimiento del Capítulo II "
                           f"(arts. 19-41; es del art. {f['articulo']})")
    marc = [f for f in marc if 19 <= f["articulo"] <= 41]
    if marc and cods & {"S41230", "S41231", "S41232", "S41233", "S41234", "S41235", "S41236"}:
        errores.append("--anestesia-cap2: la cotización ya trae un código S4123x del anestesiólogo (art. 62); "
                       "use una sola forma")
        marc = []
    mat_auto = []  # (código que lo causa, S55115 | S55116)
    if marc:
        # anestesiólogo: el procedimiento de tarifa superior (art. 62: «o de aquella superior»)
        candidatos = []
        for f in marc:
            ruta = norm(f.get("agrupador_ruta") or "")
            if f["codigo"] in NEURO_27P8 or "INTERVENCIONISTA" in ruta or RE_HEMODINAMIA.search(f["descripcion"]):
                pct = ("25 % (literal b)" if f["codigo"] in NEURO_27P8 else "30 % (literal a)"
                       if "INTERVENCIONISTA" in ruta else "30 % (literal c)")
                avisos.append(f"{f['codigo']}: anestesiólogo en intervencionismo o hemodinamia: {pct} sobre el «valor "
                              "operativo» del estudio (art. 62 par., pág. 151); el Manual no separa ese valor de la "
                              "tarifa: no se suma")
                continue
            if "RESONANCIA MAGNETICA" in ruta:
                candidatos.append((valor_codigo(d, "S41233") or 60225.0, f, "S41233", "resonancia magnética"))
            elif norm(f.get("titulo") or "") == "RADIOLOGIA" or "TOMOGRAFIA" in ruta:
                candidatos.append((valor_codigo(d, "S41232") or 29100.0, f, "S41232",
                                   "estudios radiológicos convencionales y de TAC"))
            else:
                candidatos.append((f["valor"] * 0.5, f, "", ""))
        if candidatos:
            monto, f, cod_fijo, nombre = max(candidatos, key=lambda x: (x[1]["valor"], x[0]))
            if cod_fijo:
                aj("R62", f, monto, f"Anestesiólogo: {cod_fijo} {nombre}, valor fijo", "art. 62 (pág. 150)", 62)
                if cod_fijo in MAT_85P4:
                    mat_auto.append((f, "S55116"))
            else:
                aj("R62", f, monto, "Anestesiólogo: 50 % de la tarifa del procedimiento"
                   + (" (el de tarifa superior)" if len(marc) > 1 or f["cantidad"] > 1 else ""),
                   "art. 62 (pág. 150)", 62)
            if len(candidatos) > 1 or f["cantidad"] > 1:
                avisos.append("Anestesia en varios procedimientos del Capítulo II: el anestesiólogo y el quirófano "
                              "se pagan una vez, sobre el de tarifa superior (arts. 62 y 78)")
        # quirófano: art. 27 par. 8 para los 8 intervencionistas; art. 78 para los demás
        if hay_uvr and op.get("mismo-acto"):
            avisos.append("Capítulo II con anestesia en el mismo acto de una cirugía: si es complementario de ella no "
                          "hay derechos de quirófano aparte (art. 78); no se suman")
        else:
            otros = [f for f in marc if f["codigo"] not in NEURO_27P8]  # los 8 del par. 8 van abajo
            if otros:
                f = max(otros, key=lambda x: x["valor"])
                aj("R78", f, f["valor"] * 0.8, "Derechos de quirófano: 80 % de la tarifa del procedimiento"
                   + (" (el de tarifa superior)" if len(otros) > 1 or f["cantidad"] > 1 else ""),
                   "art. 78 (pág. 156)", 78)
            if hay_uvr:
                avisos.append("Capítulo II con anestesia y cirugías en UVR en la cotización: si el procedimiento fue "
                              "complementario de la cirugía, no hay quirófano aparte (art. 78)")
    # art. 27 par. 8: los 8 intervencionistas pagan siempre el uso del quirófano o de la sala especial
    # (60 % de la tarifa, una vez; en los múltiples, sobre la superior), con o sin anestesia
    neuro = [f for f in pesos_ if f["codigo"] in NEURO_27P8]
    if neuro:
        f = max(neuro, key=lambda x: x["valor"])
        aj("R27P8", f, f["valor"] * 0.6, "Uso del quirófano o sala especial: 60 % de la tarifa (una vez; en los "
           "bilaterales o múltiples, sobre la superior)", "art. 27 par. 8 (pág. 122)", 27)
    # materiales con valor fijo (art. 85 par. 3 y 4), por cada procedimiento
    for f in pesos_:
        if f["codigo"] in MAT_85P3:
            mat_auto.append((f, "S55115"))
        elif f["codigo"] in MAT_85P4:
            mat_auto.append((f, "S55116"))
    vistos = set()
    for f, mcod in mat_auto:
        if (f["codigo"], mcod) in vistos:
            continue
        vistos.add((f["codigo"], mcod))
        if mcod in cods:
            avisos.append(f"{f['codigo']}: los materiales {mcod} ya están en la cotización (art. 85)")
            continue
        v = valor_codigo(d, mcod)
        n = f["cantidad"] if f["codigo"] in MAT_85P3 | MAT_85P4 else 1
        aj("R85P" + ("3" if mcod == "S55115" else "4"), f, (v or 0) * n,
           f"Materiales de sutura y curación, agentes y gases anestésicos {mcod}" + (f" x {n}" if n > 1 else ""),
           f"art. 85 par. {3 if mcod == 'S55115' else 4} (pág. 159)", 85)
    return ajustes, errores, avisos


def cotizar(items, op, d):
    filas, errores, avisos = resolver(items, d)
    op = dict(op)
    err_u, av_u = liquidar_uvr(filas, op, d) if filas else ([], [])
    # el bilateral y el mismo acto de las cirugías en UVR ya se aplicaron: no van a las reglas en pesos
    cod_uvr = {f["codigo"] for f in filas if f["unidad"] == "UVR"}
    op["bilateral"] = [c for c in op.get("bilateral") or [] if normcod(c) not in cod_uvr]
    op["_hay_uvr"] = bool(cod_uvr)
    pesos_ = [f for f in filas if f["base"] is not None and f["unidad"] != "UVR"]
    ajustes, err2, av2 = aplicar(pesos_, op, d) if pesos_ else ([], [], [])
    aj3, err3, av3 = capitulo2_anestesia(pesos_, op, d, cod_uvr)
    ajustes, err2, av2 = ajustes + aj3, err2 + err3, av2 + av3
    if not pesos_ and op.get("mismo-acto") and not cod_uvr:
        err2.append("--mismo-acto: la cotización no tiene conjuntos del art. 95 ni cirugías en UVR")
    return filas, ajustes, errores + err_u + err2, avisos + av_u + av2


# ---------------------------------------------------------------- consola
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.split("\n")[11:]))
    ap.add_argument("items", nargs="+", help="CODIGO, CODIGOxCANTIDAD o CODIGO@REF")
    ap.add_argument("--solo-muestra", nargs="*", metavar="COD",
                    help="solo toma de muestra: 12%% (art. 25 par. 3); sin códigos = todo el laboratorio")
    ap.add_argument("--biopsia-multiple", nargs="+", metavar="COD", help="+60%% (art. 26 par. 1)")
    ap.add_argument("--portatil-rx", nargs="+", metavar="COD:VARIANTE",
                    help="radiología portátil, simple o fluoroscopia (art. 27 par. 4)")
    ap.add_argument("--portatil-eco", nargs="+", metavar="COD", help="ecografía portátil (art. 27 par. 12)")
    ap.add_argument("--tecnecio", action="store_true", help="medicina nuclear con tecnecio 99 (art. 27 par. 16)")
    ap.add_argument("--bilateral", nargs="+", metavar="COD", help="conjunto bilateral: +55%% (art. 95 par. 6)")
    ap.add_argument("--mismo-acto", choices=["igual", "diferente", "distinta"],
                    help="varios conjuntos en un mismo acto (art. 95 par. 7): igual = mismo "
                         "especialista e igual vía (100%% + 25%%); diferente o distinta = otra vía o "
                         "especialidad (100%% + 70%% de cada uno de los demás). Cirugías en UVR: igual "
                         "(art. 65), diferente (art. 66), distinta = especialistas de distinta especialidad "
                         "(art. 67; indique cada uno con --especialista)")
    ap.add_argument("--accesorio", nargs="+", metavar="COD:CLAVE",
                    help="accesorio del art. 77 par. 7 en una cirugía en UVR en quirófano, por procedimiento: "
                         "cuchilla (artroscopio, terapéutica, $41.395) | trocar (laparoscópica, $303.995) | "
                         "asa (urológica endoscópica, $40.000); en sala de endoscopia, una vez por paciente "
                         "(art. 80 par. 2): papilotomo (extracción de cálculos, $121.075) | litotripsia "
                         "(mecánica biliar, $200.075)")
    ap.add_argument("--anestesia-cap2", nargs="+", metavar="COD",
                    help="examen o procedimiento del Capítulo II con anestesia general o regional: anestesiólogo "
                         "50%% de la tarifa (art. 62; RM S41233, radiología y TAC S41232) y quirófano 80%% "
                         "(art. 78; 60%% en los intervencionistas del art. 27 par. 8)")
    ap.add_argument("--politrauma", action="store_true",
                    help="cirugías en UVR en politrauma abdominal, torácico, craneofacial o fracturas múltiples: "
                         "igual vía, 60%% desde la tercera (art. 65 par.); diferente vía, sala y materiales 50%% "
                         "hasta la tercera adicional (art. 77 par. 6, art. 85 par. 5)")
    ap.add_argument("--especialista", nargs="+", metavar="COD:N",
                    help="con --mismo-acto distinta: qué especialista hizo cada cirugía en UVR (1, 2, 3...)")
    ap.add_argument("--region-134", metavar="DEPTO:MUNICIPIO",
                    help="atención en los departamentos/región del art. 134, con recursos del "
                         "prestador en el área: +15%% Capítulo II, +14%% conjuntos")
    ap.add_argument("--uvr-sala", nargs="+", metavar="COD:SALA",
                    help="cirugía en UVR: quirofano (por defecto) | especial | endoscopia | basica (arts. 77-81)")
    ap.add_argument("--sin-anestesia", nargs="+", metavar="COD",
                    help="cirugía en UVR con anestesia local: sin honorario de anestesiólogo (art. 61)")
    ap.add_argument("--ayudante", nargs="+", metavar="COD",
                    help="cirugía en UVR con ayudante quirúrgico (desde 50 UVR, art. 63)")
    ap.add_argument("--ayudante-especialista", nargs="+", metavar="COD",
                    help="cirugía en UVR con ayudante de igual especialidad que el cirujano: $960 por UVR "
                         "con 450 UVR o más, o en el 815101 (art. 63 par.)")
    ap.add_argument("--recuperacion", nargs="+", metavar="COD:NIVEL",
                    help="cirugía en UVR con más de 6 horas en recuperación: baja | mediana | alta (art. 84); "
                         "o recuperación en cuidado intensivo o intermedio menos de 24 h, 50 %% de la estancia "
                         "(art. 84 par.): uci-adulto | uci-pediatrica | uci-neonatal | intermedio-adulto | "
                         "intermedio-pediatrico | intermedio-neonatal")
    ap.add_argument("--materiales", nargs="+", metavar="COD:VALOR",
                    help="cirugía en UVR con materiales según consumo (más de 170 UVR o múltiples, art. 85 "
                         "par. 1): valor en pesos de la hoja de gasto")
    ap.add_argument("--descuento-sala", choices=["instrumentacion", "enfermeria", "ambos"],
                    help="la EPS aporta instrumentación (-20%%), enfermería (-25%%) o ambas (-45%%) (art. 77 par. 4)")
    ap.add_argument("--suministro", nargs="+", metavar="PRECIO[xCANT]:DESCRIPCION",
                    help="suministro del art. 88 a precio de compra (se le suma el 12%%), "
                         "ej. 850000x2:\"Placa bloqueada\"")
    ap.add_argument("--medicamento", nargs="+", metavar="PRECIO[xCANT]:DESCRIPCION",
                    help="medicamento o solución a precio de compra: +12%% prestador externo (art. 87 a)")
    ap.add_argument("--medicamento-interno", nargs="+", metavar="PRECIO[xCANT]:DESCRIPCION",
                    help="medicamento o solución a precio de compra: +5%% prestador interno (art. 87 b)")
    ap.add_argument("--tutor", nargs="+", metavar="PRECIO[xCANT]:DESCRIPCION",
                    help="tutor (fijación externa) en préstamo: 25%% de (compra + 12%%) por paciente (art. 88 par. 2)")
    ap.add_argument("--contrato", type=float, default=0.0, metavar="PCT",
                    help="ajuste del contrato en %% sobre el valor total (ej. 4 o -5; 0 = valores del Manual)")
    ap.add_argument("--csv", help="guarda el detalle en este CSV")
    a = ap.parse_args()

    rx = {}
    for x in a.portatil_rx or []:
        cod, _, var = x.partition(":")
        rx[normcod(cod)] = var.lower()
    acc_cli = {}
    for x in a.accesorio or []:
        cod, _, k = x.partition(":")
        acc_cli.setdefault(cod, []).append(k.lower())
    op = {"solo-muestra": a.solo_muestra, "biopsia-multiple": a.biopsia_multiple or [],
          "portatil-rx": rx, "portatil-eco": a.portatil_eco or [], "tecnecio": a.tecnecio,
          "bilateral": a.bilateral or [], "mismo-acto": a.mismo_acto,
          "region-134": a.region_134,
          "uvr-sala": dict(x.split(":", 1) for x in a.uvr_sala or [] if ":" in x),
          "sin-anestesia": a.sin_anestesia or [], "ayudante": a.ayudante or [],
          "ayudante-especialista": a.ayudante_especialista or [],
          "especialista": dict(x.split(":", 1) for x in a.especialista or [] if ":" in x),
          "politrauma": a.politrauma,
          "anestesia-cap2": a.anestesia_cap2 or [],
          "accesorios": acc_cli,
          "recuperacion": dict(x.split(":", 1) for x in a.recuperacion or [] if ":" in x),
          "materiales": dict(x.split(":", 1) for x in a.materiales or [] if ":" in x),
          "descuento-sala": a.descuento_sala}

    def sumin(x, prestamo=False, tipo="suministro"):
        precio, _, desc = x.partition(":")
        precio, _, cant = precio.lower().partition("x")
        return dict(descripcion=desc, precio=precio.replace(".", "").replace(",", "."), cantidad=cant or 1,
                    prestamo=prestamo, tipo=tipo)
    sumi, err_s = liquidar_suministros([sumin(x) for x in a.suministro or []]
                                       + [sumin(x, True) for x in a.tutor or []]
                                       + [sumin(x, tipo="med_externo") for x in a.medicamento or []]
                                       + [sumin(x, tipo="med_interno") for x in a.medicamento_interno or []])

    d = cargar()
    filas, ajustes, errores, avisos = cotizar(a.items, op, d)
    errores += err_s
    if errores:
        for e in errores:
            print("ERROR:", e)
        print("\nNo se calcula el total mientras haya errores.")
        sys.exit(1)

    print(f"{'código':8} {'descripción':52} {'art':>3} {'valor':>13} {'cant':>4} {'subtotal':>13}")
    for f in filas:
        val = pesos(f["valor"]) if f["unidad"] == "pesos" else f"{f['valor']:g} {f['unidad']}"
        sub = pesos(f["base"]) if f["base"] is not None else "-"
        print(f"{f['codigo']:8} {f['descripcion'][:52]:52} {f['articulo']:>3} {val:>13} "
              f"{f['cantidad']:>4} {sub:>13}")
        for c in f.get("uvr_detalle", []):
            print(f"{'':10}· {c['concepto'][:66]:66} {pesos(c['monto']):>13}  {c['cita']}")
    base = sum(f["base"] for f in filas if f["base"] is not None)
    print(f"{'Tarifas (pesos)':>83} {pesos(base):>13}")
    if ajustes:
        print("\nRecargos y descuentos aplicados (pedidos con opción o automáticos por código):")
        for x in ajustes:
            print(f" {pesos(x['monto']):>13}  {x['codigo'] or 'por paciente':12} {x['cita']}: {x['texto']}")
    total = base + sum(x["monto"] for x in ajustes)
    if sumi:
        print("\nSuministros y medicamentos (arts. 87 y 88: precio de compra + 12 % o + 5 %):")
        for x in sumi:
            print(f" {pesos(x['monto']):>13}  {x['descripcion'][:50]:50} compra {pesos(x['compra'])}  "
                  f"{x['texto']}, {x['cita']}")
        total += sum(x["monto"] for x in sumi)
    if a.contrato:
        aj = ajuste_contrato(total, a.contrato)
        print(f"\n{'Según el Manual':>83} {pesos(total):>13}")
        print(f"{f'Contrato {a.contrato:+g} %':>83} {pesos(aj):>13}")
        total += aj
    print(f"\n{'TOTAL':>83} {pesos(total):>13}")

    if a.csv:
        det = pd.DataFrame(
            [dict(tipo="tarifa", codigo=f["codigo"], descripcion=f["descripcion"],
                  articulo=f["articulo"], unidad=f["unidad"], valor=f["valor"],
                  cantidad=f["cantidad"], monto=f["base"], cita="") for f in filas] +
            [dict(tipo="ajuste", codigo=x["codigo"], descripcion=x["texto"], articulo="",
                  unidad="pesos", valor="", cantidad="", monto=x["monto"], cita=x["cita"])
             for x in ajustes])
        det.to_csv(a.csv, index=False, encoding="utf-8-sig")
        print(f"detalle en {a.csv}")

    if avisos:
        print("\nAvisos (revíselos; no se aplicaron):")
        for x in avisos:
            print(" -", x[:160])
    pa = parrafos(filas, d)
    if pa:
        print("\nParágrafos que pueden modificar el valor (revíselos):")
        for p in pa:
            marca = ("" if not p["opcion"] else " [regla pendiente de aprobación]"
                     if p["opcion"] == "pendiente" else f" [opción --{p['opcion']}]")
            print(f" - art. {p['articulo']}{marca}: {p['texto'][:140]}")


if __name__ == "__main__":
    main()
