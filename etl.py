"""ETL del Manual ISS 2001 (Acuerdo 256).
Estructura (artículos, agrupadores, procedimientos, notas) desde el Excel; el PDF es la
fuente oficial. Nada se sobrescribe sin revisión:
  1) correcciones.csv -> cambios revisados a mano, con página del PDF y motivo:
       eliminar   procedimiento, nota o agrupador (sus filas pasan al agrupador anterior)
       cambiar    campo -> valor_nuevo; campo=tipo, valor_nuevo=agrupador convierte una
                  nota del Excel en agrupador
       agregar    nota del PDF que falta en el Excel (campo=texto), después de la fila
                  fila_excel (queda con fila_excel vacío y despues_de_fila = esa fila)
       aceptar    diferencia revisada en la que se mantiene el valor de la BD
  2) se compara la BD contra el PDF en todos los campos (validar_completo.comparar, sobre
     pdf_tablas.csv y pdf_textos.csv de extraer_pdf.py). Si queda una diferencia que no
     está en correcciones.csv, el ETL termina con error, la deja en
     diferencias_pendientes.csv y no genera la base.
Cada corrección aplicada queda registrada en la tabla ajustes_pdf (auditoría)."""
import os, re, sqlite3, unicodedata
import pandas as pd

from rutas import al_proyecto

al_proyecto()
from validar_completo import PDF_TABLAS, PDF_TEXTOS, cargar_pdf, comparar, fuerte

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ARCHIVO = "manual_iss.xls"
CORRECCIONES = "correcciones.csv"
PENDIENTES = "diferencias_pendientes.csv"
JERARQUIA = "jerarquia_agrupadores.csv"
VISTAS = "vistas.sql"

RE_ART = re.compile(r"^ART[IÍ]CULO\s*(\d+)", re.I)
RE_CAP = re.compile(r"^CAP[IÍ]TULO\b", re.I)
RE_PAR = re.compile(r"^PAR[AÁ]GRAFO", re.I)
RE_COD = re.compile(r"^[A-Z]?\d{4,6}$")
RE_REF = re.compile(r"\((\d{1,4})\)$")  # nota de referencia: (5), (24), (210)

for f in (ARCHIVO,):
    if not os.path.exists(f):
        raise SystemExit(f"Falta {f} en la carpeta del proyecto")


def limpio(x):
    if pd.isna(x):
        return None
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return re.sub(r"\s+", " ", str(x)).strip() or None


def ref5(r):
    """Referencia interna con 5 dígitos (el xls pierde el cero: 5101 -> 05101)."""
    return r.zfill(5) if r and r.isdigit() else r


def unidad(art):
    if art <= 18:
        return "UVR"
    if art == 59:
        return "pesos_por_uvr"
    if art == 91:
        return "factor"
    return "pesos"


raw = pd.read_excel(ARCHIVO, header=None, engine="calamine").iloc[:, :5]
raw.columns = ["c0", "pb", "cod", "desc", "val"]

arts, agrs, procs, notas = [], [], [], []
art = agr = padre = None


COLS_COR = ["fila_excel", "codigo_esperado", "accion", "campo", "valor_nuevo", "pagina_pdf",
            "motivo"]
cor = (pd.read_csv(CORRECCIONES, dtype=str, encoding="utf-8-sig").fillna("")
       if os.path.exists(CORRECCIONES) else pd.DataFrame(columns=COLS_COR))
if not os.path.exists(CORRECCIONES):
    print("AVISO: no encontré", CORRECCIONES, "- no se aplican correcciones manuales")
# filas que el Excel deja como nota y en el PDF son un título (agrupador)
A_AGRUPADOR = {int(c.fila_excel) for _, c in cor.iterrows()
               if c.accion == "cambiar" and c.campo == "tipo" and c.valor_nuevo == "agrupador"}
# filas con el título de un capítulo que el Excel no deja en la columna 0 (quedan como nota
# o agrupador): pasan a nota de tipo capitulo, como el CAPITULO V
A_CAPITULO = {int(c.fila_excel) for _, c in cor.iterrows()
              if c.accion == "cambiar" and c.campo == "tipo" and c.valor_nuevo == "capitulo"}


def add_nota(i, tipo, texto, proc_id=None):
    notas.append(dict(id=len(notas) + 1, fila_excel=i + 1, articulo=art,
                      agrupador_id=agr, procedimiento_id=proc_id,
                      tipo=tipo, texto=texto))


for i, row in raw.iterrows():
    c0, pb, cod, desc = (limpio(row[k]) for k in ("c0", "pb", "cod", "desc"))
    vraw = limpio(row["val"])
    valn = pd.to_numeric(row["val"], errors="coerce")
    if not any([c0, pb, cod, desc, vraw]):
        continue

    # 1) artículo nuevo (el texto puede venir en col 0 o, solo, en col 2)
    cand = c0 or (cod if cod and not desc and not pb else None)
    m = RE_ART.match(cand or "")
    if m and (c0 or int(m.group(1)) == (art or 0) + 1):
        art = int(m.group(1))
        arts.append(dict(numero=art, texto=cand, fila_excel=i + 1))
        agr = padre = None
        continue
    if art is None:  # preámbulo del acuerdo
        continue

    # 1b) nota que en el PDF es un agrupador (correcciones.csv: cambiar tipo -> agrupador)
    if i + 1 in A_AGRUPADOR:
        if cod and RE_COD.match(cod) and desc:
            raise SystemExit(f"{CORRECCIONES}: la fila {i + 1} es un procedimiento, "
                             "no se puede convertir en agrupador")
        agr = len(agrs) + 1
        agrs.append(dict(id=agr, articulo=art, fila_excel=i + 1,
                         nombre=" ".join(x for x in (c0, pb, cod, desc, vraw) if x)))
        padre = None
        continue

    # 1c) capítulo fuera de la columna 0 (correcciones.csv: cambiar tipo -> capitulo)
    if i + 1 in A_CAPITULO:
        if cod and RE_COD.match(cod) and desc:
            raise SystemExit(f"{CORRECCIONES}: la fila {i + 1} es un procedimiento, "
                             "no se puede convertir en capítulo")
        add_nota(i, "capitulo", " ".join(x for x in (c0, pb, cod, desc, vraw) if x))
        agr = padre = None
        continue

    # 2) capítulo
    if c0 and RE_CAP.match(c0):
        add_nota(i, "capitulo", c0)
        agr = padre = None
        continue

    # 3) procedimiento (con valor, componente o sin valor)
    if cod and RE_COD.match(cod) and desc:
        if cod.isdigit():
            cod = cod.zfill(6)  # CUPS de 6 dígitos: recupera ceros iniciales
        ref = None
        m = RE_REF.search(desc)
        if m:
            ref, desc = m.group(1), desc[:m.start()].strip()
        if pd.notna(valn):
            tipo = "con_valor"
        elif padre and (pb == "PB" or not c0):
            tipo = "componente"
        else:
            tipo = "sin_valor"
        pid = len(procs) + 1
        procs.append(dict(
            id=pid, fila_excel=i + 1, articulo=art, agrupador_id=agr,
            codigo_manual=ref5(c0), codigo=cod, marca=pb, descripcion=desc,
            ref_nota=ref, valor=None if pd.isna(valn) else float(valn),
            unidad=unidad(art), tipo=tipo,
            padre_id=padre if tipo == "componente" else None))
        if tipo == "con_valor":
            padre = pid
        continue

    # 4) agrupador: solo la descripción llena
    if desc and not (c0 or pb or cod or vraw):
        agr = len(agrs) + 1
        agrs.append(dict(id=agr, articulo=art, nombre=desc, fila_excel=i + 1))
        padre = None
        continue

    # 5) todo lo demás es texto: notas, parágrafos, incisos
    texto = " ".join(x for x in (c0, pb, cod, desc, vraw) if x)
    if c0 and not (pb or cod or desc or vraw):
        add_nota(i, "paragrafo" if RE_PAR.match(c0) else "texto", texto)
        padre = None
    else:
        add_nota(i, "nota", texto, proc_id=padre)

# ---------------- tablas ----------------
pr = pd.DataFrame(procs)
nt = pd.DataFrame(notas)
nt["despues_de_fila"] = pd.NA  # solo para notas agregadas por correcciones.csv
nt["despues_de_fila"] = nt["despues_de_fila"].astype("Int64")
for df, cols in ((pr, ["agrupador_id", "padre_id"]), (nt, ["agrupador_id", "procedimiento_id"])):
    for c in cols:
        df[c] = df[c].astype("Int64")

# ---------------- alineación con el PDF (fuente oficial) ----------------
# Nada se sobrescribe sin revisión: solo se aplica lo que está en correcciones.csv.
# Después se compara la BD contra el PDF en todos los campos (validar_completo.comparar);
# si queda alguna diferencia que no esté revisada, el ETL termina con error.
ag = pd.DataFrame(agrs)
ar = pd.DataFrame(arts)
ajustes = []

# campos que se pueden corregir, por tabla
CAMPOS = {"procedimientos": ("codigo", "descripcion", "valor", "marca", "ref_nota"),
          "notas": ("texto",), "agrupadores": ("nombre",), "articulos": ("texto",)}


def log(fila, codigo, campo, antes, despues, motivo, accion):
    ajustes.append(dict(fila_excel=fila, codigo=codigo, campo=campo,
                        antes=None if antes is None or pd.isna(antes) else str(antes),
                        despues=None if despues is None else str(despues), motivo=motivo,
                        accion=accion))


def buscar(f):
    """Tabla y posición de la fila del Excel f (cada fila es de una sola tabla)."""
    for nombre, df in (("procedimientos", pr), ("notas", nt), ("agrupadores", ag),
                       ("articulos", ar)):
        idx = df.index[df.fila_excel == f]
        if len(idx) == 1:
            return nombre, idx[0]
    return None, None


for n, c in cor.iterrows():
    lin = n + 2  # línea del CSV (con cabecera)
    if c.accion not in ("eliminar", "cambiar", "aceptar", "agregar"):
        raise SystemExit(f"{CORRECCIONES} línea {lin}: acción '{c.accion}' no válida")
    motivo = f"{c.motivo} (PDF pág. {c.pagina_pdf})" if c.pagina_pdf else c.motivo
    if c.accion == "aceptar":  # se revisó y la BD se mantiene: se usa al filtrar diferencias
        log(c.fila_excel or None, c.codigo_esperado, c.campo, None, c.valor_nuevo, motivo,
            "aceptar")
        continue
    f = int(c.fila_excel)
    tabla, i = buscar(f)
    if tabla is None:
        raise SystemExit(f"{CORRECCIONES} línea {lin}: la fila {f} del Excel no existe "
                         "(o ya se eliminó). Revisa el archivo antes de seguir.")
    df = {"procedimientos": pr, "notas": nt, "agrupadores": ag, "articulos": ar}[tabla]
    if tabla == "procedimientos" and df.at[i, "codigo"] != c.codigo_esperado:
        raise SystemExit(f"{CORRECCIONES} línea {lin}: la fila {f} no tiene el código "
                         f"{c.codigo_esperado}. Revisa el archivo antes de seguir.")
    cod = df.at[i, "codigo"] if tabla == "procedimientos" else ""
    if c.accion == "cambiar" and c.campo == "tipo":  # ya aplicado al leer el Excel
        ok = ((c.valor_nuevo == "agrupador" and tabla == "agrupadores") or
              (c.valor_nuevo == "capitulo" and tabla == "notas"
               and nt.at[i, "tipo"] == "capitulo"))
        if not ok:
            raise SystemExit(f"{CORRECCIONES} línea {lin}: solo se admite cambiar "
                             "tipo -> agrupador o tipo -> capitulo")
        log(f, "", "tipo", "fila del Excel", c.valor_nuevo, motivo, "cambiar")
        continue
    if c.accion == "agregar":  # nota del PDF que falta en el Excel, después de la fila f
        if tabla != "procedimientos" or c.campo != "texto" or not c.valor_nuevo:
            raise SystemExit(f"{CORRECCIONES} línea {lin}: 'agregar' necesita campo=texto, "
                             "valor_nuevo y la fila de un procedimiento como ancla")
        p = pr.loc[i]
        nueva = dict(id=int(nt.id.max()) + 1, fila_excel=pd.NA, articulo=p.articulo,
                     agrupador_id=p.agrupador_id,
                     procedimiento_id=p.id if p.tipo == "con_valor" else p.padre_id,
                     tipo="nota", texto=c.valor_nuevo, despues_de_fila=f)
        nt = pd.concat([nt, pd.DataFrame([nueva])], ignore_index=True)
        for col in ("fila_excel", "agrupador_id", "procedimiento_id", "despues_de_fila"):
            nt[col] = nt[col].astype("Int64")
        log(f, cod, "nota", None, c.valor_nuevo, motivo, "agregar")
        continue
    if c.accion == "eliminar":
        if tabla == "agrupadores":
            # sus filas pasan al agrupador anterior del mismo artículo (título partido en
            # dos filas del Excel, p. ej. "(Incluye quemadura por fricción)")
            gid = ag.at[i, "id"]
            prev = ag[(ag.articulo == ag.at[i, "articulo"]) & (ag.fila_excel < f)]
            if prev.empty:
                raise SystemExit(f"{CORRECCIONES} línea {lin}: el agrupador de la fila {f} "
                                 "no tiene un agrupador anterior al que pasar sus filas")
            pid_ag = int(prev.sort_values("fila_excel").id.iloc[-1])
            for d_ in (pr, nt):
                d_.loc[d_.agrupador_id == gid, "agrupador_id"] = pid_ag
            log(f, "", "fila", "agrupador", f"unido al agrupador id {pid_ag}", motivo,
                "eliminar")
            ag = ag.drop(i)
            continue
        if tabla == "procedimientos":
            pid = pr.at[i, "id"]
            if (pr.padre_id == pid).any():
                raise SystemExit(f"fila {f}: tiene componentes, no se puede eliminar sin revisar")
            nt.loc[nt.procedimiento_id == pid, "procedimiento_id"] = pd.NA
        elif tabla != "notas":
            raise SystemExit(f"{CORRECCIONES} línea {lin}: solo se eliminan procedimientos, "
                             "notas o agrupadores")
        log(f, cod, "fila", "existe", "eliminada", motivo, "eliminar")
        if tabla == "procedimientos":
            pr = pr.drop(i)
        else:
            nt = nt.drop(i)
        continue
    if c.campo not in CAMPOS[tabla]:
        raise SystemExit(f"{CORRECCIONES} línea {lin}: el campo '{c.campo}' no se puede "
                         f"cambiar en {tabla} (válidos: {', '.join(CAMPOS[tabla])})")
    nuevo = float(c.valor_nuevo) if c.campo == "valor" else (c.valor_nuevo or None)
    log(f, cod, c.campo, df.at[i, c.campo], nuevo, motivo, "cambiar")
    df.at[i, c.campo] = nuevo

# ---------------- comparación completa contra el PDF ----------------
for fpdf in (PDF_TABLAS, PDF_TEXTOS):
    if not os.path.exists(fpdf):
        raise SystemExit(f"Falta {fpdf}: ejecuta antes `uv run extraer_pdf.py`")
dif, res = comparar(pr, ag, ar, nt, *cargar_pdf())

# diferencias revisadas con accion=aceptar: misma fila (o misma página si la fila no
# existe en la BD), mismo campo y mismo valor del PDF
acept = cor[cor.accion == "aceptar"]
clave_acept = {(c.campo, c.fila_excel or f"p{c.pagina_pdf}", limpio(c.valor_nuevo) or "")
               for _, c in acept.iterrows()}


def clave(r):
    fila = str(r.fila_excel) if pd.notna(r.fila_excel) else f"p{r.pagina_pdf}"
    return (r.campo, fila, limpio(r.valor_pdf) or "")


dif["revisada"] = [clave(r) in clave_acept for _, r in dif.iterrows()]
pend = dif[~dif.revisada].drop(columns="revisada")
usadas = {clave(r) for _, r in dif[dif.revisada].iterrows()}
sobran = clave_acept - usadas
print(f"comparación con el PDF: {res['emparejados']}/{res['proc_bd']} procedimientos "
      f"emparejados | diferencias: {len(dif)} | revisadas (aceptar): {int(dif.revisada.sum())}"
      f" | pendientes: {len(pend)}")
if sobran:
    print(f"AVISO: {len(sobran)} filas 'aceptar' de {CORRECCIONES} ya no corresponden a "
          f"ninguna diferencia (p. ej. {sorted(sobran)[:3]})")
if len(pend):
    pend.to_csv(PENDIENTES, index=False, encoding="utf-8-sig")
    print(pend.pivot_table(index="campo", columns="tipo", values="pagina_pdf", aggfunc="size",
                           fill_value=0).to_string())
    raise SystemExit(f"ERROR: {len(pend)} diferencias con el PDF sin revisar -> {PENDIENTES}. "
                     f"Revísalas y agrégalas a {CORRECCIONES} (cambiar / eliminar / aceptar). "
                     "No se generó la base de datos.")
if os.path.exists(PENDIENTES):
    os.remove(PENDIENTES)

# ---------------- jerarquía de agrupadores (título / subtítulo) ----------------
# El Excel no la trae; sale del PDF con proponer_jerarquia.py y se revisa en
# jerarquia_agrupadores.csv (como correcciones.csv). Columnas nuevas: padre_id, nivel.
ag["padre_id"], ag["nivel"] = pd.NA, pd.NA
if os.path.exists(JERARQUIA):
    jer = pd.read_csv(JERARQUIA, dtype=str, keep_default_na=False)
    id_de = dict(zip(ag.fila_excel, ag.id))
    for n, j in jer[jer.nivel != ""].iterrows():
        f = int(j.fila_excel)
        idx = ag.index[ag.fila_excel == f]
        if len(idx) != 1 or fuerte(ag.at[idx[0], "nombre"]) != fuerte(j.nombre):
            raise SystemExit(f"{JERARQUIA} línea {n + 2}: la fila {f} no es el agrupador "
                             f"'{j.nombre}'. Regenera con `uv run proponer_jerarquia.py`.")
        ag.at[idx[0], "nivel"] = int(j.nivel)
        if j.fila_excel_padre:
            if int(j.fila_excel_padre) not in id_de:
                raise SystemExit(f"{JERARQUIA} línea {n + 2}: el padre (fila "
                                 f"{j.fila_excel_padre}) no es un agrupador")
            ag.at[idx[0], "padre_id"] = id_de[int(j.fila_excel_padre)]
    for c in ("padre_id", "nivel"):
        ag[c] = ag[c].astype("Int64")
    print(f"jerarquía: {int(ag.nivel.notna().sum())}/{len(ag)} agrupadores con nivel | "
          f"por nivel: { {int(k): int(v) for k, v in ag.nivel.value_counts().sort_index().items()} }")
else:
    print("AVISO: no encontré", JERARQUIA, "- agrupadores sin jerarquía")

# ---------------- abreviaturas (leyendas al pie de tabla del PDF) ----------------
px_ley = pd.read_csv(PDF_TEXTOS, dtype=str, keep_default_na=False)
px_ley = px_ley[px_ley.tipo == "leyenda"]
abrev = (px_ley.texto.str.extract(r"^\**\s*(?P<abreviatura>[A-Z]+)\s*:\s*(?P<significado>.+)$")
         .assign(pagina=px_ley.pagina.astype(int))
         .groupby(["abreviatura", "significado"], as_index=False)
         .agg(paginas_pdf=("pagina", lambda s: ",".join(map(str, sorted(set(s)))))))

tablas = {
    "articulos": ar,
    "agrupadores": ag,
    "abreviaturas": abrev,
    "procedimientos": pr,
    "notas": nt,
    "ajustes_pdf": pd.DataFrame(ajustes, columns=["fila_excel", "codigo", "campo",
                                                  "antes", "despues", "motivo", "accion"]),
}

# Art. 59: valor de la UVR en pesos por tipo de profesional
tablas["parametros"] = (
    pr[(pr.articulo == 59) & (pr.tipo == "con_valor")][["codigo", "descripcion", "valor"]]
    .rename(columns={"codigo": "codigo_uvr", "descripcion": "profesional",
                     "valor": "pesos_por_uvr"})
    .reset_index(drop=True)
)

# ---------------- resumen de control ----------------
print("procedimientos por tipo:\n", pr["tipo"].value_counts().to_string())
print("agrupadores:", len(agrs), "| notas:", len(nt), "| artículos:", len(arts))
nums = {a["numero"] for a in arts}
print("artículos faltantes:", sorted(set(range(1, max(nums) + 1)) - nums))
print("valores por unidad:\n",
      pr.dropna(subset=["valor"]).groupby("unidad").size().to_string())
print("parametros (art. 59):\n", tablas["parametros"].to_string(index=False))
print("componentes sin padre:",
      int(((pr.tipo == "componente") & pr.padre_id.isna()).sum()))
num = pr[pr.codigo.str.isdigit()]
print("dígitos de códigos numéricos:", num.codigo.str.len().value_counts().to_dict())
aj = tablas["ajustes_pdf"]
print("correcciones aplicadas (ajustes_pdf):",
      aj.groupby(["accion", "campo"]).size().to_dict() if len(aj) else {})

# Columna para buscar sin tildes ni mayúsculas (la descripción original no cambia).
def sin_tildes(s):
    if s is None or pd.isna(s):
        return None
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()


tablas["procedimientos"]["descripcion_busqueda"] = tablas["procedimientos"]["descripcion"].map(sin_tildes)

# ---------------- salida ----------------
os.makedirs("salida", exist_ok=True)
for n, df in tablas.items():
    df.to_csv(f"salida/{n}.csv", index=False, encoding="utf-8-sig")

db = "salida/manual_iss.db"
if os.path.exists(db):
    os.remove(db)
con = sqlite3.connect(db)
for n, df in tablas.items():
    df.to_sql(n, con, index=False)
con.execute("CREATE INDEX ix_proc_codigo ON procedimientos(codigo)")
con.execute("CREATE INDEX ix_proc_art ON procedimientos(articulo)")
con.execute("CREATE INDEX ix_proc_padre ON procedimientos(padre_id)")
con.execute("CREATE INDEX ix_notas_art ON notas(articulo)")
con.execute("CREATE INDEX ix_agr_padre ON agrupadores(padre_id)")
if os.path.exists(VISTAS):
    con.executescript(open(VISTAS, encoding="utf-8").read())
    print("vistas creadas desde", VISTAS)
else:
    print("AVISO: no encontré", VISTAS, "- la base queda sin vistas")
con.commit()
con.close()
print("OK -> salida/manual_iss.db y CSV en salida/")

url = os.getenv("DB_URL")  # opcional: carga directa a PostgreSQL/MySQL/SQL Server
if url:
    from sqlalchemy import create_engine
    eng = create_engine(url)
    for n, df in tablas.items():
        df.to_sql(n, eng, if_exists="replace", index=False)
    print("cargado a DB_URL")
