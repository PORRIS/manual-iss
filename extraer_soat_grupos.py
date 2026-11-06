"""Grupo quirúrgico de cada procedimiento SOAT, leído del PDF escaneado del Decreto 780 de 2016.

El anexo técnico 1 (soat/anexo-tecnico1-decreto-780-de-2016.pdf, numerales 2 a 19, páginas 2 a
~80) clasifica cada intervención con su grupo quirúrgico (02 a 13 y especiales 20 a 23) en tablas
«código | descripción | grupo». El PDF es una imagen (sin texto), así que se reconoce solo lo
necesario: los dígitos del código (primera columna) y del grupo (última columna). Cada dígito se
compara (vecino más cercano, en escala de grises y sin deformarlo) con plantillas de la fuente del
decreto (Arial, de C:\\Windows\\Fonts si está) y con las muestras de la página 3 (verificada a ojo).

Controles (las filas que no los pasan quedan en el informe para revisarlas a mano):
- cada dígito debe parecerse a su plantilla (distancia <= UMBRAL; el texto corrido queda fuera);
- el código tiene 4 o 5 dígitos y el grupo es 2 a 13 o 20 a 23;
- dentro de cada página los códigos van en orden ascendente;
- un código no puede aparecer dos veces.
Se informa (sin descartar) si el código no está en la relación CUPS-SOAT: el decreto tiene
códigos que esa relación no trae.

Salida: soat/soat_grupos.csv (codigo, grupo, pagina, confianza) y soat/soat_grupos_revisar.csv.
Las correcciones manuales van en soat/soat_grupos_correcciones.csv (codigo, grupo, motivo) y se
aplican al final. El PDF no está en git; el CSV sí (lo usa el ETL).

Uso: uv run extraer_soat_grupos.py
"""
import csv
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from rutas import BASE, conectar

PDF = BASE / "soat" / "anexo-tecnico1-decreto-780-de-2016.pdf"
SALIDA = BASE / "soat" / "soat_grupos.csv"
REVISAR = BASE / "soat" / "soat_grupos_revisar.csv"
CORRECCIONES = BASE / "soat" / "soat_grupos_correcciones.csv"
PAGINAS = range(2, 76)  # numerales 2 a 19 (cirugía y endoscopia); desde la 76 son exámenes
ESCALA = 3.0
GRUPOS = set(range(2, 14)) | set(range(20, 24))
UMBRAL = 0.12
ALTO, ANCHO = 28, 22  # caja normalizada de cada dígito (se escala por el alto, sin deformar)
ARIAL = [Path("/mnt/c/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arial.ttf"),
         Path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf")]

# Página 3, verificada a ojo: (código, grupo) en orden de aparición
PAGINA_3 = [
    (1120, 22), (1121, 22), (1122, 23), (1123, 22), (1124, 23), (1125, 20), (1126, 20), (1127, 21),
    (1128, 22), (1131, 23), (1132, 20), (1133, 20), (1140, 12), (1141, 20), (1142, 12), (1143, 22),
    (1144, 20), (1145, 20), (1146, 20), (1147, 22), (1148, 23), (1149, 22), (1150, 20), (1151, 22),
    (1152, 20), (1160, 12), (1161, 12), (1162, 20), (1163, 12), (1164, 13)]


def pagina(pdf, n):
    """(tinta binaria sin las líneas de las tablas, tinta en grises 0-1) de la página n."""
    gris = 1 - np.asarray(pdf[n - 1].render(scale=ESCALA).to_pil().convert("L"), dtype=np.float32) / 255
    tinta = gris > 0.4
    # líneas horizontales y verticales: corridas largas de tinta
    for eje in (1, 0):
        a = tinta if eje == 1 else tinta.T
        largo = 60 if eje == 1 else 45
        for i in range(a.shape[0]):
            fila = a[i]
            if fila.sum() < largo:
                continue
            d = np.diff(np.concatenate(([0], fila.astype(np.int8), [0])))
            ini, fin = np.where(d == 1)[0], np.where(d == -1)[0]
            for s, e in zip(ini, fin):
                if e - s >= largo:
                    fila[s:e] = False
    gris = np.where(tinta, gris, 0)
    return tinta, gris


def tramos(perfil, hueco=1, minimo=1):
    """Tramos consecutivos donde el perfil es > 0, unidos si el hueco es menor que 'hueco'."""
    on = np.where(perfil > 0)[0]
    if not len(on):
        return []
    res, ini, prev = [], on[0], on[0]
    for x in on[1:]:
        if x - prev > hueco:
            if prev - ini + 1 >= minimo:
                res.append((ini, prev + 1))
            ini = x
        prev = x
    if prev - ini + 1 >= minimo:
        res.append((ini, prev + 1))
    return res


def lineas(img):
    """[(y0, y1, [palabras (x0, x1)])] de la página."""
    res = []
    for y0, y1 in tramos(img.sum(axis=1), hueco=2, minimo=6):
        if y1 - y0 > 90:  # bloque raro (imagen): se ignora
            continue
        franja = img[y0:y1]
        palabras = tramos(franja.sum(axis=0), hueco=13, minimo=2)
        res.append((y0, y1, palabras))
    return res


AGUJEROS = {"0": 1, "1": 0, "2": 0, "3": 0, "4": 1, "5": 0, "6": 1, "7": 0, "8": 2, "9": 1}


def agujeros(g):
    """Huecos cerrados del dígito (8 tiene 2; 0, 4, 6 y 9 tienen 1). g: tinta en grises 0-1."""
    b = np.pad(g > 0.25, 1)  # umbral bajo: cierra los trazos finos
    fondo = ~b
    visto = np.zeros_like(fondo)
    h, w = b.shape
    pila = [(0, 0)]
    visto[0, 0] = True
    while pila:  # fondo exterior: relleno desde el borde
        y, x = pila.pop()
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < h and 0 <= xx < w and fondo[yy, xx] and not visto[yy, xx]:
                visto[yy, xx] = True
                pila.append((yy, xx))
    resto = fondo & ~visto
    n = 0
    while resto.any():  # cada región de fondo encerrada es un agujero (las de 1-2 píxeles no)
        y, x = map(int, np.argwhere(resto)[0])
        pila, tam = [(y, x)], 0
        resto[y, x] = False
        while pila:
            y, x = pila.pop()
            tam += 1
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and resto[yy, xx]:
                    resto[yy, xx] = False
                    pila.append((yy, xx))
        n += tam > 2
    return n


def caracteres(img, y0, y1, x0, x1):
    """Recortes normalizados de cada carácter de una palabra: [(vector, agujeros)]."""
    tinta, gris = img
    zona, zg = tinta[y0:y1, x0:x1], gris[y0:y1, x0:x1]
    res = []
    for a, b in tramos(zona.sum(axis=0), hueco=1, minimo=1):
        filas = np.where(zona[:, a:b].sum(axis=1) > 0)[0]
        if not len(filas):
            continue
        g = zg[filas[0]:filas[-1] + 1, a:b]
        res.append((normalizar(g), agujeros(g)))
    return res


def normalizar(c):
    """Dígito escalado a ALTO de alto (sin deformar), centrado en una caja ALTO x ANCHO."""
    h, w = c.shape
    nw = max(1, min(ANCHO, round(w * ALTO / h)))
    im = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).resize((nw, ALTO), Image.BILINEAR)
    caja = np.zeros((ALTO, ANCHO), np.float32)
    x = (ANCHO - nw) // 2
    caja[:, x:x + nw] = np.asarray(im, np.float32) / 255
    caja = np.asarray(Image.fromarray((caja * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),
                      np.float32) / 255
    return np.concatenate([caja.ravel(), [3 * w / h]])  # la proporción separa el 1 del resto


def filas_tabla(img):
    """Filas con primera palabra en la columna del código y última en la del grupo."""
    ancho = img[0].shape[1]
    for y0, y1, pal in lineas(img[0]):
        if len(pal) < 2:
            continue
        (cx0, cx1), (gx0, gx1) = pal[0], pal[-1]
        if cx0 > ancho * 0.4 or gx0 < ancho * 0.6 or cx1 - cx0 > 135 or gx1 - gx0 > 60:
            continue
        yield y0, y1, (cx0, cx1), (gx0, gx1)


def plantillas_arial():
    """Dígitos de Arial en varios tamaños y grosores (la fuente del decreto)."""
    fuente = next((f for f in ARIAL if f.exists()), None)
    if fuente is None:
        return []
    res = []
    for tam in (30, 34, 38, 42, 46):
        f = ImageFont.truetype(str(fuente), tam)
        for d in "0123456789":
            im = Image.new("L", (tam * 2, tam * 2), 0)
            ImageDraw.Draw(im).text((tam // 2, tam // 3), d, fill=255, font=f)
            for grosor in (0, 1):
                a = np.asarray(im.filter(ImageFilter.MaxFilter(3)) if grosor else im, np.float32) / 255
                ys, xs = np.where(a > 0.4)
                res.append((d, normalizar(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1])))
    return res


def entrenar(pdf):
    img = pagina(pdf, 3)
    filas = list(filas_tabla(img))
    if len(filas) != len(PAGINA_3):
        sys.exit(f"Página 3: esperaba {len(PAGINA_3)} filas y hallé {len(filas)}; revise el recorte")
    muestras = {d: [] for d in "0123456789"}
    for (y0, y1, c, g), (cod, grp) in zip(filas, PAGINA_3):
        for palabra, texto in ((c, str(cod)), (g, str(grp))):
            cs = caracteres(img, y0, y1, *palabra)
            if len(cs) != len(texto):
                sys.exit(f"Página 3 fila {cod}: {len(cs)} caracteres para «{texto}»")
            for (v, n), d in zip(cs, texto):
                if n != AGUJEROS[d]:
                    sys.exit(f"Página 3 fila {cod}: el «{d}» tiene {n} agujeros (esperaba {AGUJEROS[d]})")
                muestras[d].append(v)
    todas = [(d, v) for d, vs in muestras.items() for v in vs] + plantillas_arial()
    faltan = sorted(set("0123456789") - {d for d, _ in todas})
    if faltan:
        sys.exit(f"Sin muestras de los dígitos {faltan}")
    return [d for d, _ in todas], np.stack([v for _, v in todas])


def leer(caracteres_, plantillas):
    """Texto y peor distancia normalizada (0 = idéntico) con el vecino más cercano entre los
    dígitos que tienen los mismos agujeros (así el 8 no se confunde con 3 o 6)."""
    etiquetas, matriz = plantillas
    et = np.array(etiquetas)
    texto, peor = "", 0.0
    for v, n in caracteres_:
        dist = np.abs(matriz - v).mean(axis=1)
        mismos = np.array([AGUJEROS[d] == n for d in etiquetas])
        if mismos.any():
            dist = np.where(mismos, dist, np.inf)
        else:
            peor = max(peor, 1.0)  # ningún dígito tiene esos agujeros: no es un dígito
        i = int(dist.argmin())
        texto += et[i]
        peor = max(peor, float(dist[i]))
    return texto, peor


def main():
    if not PDF.exists():
        sys.exit(f"No está {PDF}")
    con = conectar()
    validos = {r[0] for r in con.execute("SELECT codigo FROM soat_procedimientos")}
    con.close()
    pdf = pdfium.PdfDocument(str(PDF))
    plantillas = entrenar(pdf)
    buenos, dudosos, vistos = [], [], {}
    for n in PAGINAS:
        img = pagina(pdf, n)
        anterior = None
        for y0, y1, c, g in filas_tabla(img):
            cod, dc = leer(caracteres(img, y0, y1, *c), plantillas)
            grp, dg = leer(caracteres(img, y0, y1, *g), plantillas)
            if not cod or not grp or max(dc, dg) > 0.18 and len(cod) not in (4, 5):
                continue  # texto corrido, títulos: no es una fila de la tabla
            if len(cod) == 5 and cod.startswith("0"):
                cod = cod[1:]  # errata del decreto: «06431» es 6431
            fila = dict(codigo=cod, grupo=int(grp) if grp.isdigit() else grp, pagina=n,
                        confianza=round(1 - max(dc, dg), 3), y=y0,
                        en_relacion="si" if cod in validos else "no")
            problemas = []
            if max(dc, dg) > UMBRAL:
                problemas.append("dígito poco parecido a la plantilla")
            if len(cod) not in (4, 5):
                problemas.append("el código no tiene 4 o 5 dígitos")
            if not grp.isdigit() or int(grp) not in GRUPOS:
                problemas.append("grupo fuera de 2-13 / 20-23")
            if anterior is not None and cod.isdigit() and int(cod) <= anterior:
                problemas.append(f"fuera de orden (después de {anterior})")
            if cod in vistos:
                problemas.append(f"código repetido (también en la página {vistos[cod]})")
            if problemas:
                dudosos.append(dict(fila, problema="; ".join(problemas)))
            else:
                vistos[cod] = n
                buenos.append(fila)
            if cod.isdigit() and not problemas:
                anterior = int(cod)
    if CORRECCIONES.exists():
        with open(CORRECCIONES, encoding="utf-8") as fh:
            corr = {r["codigo"]: r for r in csv.DictReader(fh)}
        buenos = [b for b in buenos if b["codigo"] not in corr]
        for r in corr.values():
            buenos.append(dict(codigo=r["codigo"], grupo=int(r["grupo"]), pagina=r.get("pagina", ""),
                               confianza="manual", y="",
                               en_relacion="si" if r["codigo"] in validos else "no"))
        dudosos = [d for d in dudosos if d["codigo"] not in corr]
    buenos.sort(key=lambda r: (int(r["codigo"]) if str(r["codigo"]).isdigit() else 0))
    with open(SALIDA, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["codigo", "grupo", "pagina", "confianza", "en_relacion"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(buenos)
    with open(REVISAR, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["codigo", "grupo", "pagina", "y", "confianza", "problema"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(dudosos)
    print(f"{len(buenos)} procedimientos con grupo -> {SALIDA.name}; {len(dudosos)} para revisar -> {REVISAR.name}")


if __name__ == "__main__":
    main()
