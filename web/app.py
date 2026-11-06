"""Consulta web del Manual Tarifario ISS 2001 (solo lectura sobre salida/manual_iss.db).

Uso:  ./web.sh            (abre http://127.0.0.1:8000)

- Un menú por vista de la BD (VISTAS). Cada vista declara sus columnas de código y de texto.
- Búsqueda por código (exacto, varios separados por coma o espacio, prefijo con *) o por texto
  (todas las palabras, en cualquier orden, sin distinguir mayúsculas ni tildes).
- Exportación a Excel de lo filtrado o de la vista completa.
- Contraseña opcional: si existe la variable de entorno WEB_CLAVE, todo el sitio (salvo /salud)
  pide usuario y clave (HTTP Basic). Usuario: WEB_USUARIO, o "revisor" si no se define.
  Sin WEB_CLAVE (uso local) no pide nada.
"""
import base64
import hashlib
import binascii
import io
import os
import re
import secrets
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rutas import BASE, DB  # noqa: E402

ESTATICO = Path(__file__).resolve().parent / "static"

# Etiquetas de columnas (las que no estén aquí se muestran con su nombre).
ETIQUETAS = {
    "orden": "Orden", "tipo_fila": "Tipo de fila", "articulo": "Art.", "nivel": "Nivel",
    "agrupador_ruta": "Agrupador (ruta)", "agrupador": "Agrupador", "ref": "REF", "pb": "PB",
    "marca": "PB", "codigo": "Código", "descripcion": "Descripción", "ref_nota": "Nota",
    "valor": "Valor", "unidad": "Unidad", "paquete": "Paquete", "desc_paquete": "Descripción paquete",
    "valor_paquete": "Valor paquete", "fila_excel": "Fila Excel", "seccion": "Sección",
    "titulo": "Título", "tipo": "Tipo", "paquete_codigo": "Paquete", "honorario_cirujano":
    "Honorario cirujano", "area": "Área", "modalidad": "Modalidad", "uvr": "UVR",
    "cirujano": "Cirujano", "anestesia_si_aplica": "Anestesia (si aplica)",
    "ayudante_si_se_causa": "Ayudante (si se causa)", "n_componentes": "N.º componentes",
    "componentes": "Componentes", "componente_codigo": "Componente",
    "componente_descripcion": "Descripción componente", "paquete_descripcion": "Descripción paquete",
    "paquete_valor": "Valor paquete", "nombre": "Nombre", "subtitulo": "Subtítulo", "ruta": "Ruta",
    "valor_excel": "Valor Excel", "valor_pdf": "Valor PDF", "diferencia": "Diferencia",
    "valor_en_bd": "Valor en BD", "motivo": "Motivo", "id": "Id",
    "categoria": "Categoría", "accion": "Acción", "campo": "Campo", "texto_excel": "Texto en el Excel",
    "antes": "Antes", "despues": "Después", "pagina_pdf": "Pág. PDF", "que_cambio": "Qué cambió",
    "texto_excel_original": "Texto en el Excel", "texto_pdf": "Texto en el PDF",
    "grupo": "Grupo", "control": "Control", "pdf": "PDF", "bd": "BD", "resultado": "Resultado",
    "detalle": "Detalle", "filas_revisadas": "Filas revisadas",
    "diferencias_sin_explicar": "Diferencias sin explicar", "observacion": "Observación",
    "abreviatura": "Abreviatura", "significado": "Significado", "paginas_pdf": "Páginas PDF",
}

# vista -> configuración. codigo: columnas comparadas con el código; lista: columnas con códigos
# separados por coma; texto: columnas donde se buscan las palabras; ocultas: no se muestran.
VISTAS = {
    "v_manual_completo": dict(
        titulo="Manual completo", grupo="General", icono="libro",
        descripcion="Todo el Manual en el orden del Excel: artículos, agrupadores, procedimientos, "
                    "componentes (con su paquete) y notas.",
        codigo=["codigo", "ref", "paquete"], texto=["descripcion", "agrupador_ruta", "desc_paquete",
                                                    "ref_nota"], orden="orden"),
    "v_tarifas": dict(
        titulo="Tarifas", grupo="General", icono="etiqueta",
        descripcion="Lista unificada de tarifas: sección, ruta de agrupadores, unidad, valor, "
                    "paquete del componente y honorario del cirujano.",
        codigo=["codigo", "ref", "paquete_codigo"], texto=["descripcion", "agrupador_ruta"],
        ocultas=["id", "descripcion_busqueda"], orden="id"),
    "v_laboratorio": dict(
        titulo="Laboratorio", grupo="Por sección", icono="matraz",
        descripcion="Laboratorio clínico (art. 25) y anatomía patológica (art. 26).",
        codigo=["codigo", "ref"], texto=["descripcion", "agrupador", "area", "seccion"]),
    "v_imagenes": dict(
        titulo="Imágenes diagnósticas", grupo="Por sección", icono="radiografia",
        descripcion="Imagenología (art. 27) por modalidad: radiología, tomografía, ecografía, "
                    "resonancia y medicina nuclear.",
        codigo=["codigo", "ref"], texto=["descripcion", "agrupador_ruta", "modalidad"]),
    "v_honorarios_cirugia": dict(
        titulo="Honorarios de cirugía", grupo="Por sección", icono="bisturi",
        descripcion="Honorarios de cirugía (arts. 1-18) en pesos: cirujano, anestesiólogo y ayudante.",
        codigo=["codigo"], texto=["descripcion", "agrupador"], ocultas=["id"], orden="id"),
    "v_paquetes": dict(
        titulo="Paquetes", grupo="Paquetes", icono="caja",
        descripcion="Conjuntos de atención por tarifa integral (art. 95): valor, número de "
                    "componentes y lista de códigos.",
        codigo=["codigo"], lista=["componentes"], texto=["descripcion", "agrupador_ruta", "titulo"]),
    "v_paquete_componentes": dict(
        titulo="Componentes de paquetes", grupo="Paquetes", icono="piezas",
        descripcion="Qué conjunto cubre cada procedimiento (CUPS → paquete).",
        codigo=["componente_codigo", "paquete_codigo"],
        texto=["componente_descripcion", "paquete_descripcion", "agrupador_ruta"]),
    "v_agrupadores_ruta": dict(
        titulo="Agrupadores", grupo="Estructura", icono="arbol",
        descripcion="Ruta completa de cada agrupador (título > subtítulo > …).",
        codigo=[], texto=["nombre", "ruta"], ocultas=["padre_id", "raiz_id"], orden="id"),
    "v_validacion_resumen": dict(
        titulo="Resumen de la validación", grupo="Validación", icono="escudo",
        descripcion="Controles de la base contra el PDF oficial: cobertura de procedimientos y "
                    "artículos, comparación campo a campo, extracción y auditoría visual. "
                    "Se recalcula cada vez que se regenera la base.",
        codigo=[], texto=["grupo", "control", "detalle", "resultado"], orden="orden"),
    "v_auditoria_visual": dict(
        titulo="Auditoría visual", grupo="Validación", icono="ojo",
        descripcion="Páginas del PDF elegidas al azar (semilla 256) y revisadas a ojo contra la "
                    "base, fila por fila.",
        codigo=[], texto=["observacion"], orden="pagina_pdf"),
    "v_abreviaturas": dict(
        titulo="Abreviaturas", grupo="Validación", icono="texto",
        descripcion="Leyendas al pie de tabla del PDF (SOD, NCOC) y las páginas donde aparecen.",
        codigo=[], texto=["abreviatura", "significado"]),
    "v_novedades": dict(
        titulo="Todas las novedades", grupo="Novedades (Excel → PDF)", icono="lista",
        descripcion="Todo lo que la revisión cambió del Excel para dejarlo igual al PDF oficial: "
                    "categoría, fila del Excel, texto original, valor nuevo, página del PDF y motivo.",
        codigo=["codigo"], texto=["categoria", "texto_excel", "antes", "despues", "motivo"]),
    "v_novedades_eliminadas": dict(
        titulo="Filas eliminadas", grupo="Novedades (Excel → PDF)", icono="papelera",
        descripcion="Filas del Excel que no pasaron a la base: procedimientos que no existen en el "
                    "PDF, duplicados y cabeceras. Se muestra el contenido original de la fila.",
        codigo=["codigo"], texto=["texto_excel", "motivo"]),
    "v_ajustes_valor": dict(
        titulo="Cambios de valor", grupo="Novedades (Excel → PDF)", icono="alerta",
        descripcion="Valores del Excel corregidos con el PDF: valor Excel, valor PDF, diferencia "
                    "y motivo.",
        codigo=["codigo", "ref"], texto=["descripcion", "motivo"]),
    "v_novedades_texto": dict(
        titulo="Cambios de texto", grupo="Novedades (Excel → PDF)", icono="texto",
        descripcion="Descripciones, notas, agrupadores y notas de referencia corregidos con el "
                    "texto del PDF: texto original del Excel y texto del PDF.",
        codigo=["codigo"], texto=["que_cambio", "texto_excel_original", "texto_pdf", "motivo"]),
    "v_novedades_estructura": dict(
        titulo="Cambios de estructura", grupo="Novedades (Excel → PDF)", icono="capas",
        descripcion="Notas que en el PDF son títulos o capítulos, cambio de código y notas del PDF "
                    "que faltaban en el Excel.",
        codigo=["codigo"], texto=["categoria", "texto_excel", "despues", "motivo"]),
    "v_novedades_aceptadas": dict(
        titulo="Diferencias aceptadas", grupo="Novedades (Excel → PDF)", icono="check",
        descripcion="Diferencias revisadas que se dejaron como están: falsos positivos de la "
                    "extracción y textos del PDF que no van en la base (leyendas, cierre).",
        codigo=["codigo"], texto=["texto_excel", "texto_pdf", "motivo"]),
}

RE_CODIGO = re.compile(r"^[A-Za-z]?\d[\w.]*\*?$")
TAMANOS = (10, 25, 50, 100, 250)
MAX_EXCEL = 200_000

app = FastAPI(title="Manual Tarifario ISS 2001", docs_url=None, redoc_url=None, openapi_url=None)

CLAVE = os.environ.get("WEB_CLAVE", "")
USUARIO = os.environ.get("WEB_USUARIO", "revisor")


def credenciales_validas(cabecera):
    if not cabecera.startswith("Basic "):
        return False
    try:
        usuario, _, clave = base64.b64decode(cabecera[6:]).decode("utf-8").partition(":")
    except (binascii.Error, UnicodeDecodeError):
        return False
    # compare_digest en ambos para no filtrar por tiempos cuál de los dos falló
    ok_usuario = secrets.compare_digest(usuario.encode(), USUARIO.encode())
    ok_clave = secrets.compare_digest(clave.encode(), CLAVE.encode())
    return ok_usuario and ok_clave


@app.middleware("http")
async def exigir_clave(request: Request, call_next):
    if CLAVE and request.url.path != "/salud" and not credenciales_validas(
            request.headers.get("Authorization", "")):
        return Response("Se requiere usuario y clave", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Manual ISS 2001", charset="UTF-8"'})
    return await call_next(request)


@app.get("/salud")
def salud():
    """Chequeo de Render: responde sin clave, y solo si la BD existe."""
    if not DB.exists():
        raise HTTPException(503, "sin base de datos")
    return PlainTextResponse("ok")


def norm(x):
    """Mayúsculas sin tildes (registrada en SQLite como NORM)."""
    if x is None:
        return ""
    s = unicodedata.normalize("NFKD", str(x))
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


def conexion():
    if not DB.exists():
        raise HTTPException(503, f"No existe la base {DB}. Genérela con ./actualizar.sh")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.create_function("NORM", 1, norm, deterministic=True)
    return con


def columnas(con, vista):
    todas = [r[1] for r in con.execute(f"PRAGMA table_info({vista})")]
    return [c for c in todas if c not in VISTAS[vista].get("ocultas", [])]


def config(vista):
    if vista not in VISTAS:
        raise HTTPException(404, f"Vista desconocida: {vista}")
    return VISTAS[vista]


def tokens(q):
    return [t for t in re.split(r"[\s,;]+", (q or "").strip()) if t]


def modo_efectivo(cfg, q, modo):
    if modo in ("codigo", "texto"):
        return modo
    ts = tokens(q)
    if ts and (cfg["codigo"] or cfg.get("lista")) and all(RE_CODIGO.match(t) for t in ts):
        return "codigo"
    return "texto"


def escapar(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def filtro(cfg, q, modo):
    """WHERE y parámetros para la búsqueda. Código: cualquiera de los códigos (OR).
    Texto: todas las palabras (AND), cada una en cualquiera de las columnas de texto."""
    ts = tokens(q)
    if not ts:
        return "", [], None
    modo = modo_efectivo(cfg, q, modo)
    params = []
    if modo == "codigo":
        if not (cfg["codigo"] or cfg.get("lista")):
            raise HTTPException(400, "Esta vista no tiene columnas de código: busque por texto")
        partes = []
        for t in ts:
            t = t.upper()
            for c in cfg["codigo"]:
                if t.endswith("*"):
                    partes.append(f"UPPER({c}) LIKE ? ESCAPE '\\'")
                    params.append(escapar(t[:-1]) + "%")
                else:
                    partes.append(f"UPPER({c}) = ?")
                    params.append(t)
            for c in cfg.get("lista", []):
                if t.endswith("*"):
                    partes.append(f"(', ' || UPPER({c})) LIKE ? ESCAPE '\\'")
                    params.append("%, " + escapar(t[:-1]) + "%")
                else:
                    partes.append(f"INSTR(', ' || UPPER({c}) || ',', ?) > 0")
                    params.append(f", {t},")
        return "WHERE " + " OR ".join(partes), params, modo
    junto = " || ' ' || ".join(f"COALESCE({c}, '')" for c in cfg["texto"])
    partes = []
    for t in ts:
        partes.append(f"NORM({junto}) LIKE ? ESCAPE '\\'")
        params.append("%" + escapar(norm(t)) + "%")
    return "WHERE " + " AND ".join(partes), params, modo


def orden_sql(cfg, cols, orden, dir_):
    if orden and orden in cols:
        return f"ORDER BY {orden} {'DESC' if dir_ == 'desc' else 'ASC'}"
    if cfg.get("orden"):
        return f"ORDER BY {cfg['orden']}"
    return ""


@app.get("/api/vistas")
def api_vistas():
    with conexion() as con:
        return [
            dict(id=v, titulo=c["titulo"], grupo=c["grupo"], icono=c["icono"],
                 descripcion=c["descripcion"], por_codigo=bool(c["codigo"] or c.get("lista")),
                 total=con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0])
            for v, c in VISTAS.items()
        ]


@app.get("/api/datos/{vista}")
def api_datos(vista: str, q: str = "", modo: str = "auto", pagina: int = Query(1, ge=1),
              tamano: int = 25, orden: str = "", dir: str = "asc"):
    cfg = config(vista)
    tamano = tamano if tamano in TAMANOS else 25
    with conexion() as con:
        cols = columnas(con, vista)
        where, params, modo_usado = filtro(cfg, q, modo)
        total = con.execute(f"SELECT COUNT(*) FROM {vista}").fetchone()[0]
        filtrados = con.execute(f"SELECT COUNT(*) FROM {vista} {where}", params).fetchone()[0]
        filas = con.execute(
            f"SELECT {', '.join(cols)} FROM {vista} {where} {orden_sql(cfg, cols, orden, dir)} "
            f"LIMIT ? OFFSET ?", [*params, tamano, (pagina - 1) * tamano]).fetchall()
    return dict(columnas=[dict(id=c, etiqueta=ETIQUETAS.get(c, c)) for c in cols],
                filas=filas, total=total, filtrados=filtrados, pagina=pagina, tamano=tamano,
                modo=modo_usado)


@app.get("/api/buscar")
def api_buscar(q: str, modo: str = "auto"):
    """Cuántas filas coinciden en cada vista (búsqueda global desde Inicio)."""
    res = []
    with conexion() as con:
        for v, cfg in VISTAS.items():
            try:
                where, params, m = filtro(cfg, q, modo)
            except HTTPException:
                continue
            n = con.execute(f"SELECT COUNT(*) FROM {v} {where}", params).fetchone()[0]
            res.append(dict(id=v, titulo=cfg["titulo"], icono=cfg["icono"], coincidencias=n, modo=m))
    return res


@app.get("/api/exportar/{vista}")
def api_exportar(vista: str, q: str = "", modo: str = "auto", orden: str = "", dir: str = "asc",
                 completo: bool = False):
    cfg = config(vista)
    with conexion() as con:
        cols = columnas(con, vista)
        where, params, modo_usado = ("", [], None) if completo else filtro(cfg, q, modo)
        filas = con.execute(f"SELECT {', '.join(cols)} FROM {vista} {where} "
                            f"{orden_sql(cfg, cols, orden, dir)} LIMIT {MAX_EXCEL}", params).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = cfg["titulo"][:31]
    ws.append([ETIQUETAS.get(c, c) for c in cols])
    for f in filas:
        ws.append(list(f))
    cabecera = PatternFill("solid", fgColor="1DBB99")
    for celda in ws[1]:
        celda.fill = cabecera
        celda.font = Font(bold=True, color="FFFFFF")
        celda.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, c in enumerate(cols, start=1):
        muestras = [len(ETIQUETAS.get(c, c))] + [len(str(f[i - 1])) for f in filas[:300] if f[i - 1] is not None]
        ws.column_dimensions[get_column_letter(i)].width = min(max(muestras) + 2, 60)
        tipos = {type(f[i - 1]) for f in filas[:300] if f[i - 1] is not None}
        if tipos and tipos <= {int, float}:
            formato = "#,##0" if tipos == {int} else "#,##0.####"
            for (celda,) in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                celda.number_format = formato

    info = wb.create_sheet("Consulta")
    info.append(["Vista", f"{cfg['titulo']} ({vista})"])
    info.append(["Alcance", "Vista completa" if completo else ("Filtrada" if q.strip() else "Sin filtro")])
    if not completo and q.strip():
        info.append(["Búsqueda", q])
        info.append(["Modo", modo_usado])
    info.append(["Filas", len(filas)])
    info.append(["Generado", datetime.now().strftime("%Y-%m-%d %H:%M")])
    info.append(["Fuente", "Manual Tarifario ISS 2001 (Acuerdo 256 de 2001) - salida/manual_iss.db"])
    info.column_dimensions["A"].width = 12
    info.column_dimensions["B"].width = 70
    for (celda,) in info.iter_rows(min_col=1, max_col=1):
        celda.font = Font(bold=True)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    sufijo = "completo" if completo else ("filtrado" if q.strip() else "todo")
    nombre = f"{vista.removeprefix('v_')}_{sufijo}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# Documentos de donde sale la información (se sirven tal cual, sin modificarlos).
FUENTES = {
    "pdf": dict(archivo="MANUAL-ISS-2001.pdf", tipo="application/pdf",
                titulo="Manual Tarifario ISS 2001 (PDF)",
                descripcion="Acuerdo 256 de 2001. Fuente oficial: la base se validó contra este "
                            "documento y, donde difiere del Excel, manda el PDF."),
    "excel": dict(archivo="manual_iss.xls", tipo="application/vnd.ms-excel",
                  titulo="Manual Tarifario ISS 2001 (Excel)",
                  descripcion="Fuente secundaria: de aquí se cargaron las filas de la base, que "
                              "luego se corrigieron con el PDF (ver Novedades)."),
}


def ruta_fuente(fid):
    if fid not in FUENTES:
        raise HTTPException(404, "Documento desconocido")
    ruta = BASE / FUENTES[fid]["archivo"]
    if not ruta.exists():
        raise HTTPException(404, f"No está el archivo {ruta.name}")
    return ruta


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


@app.get("/api/fuentes")
def api_fuentes():
    res = []
    for fid, f in FUENTES.items():
        ruta = BASE / f["archivo"]
        if ruta.exists():
            res.append(dict(id=fid, archivo=f["archivo"], titulo=f["titulo"],
                            descripcion=f["descripcion"], bytes=ruta.stat().st_size,
                            sha256=sha256(ruta)))
    return res


@app.get("/fuentes/{fid}")
def fuente(fid: str, descargar: bool = False):
    """PDF: se abre en el navegador (admite #page=N); ?descargar=1 lo descarga."""
    ruta = ruta_fuente(fid)
    return FileResponse(ruta, media_type=FUENTES[fid]["tipo"], filename=ruta.name,
                        content_disposition_type="attachment" if descargar or fid != "pdf"
                        else "inline")


@app.get("/")
def inicio():
    return FileResponse(ESTATICO / "index.html")


app.mount("/static", StaticFiles(directory=ESTATICO), name="static")
