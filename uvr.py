"""Cirugías del Manual ISS 2001 en UVR (Capítulo I, arts. 1-18): valores posibles de una línea.

Una cirugía en UVR no tiene un valor único: la línea de la factura puede traer la cirugía completa
(honorarios + derechos de sala + materiales), una adicional del mismo acto, una bilateral, la
practicada en otra sala, o un solo componente. Este módulo calcula esos escenarios con la norma:

- Honorarios (art. 59, tabla de parámetros): cirujano UVR x $1.270 (S41101); anestesiólogo UVR x $960
  (S41201), solo con anestesia general o regional (art. 61); ayudante UVR x $360 (S41301), solo en
  cirugías de 50 UVR o más (art. 63) y a $960 por UVR con 450 UVR o más si es de la misma especialidad
  o en el 815101 (art. 63 par.).
- Derechos de sala: quirófano por rango de UVR (art. 77, S23101-S23315) y UVR x $1.410 por encima de
  450 UVR (par. 1); sala de procedimientos especial (art. 79, S22201-S22214), sala de endoscopia
  (art. 80, S22224-S22237) y sala básica (art. 81, S22104-S22115).
- Materiales de sutura y curación (art. 85): quirófano por rango hasta 170 UVR (S55101-S55113); más de
  170 UVR o en cirugías múltiples, según consumo (par. 1): el valor de la hoja de gasto si se digita; sala especial o endoscopia $24.270 (S55114, par. 2);
  sala básica $10.350 (S55115, par. 3).
- Bilateral (art. 64, art. 77 par. 5, art. 85 par. 5): honorarios, sala de cirugía y materiales +75 %,
  salvo las descritas como «uni o bilateral».
- Múltiples: mismo especialista e igual vía (art. 65): adicionales al 60 % de honorarios y 50 % de sala
  (art. 77 par. 6), salvo las excepciones del art. 65 (468601, 591100, 652901, 667601, 669901 y
  endoscópicos no artroscópicos, también laparoscopia y toracoscopia), que no tienen porcentaje
  adicional; en artroscopias el 60 % solo con grupos de complejidad distintos (anexo C40464-C40467); diferente vía (art. 66): 75 %;
  distinta especialidad (art. 67): cirujano 60 %, anestesiólogo 75 % (par. 1), ayudante 50 % (par. 2).
- Región del art. 134 literal a: +30 % en honorarios y derechos de sala del Capítulo I (no materiales).
- Descuento de la sala de cirugía cuando la EPS aporta la instrumentación (20 %), la enfermería (25 %)
  o ambas (45 %) (art. 77 par. 4, PDF pág. 156).
- Sala de recuperación después de las primeras 6 horas (art. 84): S24101-S24103 según la complejidad.
- Distinta especialidad (art. 67 y nota del art. 77): sala 100 % de la mayor de cada especialista y
  50 % de sus adicionales. Las adicionales por diferente vía del mismo especialista solo tienen sala
  (50 %, hasta 3) en politrauma (nota del art. 77).
"""
import re
import unicodedata

EXCEPCION_65 = {"468601", "591100", "652901", "667601", "669901"}
DESCUENTO_SALA = {"instrumentacion": 0.20, "enfermeria": 0.25, "ambos": 0.45}  # art. 77 par. 4
RECUPERACION = {"baja": "S24101", "mediana": "S24102", "alta": "S24103"}  # art. 84
# art. 84 par., inciso 2 (pág. 159): recuperación en cuidado intensivo o intermedio por menos de 24 horas:
# 50 % de la estancia de esa unidad (art. 56), adicional a la estancia hospitalaria
RECUP_UCI = {"uci-adulto": "S12103", "uci-pediatrica": "S12102", "uci-neonatal": "S12101",
             "intermedio-adulto": "S12203", "intermedio-pediatrico": "S12202", "intermedio-neonatal": "S12201"}
# art. 77 par. 7 (pág. 156): accesorios del quirófano que sí se pagan aparte, por cada procedimiento
# efectuado: clave -> (valor, nombre, patrón de la descripción de la cirugía). El balón de contrapulsación
# también se exceptúa, pero sin valor fijo: va como suministro (art. 88).
ACCESORIOS_77 = {
    "cuchilla": (41395.0, "Cuchilla para el artroscopio (procedimiento terapéutico)", r"ARTROSC"),
    "trocar": (303995.0, "Trocar desechable de primera punción (cirugía laparoscópica)", r"LAPAROSC"),
    "asa": (40000.0, "Asa o electrodo para cauterización y corte (cirugía urológica endoscópica)",
            r"TRANSURETRAL|CISTOSC|URETEROSC|URETROSC|RESECTOSC|NEFROSC|PIELOSC"
            r"|ENDOSC.*(VEJIG|PROSTAT|URETER|URETR|RENAL|RINON|PIELO)|(VEJIG|PROSTAT|URETER|URETR|RENAL|RINON|PIELO).*ENDOSC"),
}
# art. 80 par. 2 (págs. 157-158): en la sala de endoscopia, adicional a los derechos de sala, por paciente
ACCESORIOS_80 = {
    "papilotomo": (121075.0, "Papilótomo, esfinterótomo, catéter de dilatación y canastilla (extracción de cálculos)",
                   r"CALCUL"),
    "litotripsia": (200075.0, "Litotripsia mecánica biliar", r"BILIAR"),
}
ACCESORIOS = {**ACCESORIOS_77, **ACCESORIOS_80}


def accesorios_posibles(descripcion, sala="quirofano"):
    """Accesorios que corresponden a la cirugía según su descripción y la sala: en quirófano los del
    art. 77 par. 7 (la cuchilla solo en artroscopias terapéuticas); en la sala de endoscopia los del
    art. 80 par. 2 (extracción endoscópica de cálculos; la litotripsia, en la vía biliar)."""
    d = unicodedata.normalize("NFKD", descripcion or "").encode("ascii", "ignore").decode().upper()
    if sala == "endoscopia":
        if not (re.search(r"CALCUL", d) and RE_ENDOSCOPICO.search(d)):
            return []
        return [k for k, (_, _, pat) in ACCESORIOS_80.items() if re.search(pat, d)]
    if sala != "quirofano":
        return []
    return [k for k, (_, _, pat) in ACCESORIOS_77.items()
            if re.search(pat, d) and not (k == "cuchilla" and "DIAGNOST" in d)]
SALAS = {  # artículo -> (agrupador en la base, nombre)
    77: ("SALA DE CIRUGIA", "quirófano"), 79: ("SALA DE PROCEDIMIENTOS ESPECIAL", "sala de procedimientos especial"),
    80: ("SALA DE ENDOSCOPIA", "sala de endoscopia"), 81: ("SALA DE PROCEDIMIENTOS BASICA", "sala básica"),
}
RE_RANGO = re.compile(r"(?:DE\s+(\d+)\s+)?HASTA\s+(\d+)\s+UVR", re.I)


def tablas(con):
    """Parámetros y tablas por rango de UVR desde salida/manual_iss.db."""
    par = dict(con.execute("SELECT codigo_uvr, pesos_por_uvr FROM parametros"))
    rangos = {}
    for art, codigo, desc, valor, agr in con.execute(
            "SELECT articulo, codigo, descripcion, valor, agrupador FROM v_tarifas "
            "WHERE articulo IN (77, 79, 80, 81, 85) AND tipo = 'con_valor' ORDER BY id"):
        m = RE_RANGO.search(desc or "")
        if not m:
            continue
        clave = "materiales" if art == 85 else art
        rangos.setdefault(clave, []).append((int(m[1] or 0), int(m[2]), float(valor), codigo))
    fijos = dict(con.execute("SELECT codigo, valor FROM v_tarifas WHERE codigo IN ('S55114', 'S55115', 'S55116') "
                             "AND tipo = 'con_valor'"))
    rec = dict(con.execute("SELECT codigo, valor FROM v_tarifas WHERE codigo IN ('S24101', 'S24102', 'S24103') "
                           "AND tipo = 'con_valor'"))
    uci = {cod: (float(v), desc) for cod, v, desc in con.execute(
        f"SELECT codigo, valor, descripcion FROM v_tarifas WHERE codigo IN ({','.join('?' * len(RECUP_UCI))}) "
        "AND tipo = 'con_valor'", list(RECUP_UCI.values()))}
    # art. 65: grupos de complejidad de las artroscopias, del anexo de los conjuntos C40464-C40467
    grupo_artro = dict(con.execute(
        "SELECT componente_codigo, paquete_codigo FROM v_paquete_componentes "
        "WHERE paquete_codigo IN ('C40464', 'C40465', 'C40466', 'C40467')"))
    return dict(recup_uci={k: uci[c] for k, c in RECUP_UCI.items() if c in uci}, grupo_artro=grupo_artro, cirujano=par["S41101"], anestesiologo=par["S41201"], ayudante=par["S41301"],
                recuperacion={k: rec.get(c) for k, c in RECUPERACION.items() if rec.get(c)},
                ayudante_especialista=par["S41201"], sala_mayor_450=1410.0, rangos=rangos,
                mat_especial=fijos.get("S55114", 24270.0), mat_basica=fijos.get("S55115", 10350.0))


RE_ENDOSCOPICO = re.compile(r"\b[A-Z]*(?<!MENI)SCOPI(?:A|CA|CO)S?\b")
GRUPO_ARTRO_NOMBRE = {"C40464": "I", "C40465": "II", "C40466": "III", "C40467": "IV"}


def via_endoscopica(codigo, descripcion, tb):
    """Art. 65: None (no es por vía endoscópica) | "artroscopico" (artroscopias y las del anexo de los
    conjuntos C40464-C40467) | "endoscopico" (los demás por vía endoscópica, también laparoscopia y
    toracoscopia: el art. 65 solo exceptúa los artroscópicos)."""
    d = unicodedata.normalize("NFKD", descripcion or "").encode("ascii", "ignore").decode().upper()
    if codigo in tb.get("grupo_artro", {}) or "ARTROSC" in d:
        return "artroscopico"
    return "endoscopico" if RE_ENDOSCOPICO.search(d) else None


def por_rango(uvr, filas):
    """(valor, código) del rango de UVR; None si las UVR superan la tabla."""
    for desde, hasta, valor, codigo in filas:
        if uvr <= hasta and uvr >= desde - 1:
            return valor, codigo
    return None


def escenarios(codigo, uvr, descripcion, tb, factor=1.0, region=False, factor_texto="", descuento_sala=None):
    """[(nombre, valor, detalle)] de una cirugía en UVR. factor: contrato (ej. 1.3 = ISS + 30 %);
    region: art. 134 literal a (+30 % en honorarios y sala); descuento_sala: lo que aporta la EPS
    (instrumentacion | enfermeria | ambos, art. 77 par. 4). Devuelve también los avisos."""
    avisos = []
    reg = 1.3 if region else 1.0
    dto = 1 - DESCUENTO_SALA.get(descuento_sala or "", 0.0)
    if dto != 1:
        avisos.append(f"Derechos de sala de cirugía con descuento del {100 - dto * 100:g}%: la EPS aporta "
                      f"{descuento_sala.replace('ambos', 'instrumentación y enfermería')} (art. 77 par. 4)")
    cir = uvr * tb["cirujano"] * reg
    anes = uvr * tb["anestesiologo"] * reg
    ayu = uvr * tb["ayudante"] * reg if uvr >= 50 else 0.0
    ayu_esp = uvr * tb["ayudante_especialista"] * reg if uvr >= 450 or codigo == "815101" else 0.0
    if uvr > 450:
        sala_q, cod_sq = uvr * tb["sala_mayor_450"] * reg * dto, "art. 77 par. 1 (UVR x $1.410)"
    else:
        sq = por_rango(uvr, tb["rangos"].get(77, []))
        sala_q, cod_sq = (sq[0] * reg * dto, sq[1]) if sq else (None, "")
    mq = por_rango(uvr, tb["rangos"].get("materiales", [])) if uvr <= 170 else None
    mat_q = mq[0] if mq else None
    if uvr > 170:
        avisos.append("Más de 170 UVR: los materiales de sutura y curación se pagan según consumo "
                      "(art. 85 par. 1); no se incluyen en los escenarios")
    otras = {}
    for art in (79, 80, 81):
        s = por_rango(uvr, tb["rangos"].get(art, []))
        if s:
            otras[art] = (s[0] * reg, s[1])
    sin_tildes = unicodedata.normalize("NFKD", descripcion or "").encode("ascii", "ignore").decode().upper()
    uni_bi = re.search(r"UNI\s*(?:O|/|Y/O)?\s*BILATERAL", sin_tildes)  # «UNI Ó BILATERAL» (art. 64)
    tipo_via = via_endoscopica(codigo, descripcion, tb)
    # art. 65: sin porcentaje adicional en los 5 códigos y en los endoscópicos (no artroscópicos)
    excepcion = codigo in EXCEPCION_65 or tipo_via == "endoscopico"
    p = lambda v: f"${v:,.0f}".replace(",", ".")  # noqa: E731
    det = lambda pares: " + ".join(f"{n} {p(v)}" for n, v in pares if v)  # noqa: E731
    mat = mat_q or 0.0
    esc = []
    hon = cir + anes + ayu
    if sala_q is not None:
        esc.append(("Cirugía completa en quirófano", hon + sala_q + mat,
                    det([("cirujano", cir), ("anestesiólogo", anes), ("ayudante", ayu), (f"sala {cod_sq}", sala_q),
                         ("materiales", mat)])))
        if ayu:
            esc.append(("Cirugía completa sin ayudante", cir + anes + sala_q + mat,
                        det([("cirujano", cir), ("anestesiólogo", anes), ("sala", sala_q), ("materiales", mat)])))
        for nivel, v_rec in tb.get("recuperacion", {}).items():
            esc.append((f"Cirugía completa + recuperación de complejidad {nivel} (art. 84)", hon + sala_q + mat + v_rec,
                        det([("honorarios", hon), ("sala", sala_q), ("materiales", mat),
                             (f"recuperación {RECUPERACION[nivel]} (más de 6 horas)", v_rec)])))
        esc.append(("Mayor de otro especialista en el mismo acto (art. 67, nota del art. 77)",
                    cir + 0.75 * anes + 0.5 * ayu + sala_q,
                    "cirujano 100% (su mayor), anestesiólogo 75% (par. 1), ayudante 50% (par. 2), sala 100%"))
        if mat:
            esc.append(("Mayor de otro especialista con materiales (art. 67, 85 par. 5)",
                        cir + 0.75 * anes + 0.5 * ayu + sala_q + mat,
                        "cirujano 100%, anestesiólogo 75%, ayudante 50%, sala y materiales 100%"))
        esc.append(("Adicional de un especialista de otra especialidad (art. 67, nota del art. 77)",
                    0.6 * cir + 0.75 * anes + 0.5 * ayu + 0.5 * sala_q,
                    "cirujano 60%, anestesiólogo 75%, ayudante 50%, sala 50%"))
        if mat:
            esc.append(("Adicional de otra especialidad con materiales (art. 67, 85 par. 5)",
                        0.6 * cir + 0.75 * anes + 0.5 * ayu + 0.5 * sala_q + 0.5 * mat,
                        "cirujano 60%, anestesiólogo 75%, ayudante 50%, sala y materiales 50%"))
        # politrauma, diferente vía: sala y materiales 50 % hasta la tercera adicional (art. 77 par. 6, 85 par. 5)
        esc.append(("Adicional, diferente vía, politrauma (art. 66, 77 par. 6, 85 par. 5)",
                    0.75 * hon + 0.5 * sala_q + 0.5 * mat,
                    "75% de honorarios + 50% de sala" + (" + 50% de materiales" if mat else "")))
        if ayu_esp:
            esc.append(("Cirugía completa con ayudante especialista (art. 63 par.)", cir + anes + ayu_esp + sala_q + mat,
                        det([("cirujano", cir), ("anestesiólogo", anes), ("ayudante especialista", ayu_esp),
                             ("sala", sala_q), ("materiales", mat)])))
        if not uni_bi:
            esc.append(("Bilateral (art. 64, 77 par. 5, 85 par. 5)", 1.75 * (hon + sala_q + mat),
                        "honorarios, sala y materiales +75%"))
        if not excepcion:
            esc.append(("Adicional, mismo especialista e igual vía (art. 65, 77 par. 6)", 0.6 * hon + 0.5 * sala_q,
                        "60% de honorarios + 50% de sala"))
            if mat:
                esc.append(("Adicional, igual vía, con materiales (art. 65, 77 par. 6, 85 par. 5)",
                            0.6 * hon + 0.5 * sala_q + 0.5 * mat, "60% de honorarios + 50% de sala y materiales"))
    if not excepcion:
        esc.append(("Adicional, igual vía, solo honorarios (art. 65)", 0.6 * hon, "60% de honorarios"))
    esc.append(("Adicional, diferente vía, honorarios (art. 66)", 0.75 * hon, "75% de honorarios"))
    esc.append(("Adicional de otra especialidad, solo honorarios (art. 67)", 0.6 * cir + 0.75 * anes + 0.5 * ayu,
                "cirujano 60%, anestesiólogo 75%, ayudante 50%"))
    for art, (valor, cod) in otras.items():
        nombre = SALAS[art][1]
        if art == 81:
            v, d = cir + valor + tb["mat_basica"], det([("cirujano", cir), (f"sala {cod}", valor),
                                                        ("materiales S55115", tb["mat_basica"])])
        elif art == 80:
            v, d = cir + valor + tb["mat_especial"], det([("cirujano", cir), (f"sala {cod}", valor),
                                                          ("materiales S55114", tb["mat_especial"])])
        else:
            v, d = cir + anes + valor + tb["mat_especial"], det([("cirujano", cir), ("anestesiólogo", anes),
                                                                 (f"sala {cod}", valor), ("materiales S55114", tb["mat_especial"])])
        esc.append((f"En {nombre} (art. {art})", v, d))
    esc.append(("Honorarios (cirujano + anestesiólogo + ayudante)", hon, det([("cirujano", cir), ("anestesiólogo", anes), ("ayudante", ayu)])))
    for nombre, v in (("Solo cirujano", cir), ("Solo anestesiólogo", anes), ("Solo ayudante", ayu),
                      ("Solo derechos de sala de cirugía", sala_q), ("Solo materiales", mat_q)):
        if v:
            esc.append((nombre, v, f"{nombre.lower()} {p(v)}"))
    if excepcion:
        avisos.append(f"{codigo}: excepción del art. 65" + (" (por vía endoscópica)" if tipo_via == "endoscopico" else "")
                      + ": sin porcentaje adicional cuando es parte de cirugías múltiples por igual vía")
    if tipo_via == "artroscopico":
        g = tb.get("grupo_artro", {}).get(codigo)
        avisos.append(f"{codigo}: artroscopia" + (f" del grupo de complejidad {GRUPO_ARTRO_NOMBRE[g]} ({g})" if g else
                                                  ", no está en el anexo de los conjuntos C40464-C40467")
                      + ": como adicional por igual vía solo se paga el 60 % si la mayor es de otro grupo (art. 65)")
    if region:
        avisos.append("Art. 134 literal a: +30% en honorarios y derechos de sala (Capítulo I)")
    texto = f"ISS 2001, {uvr:g} UVR"
    return [(nombre, v * factor, f"{texto}: {d}{factor_texto}") for nombre, v, d in esc if v], avisos


# ---------------------------------------------------------------- cotizador: liquidar un acto
SALA_ART = {"quirofano": 77, "especial": 79, "endoscopia": 80, "basica": 81}


def liquidar_acto(items, tb, via=None, region=False, descuento_sala=None, politrauma=False):
    """Liquida las cirugías en UVR de un acto con lo que declara quien cotiza.

    items: [dict(codigo, uvr, descripcion, cantidad, sala, anestesia, ayudante, bilateral)]
      sala: quirofano (por defecto) | especial | endoscopia | basica; anestesia: general o regional
      (False = local, sin honorario de anestesiólogo, art. 61 par. 1); ayudante: si hubo (solo desde
      50 UVR, art. 63); ayudante_especialista: el ayudante es de igual especialidad que el cirujano
      principal (art. 63 par.: $960 por UVR con 450 UVR o más, o en el 815101; implica ayudante); bilateral: art. 64 (no en las «uni o bilateral»); recuperacion: baja | mediana | alta (art. 84) o una clave de RECUP_UCI (art. 84 par.), baja | mediana
      | alta si permaneció en recuperación más de 6 horas (art. 84); materiales_consumo: valor en
      pesos de la hoja de gasto, cuando los materiales se pagan según consumo (art. 85 par. 1: más de
      170 UVR o cirugías múltiples en quirófano); va una vez por código, sin recargos.
    descuento_sala: instrumentacion | enfermeria | ambos si la EPS los aporta (art. 77 par. 4).
    via: None (cirugías en actos distintos: cada una completa) | "igual" (art. 65) | "diferente" (art. 66)
      | "distinta" (especialistas de distinta especialidad, art. 67: cada ítem trae «especialista»).
    politrauma: abdominal, torácico, craneofacial o fracturas múltiples. Igual vía: desde la tercera
      cirugía también se paga (60 % honorarios, art. 65 par.; 50 % sala y materiales, arts. 77 par. 6 y
      85 par. 5); diferente vía: sala y materiales al 50 % en las tres primeras adicionales.
    accesorios (por ítem): claves de ACCESORIOS_77 (art. 77 par. 7), valor fijo por cada procedimiento
      en quirófano, sin recargos ni porcentajes de múltiples; o de ACCESORIOS_80 (art. 80 par. 2), en la
      sala de endoscopia, una vez por paciente.
    Devuelve ({codigo: dict(total, componentes=[(concepto, monto, cita)])}, avisos)."""
    reg = 1.3 if region else 1.0
    avisos = []
    dto = 1 - DESCUENTO_SALA.get(descuento_sala or "", 0.0)
    txt_dto = f" -{100 - dto * 100:g}% (art. 77 par. 4)" if dto != 1 else ""
    unidades = sorted(((it, k) for it in items for k in range(int(it.get("cantidad") or 1))),
                      key=lambda x: -x[0]["uvr"])
    multiple = via in ("igual", "diferente", "distinta") and len(unidades) > 1
    # art. 85 par. 1: materiales según consumo en la de más de 170 UVR y en las múltiples en las que
    # alguna pasa de 170 UVR; si todas tienen 170 o menos, van por tabla (par. 5: 100 % + 50 %)
    max_q = max((float(it["uvr"]) for it, _ in unidades if (it.get("sala") or "quirofano") == "quirofano"),
                default=0.0)
    mayor_cod = unidades[0][0]["codigo"] if unidades else None
    vistos_esp = {}  # art. 67: cirugías ya liquidadas de cada especialista
    if via == "distinta" and multiple and len({str(it.get("especialista") or "1") for it in items}) < 2:
        avisos.append("Distinta especialidad (art. 67): todas las cirugías quedaron con el mismo especialista; "
                      "indique el especialista de cada una o use igual o diferente vía (arts. 65-66)")
    res = {}
    sala_otra_pagada = set()
    acc_avisado = set()  # códigos con aviso de accesorio fuera del quirófano
    mat_consumo = set()  # códigos con la hoja de gasto ya sumada (una vez por código)
    hay_hoja = any(it.get("materiales_consumo") for it in items)
    for n, (it, _) in enumerate(unidades):
        cod, u = it["codigo"], float(it["uvr"])
        sala = it.get("sala") or "quirofano"
        comp = res.setdefault(cod, dict(total=0.0, componentes=[]))["componentes"]
        sin_tildes = unicodedata.normalize("NFKD", it.get("descripcion") or "").encode("ascii", "ignore").decode().upper()
        bil = bool(it.get("bilateral")) and not re.search(r"UNI\s*(?:O|/|Y/O)?\s*BILATERAL", sin_tildes)
        if it.get("bilateral") and not bil:
            avisos.append(f"{cod}: descrita como «uni o bilateral»: sin recargo bilateral (art. 64)")

        def poner(texto, valor, cita, quien, cita_bil):
            """Componente al 100 % y, si es bilateral, su 75 % adicional en línea aparte, como lo dice
            la norma (art. 64 honorarios, art. 77 par. 5 sala, art. 85 par. 5 materiales)."""
            comp.append((texto, valor, cita))
            if bil:
                comp.append((f"Adicional bilateral 75 % de {quien}", valor * 0.75, cita_bil))
        # porcentaje de honorarios y de sala de quirófano según el orden en el acto
        especialista = str(it.get("especialista") or "1")
        k_esp = vistos_esp.get(especialista, 0)
        vistos_esp[especialista] = k_esp + 1
        f_hon, f_sala, nota = 1.0, 1.0, ""
        f_anes = f_ayu = None  # None = igual que el cirujano
        if multiple and via == "distinta":
            # art. 67: cada especialista 100 % de su mayor y 60 % de sus demás; anestesiólogo 100 % de la
            # mayor del acto y 75 % de las demás (par. 1); ayudante 100 % + 50 % (par. 2); sala y materiales
            # 100 % de la mayor de cada especialista y 50 % de sus demás (art. 77 par. 6; art. 85 par. 5)
            f_hon = 1.0 if k_esp == 0 else 0.6
            f_sala = 1.0 if k_esp == 0 else 0.5
            f_anes = 1.0 if n == 0 else 0.75
            f_ayu = 1.0 if n == 0 else 0.5
            nota = (f" (especialista {especialista}: " + ("su mayor, 100 %" if k_esp == 0 else "adicional, 60 %")
                    + ", art. 67)")
        elif multiple and n > 0:
            tipo_via = via_endoscopica(cod, it.get("descripcion"), tb) if via == "igual" else None
            g_mayor = tb.get("grupo_artro", {}).get(mayor_cod)
            g_esta = tb.get("grupo_artro", {}).get(cod)
            if it["codigo"] in EXCEPCION_65 and via == "igual":
                f_hon, f_sala, nota = 0.0, 0.0, " (excepción del art. 65: sin porcentaje adicional)"
            elif tipo_via == "endoscopico":
                if re.search(r"LAPAROSC|TORACOSC", sin_tildes) and "lap" not in acc_avisado:
                    acc_avisado.add("lap")
                    avisos.append("Laparoscopia o toracoscopia adicional por igual vía: se tomó como «vía endoscópica» "
                                  "sin porcentaje adicional (art. 65: la excepción solo deja por fuera las "
                                  "artroscópicas). Revíselo con el contrato")
                f_hon, f_sala, nota = 0.0, 0.0, (" (por vía endoscópica, igual vía: sin porcentaje adicional, art. 65; "
                                                 "sin sala, art. 77 par. 6)")
            elif (tipo_via == "artroscopico" and via_endoscopica(mayor_cod, unidades[0][0].get("descripcion"), tb)
                  == "artroscopico" and not (g_mayor and g_esta and g_mayor != g_esta)):
                f_hon, f_sala, nota = 0.0, 0.0, (
                    " (artroscopia: el 60 % solo con grupos de complejidad diferentes, art. 65; "
                    + (f"las dos en el grupo {GRUPO_ARTRO_NOMBRE[g_esta]} ({g_esta})" if g_mayor and g_esta
                       else "no está en el anexo de los conjuntos C40464-C40467") + ")")
            elif via == "igual" and n >= 2 and not politrauma:
                f_hon, f_sala, nota = 0.0, 0.0, " (art. 65 par.: sin pagos adicionales desde la tercera, salvo politrauma)"
            elif via == "igual":
                f_hon, f_sala, nota = 0.6, 0.5, (" (adicional, igual vía: 60% honorarios, art. 65"
                                                 + (" par., politrauma" if n >= 2 else "") + "; 50% sala, art. 77 par. 6)")
            elif politrauma and n <= 3:
                f_hon, f_sala, nota = 0.75, 0.5, (" (adicional, diferente vía: 75% honorarios, art. 66; politrauma: 50% "
                                                  "sala y materiales hasta la tercera adicional, arts. 77 par. 6 y 85 par. 5)")
            else:
                f_hon, f_sala, nota = 0.75, 0.0, (" (adicional, diferente vía: 75% honorarios, art. 66; sin derechos "
                                                  "de sala" + (": politrauma solo hasta la tercera adicional, art. 77 par. 6)"
                                                               if politrauma else ": solo en politrauma, art. 77 par. 6)"))
        f_anes = f_hon if f_anes is None else f_anes
        f_ayu = f_hon if f_ayu is None else f_ayu
        f_mat = f_sala  # art. 85 par. 5: los mismos porcentajes que la sala en las múltiples
        art_pct = {"igual": "art. 65", "diferente": "art. 66"}.get(via, "")
        t_anes = (f" ({f_anes * 100:g} %, " + ("art. 67 par. 1" if via == "distinta" else art_pct) + ")"
                  if 0 < f_anes < 1 else "")
        t_ayu = (f" ({f_ayu * 100:g} %, " + ("art. 67 par. 2" if via == "distinta" else art_pct) + ")"
                 if 0 < f_ayu < 1 else "")
        cita_h = "art. 59" + (", art. 134 a" if region else "")
        poner(f"Cirujano {u:g} UVR x {tb['cirujano']:g}{nota}", u * tb["cirujano"] * reg * f_hon, cita_h,
              "cirujano", "art. 64")
        if it.get("anestesia", True):
            poner(f"Anestesiólogo {u:g} UVR x {tb['anestesiologo']:g}{t_anes}", u * tb["anestesiologo"] * reg * f_anes,
                  cita_h + ", art. 61", "anestesiólogo", "art. 64")
        if it.get("ayudante") or it.get("ayudante_especialista"):
            esp = bool(it.get("ayudante_especialista"))
            if esp and not (u >= 450 or cod == "815101"):
                avisos.append(f"{cod}: ayudante de igual especialidad, pero la cirugía tiene menos de 450 UVR: "
                              f"se paga a ${tb['ayudante']:g} por UVR (art. 63 par.)")
                esp = False
            if esp:
                poner(f"Ayudante de igual especialidad {u:g} UVR x {tb['ayudante_especialista']:g}{t_ayu}",
                      u * tb["ayudante_especialista"] * reg * f_ayu, cita_h + ", art. 63 par.", "ayudante", "art. 64")
            elif u >= 50:
                poner(f"Ayudante {u:g} UVR x {tb['ayudante']:g}{t_ayu}", u * tb["ayudante"] * reg * f_ayu,
                      cita_h + ", art. 63", "ayudante", "art. 64")
            else:
                avisos.append(f"{cod}: ayudante declarado, pero la cirugía tiene menos de 50 UVR: no se paga (art. 63)")
        art = SALA_ART.get(sala, 77)
        if art == 77:
            if u > 450:
                v_sala, txt = u * tb["sala_mayor_450"], f"Derechos de sala {u:g} UVR x $1.410"
            else:
                s = por_rango(u, tb["rangos"].get(77, []))
                v_sala, txt = (s[0], f"Derechos de sala {s[1]}") if s else (None, "")
            if v_sala is None:
                avisos.append(f"{cod}: sin tarifa de derechos de sala para {u:g} UVR")
            elif f_sala:
                poner(txt + (" al 50 %" if f_sala == 0.5 else "") + txt_dto, v_sala * reg * f_sala * dto,
                      "art. 77" + (" par. 6" if f_sala == 0.5 else "") + (" par. 4" if dto != 1 else ""),
                      "derechos de sala", "art. 77 par. 5")
            for k in it.get("accesorios") or []:
                if k in ACCESORIOS_80:
                    avisos.append(f"{cod}: {ACCESORIOS_80[k][1].lower()}: se paga en la sala de endoscopia "
                                  "(art. 80 par. 2), no en quirófano: no se suma")
                    continue
                if k not in ACCESORIOS_77:
                    avisos.append(f"{cod}: accesorio no válido ({' | '.join(ACCESORIOS)})")
                    continue
                valor, nombre, _ = ACCESORIOS_77[k]
                if k == "cuchilla" and "DIAGNOST" in sin_tildes:
                    avisos.append(f"{cod}: la cuchilla del artroscopio se paga solo en procedimientos terapéuticos, "
                                  "no en los diagnósticos (art. 77 par. 7): no se suma")
                    continue
                if k not in accesorios_posibles(it.get("descripcion")):
                    avisos.append(f"{cod}: {nombre.lower()}: la descripción de la cirugía no lo menciona; "
                                  "revise que corresponda (art. 77 par. 7)")
                comp.append((nombre, valor, "art. 77 par. 7"))
            if it.get("recuperacion") in RECUP_UCI:
                v_est, desc_est = tb.get("recup_uci", {}).get(it["recuperacion"], (None, ""))
                if v_est and "recuperacion" not in sala_otra_pagada:
                    comp.append((f"Recuperación en {desc_est.lower()} menos de 24 h: 50 % de la estancia "
                                 f"{RECUP_UCI[it['recuperacion']]}", v_est * 0.5, "art. 84 par."))
                    sala_otra_pagada.add("recuperacion")  # una sola vez por acto
                    if "uci-estancia" not in acc_avisado:
                        acc_avisado.add("uci-estancia")
                        avisos.append("Recuperación en cuidado intensivo o intermedio (art. 84 par.): el 50 % es adicional "
                                      "a la estancia hospitalaria según la cama que ocupe el paciente; agregue esa estancia")
            elif it.get("recuperacion"):
                v_rec = tb.get("recuperacion", {}).get(it["recuperacion"])
                if v_rec and not sala_otra_pagada & {"recuperacion"}:
                    comp.append((f"Recuperación más de 6 horas, complejidad {it['recuperacion']} "
                                 f"{RECUPERACION[it['recuperacion']]}", v_rec, "art. 84"))
                    sala_otra_pagada.add("recuperacion")  # una sola vez por acto
                elif not v_rec:
                    avisos.append(f"{cod}: complejidad de recuperación no válida ({' | '.join(RECUPERACION)})")
            hoja = float(it.get("materiales_consumo") or 0)
            if u > 170 or (multiple and max_q > 170):
                if hoja and cod not in mat_consumo:
                    comp.append(("Materiales según hoja de gasto", hoja, "art. 85 par. 1"))
                    mat_consumo.add(cod)
                elif multiple and n == 0 and not hay_hoja:
                    avisos.append("Cirugías múltiples con alguna de más de 170 UVR: los materiales de sutura y "
                                  "curación de todas se pagan según consumo (art. 85 par. 1); no se suman: digite "
                                  "el valor de la hoja de gasto")
                elif not multiple and not hoja:
                    avisos.append(f"{cod}: más de 170 UVR: materiales según consumo (art. 85 par. 1); no se suman: "
                                  "digite el valor de la hoja de gasto")
            else:
                if hoja and cod not in mat_consumo:
                    avisos.append(f"{cod}: hasta 170 UVR los materiales tienen tarifa fija (art. 85): no se usa la "
                                  "hoja de gasto")
                    mat_consumo.add(cod)
                m = por_rango(u, tb["rangos"].get("materiales", []))
                if m and f_mat:
                    poner(f"Materiales {m[1]}" + (" al 50 %" if f_mat == 0.5 else ""), m[0] * f_mat,
                          "art. 85" + (" par. 5" if f_mat == 0.5 else ""), "materiales", "art. 85 par. 5")
        else:
            # salas 79-81: una sola tarifa por acto (la del procedimiento de más UVR), sin recargo bilateral
            if art == 80 and it.get("anestesia", True) and ("art80-anest", cod) not in acc_avisado:
                acc_avisado.add(("art80-anest", cod))
                avisos.append(f"{cod}: la sala de endoscopia (art. 80) es para los procedimientos que no requieren "
                              "anestesia general o regional; sin ellas no se paga anestesiólogo (art. 61): marque "
                              "«Anestesia local». Si hubo anestesia general o regional, la sala es quirófano (art. 77)")
            for k in it.get("accesorios") or []:
                if art == 80 and k in ACCESORIOS_80:
                    valor, nombre, _ = ACCESORIOS_80[k]
                    if ("art80", k) in acc_avisado:  # «en cada paciente»: una vez por acto
                        continue
                    acc_avisado.add(("art80", k))
                    if k not in accesorios_posibles(it.get("descripcion"), "endoscopia"):
                        avisos.append(f"{cod}: {nombre.lower()}: la descripción no es de extracción endoscópica de "
                                      "cálculos" + (" biliares" if k == "litotripsia" else "")
                                      + "; revise que corresponda (art. 80 par. 2)")
                    comp.append((nombre, valor, "art. 80 par. 2"))
                elif cod not in acc_avisado:
                    acc_avisado.add(cod)
                    avisos.append(f"{cod}: " + (
                        f"los accesorios del art. 77 par. 7 son del quirófano; en {SALAS[art][1]} no se pagan aparte"
                        + (" (art. 79 par. 2)" if art == 79 else "") if k in ACCESORIOS_77 else
                        f"{ACCESORIOS_80.get(k, ('', k))[1].lower()}: solo en la sala de endoscopia (art. 80 par. 2)"))
            if it.get("materiales_consumo") and cod not in mat_consumo:
                avisos.append(f"{cod}: en {SALAS[art][1]} los materiales tienen tarifa fija (art. 85 par. "
                              f"{3 if art == 81 else 2}): no se usa la hoja de gasto")
                mat_consumo.add(cod)
            if art in sala_otra_pagada:
                comp.append((f"Derechos de {SALAS[art][1]}: incluidos en el de más UVR", 0.0, f"art. {art} par. 1"))
            else:
                s = por_rango(u, tb["rangos"].get(art, []))
                if s:
                    comp.append((f"Derechos de {SALAS[art][1]} {s[1]}", s[0] * reg, f"art. {art}"))
                    mat = tb["mat_basica"] if art == 81 else tb["mat_especial"]
                    comp.append((f"Materiales {'S55115' if art == 81 else 'S55114'}", mat,
                                 f"art. 85 par. {3 if art == 81 else 2}"))
                else:
                    avisos.append(f"{cod}: {u:g} UVR supera la tabla de {SALAS[art][1]} (art. {art})")
                sala_otra_pagada.add(art)
    for v in res.values():
        v["total"] = sum(m for _, m, _ in v["componentes"])
    if region:
        avisos.append("Art. 134 literal a: +30% en honorarios y derechos de sala de las cirugías (Capítulo I)")
    return res, avisos
