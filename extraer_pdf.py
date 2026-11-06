"""Extracción del PDF oficial (Acuerdo 256 de 2001) por celdas de tabla (bordes).

Genera:
  pdf_tablas.csv  -> una fila por procedimiento: pagina, orden_en_pagina, ref, pb, codigo,
                     descripcion_completa, nota_ref, valor_txt, valor (+ top, alertas)
  pdf_textos.csv  -> texto fuera de las tablas (agrupadores, notas, artículos, parágrafos)
                     pagina, orden_en_pagina, tipo, texto (+ top, x0, x1)

Cómo está armado el PDF (ver pág. 37):
  - tabla de 1 columna con la REF interna (x ≈ 84-130)
  - la marca PB va suelta, sin borde, entre las dos tablas (x ≈ 142-152)
  - tabla principal con celdas CODIGO | DESCRIPCION | VALOR (x ≈ 152-580)
Se toma como ancla cada fila de la tabla principal; REF y PB se leen como palabras dentro
de la franja vertical de esa fila. orden_en_pagina es común a los dos CSV (orden vertical).
"""
import re

import pandas as pd
import pdfplumber

PDF = "MANUAL-ISS-2001.pdf"
SAL_TABLAS = "pdf_tablas.csv"
SAL_TEXTOS = "pdf_textos.csv"

RE_COD = re.compile(r"^[A-Z]?\d{5,6}$")
RE_COD_PEGADO = re.compile(r"^([A-Z]?\d{6})(?=[A-ZÁÉÍÓÚÑ(])")
RE_NOTA = re.compile(r"(\s*\(\d{1,4}\))+\s*$")  # una o varias: "SOD (191) (202)"
RE_ENCABEZADO = re.compile(
    r"^(ACUERDO No\. ?256 DE 2\.001|\(\s*19 de Diciembre\s*\)|POR EL CUAL SE APRUEBA EL"
    r"|SOCIAL “EPS-ISS”\.?$|-{10,})")
CABECERAS = {"CODIGO", "CÓDIGO", "REF.", "REF"}


def espacios(s):
    return re.sub(r"\s+", " ", s or "").strip()


def parse_valor(t):
    """'1.270' -> 1270 ; '117.708.665' -> 117708665 ; '0,58' / '0.58' -> 0.58."""
    t = (t or "").replace(" ", "")
    if not t:
        return None
    if re.fullmatch(r"0[.,]\d+", t) or re.fullmatch(r"\d+,\d+", t):
        return float(t.replace(",", "."))
    if re.fullmatch(r"\d{1,3}(\.\d{3})*", t):
        return float(t.replace(".", ""))
    return None


def en_franja(w, top, bottom):
    c = (w["top"] + w["bottom"]) / 2
    return top <= c <= bottom


def bordes_faltantes(p, tol=3):
    """Cuando una tabla sigue de la página anterior, la primera fila no trae borde superior
    (y a veces la última no trae borde inferior): pdfplumber no la reconoce como celda.
    Para cada línea vertical cuyo extremo no toca ninguna horizontal, se agrega una
    horizontal en ese extremo copiando el ancho de la horizontal del extremo opuesto."""
    hs = [e for e in p.edges if e["orientation"] == "h" and e["x1"] - e["x0"] > 4 * tol]
    vs = [e for e in p.edges if e["orientation"] == "v" and e["height"] > tol]
    extra = []

    def toca(y, x, lista):
        return [h for h in lista if abs(h["top"] - y) <= tol and h["x0"] - tol <= x <= h["x1"] + tol]

    for v in vs:
        for y, otro in ((v["top"], v["bottom"]), (v["bottom"], v["top"])):
            if toca(y, v["x0"], hs) or toca(y, v["x0"], extra):
                continue
            base = toca(otro, v["x0"], hs)
            if base:
                h = max(base, key=lambda e: e["x1"] - e["x0"])
                extra.append(dict(x0=h["x0"], x1=h["x1"], top=y, bottom=y, width=h["x1"] - h["x0"],
                                  height=0, y0=p.height - y, y1=p.height - y,
                                  doctop=h["doctop"] - h["top"] + y,
                                  orientation="h", object_type="explicit_edge"))
    return extra


def verticales_faltantes(p, hs, palabras, tol=3):
    """Algunas filas no traen todas sus verticales (pág. 11: faltan x≈128 y x≈152; pág. 76:
    faltan 152 y 190; pág. 101: la fila no tiene ninguna). Entre cada par de horizontales
    consecutivas, si la franja contiene un código (x 150-200) o una REF (x < 128) -es decir,
    es una fila de procedimiento y no el hueco entre dos tablas-, se agregan las verticales
    que falten en las posiciones de columna habituales de la página."""
    vs = [e for e in p.edges if e["orientation"] == "v" and e["height"] > tol]
    hs = [h for h in hs if h["x1"] - h["x0"] > 4 * tol]
    tops = sorted({round(h["top"], 1) for h in hs})
    grupos = []  # bordes dobles (746.0 / 746.8) cuentan como una sola línea
    for y in tops:
        if grupos and y - grupos[-1][1] <= 1.5:
            grupos[-1][1] = y
        else:
            grupos.append([y, y])
    extra = []
    for (_, ya), (yb, _) in zip(grupos, grupos[1:]):
        if yb - ya < 5:
            continue
        fila = [w for w in palabras if en_franja(w, ya, yb)]
        es_fila = any(150 <= w["x0"] < 200 and RE_COD.match(w["text"]) for w in fila) and \
            any(86 <= w["x0"] and w["x1"] <= 130 and re.fullmatch(r"[A-Z]?\d{4,7}", w["text"])
                for w in fila)
        if not es_fila:
            continue
        # columnas = extremos de los segmentos horizontales que cierran la fila arriba y abajo
        bordes = [h for h in hs if ya - 2 <= h["top"] <= ya + 0.1 or yb - 0.1 <= h["top"] <= yb + 2]
        columnas = sorted({round(h[k]) for h in bordes for k in ("x0", "x1")})
        unicas = [x for i, x in enumerate(columnas) if i == 0 or x - columnas[i - 1] > tol]
        for x in unicas:
            if any(abs(v["x0"] - x) <= tol and v["top"] <= ya + tol and v["bottom"] >= yb - tol
                   for v in vs):
                continue
            extra.append(dict(x0=x, x1=x, top=ya, bottom=yb, width=0, height=yb - ya,
                              y0=p.height - yb, y1=p.height - ya, doctop=ya,
                              orientation="v", object_type="explicit_edge"))
    return extra


def procesar_pagina(p):
    eh = bordes_faltantes(p)
    hs = [e for e in p.edges if e["orientation"] == "h"] + eh
    palabras = p.extract_words()
    ev = verticales_faltantes(p, hs, palabras)
    tablas = p.find_tables({"explicit_horizontal_lines": eh, "explicit_vertical_lines": ev})
    filas, filas_texto = [], []
    principales = [t for t in tablas if t.bbox[2] - t.bbox[0] > 200]
    # se excluye el texto de las filas (no el rectángulo completo de la tabla: hay notas
    # entre dos filas que quedan dentro del contorno, p. ej. "EXCLUYE: ..." en pág. 125)
    zonas_excluidas = [r.bbox for t in tablas for r in t.rows] + [c for t in tablas
                                                                   for c in t.cells]
    for t in principales:
        x0, top, _, bottom = t.bbox
        # zona a la izquierda de la tabla principal (REF y PB sin borde)
        # (y a la derecha: algunos valores se salen del borde, p. ej. 56.910 en pág. 119)
        for r in t.rows:
            # toda la franja de la fila, de margen a margen (incluye celdas fusionadas),
            # salvo en "filas" que solo tienen la celda de valor: junto a ellas puede ir una
            # nota sin borde ("EXCLUYE: el electrocardiograma", pág. 125)
            if any(c is not None for c in r.cells[:-1]):
                zonas_excluidas.append((0, r.bbox[1], p.width, r.bbox[3]))
        textos = t.extract()
        # límites de columna de la tabla: posición x de cada columna
        ncol = max(len(r.cells) for r in t.rows)
        col_x = [None] * ncol
        for r in t.rows:
            for j, c in enumerate(r.cells):
                if c is not None and col_x[j] is None:
                    col_x[j] = (c[0], c[2])
        anchos = [(b - a) if a is not None else 0 for a, b in (cx or (None, None) for cx in col_x)]
        jdesc = max(range(ncol), key=lambda j: anchos[j])
        for r, txt in zip(t.rows, textos):
            rt, rb = r.bbox[1], r.bbox[3]
            celda = lambda j: txt[j] if j < len(txt) else None  # noqa: E731
            cod = espacios(celda(0)) if jdesc > 0 else ""
            desc_raw = celda(jdesc)
            desc = espacios(desc_raw)
            if jdesc < len(r.cells) and r.cells[jdesc] is None and col_x[jdesc]:
                # celda fusionada con la de arriba (pág. 48: sin línea bajo la cabecera):
                # se lee el texto de la columna dentro de la franja de la fila
                dx0, dx1 = col_x[jdesc]
                desc = espacios(p.within_bbox((dx0 - 1, rt - 1, dx1 + 1, rb + 1)).extract_text())
            # valor: palabras a la derecha de la columna de descripción, dentro de la franja
            # de la fila y sin límite derecho (el texto a veces se sale del borde de la celda).
            # Si el valor ocupa dos líneas (117.708.66 / 5) se pegan sin espacio.
            valor_txt = ""
            if jdesc + 1 < ncol and col_x[jdesc]:
                xd = col_x[jdesc][1]
                ws = sorted((w for w in palabras if w["x0"] >= xd - 1 and en_franja(w, rt, rb)),
                            key=lambda w: (round(w["top"]), w["x0"]))
                valor_txt = "".join(w["text"] for w in ws)
            if cod.upper() in CABECERAS or desc.upper().startswith("DESCRIPCION"):
                continue
            al = []
            # palabras sin borde a la izquierda de la tabla, en la franja de la fila
            izq = [w for w in palabras if w["x1"] <= x0 + 1 and en_franja(w, rt, rb)]
            pb = "PB" if any(w["text"] == "PB" and w["x0"] > 135 for w in izq) else ""
            refs = [w["text"] for w in izq if w["x1"] < 140 and w["text"] not in CABECERAS]
            ref = " ".join(refs)
            if len(refs) > 1:
                al.append("varias_ref")
            if not cod:  # código fuera del borde (pág. 129) o pegado a la descripción
                fuera = [w["text"] for w in izq if w["x0"] >= 150 and w["text"] != "PB"]
                if fuera:
                    cod = " ".join(fuera)
                    al.append("codigo_sin_borde")
                else:
                    m = RE_COD_PEGADO.match(desc)
                    if m:
                        cod, desc = m.group(1), desc[m.end():].strip()
                        al.append("codigo_pegado")
            valor = parse_valor(valor_txt)
            if valor_txt and valor is None:
                al.append("valor_no_numerico")
            if r.cells[jdesc] is None if jdesc < len(r.cells) else False:
                al.append("descripcion_fusionada")
            if jdesc > 0 and not (ref or pb or cod) and desc and not filas and \
                    tipo_texto(desc, 0, 0) == "texto":
                # primera fila de la página sin REF, PB ni código: es la continuación de una
                # fila partida entre páginas (pág. 175 -> 176); main() la une a la anterior
                filas.append(dict(pagina=p.page_number, top=round(rt, 1), ref="", pb="",
                                  codigo="", descripcion_completa=desc, valor_txt=valor_txt,
                                  valor=valor, alertas="continuacion"))
                continue
            if not ref and not RE_COD.match(cod):
                # fila de texto dentro de una tabla (notas INCLUYE/APLICA en pág. 179,
                # tablas de porcentajes o patologías en págs. 144 y 151)
                t_txt = espacios(" ".join(espacios(c) for c in txt if c))
                if not t_txt:
                    continue
                filas_texto.append(dict(pagina=p.page_number, top=round(rt, 1),
                                        x0=round(x0), x1=round(t.bbox[2]), en_tabla=True,
                                        negrita=False, tamano=None,
                                        tipo=tipo_texto(t_txt, 0, 0), texto=t_txt))
                continue
            if cod and not RE_COD.match(cod):
                al.append("codigo_raro")
            filas.append(dict(pagina=p.page_number, top=round(rt, 1), ref=ref, pb=pb,
                              codigo=cod, descripcion_completa=desc,
                              valor_txt=valor_txt, valor=valor, alertas=";".join(al)))
    return filas, filas_texto, zonas_excluidas


def dentro(obj, zonas):
    cx, cy = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
    return any(a <= cx <= c and b <= cy <= d for a, b, c, d in zonas)


def tipo_texto(t, x0, x1, negrita=False, tamano=None):
    # Los títulos reales van en mayúsculas ("ARTICULO 75."); una línea de prosa partida
    # puede empezar con "Artículo 75 de este Manual..." y no es un artículo nuevo.
    if re.match(r"^ARTICULO\s*\d+", t):
        return "articulo"
    if re.match(r"^CAP[IÍ]TULO\b", t):
        return "capitulo"
    if re.match(r"^PAR[AÁ]GRAFO", t):
        return "paragrafo"
    if re.match(r"^\**\s*(SOD|NCOC)\s*:", t):  # leyenda de abreviaturas al pie de tabla
        return "leyenda"
    if re.match(r"^(NO APLICA|APLICA|INCLUYE|NO INCLUYE|NOTA|TARIFA)\s*:", t) or \
            re.match(r"^(Incluye|Aplica|Tarifa)\b", t):
        return "nota"
    # Agrupadores: títulos dentro del área de la tabla (x0 >= 140; la prosa empieza en
    # x≈84), en mayúsculas o en negrita ("Cirugía Programada", pág. 173). No siempre van
    # centrados ("MENINGE Y CRANEOPLASTIA", pág. 2; "MENORES DE 1 AÑO", pág. 162).
    # x0 > 365: segunda línea de una cabecera de columna ("FRACCIÓN", pág. 167).
    letras = [c for c in t if c.isalpha()]
    mayus = sum(c.isupper() for c in letras) / len(letras) if letras else 0
    # tamaño >= 9.5: subtítulos en minúscula y sin negrita ("Bogotá", pág. 168; la tabla
    # usa 8.2). Ancho < 360: una línea a todo el ancho es un párrafo, aunque esté en negrita.
    if 140 <= x0 <= 365 and x1 - x0 < 360 and len(letras) >= 3 and \
            (mayus >= 0.8 or negrita or (tamano or 0) >= 9.5):  # 0.8: "10 Mv" (pág. 132)
        return "agrupador"
    return "texto"


def textos_pagina(p, zonas):
    fuera = p.filter(lambda o: o.get("object_type") != "char" or not dentro(o, zonas))
    salida = []
    for ln in fuera.extract_text_lines(layout=False, strip=True, return_chars=True):
        t = espacios(ln["text"])
        if not t or RE_ENCABEZADO.match(t):
            continue
        cs = [c for c in ln["chars"] if c["text"].strip()]
        negrita = sum("Bold" in c["fontname"] for c in cs) > len(cs) / 2
        tamano = round(sorted(c["size"] for c in cs)[len(cs) // 2], 1)
        salida.append(dict(pagina=p.page_number, top=round(ln["top"], 1), x0=round(ln["x0"]),
                           x1=round(ln["x1"]), en_tabla=False, negrita=negrita, tamano=tamano,
                           tipo=tipo_texto(t, ln["x0"], ln["x1"], negrita, tamano), texto=t))
    return salida


def main():
    tablas, textos, bloque = [], [], 0
    with pdfplumber.open(PDF) as pdf:
        for p in pdf.pages:
            filas, filas_texto, zonas = procesar_pagina(p)
            txt = textos_pagina(p, zonas) + filas_texto
            # orden común a tablas y textos dentro de la página
            todo = [("t", f) for f in filas] + [("x", x) for x in txt]
            todo.sort(key=lambda kv: kv[1]["top"])
            previo = None  # última línea de texto, si no hubo una fila de tabla en medio
            for k, (clase, d) in enumerate(todo, 1):
                d["orden_en_pagina"] = k
                if clase == "t":
                    previo = None
                    continue
                # bloque: líneas seguidas del mismo párrafo/nota/agrupador (salto <= 14 pt)
                # texto: continúa un párrafo/nota (nunca un agrupador);
                # agrupador: continúa otro agrupador con la misma fuente y alineación
                sigue = False
                if previo is not None and not d["en_tabla"] and not previo["en_tabla"]:
                    salto = d["top"] - previo["top"]
                    cen = abs((d["x0"] + d["x1"]) - (previo["x0"] + previo["x1"])) / 2
                    letras = [c for c in d["texto"] if c.isalpha()]
                    mayus = sum(c.isupper() for c in letras) / max(len(letras), 1)
                    if previo["tipo"] == "agrupador" and d["tipo"] in ("texto", "agrupador") \
                            and salto <= 12 and mayus >= 0.8 \
                            and d["negrita"] == previo["negrita"] \
                            and d["tamano"] == previo["tamano"] \
                            and abs((d["x0"] + d["x1"]) / 2 - 350) < 40 \
                            and abs((previo["x0"] + previo["x1"]) / 2 - 350) < 40:
                        # título centrado de varias líneas; la del medio puede ser más ancha
                        # que 360 pt y quedar como texto ("ESTUDIO DE ESPECIMENES SIMPLES
                        # ... / ... / ETC.", pág. 109)
                        sigue = True
                    elif d["tipo"] == "agrupador" and previo["tipo"] == "texto" \
                            and previo.get("inicio") and salto <= 12 \
                            and d["negrita"] == previo["negrita"] \
                            and d["tamano"] == previo["tamano"] \
                            and abs((d["x0"] + d["x1"]) / 2 - 350) < 40 \
                            and abs((previo["x0"] + previo["x1"]) / 2 - 350) < 40 \
                            and previo["texto"] == previo["texto"].upper():
                        # primera línea del título a todo el ancho, clasificada como texto
                        # ("ESTUDIO DE ESPECIMENES QUIRURGICOS (CON DISECCION ...", pág. 109)
                        previo["tipo"] = "agrupador"
                        sigue = True
                    elif d["tipo"] == "texto" and previo["tipo"] == "agrupador":
                        # aclaración entre paréntesis centrada bajo el título: "TRATAMIENTO
                        # EN QUEMADURAS" / "(Incluye quemadura por fricción)" (pág. 73)
                        sigue = (salto <= 14 and cen < 40
                                 and re.fullmatch(r"\(.*\)", d["texto"]) is not None)
                    elif d["tipo"] == "texto":
                        sigue = salto <= 14
                    elif d["tipo"] == previo["tipo"] == "agrupador":
                        sigue = (salto <= 12 and d["negrita"] == previo["negrita"]
                                 and d["tamano"] == previo["tamano"]
                                 and (cen < 40 or abs(d["x0"] - previo["x0"]) < 3))
                if sigue:
                    d["bloque"], d["tipo"] = previo["bloque"], previo["tipo"]
                else:
                    bloque += 1
                    d["bloque"], d["inicio"] = bloque, True
                previo = d
            for f in filas:
                if f["alertas"] == "continuacion":
                    if not tablas:
                        raise SystemExit(f"pág. {p.page_number}: continuación sin fila previa")
                    prev = tablas[-1]
                    prev["descripcion_completa"] += " " + f["descripcion_completa"]
                    if f["valor_txt"] and not prev["valor_txt"]:
                        prev["valor_txt"], prev["valor"] = f["valor_txt"], f["valor"]
                    prev["alertas"] = ";".join(x for x in (prev["alertas"], "sigue_en_pag_"
                                               + str(p.page_number)) if x)
                    continue
                tablas.append(f)
            textos += txt
    # notas al final de la descripción, ya con las filas partidas unidas: "SOD (191) (202)"
    for f in tablas:
        m = RE_NOTA.search(f["descripcion_completa"])
        f["nota_ref"] = ",".join(re.findall(r"\((\d+)\)", m.group(0))) if m else ""
        if m:
            f["descripcion_completa"] = f["descripcion_completa"][:m.start()].strip()
    ct = ["pagina", "orden_en_pagina", "ref", "pb", "codigo", "descripcion_completa",
          "nota_ref", "valor_txt", "valor", "top", "alertas"]
    tb = pd.DataFrame(tablas)[ct]
    tx = pd.DataFrame(textos)[["pagina", "orden_en_pagina", "bloque", "tipo", "texto", "en_tabla", "negrita", "tamano",
                                 "top", "x0", "x1"]]
    tb.to_csv(SAL_TABLAS, index=False, encoding="utf-8-sig")
    tx.to_csv(SAL_TEXTOS, index=False, encoding="utf-8-sig")
    print(f"{SAL_TABLAS}: {len(tb)} filas | con código: {(tb.codigo != '').sum()} "
          f"| con valor: {tb.valor.notna().sum()} | PB: {(tb.pb == 'PB').sum()}")
    al = tb.alertas.str.split(";").explode()
    print("alertas:", al[al != ""].value_counts().to_dict())
    print(f"{SAL_TEXTOS}: {len(tx)} líneas | por tipo: {tx.tipo.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
