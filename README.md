# Manual Tarifario ISS 2001 (Acuerdo 256 de 2001)

Base de datos del Manual de Tarifas del ISS, fiel al PDF oficial en todos los campos:
códigos, valores, descripciones, marca PB, notas, artículos y agrupadores.

- **Fuente oficial:** `MANUAL-ISS-2001.pdf` (207 páginas).
- **Fuente de estructura:** `manual_iss.xls` (de ahí salen las filas; el PDF manda en el contenido).
- No se modifican nunca el PDF, el XLS ni `manual_iss.csv`.

Python se gestiona con [uv](https://docs.astral.sh/uv/): `uv add` para dependencias y `uv run` para ejecutar.

## Uso rápido

Para regenerar todo de una vez (desde cualquier carpeta):

```bash
./actualizar.sh          # ETL + 4 validaciones + copia para Navicat; se detiene en el primer error
./actualizar.sh --pdf    # además vuelve a extraer el PDF
```

Comandos sueltos:

```bash
uv run extraer_pdf.py        # PDF -> pdf_tablas.csv y pdf_textos.csv (~45 s; solo si cambia el PDF o el extractor)
uv run etl.py                # XLS + correcciones.csv -> salida/manual_iss.db y CSV
uv run validar_completo.py   # informe BD vs PDF -> validacion_completa.csv
uv run cotizar.py 903801 871112x2 C40402   # cotización rápida con tarifas en pesos
uv run probar_bd.py          # 48 pruebas de la BD (consultas_prueba.sql); --ejemplos muestra filas
uv run consultar.py consultas_ver.sql --vertical   # ficha de códigos, paquetes, búsquedas (editar los WITH)
```

Consulta web (buscar por código o texto en todas las vistas y exportar a Excel):

```bash
./web.sh                     # http://localhost:8000 (también desde el navegador de Windows); Ctrl+C para detener
```

`extraer_pdf.py` solo hace falta la primera vez o si cambia el PDF o el extractor; el ETL lee los
CSV que genera.

## Flujo

```
MANUAL-ISS-2001.pdf ──extraer_pdf.py──> pdf_tablas.csv + pdf_textos.csv
                                                 │
manual_iss.xls ──┐                               ▼
correcciones.csv ┴──────etl.py──> aplica correcciones ──> compara todo con el PDF
                                                 │
                     ┌───────────────────────────┴───────────────────────┐
              sin pendientes                                  hay diferencias sin revisar
       salida/manual_iss.db + CSV                   diferencias_pendientes.csv, exit 1,
                                                    no se genera la BD
```

**Regla central: nada se sobrescribe sin revisión.** El ETL solo aplica lo que está en
`correcciones.csv`. Después compara la BD contra el PDF en todos los campos y, si queda alguna
diferencia que no esté revisada, termina con error y la lista en `diferencias_pendientes.csv`.

## Si cambia el Excel o el PDF

Use el prompt de [PROMPT_ACTUALIZACION.md](PROMPT_ACTUALIZACION.md): complete qué cambió y péguelo en
Claude Code abierto en esta carpeta. Guía el diagnóstico, la reubicación de correcciones, la
revisión de diferencias y la validación, con puntos de aprobación antes de fusionar o hacer commit.

## Archivos

`archivo/exploracion/` guarda los scripts de la exploración inicial del Excel (no los usa nada).
Lo que se regenera solo (`salida/`, informes de validación) está en `.gitignore`.

| Archivo | Qué hace |
|---|---|
| `extraer_pdf.py` | Extrae el PDF por celdas de tabla (pdfplumber, bordes). Genera `pdf_tablas.csv` (una fila por procedimiento) y `pdf_textos.csv` (agrupadores, notas, artículos y parágrafos, agrupados en bloques). |
| `control_extraccion.py` | Compara `pdf_tablas.csv` con `pdf_referencia.csv` (extracción anterior con pdftotext) en REF, código, valor y PB. Debe dar «discrepancias: ninguna». |
| `etl.py` | Lee el XLS, clasifica las filas, aplica `correcciones.csv`, valida contra el PDF y escribe la BD. |
| `validar_completo.py` | Comparación BD vs PDF campo por campo. Es un módulo: `etl.py` usa su función `comparar()`. |
| `validar.py` | Validación original: códigos y valores contra `pdf_referencia.csv`. |
| `proponer_jerarquia.py` | Propone la jerarquía de agrupadores (título / subtítulo) a partir del PDF y la escribe en `jerarquia_agrupadores.csv`, para revisarla. Los casos que la regla automática no resuelve están fijados a mano en `AJUSTES`, con la evidencia del PDF (formato o numeración REF). |
| `jerarquia_agrupadores.csv` | Jerarquía revisada que aplica `etl.py`: fila_excel, nombre, nivel, fila_excel_padre, nombre_padre, pagina_pdf, observacion. |
| `cotizar.py` | Cotiza tarifas en pesos. Aplica recargos y descuentos solo si se piden con una opción explícita (ver «Cotizar»); el resto lo avisa. |
| `reglas_tarifas.csv` | Reglas de recargo/descuento que usa `cotizar.py`: artículo, parágrafo, página, tipo, valor, alcance y estado (`aprobada` / `pendiente`). |
| `pruebas_cotizar.py` | Pruebas del cotizador con resultados calculados a mano. |
| `proponer_correcciones.py` | Genera `correcciones_propuestas.csv` a partir de `validacion_completa.csv`, para revisarlo antes de fusionarlo. |
| `auditoria_visual.py` | Muestreo reproducible de 10 páginas (semilla 256): imágenes en `salida/auditoria/` y filas de la BD en `auditoria_filas.csv`. Resultado de la revisión en `auditoria_visual.csv`. |
| `actualizar.sh` | Regenera la BD, corre las validaciones y copia la BD a `C:\Users\Porris\Documents` para Navicat. Se detiene en el primer error. |
| `web.sh`, `web/` | Interfaz web de consulta (FastAPI, solo lectura): un menú por vista, búsqueda por código (varios, o prefijo con `*`) o por texto (sin tildes, palabras en cualquier orden), detalle de cada fila y exportación a Excel filtrada o completa. Las vistas del menú y sus columnas de búsqueda se configuran en `VISTAS` de `web/app.py`. |
| `rutas.py` | Ruta del proyecto y de la BD, para que los scripts funcionen desde cualquier carpeta; si la BD no existe, avisa en vez de crear una vacía. |
| `liquidar.py` | Liquidación de honorarios quirúrgicos (arts. 59-67). |
| `vistas.sql` | Vista `v_honorarios_cirugia`. |
| `correcciones.csv` | Correcciones revisadas a mano. Ver abajo. |
| `ESTADO.md` | Estado del trabajo y decisiones tomadas. |

## `correcciones.csv`

Una fila por corrección:

| columna | contenido |
|---|---|
| `fila_excel` | Fila del XLS afectada (numerada desde 1). Cada fila del Excel es un procedimiento, una nota, un agrupador o un artículo. |
| `codigo_esperado` | Código del procedimiento en esa fila. Es una guarda: si no coincide, el ETL se detiene. Vacío para textos. |
| `accion` | `eliminar`, `cambiar`, `agregar` o `aceptar` |
| `campo` | Campo afectado (según la acción) |
| `valor_nuevo` | Valor nuevo (o, para `aceptar`, el valor del PDF que se acepta como distinto) |
| `pagina_pdf` | Página del PDF donde se comprueba |
| `motivo` | Por qué |

**Acciones**

- `cambiar`: pone `valor_nuevo` en `campo`.
  - Procedimientos: `codigo`, `descripcion`, `valor`, `marca`, `ref_nota`.
  - Notas y artículos: `texto`. Agrupadores: `nombre`.
  - `campo=tipo`, `valor_nuevo=agrupador`: convierte en agrupador una fila que el Excel deja como nota.
  - `campo=tipo`, `valor_nuevo=capitulo`: convierte en nota de tipo `capitulo` un título de capítulo
    que el Excel no deja en la columna 0 (quedaba como nota o agrupador).
- `eliminar`: borra un procedimiento (si no tiene componentes), una nota o un agrupador. Las
  filas de un agrupador eliminado pasan al agrupador anterior del mismo artículo.
- `agregar`: crea una nota que falta en el Excel (`campo=texto`) después del procedimiento de
  `fila_excel`. La nota queda con `fila_excel` vacío y `despues_de_fila` igual a esa fila.
- `aceptar`: diferencia revisada en la que **se mantiene la BD**. Se compara por campo, fila
  (o página, si la fila no existe en la BD) y el valor del PDF en `valor_nuevo`; si el PDF
  cambia, la diferencia vuelve a aparecer.

Todo lo aplicado queda en la tabla `ajustes_pdf` (auditoría, con columna `accion`).

## Cuando el ETL falla

1. Abre `diferencias_pendientes.csv`: tipo, campo, fila_excel, pagina_pdf, valor_bd, valor_pdf, detalle.
2. Comprueba cada caso en el PDF.
3. Agrega a `correcciones.csv` la acción que corresponda y vuelve a correr `uv run etl.py`.

Para muchas diferencias, `uv run validar_completo.py` y luego `uv run proponer_correcciones.py`
generan una propuesta en `correcciones_propuestas.csv`. **Revísala antes de fusionarla.**

Clasificación de las diferencias:

- `MENOR`: solo cambian tildes, mayúsculas, puntuación o espacios.
- `MAYOR`: cambian palabras, números, la marca PB, la nota o la asignación (artículo, agrupador, padre).

## Base de datos (`salida/manual_iss.db`)

| Tabla | Contenido |
|---|---|
| `articulos` | `numero`, `texto`, `fila_excel` |
| `agrupadores` | `id`, `articulo`, `nombre`, `fila_excel`, `padre_id`, `nivel` (1 = título; 2 = subtítulo; …) |
| `procedimientos` | `id`, `fila_excel`, `articulo`, `agrupador_id`, `codigo_manual` (REF), `codigo` (CUPS), `marca` (PB), `descripcion`, `ref_nota`, `valor`, `unidad`, `tipo`, `padre_id`, `descripcion_busqueda` (sin tildes y en mayúsculas, para buscar) |
| `notas` | `id`, `fila_excel`, `articulo`, `agrupador_id`, `procedimiento_id`, `tipo`, `texto`, `despues_de_fila` |
| `parametros` | Valor de la UVR en pesos por tipo de profesional (art. 59) |
| `abreviaturas` | Leyendas del PDF: `SOD` (Sin Otra Denominación), `NCOC` (No Clasificable bajo Otro Concepto), con sus páginas |
| `ajustes_pdf` | Registro de auditoría de las correcciones aplicadas |

- `tipo` de procedimiento: `con_valor`, `componente` (de un paquete; `padre_id` apunta al paquete) o `sin_valor`.
- `unidad`: `UVR` (arts. 1-18), `pesos_por_uvr` (art. 59), `factor` (art. 91), `pesos` (resto).
- `ref_nota`: la última nota entre paréntesis de la descripción; si hay varias, las anteriores quedan
  en la descripción (p. ej. `... SOD (4)` con `ref_nota = 196`).

**Vistas**

| Vista | Contenido |
|---|---|
| `v_tarifas` | Lista de tarifas unificada: sección del Manual, ruta de agrupadores, código, descripción, unidad, valor, paquete del componente y honorario del cirujano (UVR). |
| `v_laboratorio` | Laboratorio clínico (art. 25) y anatomía patológica (art. 26). |
| `v_imagenes` | Imagenología (art. 27) por modalidad: radiología, tomografía, ecografía y resonancia, medicina nuclear. |
| `v_paquetes` | Conjuntos de atención por tarifa integral (art. 95): valor, número de componentes y lista de códigos. |
| `v_paquete_componentes` | Qué conjunto cubre cada procedimiento (CUPS → paquete). |
| `v_agrupadores_ruta` | Ruta completa de cada agrupador, p. ej. `RADIOLOGIA > HUESOS > EXTREMIDADES Y PELVIS`. |
| `v_honorarios_cirugia` | Honorarios de cirugía (arts. 1-18) en pesos por profesional. |
| `v_manual_completo` | Todo el Manual en el orden del Excel (artículos, agrupadores, procedimientos, componentes y notas); los componentes traen código, descripción y valor de su paquete. |
| `v_ajustes_valor` | Valores con novedad: valor del Excel, valor del PDF, diferencia y motivo, de mayor a menor diferencia. |

Ejemplo: `SELECT * FROM v_paquete_componentes WHERE componente_codigo = '512104';`

Buscar sin importar tildes: `WHERE descripcion_busqueda LIKE '%CIRUGIA%'` (escriba el texto sin
tildes; la consulta de búsqueda de `consultas_ver.sql` las quita sola).

Las vistas **no aplican** recargos ni descuentos de los parágrafos: dependen del caso. Para eso está `cotizar.py`.

## Cotizar

```bash
uv run cotizar.py 903801 871112x2 C40402                  # CODIGO, CODIGOxCANTIDAD, CODIGO@REF
uv run cotizar.py 871112 --portatil-rx 871112:fluoroscopia
uv run cotizar.py 903801 C40402 --region-134 META:Granada
uv run pruebas_cotizar.py                                  # pruebas con resultados calculados a mano
```

Una cotización corresponde a un paciente. Los procedimientos en UVR (arts. 1-18) no se suman:
se liquidan con `liquidar.py`. Si hay un error (código inexistente, opción fuera de alcance,
regla pendiente), no se calcula el total.

Los recargos y descuentos **nunca se deducen**: se aplican solo con una opción explícita, porque
el código no dice si un estudio fue portátil o un conjunto bilateral. Cifras y alcance en
`reglas_tarifas.csv`:

| Opción | Regla | Efecto |
|---|---|---|
| `--solo-muestra [COD…]` | Art. 25 par. 3 (pág. 108) | Solo toma de muestra: se paga el 12 % (sin códigos: todo el laboratorio) |
| `--biopsia-multiple COD…` | Art. 26 par. 1 (pág. 110) | Biopsia múltiple: +60 % (solo estudios de BIOPSIAS) |
| `--portatil-rx COD:simple\|fluoroscopia` | Art. 27 par. 4 (pág. 122) | Radiología portátil: +$15.610 / +$46.305 por estudio (no aplica a TAC) |
| `--portatil-eco COD…` | Art. 27 par. 12 (pág. 122) | Ecografía portátil: +$9.095 por estudio |
| `--tecnecio` | Art. 27 par. 16 (pág. 123) | Medicina nuclear con tecnecio 99: +$13.120 por paciente |
| (automático) | Art. 27 par. 16 (pág. 123) | Códigos 920302, 920304, 920305, 920306: +$103.225 por paciente (radioaerosoles) |
| `--bilateral COD…` | Art. 95 par. 6 (pág. 188) | Conjunto bilateral: +55 % |
| `--region-134 DEPTO:MUNICIPIO` | Art. 134 (págs. 204-205) y art. 95 par. 23 (pág. 192) | +15 % Capítulo II (arts. 19-41), +14 % conjuntos. Va al final, sobre lo que efectivamente se paga (incluye bilateral, 12 % de toma de muestra y adicionales por paciente del Capítulo II). No aplica en Arauca, Florencia, Riohacha, Sincelejo, Villavicencio ni Yopal. `URABA` = municipios de la región de Urabá |

No se automatizan (solo se avisan): varios conjuntos en un mismo acto (art. 95 par. 7),
anestesia general en hemodinamia o radiología intervencionista (art. 95 par. 22: falta la
lista de conjuntos a los que aplica) y todo lo que depende del contrato o del consumo.

Si se define `DB_URL` (en `.env`), el ETL también carga las tablas en PostgreSQL, MySQL o SQL Server.

## Particularidades del PDF

Lo que el extractor ya resuelve, para tenerlo en cuenta si se modifica:

- REF en una tabla de una columna; PB suelto entre las tablas; tabla principal CÓDIGO | DESCRIPCIÓN | VALOR.
- Filas sin borde superior (continúan de la página anterior), sin algunas verticales o sin ninguna.
- Filas partidas entre páginas (la última línea de la descripción queda en la página siguiente).
- Valores que se salen del borde de la celda (`56.910`, pág. 119) o partidos en dos líneas (`117.708.66` / `5`).
- Miles con punto (`1.270`), decimales con coma o punto (`0,58` / `0.58`).
- Notas dentro del contorno de una tabla, entre dos filas (pág. 125).
- Agrupadores en mayúsculas, en negrita o en letra más grande; no siempre centrados. Hay títulos de dos y tres niveles.
- Prosa partida que empieza con «Artículo 75…»: los artículos reales van en mayúsculas («ARTICULO 75.»).

## Decisiones tomadas

Revisadas y aprobadas el 2026-11-05 (detalle en `correcciones.csv`):

- Se corrigen al texto del PDF también las diferencias `MENOR`.
- Los errores de redacción del PDF se copian tal cual (p. ej. 993122, 793305-793307).
- 903046 conserva «TRANSFERRINA POR NEFELOMETRÍA» (el PDF omite «TRANSFERRINA»).
- Títulos de dos niveles: la BD mantiene un solo nivel de agrupador (68 filas aceptadas).
- Las leyendas `SOD:`/`NCOC:` no se guardan como notas; van en la tabla `abreviaturas`.
  La fórmula de cierre (pág. 207) no se guarda.
- Jerarquía de agrupadores: los subtítulos que el Excel guardaba como nota pasan a agrupador
  (11 filas, `cambiar tipo` en `correcciones.csv`) y cada agrupador tiene `padre_id` y `nivel`.
  Donde la regla automática falla, el nivel se fijó a mano con evidencia del PDF (formato o
  numeración REF; 5 títulos en `AJUSTES` de
  `proponer_jerarquia.py`); 3 agrupadores de la BD que no son títulos del PDF quedan sin nivel
  (filas de tablas de texto de los arts. 59 y 63).
- Capítulos II a V: notas de tipo `capitulo` (II, III y IV con `cambiar tipo` en `correcciones.csv`).
  El capítulo I está en el preámbulo, que el ETL no carga.
