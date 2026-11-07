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

Publicar en Render (gratis): `render.yaml` crea el servicio. En el build genera la BD con
`etl.py` (la BD no está en el repositorio) y pide la contraseña `WEB_CLAVE` (usuario `revisor`).
Pasos: subir el repositorio a GitHub → render.com → New → Blueprint → elegir el repositorio →
escribir la clave. Sin `WEB_CLAVE` (uso local con `./web.sh`) no pide clave.

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
| `render.yaml` | Despliegue en Render (build con `etl.py`, chequeo `/salud`, clave en `WEB_CLAVE`). |
| `web.sh`, `web/` | Interfaz web de consulta (FastAPI, solo lectura): un menú por vista, búsqueda por código (varios, o prefijo con `*`) o por texto (sin tildes, palabras en cualquier orden), detalle de cada fila, exportación a Excel filtrada o completa, y descarga del PDF y el Excel de origen (`/fuentes/pdf`, `/fuentes/excel`; el PDF abre en una página con `#page=N`). Las vistas del menú y sus columnas de búsqueda se configuran en `VISTAS` de `web/app.py`. |
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
| `ajustes_pdf` | Registro de auditoría de las correcciones aplicadas; `texto_excel` guarda el contenido original de la fila del Excel y `pagina_pdf` la página del PDF |

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
| `v_validacion_resumen` | Resumen de la validación BD vs PDF (tabla `validacion_resumen`, la calcula `etl.py`): cobertura de procedimientos y artículos, comparación campo a campo, control de extracción, auditoría visual y conteo de novedades. |
| `v_auditoria_visual` | Las 10 páginas de la auditoría visual (tabla `auditoria_visual`, desde `auditoria_visual.csv`). |
| `v_abreviaturas` | Leyendas SOD y NCOC del PDF. |
| `v_novedades` | Todas las novedades de la revisión Excel → PDF (371): categoría, fila del Excel, texto original del Excel, antes/después, página del PDF y motivo. |
| `v_novedades_eliminadas` | Las 11 filas del Excel que no pasaron a la BD, con su contenido original. |
| `v_novedades_texto` | Los 280 textos corregidos con el del PDF (descripciones, notas, agrupadores, notas de referencia). |
| `v_novedades_estructura` | Cambios de clasificación (nota → agrupador o capítulo), de código y notas agregadas desde el PDF (20). |
| `v_novedades_aceptadas` | Las 23 diferencias revisadas que se dejaron como están. |

Ejemplo: `SELECT * FROM v_paquete_componentes WHERE componente_codigo = '512104';`

Buscar sin importar tildes: `WHERE descripcion_busqueda LIKE '%CIRUGIA%'` (escriba el texto sin
tildes; la consulta de búsqueda de `consultas_ver.sql` las quita sola).

Las vistas **no aplican** recargos ni descuentos de los parágrafos: dependen del caso. Para eso está `cotizar.py`.

## Cotizar

```bash
uv run cotizar.py 903801 871112x2 C40402                  # CODIGO, CODIGOxCANTIDAD, CODIGO@REF
uv run cotizar.py 871112 --portatil-rx 871112:fluoroscopia
uv run cotizar.py 903801 C40402 --region-134 META:Granada
uv run cotizar.py C40402 C40403 --mismo-acto igual        # varios conjuntos en un mismo acto
uv run pruebas_cotizar.py                                  # pruebas con resultados calculados a mano
```

Una cotización corresponde a un paciente. Las cirugías en UVR (arts. 1-18) se liquidan con
`uvr.py` (honorarios, derechos de sala y materiales): por código se declaran la sala
(`--uvr-sala COD:quirofano|especial|endoscopia|basica`), la anestesia local (`--sin-anestesia`),
el ayudante (`--ayudante`, desde 50 UVR) y la bilateralidad (`--bilateral`); `--mismo-acto igual`
aplica el art. 65 (60 % de honorarios y 50 % de sala de la adicional, sin pagos desde la tercera
salvo politrauma) y `diferente` el art. 66 (75 % de honorarios). En la web, cada cirugía en UVR
muestra esas opciones y el desglose por componente. Si hay un error (código inexistente, opción fuera de alcance,
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
| `--mismo-acto igual\|diferente` | Art. 95 par. 7 (pág. 188) | Varios conjuntos en un mismo acto: el de mayor tarifa al 100 %; `igual` (mismo especialista, igual vía) + 25 % del siguiente; `diferente` (otra vía o especialidad) + 70 % de cada uno de los demás. Con un solo conjunto no procede el conjunto (literal a): error. Quedan como error, pendientes de consulta: `igual` con 3 o más conjuntos y la combinación con `--bilateral` |
| `--region-134 DEPTO:MUNICIPIO` | Art. 134 (págs. 204-205) y art. 95 par. 23 (pág. 192) | +30 % consultas, interconsultas, urgencias y atención intrahospitalaria (arts. 75-76, literal a; sin 399601 ni 890503, pendientes de consulta), +15 % Capítulo II (arts. 19-41), +14 % conjuntos. Va al final, sobre lo que efectivamente se paga (incluye bilateral, 12 % de toma de muestra y adicionales por paciente del Capítulo II). No aplica en Arauca, Florencia, Riohacha, Sincelejo, Villavicencio ni Yopal. `URABA` = municipios de la región de Urabá |

Los departamentos, la región y las ciudades exceptuadas del art. 134 están en `regiones_134.csv`
(vista `v_regiones_134`); las reglas, en la vista `v_reglas_tarifas`.

En la web, el menú **Cotizador > Cotizar** hace el mismo cálculo (POST `/api/cotizar`): se agregan
códigos, se marcan por fila las opciones que aplican a cada uno, se elige el lugar de la atención y
si hubo varios conjuntos en un mismo acto, y se exporta la cotización a Excel.

No se automatizan (solo se avisan): anestesia general en hemodinamia o radiología intervencionista (art. 95 par. 22: falta la
lista de conjuntos a los que aplica) y todo lo que depende del contrato o del consumo.

## Auditar facturas

```bash
uv run auditar.py ejemplos/rips_ejemplo.json               # RIPS JSON (Res. 2275 de 2023)
uv run auditar.py ejemplos/factura_ejemplo.xml --mismo-acto igual   # factura electrónica DIAN (UBL)
uv run auditar.py factura.json --usuario 2 --region-134 META:Granada --csv auditoria.csv
uv run auditar.py factura.json --contrato 30               # contrato "ISS 2001 + 30 %"
uv run pruebas_auditar.py
```

Compara cada línea de la factura con el valor del Manual (tarifa más los recargos y descuentos que
declare el auditor, calculados como en `cotizar.py`) y sugiere un estado:

- **Glosa**: valor facturado mayor que el del Manual (tolerancia $1 por redondeo); valor sugerido = la diferencia.
- **Revisar**: posible doble cobro (componente cobrado aparte junto con el conjunto que lo cubre,
  art. 95 par. 1, pág. 187), código que no está en el Manual (puede necesitar homologación si la
  factura usa CUPS vigentes), código con varios valores, código repetido, o cirugía en UVR cuyo
  valor no coincide con ningún escenario de la norma.

**Cirugías en UVR** (`uvr.py`, Capítulo I): una línea puede traer la cirugía completa (honorarios
de cirujano $1.270/UVR, anestesiólogo $960/UVR, ayudante $360/UVR desde 50 UVR; derechos de sala
de quirófano por rango, o UVR × $1.410 con más de 450 UVR; materiales por rango hasta 170 UVR),
sin ayudante, con ayudante especialista (art. 63 par.), en sala especial, de endoscopia o básica
(arts. 79-81 y 85 par. 2-3), bilateral (+75 %, salvo las «uni o bilateral»), adicional del mismo
acto (art. 65: 60 % de honorarios y 50 % de sala; art. 66: 75 %; art. 67: 60/75/50 %) o un solo
componente. Se aplican el contrato y el +30 % del art. 134 literal a (honorarios y sala). Si lo
cobrado coincide con un escenario (tolerancia $100) queda Conforme con el escenario explicado; si
supera a todos, Glosa sobre el mayor; si no, Revisar. `liquidar.py` (solo honorarios) se conserva
sin cambios.
- **Conforme**: igual o menor que el Manual.

El lector de RIPS toma **todos los campos** de cada registro, también los nuevos de la Res. 948 de
2026 (CIE-11, `codigoVIDA`, `vrDispensacion`, `registroSIRAS`), acepta las variantes de nombre de
la norma (`otros_servicios`, `fechalnicioAtencion`, `...Relacionadol`) y muestra urgencias,
hospitalización y recién nacidos. Los documentos de los pacientes se enmascaran.

No se comparan por código (van a la hoja «Sin tarifa por código»): medicamentos (art. 87, precio de
adquisición más un porcentaje), dispositivos e insumos `tipoOS` 01 (art. 88, hasta el precio de
adquisición + 12 %) y servicios complementarios `tipoOS` 04 (MIPRES).

Los RIPS usan **CUPS vigentes**. Para compararlos, el ETL carga «Relación Manual ISS - CUPS
2026.xlsx» (9.379 CUPS con su código ISS; el Excel pierde los ceros a la izquierda y se completan
a 6) en la tabla `homologacion_cups` (vista `v_homologacion_cups`, menú «Relación CUPS → ISS»). Las
líneas que vienen de un RIPS siempre se comparan con su código ISS equivalente (313 CUPS existen
también como código ISS con otro significado); las digitadas se toman como código ISS.
`homologacion.csv` (`codigo_factura,codigo_manual,estado,observacion`) corrige o completa la
relación: solo las filas con estado `aprobada` se aplican (tienen prioridad sobre la relación).

`revision_relacion_cups.py` (corre en cada ETL) busca **posibles errores de la relación**
comparando la descripción CUPS con la ISS y con el resto del Manual (4 reglas, ver el
docstring): hoy 210 casos, en Novedades → «Relación CUPS por revisar» y en «Todas las
novedades». Cada sugerencia se agrega a `homologacion.csv` con estado `por_revisar`: no cambia la
auditoría (la línea queda en Revisar con la alerta «Relación dudosa») hasta que alguien cambie el
estado a `aprobada` (o a `rechazada` para descartarla) y se regenere la base. La factura electrónica XML suele traer el código interno
del prestador y no el CUPS: sirve para cuadrar el total, la comparación se hace con el RIPS.

Además muestra por línea las notas del procedimiento (INCLUYE, EXCLUYE, APLICA, por sesión...) para
que el auditor verifique. Los RIPS se auditan por usuario (paciente); los medicamentos no se
comparan (el Manual no los tarifa, art. 87). En la web (**Cotizar y auditar > Auditar factura**) se
carga el archivo o se digitan las líneas, el auditor confirma o cambia cada estado, ajusta el valor a
glosar, escribe la observación y exporta el informe a Excel. El archivo no se guarda en el servidor.

## SOAT y tarifas propias

`tarifarios.py` (lo llama el ETL) carga el SOAT aparte, con tablas relacionales propias (llaves
primarias y foráneas; prefijo `soat_`), sin tocar las del Manual ISS:

| Tabla | Contenido | Fuente |
|---|---|---|
| `tarifarios` | Catálogo: `iss`, `soat`, `propia` | — |
| `soat_parametros` | UVB, UVT, SMLV y SMLDV 2026 con su norma | `soat/SOAT A SALARIO MINIMO_UVT_UVB.xlsx` (hoja TD) |
| `soat_procedimientos` | Todos los códigos SOAT (PK) | tabla SOAT y relación CUPS-SOAT |
| `soat_tarifas` | Factores UVB/UVT/SMLV y valor 2026 = factor UVB × UVB (FK → `soat_procedimientos`) | hoja TABLA (1.426 códigos) |
| `soat_relacion_cups` | CUPS → código SOAT, PK (cups, código) (FK → `soat_procedimientos`) | `soat/CUPS A SOAT_ANDER_OKANDER.xlsb` (10.300 pares) |

| `soat_grupos` | Grupo quirúrgico de 1.770 procedimientos (FK → `soat_procedimientos`) | `soat/soat_grupos.csv` |
| `soat_grupo_componentes` | Código de tarifa de cada componente por grupo (FK → `soat_tarifas`) | series 39000, 39100, 39117, 39204 y 39301 de la tabla SOAT 2026 |
| `soat_reglas_cirugia` | Porcentajes de bilaterales y cirugías múltiples (num. 48.2, 54.2, 54.5, 69-72) | Decreto 780 de 2016 |

Vistas: `v_tarifarios`, `v_soat_tarifas`, `v_soat_relacion_cups`, `v_soat_grupos`,
`v_soat_reglas_cirugia` (menú «SOAT y tarifas propias»).

**Cirugía SOAT.** El anexo técnico 1 del Decreto 780 de 2016 (`soat/anexo-tecnico1-decreto-780-de-2016.pdf`,
fuera de git por su tamaño) es un PDF escaneado. `extraer_soat_grupos.py` lee de las páginas 2 a 75
el código y el grupo de cada procedimiento (reconoce solo dígitos: plantillas de la fuente Arial y de
la página 3 verificada a ojo, y cuenta los agujeros de cada dígito para no confundir el 8 con 3 o 6).
Controles: confianza de cada dígito, código de 4-5 dígitos, grupo 2-13 o 20-23, orden ascendente por
página y sin repetidos; 81 filas revisadas a ojo sin errores. Correcciones manuales en
`soat/soat_grupos_correcciones.csv` (hoy: 17623, impreso «I7623»). El CSV resultante sí está en git
y es el que usa el ETL.

Al auditar con SOAT, una cirugía no tiene un valor único: la línea del RIPS puede traer la cirugía
completa (cirujano + anestesiólogo + ayudante + sala + materiales; en grupos 20-23 los materiales van
a precio de catálogo), una adicional del mismo acto (50 % de honorarios con igual vía, 75 % con otra
vía, o 75 % + 50 % de sala + 75 % de materiales en otra región), una bilateral o un solo componente.
Si lo cobrado coincide con un escenario (tolerancia de $500 por el redondeo de cada componente) queda
Conforme con el escenario explicado; si supera a todos, Glosa sobre el mayor; si no, Revisar.

La tabla SOAT 2026 no trae la sala del grupo 03 (39205). Se calcula con el decreto: la proporción
UVB/SMLDV es la misma en todos los componentes de la tabla (3,7696, variación < 0,2 %), así que
39205 = 5,97 SMLDV × 3,7696 = 22,50 UVB ($272.475). `tarifarios.completar_componentes` hace lo mismo
con cualquier tabla a la que le falte un componente de cirugía; la columna `origen` de
`soat_tarifas` lo indica («tabla» o «calculado: ...»).

### Versiones de la tarifa SOAT (`soat_versiones.py`)

La tarifa SOAT cambia cada año. La SOAT 2026 del repositorio es la versión por defecto; las de otros
años se suben con la **plantilla prellenada** (botón «Plantilla» en «Versiones de tarifa SOAT» o
`/api/soat/plantilla?version=ID`: trae todos los códigos y factores de la versión elegida y la UVB
resaltada en la hoja TD; se cambian la UVB y los factores que cambien) (web: «Versiones de tarifa SOAT»; consola: `uv run soat_versiones.py cargar archivo.xlsx
--anio 2027 [--uvb 12600]`) con el mismo formato del maestro SOAT (hoja TABLA con los factores y hoja
TD con la UVB). Se guardan en la base de tarifas propias (`soat_versiones`, `soat_version_archivos`,
`soat_version_tarifas`) con su Excel original, año, UVB y estado. Al auditar con SOAT se elige la
versión (`--soat-version ID`) y la UVB se toma de ella (se puede cambiar). La relación CUPS-SOAT y
los grupos quirúrgicos se comparten entre versiones.

### Manuales de tarifas propias (`tarifas_propias.py`)

Parametrización, versionamiento y aplicación de tarifas propias por pagador. Cada **manual** tiene
un código propio (ej. `TAR-PROPIA-2026-01`), nombre y pagador; cada **versión** guarda el tipo de
liquidación base (valor fijo en pesos, o factor % sobre SOAT o ISS), la vigencia (inicio y fin del
contrato), el estado (borrador, activo, inactivo; «vencido» si ya pasó la fecha de fin), el Excel
original (anexo de contratación, descargable) y sus códigos. Subir un Excel a un código existente
crea una versión nueva y conserva las anteriores (glosas de vigencias pasadas).

| Tabla | Contenido |
|---|---|
| `tarifa_manuales` | código (PK), nombre, pagador |
| `tarifa_versiones` | id (PK), manual (FK), versión (única por manual), tipo base, factor %, vigencia, estado, archivo, SHA-256 |
| `tarifa_archivos` | el Excel original de cada versión (FK → versión) |
| `tarifa_items` | versión (FK), tipo (`cups`, `cum`, `insumo`, `material`), código, descripción, tarifa, tipo de liquidación y factor % propios de la fila (únicos por versión, tipo y código) |

Se guardan en la base de `TARIFAS_DB_URL` (PostgreSQL externo, p. ej. Neon o Supabase:
`postgresql://usuario:clave@servidor/base`), independiente de `salida/manual_iss.db` y que sobrevive
a los despliegues de Render; sin esa variable, en `datos/tarifas_propias.db` (SQLite local, fuera de
git). En Render se configura como variable de entorno del servicio.

Excel: una hoja por tipo (CUPS; CUMS o MEDICAMENTOS; INSUMOS; MATERIALES) con Código, Descripción,
Tarifa y, opcionales, «Tipo liquidación» (valor fijo, SOAT, ISS) y «Factor %»; la cabecera puede no
estar en la primera fila. La web muestra una vista previa (conteos, primeras filas, avisos y errores)
antes de guardar y ofrece una plantilla para llenar (hojas vacías con lista desplegable en «Tipo
liquidación» y una hoja INSTRUCCIONES con ejemplos, que no se carga).

```bash
uv run tarifas_propias.py cargar "tarifas propias/TARIFAS PROPIAS.xlsx" --codigo TAR-PROPIA-2026-01 \
    --nombre "Tarifario ejemplo" --tipo-base valor_fijo --inicio 2026-01-01 --fin 2026-12-31 --estado activo
uv run tarifas_propias.py listar
uv run tarifas_propias.py plantilla
```

Al auditar con tarifa propia el auditor elige el manual y la versión (o sube uno nuevo). Cada código
usa su tipo de liquidación (o el del manual); los códigos que no están en el manual usan la base del
manual si es SOAT o ISS, y quedan en Revisar si es valor fijo.

Al auditar se elige el tarifario (en la web se pregunta al cargar el RIPS; en consola `--tarifario
iss|soat|propia`):

- **SOAT**: el CUPS se lleva a código SOAT con la relación; valor = factor UVB × UVB (2026: $12.110;
  para facturas de otro año se indica la UVB de ese año con `--uvb`). Se acepta una diferencia de
  hasta $100 por el redondeo. Si el CUPS tiene varias opciones SOAT: si lo facturado coincide con una,
  Conforme; si supera a todas, Glosa sobre la de mayor valor; si no, Revisar. La cirugía SOAT (grupo
  quirúrgico, Decreto 780 de 2016) aún no se liquida: esas líneas quedan en Revisar.
- **Tarifa propia**: manual y versión elegidos (`--version-propia ID`); compara también insumos y
  materiales (`tipoOS` 01) y medicamentos (CUM).
- Con ISS y SOAT, `--contrato PCT` aplica el porcentaje pactado sobre la tarifa (ej. `-5` = SOAT − 5 %).

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
