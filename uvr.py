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
"""
import re
import unicodedata

EXCEPCION_65 = {"468601", "591100", "652901", "667601", "669901"}
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
    return dict(cirujano=par["S41101"], anestesiologo=par["S41201"], ayudante=par["S41301"],
                ayudante_especialista=par["S41201"], sala_mayor_450=1410.0, rangos=rangos,
                mat_especial=fijos.get("S55114", 24270.0), mat_basica=fijos.get("S55115", 10350.0))


def por_rango(uvr, filas):
    """(valor, código) del rango de UVR; None si las UVR superan la tabla."""
    for desde, hasta, valor, codigo in filas:
        if uvr <= hasta and uvr >= desde - 1:
            return valor, codigo
    return None


def escenarios(codigo, uvr, descripcion, tb, factor=1.0, region=False, factor_texto=""):
    """[(nombre, valor, detalle)] de una cirugía en UVR. factor: contrato (ej. 1.3 = ISS + 30 %);
    region: art. 134 literal a (+30 % en honorarios y sala). Devuelve también los avisos."""
    avisos = []
    reg = 1.3 if region else 1.0
    cir = uvr * tb["cirujano"] * reg
    anes = uvr * tb["anestesiologo"] * reg
    ayu = uvr * tb["ayudante"] * reg if uvr >= 50 else 0.0
    ayu_esp = uvr * tb["ayudante_especialista"] * reg if uvr >= 450 or codigo == "815101" else 0.0
    if uvr > 450:
        sala_q, cod_sq = uvr * tb["sala_mayor_450"] * reg, "art. 77 par. 1 (UVR x $1.410)"
    else:
        sq = por_rango(uvr, tb["rangos"].get(77, []))
        sala_q, cod_sq = (sq[0] * reg, sq[1]) if sq else (None, "")
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
    esc.append(("Adicional de otra especialidad (art. 67)", 0.6 * cir + 0.75 * anes + 0.5 * ayu,
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
