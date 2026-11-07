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
  170 UVR, según consumo (par. 1, sin valor fijo); sala especial o endoscopia $24.270 (S55114, par. 2);
  sala básica $10.350 (S55115, par. 3).
- Bilateral (art. 64, art. 77 par. 5, art. 85 par. 5): honorarios, sala de cirugía y materiales +75 %,
  salvo las descritas como «uni o bilateral».
- Múltiples: mismo especialista e igual vía (art. 65): adicionales al 60 % de honorarios y 50 % de sala
  (art. 77 par. 6), salvo las excepciones del art. 65 (468601, 591100, 652901, 667601, 669901 y
  endoscópicos no artroscópicos), que no tienen porcentaje adicional; diferente vía (art. 66): 75 %;
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
    return dict(cirujano=par["S41101"], anestesiologo=par["S41201"], ayudante=par["S41301"],
                recuperacion={k: rec.get(c) for k, c in RECUPERACION.items() if rec.get(c)},
                ayudante_especialista=par["S41201"], sala_mayor_450=1410.0, rangos=rangos,
                mat_especial=fijos.get("S55114", 24270.0), mat_basica=fijos.get("S55115", 10350.0))


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
    excepcion = codigo in EXCEPCION_65
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
        esc.append(("Adicional de un especialista de otra especialidad (art. 67, nota del art. 77)",
                    0.6 * cir + 0.75 * anes + 0.5 * ayu + 0.5 * sala_q,
                    "cirujano 60%, anestesiólogo 75%, ayudante 50%, sala 50%"))
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
        avisos.append(f"{codigo}: excepción del art. 65, sin porcentaje adicional cuando es parte de "
                      "cirugías múltiples por igual vía")
    if region:
        avisos.append("Art. 134 literal a: +30% en honorarios y derechos de sala (Capítulo I)")
    texto = f"ISS 2001, {uvr:g} UVR"
    return [(nombre, v * factor, f"{texto}: {d}{factor_texto}") for nombre, v, d in esc if v], avisos


# ---------------------------------------------------------------- cotizador: liquidar un acto
SALA_ART = {"quirofano": 77, "especial": 79, "endoscopia": 80, "basica": 81}


def liquidar_acto(items, tb, via=None, region=False, descuento_sala=None):
    """Liquida las cirugías en UVR de un acto con lo que declara quien cotiza.

    items: [dict(codigo, uvr, descripcion, cantidad, sala, anestesia, ayudante, bilateral)]
      sala: quirofano (por defecto) | especial | endoscopia | basica; anestesia: general o regional
      (False = local, sin honorario de anestesiólogo, art. 61 par. 1); ayudante: si hubo (solo desde
      50 UVR, art. 63); bilateral: art. 64 (no en las «uni o bilateral»); recuperacion: baja | mediana
      | alta si permaneció en recuperación más de 6 horas (art. 84).
    descuento_sala: instrumentacion | enfermeria | ambos si la EPS los aporta (art. 77 par. 4).
    via: None (cirugías en actos distintos: cada una completa) | "igual" (art. 65) | "diferente" (art. 66).
    Devuelve ({codigo: dict(total, componentes=[(concepto, monto, cita)])}, avisos)."""
    reg = 1.3 if region else 1.0
    avisos = []
    dto = 1 - DESCUENTO_SALA.get(descuento_sala or "", 0.0)
    txt_dto = f" -{100 - dto * 100:g}% (art. 77 par. 4)" if dto != 1 else ""
    unidades = sorted(((it, k) for it in items for k in range(int(it.get("cantidad") or 1))),
                      key=lambda x: -x[0]["uvr"])
    multiple = via in ("igual", "diferente") and len(unidades) > 1
    res = {}
    sala_otra_pagada = set()
    for n, (it, _) in enumerate(unidades):
        cod, u = it["codigo"], float(it["uvr"])
        sala = it.get("sala") or "quirofano"
        comp = res.setdefault(cod, dict(total=0.0, componentes=[]))["componentes"]
        sin_tildes = unicodedata.normalize("NFKD", it.get("descripcion") or "").encode("ascii", "ignore").decode().upper()
        bil = bool(it.get("bilateral")) and not re.search(r"UNI\s*(?:O|/|Y/O)?\s*BILATERAL", sin_tildes)
        if it.get("bilateral") and not bil:
            avisos.append(f"{cod}: descrita como «uni o bilateral»: sin recargo bilateral (art. 64)")
        f_bil = 1.75 if bil else 1.0
        # porcentaje de honorarios y de sala de quirófano según el orden en el acto
        f_hon, f_sala, nota = 1.0, 1.0, ""
        if multiple and n > 0:
            if it["codigo"] in EXCEPCION_65 and via == "igual":
                f_hon, f_sala, nota = 0.0, 0.0, " (excepción del art. 65: sin porcentaje adicional)"
            elif via == "igual" and n >= 2:
                f_hon, f_sala, nota = 0.0, 0.0, " (art. 65 par.: sin pagos adicionales desde la tercera, salvo politrauma)"
            elif via == "igual":
                f_hon, f_sala, nota = 0.6, 0.5, " (adicional, igual vía: 60% honorarios, art. 65; 50% sala, art. 77 par. 6)"
            else:
                f_hon, f_sala, nota = 0.75, 0.0, (" (adicional, diferente vía: 75% honorarios, art. 66; sin derechos "
                                                  "de sala: solo en politrauma, nota del art. 77)")
        cita_h = "art. 59" + (", art. 64" if bil else "") + (", art. 134 a" if region else "")
        cir = u * tb["cirujano"] * reg * f_bil * f_hon
        comp.append((f"Cirujano {u:g} UVR x {tb['cirujano']:g}{nota}", cir, cita_h))
        if it.get("anestesia", True):
            comp.append((f"Anestesiólogo {u:g} UVR x {tb['anestesiologo']:g}", u * tb["anestesiologo"] * reg * f_bil * f_hon, cita_h + ", art. 61"))
        if it.get("ayudante"):
            if u >= 50:
                comp.append((f"Ayudante {u:g} UVR x {tb['ayudante']:g}", u * tb["ayudante"] * reg * f_bil * f_hon, cita_h + ", art. 63"))
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
                comp.append((txt + (" +75% bilateral" if bil else "") + txt_dto, v_sala * reg * f_bil * f_sala * dto,
                             "art. 77" + (" par. 5" if bil else "") + (" par. 6" if f_sala == 0.5 else "")
                             + (" par. 4" if dto != 1 else "")))
            if it.get("recuperacion"):
                v_rec = tb.get("recuperacion", {}).get(it["recuperacion"])
                if v_rec and not sala_otra_pagada & {"recuperacion"}:
                    comp.append((f"Recuperación más de 6 horas, complejidad {it['recuperacion']} "
                                 f"{RECUPERACION[it['recuperacion']]}", v_rec, "art. 84"))
                    sala_otra_pagada.add("recuperacion")  # una sola vez por acto
                elif not v_rec:
                    avisos.append(f"{cod}: complejidad de recuperación no válida ({' | '.join(RECUPERACION)})")
            if multiple:
                if n == 0:
                    avisos.append("Cirugías múltiples: los materiales de sutura y curación se pagan según consumo "
                                  "(art. 85 par. 1); no se suman")
            elif u > 170:
                avisos.append(f"{cod}: más de 170 UVR: materiales según consumo (art. 85 par. 1); no se suman")
            else:
                m = por_rango(u, tb["rangos"].get("materiales", []))
                if m:
                    comp.append((f"Materiales {m[1]}" + (" +75% bilateral" if bil else ""), m[0] * f_bil,
                                 "art. 85" + (" par. 5" if bil else "")))
        else:
            # salas 79-81: una sola tarifa por acto (la del procedimiento de más UVR), sin recargo bilateral
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
