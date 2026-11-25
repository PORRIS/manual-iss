"""Cotizador del Manual Tarifario SOAT 2026 (UVB), sobre soat2026/salida/manual_soat_2026.db.

Una cotización es un paciente y un acto. Cada ítem es un código del Manual con opciones:

- Unidad de liquidación, a elegir (el PDF trae las tres): UVB ($12.110, la tarifa oficial 2026), UVT
  ($52.374) o SMLDV ($58.363). Valor = factor de esa unidad x valor de la unidad. El valor de la unidad
  se puede cambiar (otro año). En UVT el PDF imprime el factor con 2 decimales y su columna de valor
  se calculó con más decimales: en 200 códigos factor x $52.374 difiere del valor impreso hasta $300.
- Procedimiento con valor (cap. IV y V, conjuntos del art. 64): factor x unidad, por la cantidad.
    bilateral       +75 % (art. 70 par. 2; conjuntos: art. 64 par. 3)
    anestesia       anestesia general en un examen o procedimiento: +50 % de su tarifa (art. 48 a.2);
                    los códigos 39150-39155 tienen valor propio y se cotizan aparte
- Cirugía (código con grupo quirúrgico, cap. III): se liquida por componentes del grupo
    cirujano y anestesiólogo (art. 48 a.1 y a.2), ayudante desde el grupo 06 (art. 48 a.3),
    derechos de sala (art. 49) y materiales (art. 55; grupos 20-23 a precio de catálogo, par. 1).
    sin_anestesiologo  anestesia local: no se cobra anestesiólogo
    sin_ayudante       no se requirió ayudante (art. 48: solo cuando se requiere el recurso)
    perfusionista      39129, solo grupos especiales 20-23 (art. 48 b)
    bilateral          honorarios +75 % (art. 70), sala +50 % (art. 49 par. 1), materiales +75 % (art. 55 par. 4)
    incruenta          en sala quirúrgica o especial (art. 52): sala = 45 % de la sala del grupo y
                       materiales = 39305 (art. 55 par. 2)
- Varias cirugías en el mismo acto: la mayor (grupo con mayor honorario de cirujano) va al 100 % y
  cada adicional según su relación con ella:
    igual_via          mismo cirujano, igual vía (art. 71): honorarios 50 %; sala y materiales no se suman
    diferente_via      mismo cirujano, diferente vía (art. 72): honorarios 75 %; sala 50 % (art. 49
                       par. 1); materiales 75 % (art. 55 inciso del par. 4)
    otra_especialidad  cirujano de otra especialidad (art. 73): cirujano 100 %, anestesiólogo 75 %
                       (par. 1), ayudante 50 % solo de la adicional de mayor grupo (par. 2), sala 50 %
                       (art. 49 par. 1); materiales no se suman
  Conjuntos (art. 64 par. 4 b): con más de uno, el mayor va al 100 % y cada otro al 25 % (igual vía)
  o al 70 % (diferente vía u otra especialidad). Conjunto y cirugías (par. 4 a): el conjunto es la mayor
  y todas las cirugías son adicionales.
- Parto (12101, 12102): cirujano o ginecoobstetra del grupo 07, anestesiólogo 39116 (art. 48 a.2), sala de parto
  39220 (art. 50); parto y legrado (11430, 12111): materiales incluidos
  en la sala (art. 55 par. 3).
- Región (art. 86): +25 % a consultas, valoraciones, cuidado intrahospitalario y servicios
  profesionales de cirujano, ginecobstetra, anestesiólogo y ayudante (literal a); +15 % a los
  exámenes y procedimientos del capítulo IV (literal b). No aplica en los municipios exceptuados.
- Cada valor se ajusta a la centena más próxima (art. 89).
- Ajuste del contrato (opcional, 0 % por defecto): un porcentaje (+4, -5...) que se aplica al final sobre
  cada valor ya liquidado con las reglas del PDF, a la centena. Con 0 % no cambia nada.

Uso:
  uv run soat2026/cotizar.py 19001 21101x2 1101            # código, códigoxcantidad
  uv run soat2026/cotizar.py 1101 1102:diferente_via 1101:bilateral --region META
  uv run soat2026/cotizar.py 1101:sin_ayudante:sin_anestesiologo --valor 11552   # UVB de otro año
  uv run soat2026/cotizar.py 1101 19001 --unidad smldv                           # en SMLDV
  uv run soat2026/cotizar.py 1101 --contrato 4                                   # contrato SOAT + 4 %
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "salida" / "manual_soat_2026.db"

OPCIONES_CIRUGIA = ("bilateral", "sin_anestesiologo", "sin_ayudante", "perfusionista", "incruenta")
OPCIONES_VALOR = ("bilateral", "anestesia", "incruenta")
RELACIONES = ("igual_via", "diferente_via", "otra_especialidad")
RELACION_TXT = {"igual_via": "mismo cirujano, igual vía", "diferente_via": "mismo cirujano, diferente vía",
                "otra_especialidad": "cirujano de otra especialidad"}
CONCEPTOS = (("cirujano", "Cirujano"), ("anestesiologo", "Anestesiólogo"), ("ayudante", "Ayudante"),
             ("sala", "Derechos de sala"), ("materiales", "Materiales"))
PROFESIONALES = {"cirujano", "anestesiologo", "ayudante"}
# Art. 50: el parto usa la sala de parto 39220, que incluye materiales, medicamentos, oxígeno y gases (la
# cesárea, por el par. del art. 50, va con la sala de su grupo). Art. 55 par. 3: en el parto y en el legrado
# uterino obstétrico y ginecológico los materiales están incluidos en los derechos de sala.
PARTO = {"12101", "12102"}
# Art. 51 (pág. de estancias del art. 47): recuperación de más de 6 horas -> 50 % de la estancia de la cama que
# ocupe el paciente; cirugía ambulatoria -> estancia de habitación de tres camas según el nivel; grupos
# especiales con recuperación en UCI menos de 24 h -> 50 % de la estancia en UCI (38525)
CAMAS_47 = ("38111", "38112", "38113", "38114", "38121", "38122", "38123", "38124",
            "38131", "38132", "38133", "38134")
AMBULATORIA_51 = {"1": "38113", "2": "38123", "3": "38133"}
UCI_51 = "38525"
# Arts. 55 par. 1, 56, 57, 59 y 64 par. 2: a precio comercial de catálogo (sin porcentaje)
TIPOS_CATALOGO = {
    "suministro": ("Suministro (prótesis, órtesis, placas, tornillos, mallas, catéteres...)", "art. 57"),
    "medicamento": ("Drogas, medicamentos y soluciones", "art. 56"),
    "oxigeno": ("Oxígeno", "art. 59"),
    "insumo_conjunto": ("Insumo que se cobra aparte del conjunto", "art. 64 par. 2; art. 57"),
}
MATERIALES_EN_SALA = PARTO | {"11430", "12111"}

# Art. 86: departamentos y región con incremento, y municipios exceptuados
REGIONES_86 = ("AMAZONAS", "ARAUCA", "CASANARE", "CAQUETÁ", "CHOCÓ", "LA GUAJIRA", "GUAINÍA", "GUAVIARE", "META",
               "PUTUMAYO", "SAN ANDRÉS Y PROVIDENCIA", "SUCRE", "VAUPÉS", "VICHADA", "REGIÓN DE URABÁ")
EXCEPTUADOS_86 = ("Arauca", "Florencia", "Riohacha", "Sincelejo", "Villavicencio", "Yopal")
# Art. 86 literal a: consultas, valoraciones, cuidado intrahospitalario, recién nacido, urgencias (art. 48 c)
# y el anestesiólogo del parto (39116, en «servicios profesionales del anestesiólogo», pág. 91). Perfusión (39129), junta médica (39144) y sutura (39146)
# no están en la lista del literal a.
LITERAL_A = {"39116", "39130", "39131", "39132", "39133", "39134", "39135", "39136", "39137", "39138", "39139",
             "39140", "39141", "39143", "39145", "39149", "39150", "39151", "39152", "39153", "39154", "39155"}
UNIDADES = {"uvb": "UVB", "uvt": "UVT", "smldv": "SMLDV"}
RE_ITEM = re.compile(r"^(?P<codigo>\d{4,6})(?:x(?P<cant>\d+))?(?P<opc>(?::[a-z_0-9]+)*)$")


def centena(v):
    """Art. 89: ajuste a la centena más próxima (las mitades suben)."""
    return int((v + 50) // 100 * 100) if v >= 0 else -centena(-v)


def pesos(v):
    return "$" + f"{v:,.0f}".replace(",", ".")


# ------------------------------------------------------------------------------------- datos
def cargar(db=DB):
    if not Path(db).exists():
        raise FileNotFoundError(f"No existe {db}: genérela con soat2026/actualizar.sh")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    procs = {}
    for cod, desc, art, grupo, fsm, fut, fuvb, pag, cap in con.execute(
            "SELECT p.codigo, p.descripcion, p.articulo, p.grupo_quirurgico, p.factor_smldv, p.factor_uvt, "
            "p.factor_uvb, p.pagina, c.numero "
            "FROM procedimientos p JOIN articulos a ON a.numero = p.articulo "
            "JOIN capitulos c ON c.id = a.capitulo_id"):
        procs[cod] = dict(codigo=cod, descripcion=desc, articulo=art, grupo=grupo, factor_uvb=fuvb,
                          factor_uvt=fut, factor_smldv=fsm,
                          pagina=pag, capitulo=cap)
    grupos = {}
    for grupo, concepto, cod in con.execute(
            "SELECT g.grupo, g.concepto, p.codigo FROM tarifas_grupo g JOIN procedimientos p ON p.id = g.procedimiento_id"):
        grupos[(grupo, concepto)] = cod
    param = dict(con.execute("SELECT concepto, valor FROM parametros"))
    con.close()
    return dict(procs=procs, grupos=grupos, uvb=param["UVB"],
                valores={u: param[n] for u, n in UNIDADES.items()})


def factor(d, cod, u):
    """Factor del código en la unidad elegida (None o 0 = el PDF no lo trae)."""
    return d["procs"][cod][f"factor_{u['unidad']}"]


def valor(d, cod, u):
    """Valor en pesos: factor de la unidad x valor de la unidad, a la centena (art. 89)."""
    f = factor(d, cod, u)
    return centena(f * u["valor"]) if f else None


def tasa(d, unidad="uvb", valor_unidad=None):
    unidad = (unidad or "uvb").lower()
    if unidad not in UNIDADES:
        raise ValueError(f"Unidad «{unidad}» no válida: use {', '.join(UNIDADES)}")
    return dict(unidad=unidad, nombre=UNIDADES[unidad], valor=valor_unidad or d["valores"][unidad])


def formula(d, cod, u):
    return f"{factor(d, cod, u):g} {u['nombre']} x {pesos(u['valor'])}"


# ------------------------------------------------------------------------------------- lectura
def leer_items(textos):
    """'1101', '19001x2', '1102:diferente_via:bilateral' -> [{codigo, cantidad, opciones, relacion}]"""
    items, errores = [], []
    for t in textos:
        t = t.strip()
        if not t:
            continue
        m = RE_ITEM.match(t.lower())
        if not m:
            errores.append(f"«{t}»: escriba CODIGO, CODIGOxCANTIDAD o CODIGO:opcion (ej. 1101:bilateral)")
            continue
        opc = [o for o in m["opc"].split(":") if o]
        esp = [o[3:] for o in opc if re.fullmatch(r"esp\d", o)]
        opc = [o for o in opc if not re.fullmatch(r"esp\d", o)]
        rel = [o for o in opc if o in RELACIONES]
        malas = [o for o in opc if o not in RELACIONES and o not in OPCIONES_CIRUGIA + OPCIONES_VALOR]
        if malas:
            errores.append(f"«{t}»: opción desconocida {', '.join(malas)}")
            continue
        items.append(dict(codigo=m["codigo"], cantidad=int(m["cant"] or 1),
                          opciones=[o for o in opc if o not in RELACIONES], relacion=rel[0] if rel else "",
                          especialista=esp[0] if esp else ""))
    return items, errores


# ------------------------------------------------------------------------------------- cálculo
def cotizar(items, d, valor_unidad=None, region="", exceptuado=False, unidad="uvb", contrato_pct=0.0,
            suministros=None):
    """items: [{codigo, cantidad, opciones: [...], relacion: ''|igual_via|diferente_via|otra_especialidad}]
    unidad: uvb | uvt | smldv; valor_unidad: pesos por unidad (por defecto el del PDF).
    contrato_pct: ajuste del contrato en % sobre cada valor final (0 = valores del PDF tal cual).
    Cada ítem de cirugía puede traer: especialista (art. 73, con relacion otra_especialidad: «2», «3»...),
    catalogo (pesos: materiales y elementos a precio de catálogo, grupos 20-23, art. 55 par. 1) y
    recuperacion («media:CAMA» 50 % de la estancia, «ambulatoria:NIVEL» o «uci», art. 51).
    suministros: [{descripcion, precio, cantidad, tipo}] a precio de catálogo (arts. 56, 57, 59, 64 par. 2).
    Devuelve {lineas, total, avisos, errores, unidad, valor_unidad, region, items}. Cada línea: item (índice), codigo, descripcion,
    concepto, base, porcentaje, valor, regla."""
    uvb = tasa(d, unidad, valor_unidad)          # unidad elegida: {unidad, nombre, valor}
    contrato_pct = float(contrato_pct or 0)
    salida = dict(unidad=uvb["unidad"], unidad_nombre=uvb["nombre"], valor_unidad=uvb["valor"],
                  contrato_pct=contrato_pct)
    if contrato_pct <= -100:
        return dict(lineas=[], total=0, total_manual=0, ajuste_contrato=0, avisos=[], items=[], region="",
                    errores=["El ajuste del contrato debe ser mayor que -100 %"], **salida)
    region = (region or "").strip().upper()
    if region and region not in REGIONES_86:
        return dict(lineas=[], total=0, total_manual=0, ajuste_contrato=0, avisos=[],
                    errores=[f"Región «{region}» no está en el art. 86"], region=region, items=[], **salida)
    lineas, avisos, errores = [], [], []
    cirugias, conjuntos = [], []
    info = []      # por ítem de entrada: tipo, grupo y si es la intervención mayor del acto

    def linea(i, it, concepto, base, pct, regla, codigo=None, descripcion=None, exacto=False):
        """exacto: precio de catálogo (no es una tarifa del Decreto: no se lleva a la centena)."""
        v = base * pct / 100
        lineas.append(dict(item=i, codigo=codigo or it["codigo"], descripcion=descripcion or it["descripcion"],
                           concepto=concepto, base=base, porcentaje=pct, valor=round(v, 2) if exacto else centena(v),
                           regla=regla, region86=0))

    # 1) validar y separar
    norm = []
    for i, it in enumerate(items):
        p = d["procs"].get(str(it["codigo"]).strip())
        if not p:
            errores.append(f"El código {it['codigo']} no está en el Manual SOAT 2026")
            info.append(dict(item=i, codigo=str(it["codigo"]), error=True))
            continue
        tipo = ("cirugia" if p["grupo"] is not None else
                "conjunto" if p["articulo"] == 64 and len(p["codigo"]) == 6 else "valor")
        info.append(dict(item=i, codigo=p["codigo"], descripcion=p["descripcion"], tipo=tipo, grupo=p["grupo"],
                         articulo=p["articulo"], pagina=p["pagina"], mayor=False,
                         opciones=list(OPCIONES_CIRUGIA) if tipo == "cirugia" else
                         [o for o in OPCIONES_VALOR if o != "incruenta" or (tipo == "valor" and p["capitulo"] == "IV")]))
        it = dict(it, **{k: p[k] for k in ("descripcion", "articulo", "grupo", "capitulo", "pagina")})
        it["opciones"] = list(dict.fromkeys(it.get("opciones") or []))
        it["cantidad"] = max(1, int(it.get("cantidad") or 1))
        it["i"] = i
        norm.append(it)
        if p["grupo"] is not None:
            malas = [o for o in it["opciones"] if o not in OPCIONES_CIRUGIA]
            if malas:
                avisos.append(f"{p['codigo']}: la opción {', '.join(malas)} no aplica a una cirugía; se ignora")
            for n in range(it["cantidad"]):    # cada repetición es otra cirugía del mismo acto
                cirugias.append(dict(it, cantidad=1, rep=n))
        else:
            malas = [o for o in it["opciones"] if o not in OPCIONES_VALOR]
            if malas:
                avisos.append(f"{p['codigo']}: la opción {', '.join(malas)} solo aplica a cirugías; se ignora")
            if not factor(d, p["codigo"], uvb):
                errores.append(f"{p['codigo']}: el PDF no trae factor {uvb['nombre']} para este código"
                               + (" (pruebe con otra unidad)" if any(p[f"factor_{x}"] for x in UNIDADES) else ""))
            elif p["articulo"] == 64 and len(p["codigo"]) == 6:   # conjuntos quirúrgicos (502001...)
                conjuntos.append(it)
            else:
                valorado(it, d, uvb, linea, avisos)

    # 2) cirugías: componentes del grupo y porcentajes del mismo acto
    mayores = set()
    if cirugias:   # con un conjunto en el acto, el conjunto es la mayor (art. 64 par. 4 a)
        mayores.add(liquidar_cirugias(cirugias, d, uvb, linea, avisos, errores, bool(conjuntos)))
    # 3) conjuntos de atención integral (art. 64)
    if conjuntos:
        mayores.add(liquidar_conjuntos(conjuntos, d, uvb, linea, avisos, bool(cirugias)))
    # 3b) a precio comercial de catálogo: suministros, medicamentos, oxígeno (arts. 56, 57, 59, 64 par. 2)
    for k, x in enumerate(suministros or []):
        tipo = x.get("tipo") or "suministro"
        try:
            precio, cant = float(x.get("precio")), float(x.get("cantidad") or 1)
        except (TypeError, ValueError):
            precio, cant = -1, 1
        desc = (x.get("descripcion") or "").strip() or TIPOS_CATALOGO.get(tipo, ("",))[0]
        if tipo not in TIPOS_CATALOGO:
            errores.append(f"«{desc}»: tipo no válido ({' | '.join(TIPOS_CATALOGO)})")
        elif precio <= 0 or cant <= 0:
            errores.append(f"«{desc}»: el precio de catálogo y la cantidad deben ser mayores que 0")
        else:
            nombre, art = TIPOS_CATALOGO[tipo]
            linea(10_000 + k, {"codigo": "", "descripcion": desc}, "catalogo", precio * cant, 100,
                  f"{nombre}: hasta el precio comercial de catálogo ({art})"
                  + (f"; {cant:g} x {pesos(precio)}" if cant != 1 else ""), codigo=tipo, exacto=True)
    for x in info:
        x["mayor"] = x["item"] in mayores

    # 4) art. 86: incremento regional
    if region and not exceptuado:
        for ln in lineas:
            pct = incremento_86(ln, d)
            if pct:
                ln["region86"] = pct
                ln["valor"] = centena(ln["valor"] * (1 + pct / 100))
                ln["regla"] += f"; +{pct} % región (art. 86 literal {'a' if pct == 25 else 'b'})"
    elif region and exceptuado:
        avisos.append("Municipio exceptuado del art. 86 (Arauca, Florencia, Riohacha, Sincelejo, Villavicencio o "
                      "Yopal): no se aplica el incremento regional")
    # 5) ajuste del contrato, al final y sobre el valor ya liquidado con las reglas del PDF
    for ln in lineas:
        ln["valor_manual"] = ln["valor"]
        ln["ajuste_contrato"] = 0
        if contrato_pct:
            ln["valor"] = centena(ln["valor_manual"] * (1 + contrato_pct / 100))
            ln["ajuste_contrato"] = ln["valor"] - ln["valor_manual"]
            ln["regla"] += f"; contrato {contrato_pct:+g} %"
    lineas.sort(key=lambda ln: (ln["item"], [c for c, _ in CONCEPTOS].index(ln["concepto"])
                                if ln["concepto"] in dict(CONCEPTOS) else 9))
    return dict(lineas=lineas, total=sum(ln["valor"] for ln in lineas), avisos=avisos, errores=errores,
                total_manual=sum(ln["valor_manual"] for ln in lineas),
                ajuste_contrato=sum(ln["ajuste_contrato"] for ln in lineas),
                region=region if not exceptuado else "", items=info, **salida)


def incremento_86(ln, d):
    p = d["procs"].get(ln["codigo"])
    if ln["concepto"] in PROFESIONALES:
        return 25
    if ln["concepto"] == "anestesia":
        return 25
    if ln["concepto"] != "tarifa" or not p:
        return 0
    if ln["codigo"] in LITERAL_A:
        return 25
    if p["capitulo"] == "IV":
        return 15
    return 0


def valorado(it, d, uvb, linea, avisos):
    """Procedimiento con valor propio (cap. IV y V)."""
    v = valor(d, it["codigo"], uvb) * it["cantidad"]
    pct, regla = 100, formula(d, it["codigo"], uvb)
    if it["cantidad"] > 1:
        regla += f" x {it['cantidad']}"
    if "bilateral" in it["opciones"]:
        pct, regla = 175, regla + "; bilateral +75 % (art. 70 par. 2)"
    linea(it["i"], it, "tarifa", v, pct, regla)
    if "incruenta" in it["opciones"]:
        if it.get("capitulo") != "IV":
            avisos.append(f"{it['codigo']}: «incruenta» con valor propio aplica a procedimientos del capítulo IV "
                          "(art. 52, art. 55 par. 2); se ignora")
        else:
            linea(it["i"], it, "sala", v, 45, "incruenta en sala quirúrgica o especial: 45 % de la tarifa del "
                  "procedimiento (art. 52)", descripcion=f"Derechos de sala — {it['descripcion']}")
            linea(it["i"], it, "materiales", valor(d, "39305", uvb) * it["cantidad"], 100,
                  "materiales en procedimiento incruento del capítulo IV: 39305 (art. 55 par. 2)"
                  + (f" x {it['cantidad']}" if it["cantidad"] > 1 else ""), codigo="39305",
                  descripcion=f"Materiales — {it['descripcion']}")
    if "anestesia" in it["opciones"]:
        if it["codigo"].startswith("3915"):
            avisos.append(f"{it['codigo']} ya es una tarifa de anestesia (art. 48): no se suma el 50 %")
        else:
            linea(it["i"], it, "anestesia", v, 50, "anestesia general: 50 % de la tarifa del procedimiento (art. 48 a.2)",
                  descripcion=f"Anestesia general — {it['descripcion']}")


def componentes(c, d, uvb):
    """Valores base del grupo de una cirugía: {concepto: (código, valor)}."""
    g = c["grupo"]
    out = {}
    for concepto, _ in CONCEPTOS:
        cod = d["grupos"].get((g, concepto))
        if cod:
            out[concepto] = (cod, valor(d, cod, uvb))
    return out


def liquidar_cirugias(cirugias, d, uvb, linea, avisos, errores, hay_conjunto=False):
    validas = []
    for c in cirugias:
        comp = componentes(c, d, uvb)
        if "cirujano" not in comp:
            errores.append(f"{c['codigo']} (grupo {c['grupo']:02d}): el art. 48 no trae honorarios para este grupo "
                           "(la tabla empieza en el grupo 02)")
            continue
        c["comp"] = comp
        validas.append(c)
    if not validas:
        return None
    # la mayor: grupo con mayor honorario de cirujano (a igualdad, la primera digitada); si en el acto hay
    # un conjunto, él es la intervención mayor y todas las cirugías son adicionales (art. 64 par. 4 a)
    if hay_conjunto:
        mayor = None
        adicionales = list(validas)
    else:
        mayor = max(validas, key=lambda c: (c["comp"]["cirujano"][1], -c["i"], -c["rep"]))
        adicionales = [c for c in validas if c is not mayor]
    # art. 73 par. 2: con otra especialidad, el ayudante solo cobra la adicional de mayor grupo
    otras = [c for c in adicionales if (c.get("relacion") or "igual_via") == "otra_especialidad"]
    ayud_otra = max(otras, key=lambda c: c["grupo"]) if otras else None
    # art. 73: cada cirujano de otra especialidad cobra 100 % de su mayor y 50 % de sus adicionales. Sin
    # especialista indicado, cada cirugía de otra especialidad es de un especialista distinto.
    esp_de = lambda c: str(c.get("especialista") or "") or f"_{c['i']}_{c['rep']}"  # noqa: E731
    mayor_esp = {}
    for c in otras:
        k = esp_de(c)
        if k not in mayor_esp or c["comp"]["cirujano"][1] > mayor_esp[k]["comp"]["cirujano"][1]:
            mayor_esp[k] = c
    recup_hecha = False
    for c in ([mayor] if mayor else []) + adicionales:
        es_mayor = c is mayor
        rel = "" if es_mayor else (c.get("relacion") or "igual_via")
        o = c["opciones"]
        g = c["grupo"]
        bil = "bilateral" in o
        incruenta = "incruenta" in o
        sufijo = f" — {'cirugía mayor' if es_mayor and adicionales else ('adicional, ' + RELACION_TXT[rel]) if rel else 'cirugía'}"
        if c["rep"]:
            sufijo += f" (repetición {c['rep'] + 1})"
        for concepto, nombre in CONCEPTOS:
            if concepto not in c["comp"]:
                if concepto == "materiales" and g >= 20 and not incruenta and not c.get("catalogo") and c["rep"] == 0:
                    avisos.append(f"{c['codigo']} (grupo {g}): los materiales de los grupos 20-23 se pagan a precio "
                                  "comercial de catálogo (art. 55 par. 1); digite su valor en «Precio de catálogo»")
                continue
            cod, base = c["comp"][concepto]
            if concepto == "anestesiologo" and "sin_anestesiologo" in o:
                continue
            if concepto == "ayudante" and "sin_ayudante" in o:
                continue
            if concepto == "materiales" and c["codigo"] in MATERIALES_EN_SALA:
                continue      # art. 55 par. 3 (y art. 50 en el parto): incluidos en los derechos de sala
            if concepto == "anestesiologo" and c["codigo"] in PARTO:
                # art. 48 a.2 (pág. 91): el anestesiólogo del parto normal o intervenido tiene código propio
                cod, base = "39116", valor(d, "39116", uvb)
                reglas = [f"Anestesiólogo en parto normal o intervenido: {cod} = {formula(d, cod, uvb)} (art. 48 a.2)"]
            elif concepto == "sala" and c["codigo"] in PARTO:
                cod, base = "39220", valor(d, "39220", uvb)
                nombre_sala = "Derechos de sala de parto (art. 50: incluye materiales, medicamentos, oxígeno y gases)"
                reglas = [f"{nombre_sala}: {cod} = {formula(d, cod, uvb)}"]
            else:
                reglas = [f"{nombre} grupo {g:02d}: {cod} = {formula(d, cod, uvb)}"]
            pct = 100.0
            # bilateral (art. 70 honorarios; art. 49 par. 1 sala; art. 55 par. 4 materiales)
            if bil:
                extra = 50 if concepto == "sala" else 75
                pct *= 1 + extra / 100
                reglas.append(f"bilateral +{extra} % ({'art. 49 par. 1' if concepto == 'sala' else 'art. 55 par. 4' if concepto == 'materiales' else 'art. 70'})")
            # incruenta en sala (art. 52 y art. 55 par. 2)
            if incruenta and concepto == "sala":
                pct *= 0.45
                reglas.append("incruenta: 45 % de la sala del grupo (art. 52)")
            if incruenta and concepto == "materiales":
                continue      # se reemplaza por 39305 abajo
            # cirugía adicional del mismo acto
            if rel:
                p = porcentaje_adicional(concepto, rel, c is ayud_otra)
                if (concepto == "cirujano" and rel == "otra_especialidad" and c.get("especialista")
                        and mayor_esp.get(esp_de(c)) is not c):
                    p = 50
                    reglas.append(f"segunda cirugía del especialista {c['especialista']}: 50 % (art. 73)")
                    pct *= p / 100
                    linea(c["i"], c, concepto, base, round(pct, 4), "; ".join(reglas),
                          descripcion=f"{c['descripcion']}{sufijo}")
                    continue
                if p == 0:
                    continue
                pct *= p / 100
                reglas.append(f"adicional {RELACION_TXT[rel]}: {p:g} % ({ARTICULO_REL[(rel, concepto)]})")
            linea(c["i"], c, concepto, base, round(pct, 4), "; ".join(reglas),
                  descripcion=f"{c['descripcion']}{sufijo}")
        if incruenta:
            mat = valor(d, "39305", uvb)
            pct = 100.0
            reglas = ["materiales en procedimiento incruento: 39305 (art. 55 par. 2)"]
            if rel and porcentaje_adicional("materiales", rel, False):
                p = porcentaje_adicional("materiales", rel, False)
                pct = p
                reglas.append(f"adicional {RELACION_TXT[rel]}: {p:g} %")
            if not rel or porcentaje_adicional("materiales", rel, False):
                linea(c["i"], c, "materiales", mat, pct, "; ".join(reglas), codigo="39305",
                      descripcion=f"{c['descripcion']}{sufijo}")
        if "perfusionista" in o:
            if g >= 20:
                linea(c["i"], c, "perfusionista", valor(d, "39129", uvb), 100,
                      "perfusionista, grupos especiales 20-23 (art. 48 b)", codigo="39129",
                      descripcion=f"Perfusionista — {c['descripcion']}")
            else:
                avisos.append(f"{c['codigo']}: el perfusionista solo se paga en los grupos especiales 20 a 23 (art. 48 b)")
        cat = float(c.get("catalogo") or 0)
        if cat and c["rep"] == 0:
            if g >= 20:
                linea(c["i"], c, "catalogo", cat, 100,
                      "materiales de sutura y curación y elementos de anestesia a precio de catálogo, grupos 20-23"
                      + ("; y drogas, medicamentos y soluciones del acto (cardiovascular, grupos 22-23)" if g >= 22 else "")
                      + " (art. 55 par. 1)", codigo="catalogo", descripcion=f"Precio de catálogo — {c['descripcion']}",
                      exacto=True)
            else:
                avisos.append(f"{c['codigo']} (grupo {g:02d}): el precio de catálogo del art. 55 par. 1 es para los grupos "
                              "20-23; los demás tienen materiales por grupo: se ignora")
        rec = (c.get("recuperacion") or "").strip()
        if rec and c["rep"] == 0:
            tipo_r, _, arg = rec.partition(":")
            if recup_hecha:
                avisos.append(f"{c['codigo']}: la recuperación se cobra una vez por acto (art. 51); se ignora")
            elif tipo_r == "media" and arg in CAMAS_47:
                linea(c["i"], c, "recuperacion", valor(d, arg, uvb), 50, f"recuperación de más de 6 horas: 50 % de la "
                      f"estancia {arg} = {formula(d, arg, uvb)} (art. 51)", codigo=arg,
                      descripcion=f"Recuperación — {d['procs'][arg]['descripcion']}")
                recup_hecha = True
            elif tipo_r == "ambulatoria" and arg in AMBULATORIA_51:
                cod_a = AMBULATORIA_51[arg]
                linea(c["i"], c, "recuperacion", valor(d, cod_a, uvb), 100, f"cirugía ambulatoria, más de 6 horas: "
                      f"estancia habitación de tres camas nivel {arg} {cod_a} = {formula(d, cod_a, uvb)} (art. 51)",
                      codigo=cod_a, descripcion=f"Recuperación ambulatoria — nivel {arg}")
                recup_hecha = True
            elif tipo_r == "uci":
                if g >= 20:
                    linea(c["i"], c, "recuperacion", valor(d, UCI_51, uvb), 50, "grupos especiales, recuperación en UCI "
                          f"menos de 24 h: 50 % de la estancia {UCI_51} = {formula(d, UCI_51, uvb)} (art. 51)",
                          codigo=UCI_51, descripcion="Recuperación en cuidado intensivo")
                    recup_hecha = True
                    avisos.append("Recuperación en UCI (art. 51): el 50 % es adicional a la estancia hospitalaria")
                else:
                    avisos.append(f"{c['codigo']} (grupo {g:02d}): la recuperación en UCI del art. 51 es para los grupos "
                                  "especiales 20-23; se ignora")
            else:
                errores.append(f"{c['codigo']}: recuperación no válida («{rec}»: media:CAMA, ambulatoria:1|2|3 o uci)")
    if any("bilateral" in c["opciones"] for c in validas):
        avisos.append("Bilateral (art. 70 par. 1): solo en ojo, oído, glándula salival, maxilar, malar, seno paranasal, "
                      "plexo nervioso, mama, suprarrenal, riñón, uréter, testículo, epidídimo, ovario y trompa (excepto "
                      "ligadura), en los dos miembros superiores o inferiores y en la herniorrafia inguinal, femoral o "
                      "crural: verifique que corresponda")
    for c in validas:
        if c["codigo"] in MATERIALES_EN_SALA and c["rep"] == 0:
            avisos.append(f"{c['codigo']}: los materiales, medicamentos, oxígeno y gases están incluidos en los derechos "
                          "de sala (art. 55 par. 3" + (", art. 50: sala de parto 39220)" if c["codigo"] in PARTO else ")"))
    if mayor is None:
        return None
    if len(validas) > 1:
        avisos.append(f"Cirugía mayor del acto: {mayor['codigo']} (grupo {mayor['grupo']:02d}); "
                      "las demás se liquidan como adicionales según su relación con ella")
    return mayor["i"]


# (relación, concepto) -> artículo que la sustenta
ARTICULO_REL = {
    ("igual_via", "cirujano"): "art. 71", ("igual_via", "anestesiologo"): "art. 71", ("igual_via", "ayudante"): "art. 71",
    ("diferente_via", "cirujano"): "art. 72", ("diferente_via", "anestesiologo"): "art. 72",
    ("diferente_via", "ayudante"): "art. 72", ("diferente_via", "sala"): "art. 49 par. 1",
    ("diferente_via", "materiales"): "art. 55 par. 4",
    ("otra_especialidad", "cirujano"): "art. 73", ("otra_especialidad", "anestesiologo"): "art. 73 par. 1",
    ("otra_especialidad", "ayudante"): "art. 73 par. 2", ("otra_especialidad", "sala"): "art. 49 par. 1",
}


def porcentaje_adicional(concepto, rel, ayudante_de_la_mayor_adicional):
    if rel == "igual_via":
        return 50 if concepto in PROFESIONALES else 0
    if rel == "diferente_via":
        return {"cirujano": 75, "anestesiologo": 75, "ayudante": 75, "sala": 50, "materiales": 75}[concepto]
    if rel == "otra_especialidad":
        if concepto == "ayudante":
            return 50 if ayudante_de_la_mayor_adicional else 0
        return {"cirujano": 100, "anestesiologo": 75, "sala": 50, "materiales": 0}[concepto]
    return 100


def liquidar_conjuntos(conjuntos, d, uvb, linea, avisos, hay_cirugias):
    vals = [(c, valor(d, c["codigo"], uvb)) for c in conjuntos]
    mayor = max(vals, key=lambda x: (x[1], -x[0]["i"]))[0]
    for c, v in vals:
        pct, regla = 100.0, f"conjunto integral {formula(d, c['codigo'], uvb)} (art. 64)"
        if "bilateral" in c["opciones"]:
            pct *= 1.75
            regla += "; bilateral +75 % (art. 64 par. 3)"
        if c is not mayor:
            rel = c.get("relacion") or "igual_via"
            p = 25 if rel == "igual_via" else 70
            pct *= p / 100
            regla += f"; otro conjunto del mismo acto, {RELACION_TXT[rel]}: {p} % (art. 64 par. 4 b)"
        for n in range(c["cantidad"]):
            linea(c["i"], c, "tarifa", v, round(pct, 4), regla)
    if hay_cirugias:
        avisos.append("Conjunto y cirugías en el mismo acto: el conjunto es la intervención mayor (100 %) y cada "
                      "cirugía se paga como adicional según su relación con él: igual vía, diferente vía u otra "
                      "especialidad (art. 64 par. 4 a)")
    return mayor["i"]


# ------------------------------------------------------------------------------------- consola
def main():
    ap = argparse.ArgumentParser(description="Cotizador del Manual Tarifario SOAT 2026 (UVB)")
    ap.add_argument("items", nargs="+", help="CODIGO, CODIGOxCANTIDAD, CODIGO:opcion[:opcion] "
                    f"(cirugía: {', '.join(OPCIONES_CIRUGIA + RELACIONES)}; con valor: {', '.join(OPCIONES_VALOR)})")
    ap.add_argument("--unidad", default="uvb", choices=list(UNIDADES), help="unidad de liquidación (por defecto uvb)")
    ap.add_argument("--valor", type=float, help="pesos por unidad (por defecto el del PDF: UVB 12.110, "
                    "UVT 52.374, SMLDV 58.363)")
    ap.add_argument("--region", default="", help=f"departamento del art. 86: {', '.join(REGIONES_86)}")
    ap.add_argument("--exceptuado", action="store_true", help="municipio exceptuado del art. 86")
    ap.add_argument("--contrato", type=float, default=0.0, help="ajuste del contrato en %% (ej. 4 o -5; por defecto 0)")
    ap.add_argument("--catalogo", nargs="+", metavar="COD:VALOR", default=[],
                    help="cirugía de los grupos 20-23: materiales y elementos a precio de catálogo (art. 55 par. 1)")
    ap.add_argument("--recuperacion", nargs="+", metavar="COD:TIPO", default=[],
                    help="art. 51: COD:media-CAMA (50 %% de la estancia, ej. 1101:media-38123), "
                         "COD:ambulatoria-NIVEL (1, 2 o 3) o COD:uci (grupos 20-23)")
    ap.add_argument("--suministro", nargs="+", metavar="TIPO:PRECIO[xCANT]:DESC", default=[],
                    help=f"a precio de catálogo; TIPO: {' | '.join(TIPOS_CATALOGO)} (arts. 56, 57, 59, 64 par. 2)")
    a = ap.parse_args()
    d = cargar()
    items, errores = leer_items(a.items)
    if errores:
        sys.exit("\n".join(errores))
    for x in a.catalogo:
        cod, _, v = x.partition(":")
        for it in items:
            if it["codigo"] == cod:
                it["catalogo"] = float(v)
    for x in a.recuperacion:
        cod, _, v = x.partition(":")
        for it in items:
            if it["codigo"] == cod:
                it["recuperacion"] = v.replace("-", ":", 1)
    sumi = []
    for x in a.suministro:
        tipo, _, resto = x.partition(":")
        precio, _, desc = resto.partition(":")
        precio, _, cant = precio.lower().partition("x")
        sumi.append(dict(tipo=tipo, precio=precio, cantidad=cant or 1, descripcion=desc))
    r = cotizar(items, d, a.valor, a.region, a.exceptuado, a.unidad, a.contrato, sumi)
    for e in r["errores"]:
        print("ERROR:", e)
    print(f"{r['unidad_nombre']} {pesos(r['valor_unidad'])}" + (f" · región {r['region']} (art. 86)" if r["region"] else ""))
    for ln in r["lineas"]:
        print(f"  {ln['codigo']:>6}  {ln['concepto']:<14} {pesos(ln['base']):>13} x {ln['porcentaje']:>7g} % "
              f"= {pesos(ln['valor']):>13}   {ln['descripcion'][:50]}  [{ln['regla']}]")
    if r["contrato_pct"]:
        print(f"Según el PDF {pesos(r['total_manual'])} · contrato {r['contrato_pct']:+g} % "
              f"{'+' if r['ajuste_contrato'] >= 0 else ''}{pesos(r['ajuste_contrato'])}")
    print(f"TOTAL {pesos(r['total'])}")
    for av in r["avisos"]:
        print("AVISO:", av)
    sys.exit(1 if r["errores"] else 0)


if __name__ == "__main__":
    main()
