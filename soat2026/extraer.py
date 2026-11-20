"""Extrae el Manual Tarifario SOAT 2026 (PDF de Asesoría y Servicios AYC, UVB) a una lista ordenada.

Salida: soat2026/salida/items.csv, una fila por elemento en el orden del PDF:
  - tipo=procedimiento: código, descripción, grupo quirúrgico (capítulo III) o factores y valores
    en SMLDV, UVT y UVB (capítulo IV en adelante).
  - tipo=texto: bloque de texto (capítulo, artículo, título, nota, parágrafo...). Lo clasifica etl.py.

Cómo lee el PDF (texto nativo, sin OCR), por posición de cada palabra:
  - código: 4 a 6 dígitos en x < 66 (6 en los conjuntos integrales del art. 64), letra 5,3 normal.
  - descripción: letra 7,4 en x >= 70. El código queda alineado con la ÚLTIMA línea de su
    descripción, así que las líneas 7,4 sin código se acumulan y se cierran con el código.
  - grupo quirúrgico: número en negrilla 6,4 en 300 <= x < 330 (capítulo III).
  - columnas de valor (capítulo IV+): factor SMLDV (normal 5,3, x 295-336), valor SMLDV, factor UVT
    (negrilla 5,3), valor UVT, factor UVB y valor UVB (negrilla 6,4). Pueden quedar centradas
    verticalmente: cada celda se asigna al procedimiento más cercano (franja de su descripción).
  - se descartan: encabezado y pie de página del editor, las anotaciones al margen del editor
    (negrilla 6,4 en x >= 330 del capítulo III: "RECUERDE FACTURAR", "ARTICULO. 48 - 1"...) y los
    errores de hoja de cálculo que trae el PDF (#N/D, #######, #¡VALOR!, "$ -") en las columnas
    de valor (x >= 295; a la izquierda un "-" es parte del texto: "GRUPOS 02 - 03").

Uso: uv run soat2026/extraer.py [ruta.pdf]
"""
import csv
import re
import sys
from pathlib import Path

import pdfplumber

BASE = Path(__file__).resolve().parent
PDF = BASE.parent / "manual tarifario sota" / "Manual-Tarifario-SOAT-2026-uvb.pdf"
SALIDA = BASE / "salida"

TOP_MIN, TOP_MAX = 112, 776          # fuera de esto: encabezado y pie del editor
BASURA = {"#N/D", "#######", "#¡VALOR!", "$", "-", "$-"}
RE_CODIGO = re.compile(r"^\d{4,6}$")
RE_NUM = re.compile(r"^[\d.,]+$")

# Columnas del capítulo IV en adelante: (nombre, x0 mínimo, x0 máximo, negrilla, tamaño)
COLUMNAS = [
    ("f_smldv", 295, 336, False, 5.3),
    ("v_smldv", 340, 393, True, 6.4),
    ("f_uvt", 395, 423, True, 5.3),
    ("v_uvt", 428, 471, True, 6.4),
    ("f_uvb", 471, 505, True, 6.4),
    ("v_uvb", 508, 552, True, 6.4),
]
CAMPOS = ["orden", "pagina", "top", "tipo", "codigo", "descripcion", "grupo",
          "f_smldv", "v_smldv", "f_uvt", "v_uvt", "f_uvb", "v_uvb", "texto", "aviso"]


def es_negrilla(w):
    return "Bold" in w["fontname"]


def tam(w):
    return round(w["size"], 1)


def num_factor(s):
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    return float(s)


def num_valor(partes):
    d = "".join(partes).replace(".", "").replace(",", "")
    return int(d) if d.isdigit() else None


def filas(palabras, tol=2.0):
    """Agrupa palabras en filas por su 'top'."""
    out = []
    for w in sorted(palabras, key=lambda w: (w["top"], w["x0"])):
        if out and w["top"] - out[-1][0]["top"] <= tol:
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(f, key=lambda w: w["x0"]) for f in out]


def unir(ws):
    """Texto de una fila respetando espacios (pdfplumber ya separa las palabras)."""
    return " ".join(w["text"] for w in ws).strip()


def columna(w):
    for nombre, xmin, xmax, neg, t in COLUMNAS:
        if xmin <= w["x0"] < xmax and es_negrilla(w) == neg and abs(tam(w) - t) < 0.2:
            return nombre
    return None


def extraer(pdf_path):
    items = []
    avisos = []
    modo_valores = False      # False: capítulo III (grupo quirúrgico); True: capítulo IV+ (SMLDV/UVT/UVB)
    pendiente = []            # líneas de descripción aún sin código: [(pagina, top, texto)]
    with pdfplumber.open(pdf_path) as pdf:
        for npag, pag in enumerate(pdf.pages, 1):
            top_min = 280 if npag == 1 else TOP_MIN   # pág. 1: portada (los parámetros los lee etl.py)
            ws = [w for w in pag.extract_words(extra_attrs=["size", "fontname"])
                  if top_min <= w["top"] <= TOP_MAX and (w["text"] not in BASURA or w["x0"] < 295)]
            procs = []        # procedimientos de la página (con franja vertical)
            flotantes = []    # celdas de grupo/valor a asignar: (columna, top, [palabras])
            for fila in filas(ws):
                # 1) separar lo que no es texto corrido
                texto_ws, desc_ws, cod, f_smldv = [], [], None, []
                for w in fila:
                    t = tam(w)
                    if not modo_valores and es_negrilla(w) and abs(t - 6.4) < 0.2:
                        if 300 <= w["x0"] < 330 and RE_NUM.match(w["text"]):
                            flotantes.append(("grupo", w["top"], [w]))
                        continue                              # al margen o encabezado "GRUPO QUIRÚRGICO"
                    if modo_valores and w["x0"] >= 295 and (es_negrilla(w) or abs(t - 5.3) < 0.2):
                        col = columna(w)
                        if col == "f_smldv" and RE_NUM.match(w["text"]):
                            f_smldv.append(w)                 # se confirma al final de la fila
                            continue
                        if col and RE_NUM.match(w["text"]):
                            flotantes.append((col, w["top"], [w]))
                            continue
                        if es_negrilla(w):
                            continue                          # rótulos de columna, #N/D...
                    if es_negrilla(w) and t <= 6.5 and w["x0"] >= 295:
                        continue
                    if cod is None and w["x0"] < 66 and abs(t - 5.3) < 0.2 and not es_negrilla(w) \
                            and RE_CODIGO.match(w["text"]) and not texto_ws:
                        cod = w
                        continue
                    if t > 7.0 and (desc_ws or 70 <= w["x0"] < 90):
                        desc_ws.append(w)                     # descripción (7,4 alineada a la izquierda)
                    else:
                        texto_ws.append(w)                    # texto corrido o título (7,4 centrado)
                top = min(w["top"] for w in fila)
                if cod is not None and texto_ws and not desc_ws:
                    # código citado dentro de un texto ("... bajo los siguientes códigos: 02501 ..."):
                    # no es un procedimiento con tarifa, la fila completa es texto
                    texto_ws, cod = [cod] + texto_ws, None
                if f_smldv:
                    if texto_ws and cod is None:
                        texto_ws = sorted(texto_ws + f_smldv, key=lambda w: w["x0"])   # número del texto
                    else:
                        flotantes.append(("f_smldv", f_smldv[0]["top"], f_smldv))
                if cod is not None:
                    lineas = pendiente + ([(npag, top, unir(desc_ws))] if desc_ws else [])
                    pendiente = []
                    if texto_ws:
                        avisos.append(f"pág {npag} código {cod['text']}: texto suelto en la fila: {unir(texto_ws)}")
                    if any(p != npag for p, _, _ in lineas):
                        avisos.append(f"pág {npag} código {cod['text']}: descripción empieza en la página anterior")
                    tops = [tp for p, tp, _ in lineas if p == npag] + [cod["top"]]
                    procs.append({
                        "pagina": npag, "top": round(cod["top"], 1), "tipo": "procedimiento",
                        "codigo": cod["text"], "descripcion": " ".join(t for _, _, t in lineas).strip(),
                        "ini": min(tops) - 1, "fin": cod["top"] + 1, "celdas": {}, "aviso": "",
                    })
                    items.append(procs[-1])
                    continue
                if desc_ws and not texto_ws:
                    pendiente.append((npag, top, unir(desc_ws)))
                    continue
                if texto_ws:
                    txt = unir(texto_ws + desc_ws)
                    if pendiente:
                        avisos.append(f"pág {npag}: descripción sin código antes de «{txt[:60]}»: "
                                      + " | ".join(t for _, _, t in pendiente))
                        items.append({"pagina": npag, "top": round(pendiente[0][1], 1), "tipo": "texto",
                                      "texto": " ".join(t for _, _, t in pendiente),
                                      "aviso": "descripción sin código"})
                        pendiente = []
                    items.append({"pagina": npag, "top": round(top, 1), "tipo": "texto", "texto": txt,
                                  "x0": round(texto_ws[0]["x0"], 1)})
                    if re.match(r"^CAP[IÍ]TULO\s+IV\b", txt) or re.sub(r"\s", "", txt).upper() in ("CAPITULOV", "CAPÍTULOV"):
                        modo_valores = True
            # 2) asignar celdas flotantes al procedimiento más cercano de la página
            asignar(flotantes, procs, npag, avisos)
    # pendiente al final del documento
    if pendiente:
        avisos.append("fin del documento: descripción sin código: " + " | ".join(t for _, _, t in pendiente))
    return items, avisos


def asignar(flotantes, procs, npag, avisos):
    # unir palabras de la misma celda (misma columna y misma altura): "$ 1" ".565.300"
    celdas = {}
    for col, top, ws in flotantes:
        clave = next((k for k in celdas if k[0] == col and abs(k[1] - top) <= 1.5), (col, top))
        celdas.setdefault(clave, []).extend(ws)
    for (col, top), ws in sorted(celdas.items(), key=lambda kv: kv[0][1]):
        if not procs:
            avisos.append(f"pág {npag}: valor {col}={unir(ws)} sin procedimiento en la página")
            continue

        def dist(p):
            return 0 if p["ini"] <= top <= p["fin"] else min(abs(top - p["ini"]), abs(top - p["fin"]))
        p = min(procs, key=dist)
        if dist(p) > 12:
            avisos.append(f"pág {npag}: valor {col}={unir(ws)} (top {top:.0f}) lejos de todo procedimiento")
            continue
        if col in p["celdas"]:
            avisos.append(f"pág {npag} código {p['codigo']}: dos valores en {col}: "
                          f"{unir(p['celdas'][col])} y {unir(ws)}")
            p["aviso"] += f"{col} repetido; "
            continue
        p["celdas"][col] = sorted(ws, key=lambda w: w["x0"])


def a_filas(items):
    out = []
    for i, it in enumerate(items, 1):
        f = {k: "" for k in CAMPOS}
        f.update({"orden": i, "pagina": it["pagina"], "top": it["top"], "tipo": it["tipo"],
                  "aviso": it.get("aviso", "")})
        if it["tipo"] == "texto":
            f["texto"] = it["texto"]
        else:
            f["codigo"], f["descripcion"] = it["codigo"], it["descripcion"]
            for col, ws in it["celdas"].items():
                partes = [w["text"] for w in ws]
                if col == "grupo":
                    f["grupo"] = "".join(partes)
                elif col.startswith("f_"):
                    f[col] = num_factor("".join(partes))
                else:
                    f[col] = num_valor(partes)
        out.append(f)
    return out


def main():
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    items, avisos = extraer(pdf)
    SALIDA.mkdir(exist_ok=True)
    filas_csv = a_filas(items)
    with open(SALIDA / "items.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas_csv)
    (SALIDA / "avisos_extraccion.txt").write_text("\n".join(avisos) + "\n", encoding="utf-8")
    n_proc = sum(1 for f in filas_csv if f["tipo"] == "procedimiento")
    print(f"{len(filas_csv)} elementos ({n_proc} procedimientos) -> {SALIDA / 'items.csv'}")
    print(f"{len(avisos)} avisos -> {SALIDA / 'avisos_extraccion.txt'}")


if __name__ == "__main__":
    main()
