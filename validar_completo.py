"""Validación completa BD (salida/manual_iss.db) contra el PDF oficial, campo por campo.

Fuentes del PDF (generadas por extraer_pdf.py):
  pdf_tablas.csv  -> procedimientos (ref, PB, código, descripción completa, nota_ref, valor)
  pdf_textos.csv  -> artículos, agrupadores, notas, parágrafos y demás texto fuera de tablas

Compara:
  procedimientos: descripcion, pb, nota_ref, valor, articulo, agrupador, padre (componentes)
  textos:         articulos.texto, agrupadores.nombre, notas.texto
Los textos se alinean palabra por palabra dentro de cada artículo (la BD guarda párrafos
de una celda del Excel; el PDF, líneas), y para cada ítem de la BD se reconstruye el
tramo del PDF que le corresponde.

Clasificación:
  MENOR -> solo cambian tildes, mayúsculas, puntuación o espacios
  MAYOR -> cambian palabras, números, marcas o la asignación (artículo, agrupador, padre)

Salida: validacion_completa.csv con tipo, campo, fila_excel, pagina_pdf, valor_bd, valor_pdf
(+ codigo, articulo, detalle).
"""
import difflib
import re
import sqlite3
import unicodedata

import pandas as pd

DB = "salida/manual_iss.db"
PDF_TABLAS = "pdf_tablas.csv"
PDF_TEXTOS = "pdf_textos.csv"
SALIDA = "validacion_completa.csv"
RE_NOTAS_FINAL = re.compile(r"(\s*\(\d{1,4}\))+\s*$")


# ---------------------------------------------------------------- utilidades
def espacios(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def fuerte(s):
    """Sin tildes, sin mayúsculas/minúsculas, sin puntuación ni espacios."""
    s = unicodedata.normalize("NFKD", espacios(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


def clasificar(bd, pdf):
    a, b = espacios(bd), espacios(pdf)
    if a == b:
        return None
    return "MENOR" if fuerte(a) == fuerte(b) else "MAYOR"


def ref5(r):
    r = espacios(r)
    if r.endswith(".0"):
        r = r[:-2]
    return r.zfill(5) if r.isdigit() else r


def notas_de(s):
    return ",".join(re.findall(r"\((\d+)\)", s or ""))


def fx(v):
    """Fila del Excel como entero, o None (notas agregadas por correcciones.csv)."""
    return None if v is None or pd.isna(v) else int(v)


def num(v):
    try:
        return None if v is None or pd.isna(v) or v == "" else float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- comparación
def cargar_pdf():
    pt = pd.read_csv(PDF_TABLAS, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    px = pd.read_csv(PDF_TEXTOS, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return pt, px


def comparar(pr, ag, ar, nt, pt, px):
    """Compara las tablas de la BD (procedimientos, agrupadores, articulos, notas) contra
    pdf_tablas / pdf_textos. Devuelve (diferencias, resumen). La usa también etl.py."""
    pr, ag, ar, nt, pt, px = (x.copy() for x in (pr, ag, ar, nt, pt, px))
    for d in (pt, px):
        d["pagina"] = d.pagina.astype(int)
        d["orden_en_pagina"] = d.orden_en_pagina.astype(int)

    # bloques de texto del PDF (líneas seguidas del mismo párrafo)
    px["bloque"] = px.bloque.astype(int)
    bloques = (px.sort_values(["pagina", "orden_en_pagina"])
                 .groupby("bloque", sort=False)
                 .agg(pagina=("pagina", "first"), orden_en_pagina=("orden_en_pagina", "first"),
                      tipo=("tipo", "first"), texto=("texto", lambda s: " ".join(s)))
                 .reset_index())

    # ---------------------------------------------------------------- recorrido del PDF
    # Orden de lectura: filas de tabla y bloques de texto intercalados por página y orden.
    ev = ([("proc", r.pagina, r.orden_en_pagina, i) for i, r in pt.iterrows()] +
          [("texto", r.pagina, r.orden_en_pagina, i) for i, r in bloques.iterrows()])
    ev.sort(key=lambda e: (e[1], e[2]))

    art, agr, ult_valor = None, None, None
    grupo, tras_fila = [], True  # títulos seguidos antes de una tabla (título + subtítulo)
    pt["art_pdf"], pt["agr_pdf"], pt["padre_pdf"], pt["grupo_pdf"] = None, None, None, None
    bloques["articulo"] = None
    for clase, _, _, i in ev:
        if clase == "texto":
            b = bloques.loc[i]
            if b.tipo == "articulo":
                n = int(re.match(r"ARTICULO\s*(\d+)", b.texto).group(1))
                if n == (art or 0) + 1:
                    art, agr, ult_valor, grupo = n, None, None, []
            elif b.tipo == "capitulo":
                agr, ult_valor, grupo = None, None, []
            elif b.tipo == "agrupador":
                if tras_fila:
                    grupo, tras_fila = [], False
                agr, ult_valor = b.texto, None
                grupo.append(b.texto)
            elif b.tipo == "paragrafo":
                ult_valor = None
            bloques.at[i, "articulo"] = art
            continue
        r = pt.loc[i]
        pt.at[i, "art_pdf"], pt.at[i, "agr_pdf"] = art, agr
        pt.at[i, "grupo_pdf"] = " / ".join(grupo)
        tras_fila = True
        if r.valor != "":
            ult_valor = i
        else:
            pt.at[i, "padre_pdf"] = ult_valor  # componente del último procedimiento con valor

    # ---------------------------------------------------------------- emparejar procedimientos
    pr["ref"] = pr.codigo_manual.map(ref5)
    pt["ref5"] = pt.ref.map(ref5)
    pr["k"] = pr.groupby(["ref", "codigo"]).cumcount()
    pt["k"] = pt.sort_values(["pagina", "orden_en_pagina"]).groupby(["ref5", "codigo"]).cumcount()
    pt["idx_pdf"] = pt.index
    m = pr.merge(pt.rename(columns={"ref5": "ref_k", "codigo": "codigo_pdf"}),
                 left_on=["ref", "codigo", "k"], right_on=["ref_k", "codigo_pdf", "k"],
                 how="outer", indicator=True, suffixes=("", "_pdf"))

    agr_nombre = dict(zip(ag.id, ag.nombre))
    id_a_pdf = dict(zip(m.id.dropna().astype(int), m.idx_pdf))
    pdf_cod = dict(zip(pt.index, pt.codigo))

    dif = []


    def add(tipo, campo, fila, pag, vbd, vpdf, codigo="", articulo=None, detalle=""):
        dif.append(dict(tipo=tipo, campo=campo, fila_excel=fila, pagina_pdf=pag,
                        valor_bd=vbd, valor_pdf=vpdf, codigo=codigo, articulo=articulo,
                        detalle=detalle))


    for _, r in m.iterrows():
        if r._merge == "left_only":
            add("MAYOR", "fila", r.fila_excel, None, r.codigo, "", r.codigo, r.articulo,
                "procedimiento de la BD sin pareja en el PDF")
            continue
        if r._merge == "right_only":
            add("MAYOR", "fila", None, r.pagina, "", r.codigo_pdf, r.codigo_pdf, r.art_pdf,
                "procedimiento del PDF sin pareja en la BD")
            continue
        f, pag, cod, a = int(r.fila_excel), int(r.pagina), r.codigo, int(r.articulo)

        # descripción y notas: la BD separa solo la última nota de 2-4 dígitos; si quedan
        # notas al final de la descripción, se comparan como nota_ref y no como descripción
        d_bd = espacios(r.descripcion)
        n_bd_extra = notas_de(RE_NOTAS_FINAL.search(d_bd).group(0)) if RE_NOTAS_FINAL.search(d_bd) else ""
        d_bd_core = RE_NOTAS_FINAL.sub("", d_bd).strip()
        t = clasificar(d_bd_core, r.descripcion_completa)
        if t:
            add(t, "descripcion", f, pag, d_bd_core, r.descripcion_completa, cod, a)
        nota_bd = ",".join(x for x in (n_bd_extra, espacios(r.ref_nota).removesuffix(".0")) if x)
        if nota_bd != r.nota_ref:
            add("MAYOR", "nota_ref", f, pag, nota_bd, r.nota_ref, cod, a,
                "la BD deja notas dentro de la descripción" if n_bd_extra else "")

        if (espacios(r.marca) == "PB") != (r.pb == "PB"):
            add("MAYOR", "pb", f, pag, espacios(r.marca), r.pb, cod, a)

        vb, vp = num(r.valor), num(r.valor_pdf)
        if (vb is None) != (vp is None) or (vb is not None and abs(vb - vp) > 0.001):
            add("MAYOR", "valor", f, pag, vb, vp, cod, a)

        if r.art_pdf is None or int(r.art_pdf) != a:
            add("MAYOR", "articulo", f, pag, a, r.art_pdf, cod, a)

        g_bd = agr_nombre.get(r.agrupador_id) if pd.notna(r.agrupador_id) else None
        if fuerte(g_bd) != fuerte(r.agr_pdf):
            niveles = (r.grupo_pdf or "").split(" / ")
            otro_nivel = bool(g_bd) and (fuerte(g_bd) in {fuerte(x) for x in niveles}
                                         or fuerte(g_bd) == fuerte(" ".join(niveles)))
            add("MAYOR", "agrupador", f, pag, g_bd or "", r.agr_pdf or "", cod, a,
                f"jerarquía: la BD usa otro nivel de los títulos del PDF [{r.grupo_pdf}]"
                if otro_nivel else f"títulos del PDF: [{r.grupo_pdf}]")

        p_bd = id_a_pdf.get(int(r.padre_id)) if pd.notna(r.padre_id) else None
        p_pdf = r.padre_pdf if r.padre_pdf is not None and not pd.isna(r.padre_pdf) else None
        if p_bd != p_pdf:
            add("MAYOR", "padre", f, pag, pdf_cod.get(p_bd, "") if p_bd is not None else "",
                pdf_cod.get(p_pdf, "") if p_pdf is not None else "", cod, a,
                f"tipo en BD: {r.tipo}")

    # ---------------------------------------------------------------- textos
    items = pd.concat([
        ar.assign(clase="articulo", articulo=ar.numero, texto=ar.texto)[["clase", "fila_excel", "articulo", "texto"]],
        ag.assign(clase="agrupador", texto=ag.nombre)[["clase", "fila_excel", "articulo", "texto"]],
        nt.assign(clase=nt.tipo)[["clase", "fila_excel", "articulo", "texto"]
                                 + (["despues_de_fila"] if "despues_de_fila" in nt else [])],
    ])
    # notas agregadas por correcciones.csv: sin fila del Excel, van después de su fila ancla
    ancla = items["despues_de_fila"] if "despues_de_fila" in items else pd.Series(pd.NA, index=items.index)
    items["orden"] = (pd.to_numeric(items.fila_excel, errors="coerce").astype(float)
                      .fillna(pd.to_numeric(ancla, errors="coerce").astype(float) + 0.5))
    items = items.sort_values("orden", kind="stable").reset_index(drop=True)
    items = items[items.articulo.notna()]
    items["articulo"] = items.articulo.astype(int)

    bl = bloques[bloques.articulo.notna()].copy()
    bl["articulo"] = bl.articulo.astype(int)


    def tokens(texto):
        return [(w, fuerte(w)) for w in espacios(texto).split(" ") if w]


    for a in sorted(set(items.articulo) | set(bl.articulo)):
        ib = items[items.articulo == a]
        bb = bl[bl.articulo == a]
        # tokens de la BD (con su ítem) y del PDF (con su bloque y página)
        tb, tp = [], []  # (norm, ítem)  /  (orig, norm, página, bloque)
        for k, (_, it) in enumerate(ib.iterrows()):
            tb += [(n, k) for _, n in tokens(it.texto) if n]
        for _, b in bb.iterrows():
            tp += [(o, n, b.pagina, b.bloque) for o, n in tokens(b.texto)]
        pos_p = [j for j, t in enumerate(tp) if t[1]]  # índices del PDF con contenido
        sm = difflib.SequenceMatcher(a=[t[0] for t in tb], b=[tp[j][1] for j in pos_p],
                                     autojunk=False)
        asignado = {}  # ítem -> lista de índices globales del PDF
        usados = set()
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op in ("equal", "replace"):
                for i in range(i1, i2):
                    if op == "equal":
                        j = j1 + (i - i1)
                    else:  # reparte el tramo del PDF proporcionalmente
                        j = j1 + (i - i1) * (j2 - j1) // (i2 - i1)
                        if j >= j2:
                            continue
                    asignado.setdefault(tb[i][1], []).append(pos_p[j])
                if op == "replace":
                    for j in range(j1, j2):
                        usados.add(pos_p[j])
            elif op == "insert":
                # palabras solo en el PDF: se suman al ítem vecino si están en el mismo bloque
                prev_it = tb[i1 - 1][1] if i1 > 0 else None
                next_it = tb[i1][1] if i1 < len(tb) else None
                prev_g = pos_p[j1 - 1] if j1 > 0 else None
                next_g = pos_p[j2] if j2 < len(pos_p) else None
                for j in range(j1, j2):
                    g = pos_p[j]
                    if prev_it is not None and prev_g is not None and tp[prev_g][3] == tp[g][3]:
                        asignado.setdefault(prev_it, []).append(g)
                    elif next_it is not None and next_g is not None and tp[next_g][3] == tp[g][3]:
                        asignado.setdefault(next_it, []).append(g)
        for k, (_, it) in enumerate(ib.iterrows()):
            js = asignado.get(k)
            campo = "texto_" + it.clase
            if not js:
                # 2.ª pasada: el Excel a veces tiene los textos en otro orden que el PDF y la
                # alineación secuencial no los empareja. Se busca un bloque del mismo artículo
                # con el mismo texto; si la BD tiene más copias que el PDF, es un duplicado.
                ft = fuerte(it.texto)
                cand = bb[bb.texto.map(fuerte).str.contains(ft, regex=False)] if ft else bb.iloc[0:0]
                iguales = [q for q, (_, o) in enumerate(ib.iterrows()) if fuerte(o.texto) == ft]
                if len(cand) and iguales.index(k) < len(cand):
                    b = cand.iloc[min(iguales.index(k), len(cand) - 1)]
                    t = clasificar(it.texto, b.texto) if fuerte(b.texto) == ft else None
                    if t:
                        add(t, campo, fx(it.fila_excel), int(b.pagina), espacios(it.texto),
                            b.texto, "", a, "emparejado por texto (orden distinto en el Excel)")
                    continue
                add("MAYOR", campo, fx(it.fila_excel), None, espacios(it.texto), "", "", a,
                    f"duplicado en la BD: la BD lo tiene {len(iguales)} veces y el PDF "
                    f"{len(cand)} en el artículo {a}" if len(cand)
                    else "texto de la BD sin pareja en el PDF")
                continue
            j0, j1 = min(js), max(js)
            usados.update(range(j0, j1 + 1))
            txt_pdf = " ".join(tp[j][0] for j in range(j0, j1 + 1))
            t = clasificar(it.texto, txt_pdf)
            if t:
                add(t, campo, fx(it.fila_excel), int(tp[j0][2]), espacios(it.texto), txt_pdf, "", a)
        # texto del PDF que no quedó dentro de ningún ítem de la BD
        run = []
        for j in pos_p + [None]:
            if j is not None and j not in usados:
                run.append(j)
                continue
            if run:
                txt = " ".join(tp[q][0] for q in range(run[0], run[-1] + 1))
                ley = re.match(r"^\**\s*(SOD|NCOC)\s*:", txt)
                add("MAYOR", "texto_solo_pdf", None, int(tp[run[0]][2]), "", txt, "", a,
                    "leyenda de abreviaturas al pie de tabla; la BD no guarda leyendas" if ley
                    else "texto del PDF sin pareja en la BD")
                run = []

    d = pd.DataFrame(dif, columns=["tipo", "campo", "fila_excel", "pagina_pdf", "valor_bd",
                                   "valor_pdf", "codigo", "articulo", "detalle"])
    for c in ("fila_excel", "pagina_pdf", "articulo"):
        d[c] = pd.to_numeric(d[c], errors="coerce").astype("Int64")
    resumen = dict(proc_bd=len(pr), proc_pdf=len(pt), emparejados=int((m._merge == "both").sum()),
                   textos_bd=len(items), bloques_pdf=len(bl))
    return d, resumen


def main():
    con = sqlite3.connect(DB)
    pr = pd.read_sql("SELECT * FROM procedimientos ORDER BY fila_excel", con)
    ag = pd.read_sql("SELECT * FROM agrupadores", con)
    ar = pd.read_sql("SELECT * FROM articulos", con)
    nt = pd.read_sql("SELECT * FROM notas", con)
    con.close()
    d, r = comparar(pr, ag, ar, nt, *cargar_pdf())
    d.to_csv(SALIDA, index=False, encoding="utf-8-sig")
    print(f"procedimientos BD: {r['proc_bd']} | PDF: {r['proc_pdf']} | emparejados: {r['emparejados']}")
    print(f"textos BD: {r['textos_bd']} ítems | PDF: {r['bloques_pdf']} bloques")
    if len(d):
        print("diferencias por campo y tipo:")
        print(d.pivot_table(index="campo", columns="tipo", values="codigo", aggfunc="size",
                            fill_value=0).to_string())
    else:
        print("sin diferencias")
    print(f"detalle en {SALIDA}")


if __name__ == "__main__":
    main()
