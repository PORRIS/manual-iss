"""Cotizador de servicios con tarifas del Manual ISS 2001 (salida/manual_iss.db).

Suma las tarifas en pesos de los códigos dados y aplica SOLO las reglas de recargo o
descuento que se piden con una opción explícita (el código no dice si un estudio fue
portátil o un conjunto bilateral; eso lo declara quien cotiza). Las cifras y el alcance
de cada regla están en reglas_tarifas.csv, con artículo, parágrafo y página del PDF; las
que tienen estado distinto de "aprobada" no se aplican.

Lo demás que puede cambiar el valor (varios conjuntos en un mismo acto, contrato,
insumos según consumo, ...) solo se avisa. Los procedimientos en UVR (arts. 1-18) no se
suman: se liquidan con liquidar.py. Una cotización corresponde a un paciente.

Uso:
    uv run cotizar.py 903801 871112x2 C40402
    uv run cotizar.py 903801 --solo-muestra                 # 12% (art. 25 par. 3)
    uv run cotizar.py 898101 --biopsia-multiple 898101       # +60% (art. 26 par. 1)
    uv run cotizar.py 871112 --portatil-rx 871112:fluoroscopia   # simple | fluoroscopia
    uv run cotizar.py 951301 --portatil-eco 951301          # +$9.095 (art. 27 par. 12)
    uv run cotizar.py 920302 --tecnecio                     # +$13.120 por paciente
    uv run cotizar.py C40402 --bilateral C40402             # +55% (art. 95 par. 6)
    uv run cotizar.py 903801 C40402 --region-134 META:Granada   # +15% / +14% (art. 134)
    uv run cotizar.py 697100@41501                          # CODIGO@REF si hay varios valores
    uv run cotizar.py 903801 --csv cotizacion.csv
"""
import argparse
import re
import sys
import unicodedata

import pandas as pd

from rutas import BASE, conectar

DB = BASE / "salida" / "manual_iss.db"
REGLAS = BASE / "reglas_tarifas.csv"
RE_ITEM = re.compile(r"^(?P<codigo>[A-Za-z]?\d{4,6})(?:x(?P<cant>\d+))?(?:@(?P<ref>\w+))?$")
# Art. 134 (pág. 204): departamentos y región con incremento; par. 2 (pág. 205): ciudades
# donde no aplica. "URABA" = municipios de la región de Urabá (el Manual no los enumera).
DEPTOS_134 = {"AMAZONAS", "ARAUCA", "CASANARE", "CAQUETA", "CHOCO", "GUAJIRA", "LA GUAJIRA",
              "GUAINIA", "GUAVIARE", "META", "PUTUMAYO", "SAN ANDRES", "SAN ANDRES Y PROVIDENCIA",
              "SUCRE", "VAUPES", "VICHADA", "URABA"}
EXCEPTUADAS_134 = {"ARAUCA", "FLORENCIA", "RIOHACHA", "SINCELEJO", "VILLAVICENCIO", "YOPAL"}
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
            avisos.append(f"{cod}: está en UVR ({r.valor:g}); liquídelo con liquidar.py")
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
                            texto=r.texto, monto=monto))

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
    for opcion in {k for k, v in op.items() if v not in (None, False, [], {})}:
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
                                             if x["codigo"] == f["codigo"])
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


def cotizar(items, op, d):
    filas, errores, avisos = resolver(items, d)
    ajustes, err2, av2 = aplicar(filas, dict(op), d) if filas else ([], [], [])
    return filas, ajustes, errores + err2, avisos + av2


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
    ap.add_argument("--region-134", metavar="DEPTO:MUNICIPIO",
                    help="atención en los departamentos/región del art. 134, con recursos del "
                         "prestador en el área: +15%% Capítulo II, +14%% conjuntos")
    ap.add_argument("--csv", help="guarda el detalle en este CSV")
    a = ap.parse_args()

    rx = {}
    for x in a.portatil_rx or []:
        cod, _, var = x.partition(":")
        rx[normcod(cod)] = var.lower()
    op = {"solo-muestra": a.solo_muestra, "biopsia-multiple": a.biopsia_multiple or [],
          "portatil-rx": rx, "portatil-eco": a.portatil_eco or [], "tecnecio": a.tecnecio,
          "bilateral": a.bilateral or [], "region-134": a.region_134}

    d = cargar()
    filas, ajustes, errores, avisos = cotizar(a.items, op, d)
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
    base = sum(f["base"] for f in filas if f["base"] is not None)
    print(f"{'Tarifas (pesos)':>83} {pesos(base):>13}")
    if ajustes:
        print("\nRecargos y descuentos aplicados (pedidos con opción o automáticos por código):")
        for x in ajustes:
            print(f" {pesos(x['monto']):>13}  {x['codigo'] or 'por paciente':12} {x['cita']}: {x['texto']}")
    total = base + sum(x["monto"] for x in ajustes)
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
    arts = {f["articulo"] for f in filas}
    pa = d["parr"][d["parr"].articulo.isin(arts) & d["parr"].texto.str.contains(RE_MODIFICA)]
    if len(pa):
        print("\nParágrafos que pueden modificar el valor (revíselos):")
        for p in pa.itertuples():
            rr = d["reglas"][(d["reglas"].articulo == str(p.articulo)) & d["reglas"].paragrafo.map(
                lambda n, t=p.texto: t.startswith((f"PARAGRAFO {n}.", f"PARAGRAFO {n} ")))]
            marca = ""
            if len(rr):
                marca = (f" [opción --{rr.opcion.iloc[0]}]" if (rr.estado == "aprobada").all()
                         else " [regla pendiente de aprobación]")
            print(f" - art. {p.articulo}{marca}: {p.texto[:140]}")


if __name__ == "__main__":
    main()
