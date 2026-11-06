"""Consulta web del Manual Tarifario ISS 2001 (solo lectura sobre salida/manual_iss.db).

Uso:  ./web.sh            (abre http://127.0.0.1:8000)

- Un menú por vista de la BD (VISTAS). Cada vista declara sus columnas de código y de texto.
- Búsqueda por código (exacto, varios separados por coma o espacio, prefijo con *) o por texto
  (todas las palabras, en cualquier orden, sin distinguir mayúsculas ni tildes).
- Exportación a Excel de lo filtrado o de la vista completa.
- Cotizador (/api/cotizar): el mismo cálculo de cotizar.py, con sus reglas y regiones.
- Auditoría (/api/auditar): compara una factura (RIPS JSON o XML DIAN) con el Manual (auditar.py).
  El archivo se procesa en memoria y no se guarda.
- Contraseña opcional: si existe la variable de entorno WEB_CLAVE, todo el sitio (salvo /salud)
  pide usuario y clave (HTTP Basic). Usuario: WEB_USUARIO, o "revisor" si no se define.
  Sin WEB_CLAVE (uso local) no pide nada.
"""
import base64
import hashlib
import binascii
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auditar as au  # noqa: E402
import soat_versiones as sv  # noqa: E402
import tarifas_propias as tp  # noqa: E402
import cotizar as cz  # noqa: E402
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
    "regla": "Regla", "paragrafo": "Parágrafo", "opcion": "Opción", "variante": "Variante",
    "base": "Base", "alcance": "Alcance", "estado": "Estado", "texto": "Texto",
    "clase": "Clase", "departamento": "Departamento",
    "vigencia": "Vigencia", "fuente": "Fuente", "factor_uvb": "Factor UVB", "factor_uvt": "Factor UVT",
    "factor_smlv": "Factor SMLV", "valor_2026": "Valor 2026", "codigo_soat": "Código SOAT",
    "nombre_cups": "Nombre CUPS", "descripcion_soat": "Descripción SOAT",
    "codigos_soat_del_cups": "Opciones SOAT del CUPS", "tipo_descripcion": "Tipo",
    "anestesiologo": "Anestesiólogo", "ayudante": "Ayudante", "sala": "Derechos de sala",
    "materiales": "Materiales", "numeral": "Numeral", "componente": "Componente",
    "porcentaje": "Porcentaje",
    "cups": "CUPS 2026", "descripcion_cups": "Descripción CUPS", "codigo_iss": "Código ISS",
    "descripcion_iss": "Descripción ISS",
    "codigo_iss_actual": "ISS actual", "descripcion_iss_actual": "Descripción ISS actual",
    "parecido_actual": "Parecido actual", "codigo_sugerido": "ISS sugerido",
    "descripcion_sugerida": "Descripción sugerida", "parecido_sugerido": "Parecido sugerido",
    "estado_revision": "Estado", "codigo_en_homologacion": "En homologacion.csv",
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
    "v_reglas_tarifas": dict(
        titulo="Recargos y descuentos", grupo="Cotizar y auditar", icono="porcentaje",
        descripcion="Reglas que aplica el cotizador, con artículo, parágrafo y página del PDF: "
                    "toma de muestra, biopsia múltiple, portátiles, medicina nuclear, bilateral, "
                    "varios conjuntos en un mismo acto y regiones del art. 134.",
        codigo=["regla"], texto=["texto", "opcion", "alcance"], orden="articulo"),
    "v_homologacion_cups": dict(
        titulo="Relación CUPS → ISS", grupo="Cotizar y auditar", icono="piezas",
        descripcion="Equivalencia de cada CUPS 2026 con su código del Manual ISS 2001 y la tarifa "
                    "ISS (archivo «Relación Manual ISS - CUPS 2026»). La auditoría la usa para "
                    "comparar los RIPS.",
        codigo=["cups", "codigo_iss"], texto=["descripcion_cups", "descripcion_iss", "observacion"],
        orden="cups"),
    "v_tarifarios": dict(
        titulo="Tarifarios", grupo="SOAT y tarifas propias", icono="capas",
        descripcion="Tarifarios con los que se puede auditar: Manual ISS 2001, SOAT 2026 y "
                    "tarifas propias, con su fuente y cómo se calcula el valor.",
        codigo=["id"], texto=["nombre", "descripcion", "fuente"]),
    "v_soat_tarifas": dict(
        titulo="SOAT 2026", grupo="SOAT y tarifas propias", icono="etiqueta",
        descripcion="Códigos SOAT con tarifa: factor UVB, UVT y SMLV y valor 2026 "
                    "(factor UVB x $12.110).",
        codigo=["codigo"], texto=["descripcion"]),
    "v_soat_relacion_cups": dict(
        titulo="Relación CUPS → SOAT", grupo="SOAT y tarifas propias", icono="piezas",
        descripcion="Códigos SOAT relacionados con cada CUPS y su valor 2026. La cirugía SOAT "
                    "(grupo quirúrgico) aparece sin valor.",
        codigo=["cups", "codigo_soat"], texto=["nombre_cups", "descripcion_soat", "observacion"]),
    "v_soat_grupos": dict(
        titulo="Cirugía SOAT por grupo", grupo="SOAT y tarifas propias", icono="bisturi",
        descripcion="Grupo quirúrgico de cada procedimiento (Decreto 780 de 2016, anexo técnico 1) "
                    "y valor 2026 de cirujano, anestesiólogo, ayudante, sala y materiales.",
        codigo=["codigo"], texto=["descripcion"], orden="codigo"),
    "v_soat_reglas_cirugia": dict(
        titulo="Reglas de cirugía SOAT", grupo="SOAT y tarifas propias", icono="porcentaje",
        descripcion="Porcentajes del decreto para bilaterales y cirugías múltiples (numerales 48.2, "
                    "54.2, 54.5 y 69 a 72).",
        codigo=["regla"], texto=["texto", "componente"]),
    "v_regiones_134": dict(
        titulo="Regiones del art. 134", grupo="Cotizar y auditar", icono="mapa",
        descripcion="Departamentos y región con incremento en las tarifas (art. 134, pág. 204) y "
                    "ciudades donde no aplica (par. 2, pág. 205).",
        codigo=[], texto=["nombre", "clase", "observacion"]),
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
    "v_novedades_relacion_cups": dict(
        titulo="Relación CUPS sin código en el PDF", grupo="Novedades (Excel → PDF)", icono="piezas",
        descripcion="Códigos ISS de la relación CUPS 2026 que no existen en el Manual (PDF): de "
                    "dónde salen (Excel o ninguno) y por qué no se pueden usar para comparar.",
        codigo=["cups", "codigo_iss"], texto=["descripcion_cups", "texto_excel", "motivo"]),
    "v_novedades_relacion_revision": dict(
        titulo="Relación CUPS por revisar", grupo="Novedades (Excel → PDF)", icono="alerta",
        descripcion="Posibles errores de la relación CUPS 2026 → ISS: el código ISS actual, el "
                    "sugerido, qué tanto se parecen las descripciones y por qué. Las sugerencias "
                    "están en homologacion.csv como «por_revisar» y no se aplican hasta aprobarlas.",
        codigo=["cups", "codigo_iss_actual", "codigo_sugerido"],
        texto=["descripcion_cups", "descripcion_iss_actual", "descripcion_sugerida", "tipo"]),
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


# ---------------------------------------------------------------- cotizador
OPC_ITEM = ("solo-muestra", "biopsia-multiple", "portatil-rx", "portatil-eco", "bilateral")
_DATOS_COT = {}


def datos_cotizador():
    """Tarifas, notas y reglas de cotizar.py (se cargan una vez por proceso)."""
    if "d" not in _DATOS_COT:
        if not DB.exists():
            raise HTTPException(503, f"No existe la base {DB}. Genérela con ./actualizar.sh")
        _DATOS_COT["d"] = cz.cargar(DB)
    return _DATOS_COT["d"]


class Cotizacion(BaseModel):
    items: list[str] = Field(default_factory=list, max_length=200)
    solo_muestra: list[str] = Field(default_factory=list)
    biopsia_multiple: list[str] = Field(default_factory=list)
    portatil_rx: dict[str, str] = Field(default_factory=dict)
    portatil_eco: list[str] = Field(default_factory=list)
    bilateral: list[str] = Field(default_factory=list)
    tecnecio: bool = False
    mismo_acto: str | None = None
    region: str | None = None  # DEPARTAMENTO:MUNICIPIO, como en cotizar.py --region-134


def sin_nan(x):
    """pandas deja NaN en los campos vacíos; JSON no los admite."""
    if isinstance(x, dict):
        return {k: sin_nan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [sin_nan(v) for v in x]
    return None if isinstance(x, float) and x != x else x


def opciones(c: Cotizacion):
    return {"solo-muestra": c.solo_muestra or None, "biopsia-multiple": c.biopsia_multiple,
          "portatil-rx": {cz.normcod(k): v for k, v in c.portatil_rx.items()},
          "portatil-eco": c.portatil_eco, "tecnecio": c.tecnecio, "bilateral": c.bilateral,
          "mismo-acto": c.mismo_acto or None, "region-134": c.region or None}


def calcular(c: Cotizacion):
    d = datos_cotizador()
    op = opciones(c)
    items = [i for i in (x.strip() for x in c.items) if i]
    filas, ajustes, errores, avisos = cz.cotizar(items, op, d)
    R = d["reglas"]
    R = R[R.estado == "aprobada"]
    for f in filas:
        f["aplicables"] = sorted({r.opcion for r in R[R.opcion.isin(OPC_ITEM)].itertuples()
                                  if f["base"] is not None and cz.en_alcance(f, r.alcance)})
    conj = [f for f in filas if f["base"] is not None and cz.en_alcance(f, "art:95")]
    tec = R[R.opcion == "tecnecio"]
    base = sum(f["base"] for f in filas if f["base"] is not None)
    return sin_nan(dict(
        filas=filas, ajustes=ajustes, errores=errores, avisos=avisos,
        parrafos=cz.parrafos(filas, d), base=base,
        total=None if errores else base + sum(a["monto"] for a in ajustes),
        globales=dict(
            tecnecio=any(cz.en_alcance(f, tec.alcance.iloc[0]) for f in filas
                         if f["base"] is not None) if len(tec) else False,
            conjuntos=sum(f["cantidad"] for f in conj))))


@app.get("/api/cotizador")
def api_cotizador():
    """Opciones del formulario: reglas aprobadas y regiones del art. 134."""
    R = datos_cotizador()["reglas"]
    reg = cz._REG
    return dict(
        reglas=[dict(regla=r.regla, opcion=r.opcion, variante=r.variante, texto=r.texto,
                     cita=f"art. {r.articulo} {cz.parte(r.paragrafo)} (pág. {r.pagina_pdf})")
                for r in R[R.estado == "aprobada"].itertuples()],
        regiones=[dict(clave=r.clave, nombre=r.nombre, clase=r.clase,
                       exceptuadas=[dict(clave=e.clave, nombre=e.nombre) for e in
                                    reg[(reg.clase == "ciudad_exceptuada")
                                        & (reg.departamento == r.clave)].itertuples()],
                       observacion=r.observacion)
                  for r in reg[reg.clase != "ciudad_exceptuada"].itertuples()])


@app.post("/api/cotizar")
def api_cotizar(c: Cotizacion):
    return calcular(c)


@app.post("/api/cotizar/excel")
def api_cotizar_excel(c: Cotizacion):
    r = calcular(c)
    if r["errores"]:
        raise HTTPException(422, "Corrija los errores antes de exportar: " + r["errores"][0])
    wb = Workbook()
    ws = wb.active
    ws.title = "Cotización"
    ws.append(["Concepto", "Código", "Descripción", "Art.", "Unidad", "Valor", "Cantidad",
               "Monto", "Cita"])
    for f in r["filas"]:
        ws.append(["Tarifa", f["codigo"], f["descripcion"], f["articulo"], f["unidad"],
                   f["valor"], f["cantidad"], f["base"], ""])
    for a in r["ajustes"]:
        ws.append(["Recargo" if a["monto"] >= 0 else "Descuento", a["codigo"] or "por paciente",
                   a["texto"], a["articulo"], "pesos", None, None, a["monto"], a["cita"]])
    ws.append([])
    ws.append(["Tarifas (pesos)", None, None, None, None, None, None, r["base"]])
    ws.append(["TOTAL", None, None, None, None, None, None, r["total"]])
    for celda in ws[1]:
        celda.fill = PatternFill("solid", fgColor="1DBB99")
        celda.font = Font(bold=True, color="FFFFFF")
    for fila in ws.iter_rows(min_row=ws.max_row - 1):
        fila[0].font = fila[7].font = Font(bold=True)
    for (v,) in ws.iter_rows(min_row=2, min_col=6, max_col=6):
        v.number_format = "#,##0"
    for (m,) in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        m.number_format = "#,##0.00"
    for col, ancho in zip("ABCDEFGHI", (14, 14, 60, 6, 8, 14, 9, 16, 34)):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = "A2"

    info = wb.create_sheet("Avisos")
    info.append(["Tipo", "Texto"])
    for x in r["avisos"]:
        info.append(["Aviso (no aplicado)", x])
    for p in r["parrafos"]:
        info.append([f"Parágrafo art. {p['articulo']}", p["texto"]])
    info.append(["Opciones", c.model_dump_json(exclude_defaults=True)])
    info.append(["Generado", datetime.now().strftime("%Y-%m-%d %H:%M")])
    info.append(["Fuente", "Manual Tarifario ISS 2001 (Acuerdo 256 de 2001) - cotizar.py"])
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 120
    for celda in info[1]:
        celda.font = Font(bold=True)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nombre = f"cotizacion_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# ---------------------------------------------------------------- auditoría de facturas
MAX_ARCHIVO = 15_000_000


class Archivo(BaseModel):
    nombre: str = Field(max_length=300)
    contenido: str = Field(max_length=MAX_ARCHIVO)


class Linea(BaseModel):
    codigo: str = Field("", max_length=40)
    cantidad: float = 1
    valor_unitario: float | None = None
    descripcion: str = Field("", max_length=500)
    origen: str = Field("", max_length=100)
    fecha: str = Field("", max_length=40)
    seccion: str = Field("", max_length=40)
    motivo: str = Field("", max_length=400)
    datos: dict = Field(default_factory=dict)


class Decision(BaseModel):
    estado: str = Field("", max_length=20)
    glosa: float | None = None
    observacion: str = Field("", max_length=2000)


class Auditoria(Cotizacion):
    lineas: list[Linea] = Field(default_factory=list, max_length=6000)
    decisiones: list[Decision] = Field(default_factory=list, max_length=6000)
    no_tarifadas: list[Linea] = Field(default_factory=list, max_length=6000)
    contrato_pct: float = Field(0, ge=-100, le=1000)
    tarifario: str = Field("iss", pattern="^(iss|soat|propia)$")
    uvb: float = Field(au.UVB_2026, gt=0, le=1_000_000)
    propia_version_id: int | None = None
    soat_version: str = Field("base", pattern=r"^(base|\d{1,9})$")
    factura: str = Field("", max_length=100)
    grupo: str = Field("", max_length=200)


@app.post("/api/auditar/leer")
def api_auditar_leer(a: Archivo):
    try:
        return sin_nan(au.leer_factura(a.nombre, a.contenido))
    except (ValueError, json.JSONDecodeError, ET.ParseError) as e:
        raise HTTPException(422, f"No se pudo leer {a.nombre}: {e}") from e


def tarifas_otras(version="base"):
    """Índices SOAT de la versión pedida (la 2026 del repositorio por defecto), en caché."""
    if "t" not in _DATOS_COT:
        datos_cotizador()  # verifica que exista la base
        _DATOS_COT["t"] = au.cargar_tarifas()
    cache = _DATOS_COT.setdefault("versiones_soat", {})
    if version not in cache:
        try:
            cache[version] = sv.aplicar(_DATOS_COT["t"], version)[0]
        except ValueError as e:
            raise HTTPException(404, str(e)) from e
    return cache[version]


def calcular_auditoria(a: Auditoria):
    lineas = [ln.model_dump() for ln in a.lineas]
    if a.tarifario == "iss":
        return sin_nan(au.auditar(lineas, opciones(a), datos_cotizador(), a.contrato_pct))
    propia = None
    if a.tarifario == "propia":
        if not a.propia_version_id:
            raise HTTPException(422, "Elija el manual de tarifas propias (y su versión) o suba uno nuevo")
        try:
            propia = tp.cargar_version(a.propia_version_id)
        except ValueError as e:
            raise HTTPException(404, str(e)) from e
    T = tarifas_otras(a.soat_version if a.tarifario == "soat" else "base")
    return sin_nan(au.auditar_tarifa(lineas, a.tarifario, T, a.contrato_pct, a.uvb,
                                     propia, datos_cotizador()))


@app.get("/api/tarifarios")
def api_tarifarios():
    """Tarifarios disponibles para auditar (catálogo de la base) y la UVB 2026 del SOAT."""
    with conexion() as con:
        cat = [dict(id=i, nombre=n, vigencia=v, descripcion=d) for i, n, v, d in con.execute(
            "SELECT id, nombre, vigencia, descripcion FROM v_tarifarios")]
        uvb = con.execute("SELECT valor FROM soat_parametros WHERE UPPER(concepto) = 'UVB'").fetchone()
    return dict(tarifarios=cat, uvb=uvb[0] if uvb else au.UVB_2026)


@app.post("/api/auditar")
def api_auditar(a: Auditoria):
    return calcular_auditoria(a)


@app.post("/api/auditar/excel")
def api_auditar_excel(a: Auditoria):
    r = calcular_auditoria(a)
    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    cab = ["Origen", "Código", "Descripción (tarifa)", "Art.", "Cant.", "Valor facturado",
           "Valor según tarifa", "Diferencia", "Estado", "Valor a glosar", "Motivo", "Observación",
           "Alertas", "Citas", "Fecha", "Autorización", "Diagnóstico principal"]
    ws.append(cab)
    total_glosa = 0.0
    for i, x in enumerate(r["lineas"]):
        dec = a.decisiones[i] if i < len(a.decisiones) else Decision()
        estado = dec.estado or x["estado"]
        glosa = (dec.glosa if dec.glosa is not None else x["glosa"]) if estado == "Glosa" else 0
        total_glosa += glosa or 0
        m = x["manual"] or {}
        citas = [a_["cita"] for a_ in x["ajustes"]] + [al["cita"] for al in x["alertas"] if al["cita"]]
        ws.append([x["origen"], x["codigo"], m.get("descripcion") or x["descripcion_factura"],
                   m.get("articulo"), x["cantidad"], x["facturado"], x["esperado"], x["diferencia"],
                   estado, glosa, x["motivo"], dec.observacion,
                   "\n".join(f"{al['tipo']}: {al['texto']}" for al in x["alertas"]),
                   "; ".join(dict.fromkeys(citas)), x["fecha"],
                   x["datos"].get("numAutorizacion"),
                   " / ".join(str(v) for k, v in x["datos"].items()
                              if k.startswith("codDiagnosticoPrincipal") and v
                              and not k.endswith("E"))])
    ws.append([])
    s = r["resumen"]
    for etiqueta, valor in (("Total facturado", s["facturado"]), ("Total según la tarifa", s["esperado"]),
                            ("Total a glosar", total_glosa)):
        ws.append([etiqueta, None, None, None, None, valor if "facturado" in etiqueta else None,
                   valor if "Manual" in etiqueta else None, None, None,
                   valor if "glosar" in etiqueta else None])
        ws[ws.max_row][0].font = Font(bold=True)
    for celda in ws[1]:
        celda.fill = PatternFill("solid", fgColor="1DBB99")
        celda.font = Font(bold=True, color="FFFFFF")
    for col in "FGHJ":
        for (c_,) in ws.iter_rows(min_row=2, min_col=ord(col) - 64, max_col=ord(col) - 64):
            c_.number_format = "#,##0.00"
    for col, ancho in zip("ABCDEFGHIJKLMNOPQ", (20, 10, 46, 6, 6, 15, 15, 14, 10, 15, 40, 40, 70, 30,
                                                17, 16, 16)):
        ws.column_dimensions[col].width = ancho
    for fila in ws.iter_rows(min_row=2):
        for c_ in fila:
            c_.alignment = Alignment(vertical="top", wrap_text=c_.column_letter in "CKLMN")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:Q{len(r['lineas']) + 1}"

    if a.no_tarifadas:
        st = wb.create_sheet("Sin tarifa por código")
        st.append(["Origen", "Código", "Descripción", "Cant.", "Valor unitario", "Valor total",
                   "Motivo"])
        for o in a.no_tarifadas:
            st.append([o.origen, o.codigo, o.descripcion, o.cantidad, o.valor_unitario,
                       None if o.valor_unitario is None else o.valor_unitario * o.cantidad,
                       o.motivo])
        for celda in st[1]:
            celda.fill = PatternFill("solid", fgColor="6D5EAC")
            celda.font = Font(bold=True, color="FFFFFF")
        for col, ancho in zip("ABCDEFG", (34, 18, 50, 7, 15, 15, 80)):
            st.column_dimensions[col].width = ancho
        for col in "EF":
            for (c_,) in st.iter_rows(min_row=2, min_col=ord(col) - 64, max_col=ord(col) - 64):
                c_.number_format = "#,##0.00"
        st.freeze_panes = "A2"

    info = wb.create_sheet("Datos")
    for k, v in (("Factura", a.factura), ("Paciente / grupo", a.grupo),
                 ("Tarifario", {"iss": "Manual ISS 2001",
                                "soat": f"SOAT versión {a.soat_version} (UVB {a.uvb:g})",
                                "propia": f"Tarifas propias (versión id {a.propia_version_id})"}[a.tarifario]),
                 ("Condiciones", opciones(a) if a.tarifario == "iss" else "—"),
                 ("Contrato (% sobre la tarifa)", f"{a.contrato_pct:g}"), ("Errores", "; ".join(r["errores"])),
                 ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M")),
                 ("Fuente", "Manual Tarifario ISS 2001 (Acuerdo 256 de 2001) - auditar.py"),
                 ("Nota", "Estados y valores a glosar sugeridos por la herramienta y revisados por "
                          "el auditor; la decisión final es del auditor.")):
        info.append([k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)])
    for p_ in r["parrafos"]:
        info.append([f"Parágrafo art. {p_['articulo']}", p_["texto"]])
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 120
    for (celda,) in info.iter_rows(min_col=1, max_col=1):
        celda.font = Font(bold=True)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    base = re.sub(r"[^\w-]+", "_", a.factura or "factura")[:40]
    nombre = f"auditoria_{base}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# ---------------------------------------------------------------- manuales de tarifas propias
def _json(x):
    """Fechas a texto para JSON."""
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_json(v) for v in x]
    return x.isoformat() if hasattr(x, "isoformat") else x


class ArchivoExcel(BaseModel):
    nombre: str = Field(max_length=300)
    contenido_b64: str = Field(max_length=int(tp.MAX_ARCHIVO * 1.4))
    tipo_base: str = Field("valor_fijo", pattern="^(valor_fijo|soat|iss)$")


class ManualNuevo(ArchivoExcel):
    codigo: str = Field(max_length=50)
    nombre_manual: str = Field(max_length=200)
    pagador: str = Field("", max_length=200)
    factor_pct: float = Field(0, ge=-100, le=1000)
    vigencia_inicio: date | None = None
    vigencia_fin: date | None = None
    estado: str = Field("borrador", pattern="^(borrador|activo|inactivo)$")
    observacion: str = Field("", max_length=2000)


class CambioEstado(BaseModel):
    estado: str = Field(pattern="^(borrador|activo|inactivo)$")  # (las versiones SOAT: activo|inactivo)


def _bytes(b64):
    try:
        return base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise HTTPException(422, "Archivo mal codificado") from e


@app.get("/api/propias")
def api_propias():
    try:
        return _json(dict(destino=tp.destino(), manuales=tp.listar()))
    except Exception as e:  # noqa: BLE001 - p. ej. TARIFAS_DB_URL inaccesible
        raise HTTPException(503, f"No se pudo abrir la base de tarifas propias: {e.__class__.__name__}") from e


@app.post("/api/propias/previa")
def api_propias_previa(a: ArchivoExcel):
    """Lee el Excel sin guardarlo: conteos, primeras filas, avisos y errores."""
    try:
        filas, avisos = tp.leer_excel(_bytes(a.contenido_b64))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    conteo = {}
    for f in filas:
        conteo[f["tipo"]] = conteo.get(f["tipo"], 0) + 1
    return dict(filas=len(filas), por_tipo=conteo, muestra=filas[:20], avisos=avisos,
                errores=tp.validar(filas, a.tipo_base))


@app.post("/api/propias")
def api_propias_guardar(m: ManualNuevo):
    try:
        v = tp.guardar(_bytes(m.contenido_b64), m.nombre, m.codigo, m.nombre_manual, m.tipo_base,
                       m.factor_pct, m.vigencia_inicio, m.vigencia_fin, m.estado, m.pagador,
                       m.observacion)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return v


@app.post("/api/propias/{version_id}/estado")
def api_propias_estado(version_id: int, c: CambioEstado):
    try:
        tp.cambiar_estado(version_id, c.estado)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True}


@app.get("/api/propias/{version_id}/items")
def api_propias_items(version_id: int):
    return _json(tp.items_version(version_id))


@app.get("/api/propias/{version_id}/archivo")
def api_propias_archivo(version_id: int):
    try:
        nombre, contenido = tp.archivo(version_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return Response(contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nombre or "manual.xlsx"}"'})


# ---------------------------------------------------------------- versiones de la tarifa SOAT
class TablaSoat(BaseModel):
    nombre: str = Field(max_length=300)
    contenido_b64: str = Field(max_length=int(tp.MAX_ARCHIVO * 1.4))


class VersionSoat(TablaSoat):
    anio: int = Field(ge=2000, le=2100)
    nombre_version: str = Field("", max_length=200)
    uvb: float | None = Field(None, gt=0, le=10_000_000)
    estado: str = Field("activo", pattern="^(activo|inactivo)$")
    observacion: str = Field("", max_length=2000)


@app.get("/api/soat/versiones")
def api_soat_versiones():
    with conexion() as con:
        return _json(dict(destino=tp.destino(), versiones=sv.listar(con)))


@app.post("/api/soat/previa")
def api_soat_previa(t: TablaSoat):
    try:
        tar, uvb, calculados = sv.leer_excel(_bytes(t.contenido_b64))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    cir = [c for c in tar.codigo if c in tarifarios_series()]
    return sin_nan(dict(filas=len(tar), uvb=uvb, calculados=calculados, componentes_cirugia=len(cir),
                        muestra=tar.head(20).to_dict("records")))


def tarifarios_series():
    from tarifarios import SERIES_CIRUGIA
    return {str(k) for a, b in SERIES_CIRUGIA.values() for k in range(a, b + 1)}


@app.post("/api/soat/versiones")
def api_soat_guardar(v: VersionSoat):
    try:
        r = sv.guardar(_bytes(v.contenido_b64), v.nombre, v.anio, v.nombre_version, v.uvb, v.estado,
                       v.observacion)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    _DATOS_COT.pop("versiones_soat", None)
    return r


@app.post("/api/soat/versiones/{version_id}/estado")
def api_soat_estado(version_id: int, c: CambioEstado):
    try:
        sv.cambiar_estado(version_id, c.estado)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"ok": True}


@app.get("/api/soat/versiones/{version_id}/tarifas")
def api_soat_tarifas(version_id: int):
    return _json(sv.tarifas_version(version_id))


@app.get("/api/soat/versiones/{version_id}/archivo")
def api_soat_archivo(version_id: int):
    try:
        nombre, contenido = sv.archivo(version_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return Response(contenido, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nombre or "soat.xlsx"}"'})


@app.get("/api/propias-plantilla")
def api_propias_plantilla():
    return Response(tp.plantilla(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="plantilla_tarifas_propias.xlsx"'})


@app.get("/")
def inicio():
    return FileResponse(ESTATICO / "index.html")


app.mount("/static", StaticFiles(directory=ESTATICO), name="static")
