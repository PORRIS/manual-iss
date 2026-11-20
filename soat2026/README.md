# Manual Tarifario SOAT 2026 (UVB) — base de datos nueva

Base normalizada del PDF `manual tarifario sota/Manual-Tarifario-SOAT-2026-uvb.pdf` (102 páginas,
Decreto 2423 de 1996 actualizado a 2026 en SMLDV, UVT y UVB). Es **independiente** de
`salida/manual_iss.db`: no lee ni escribe sus tablas (solo la consulta, en modo lectura, para un
control cruzado opcional).

- BD: `soat2026/salida/manual_soat_2026.db` (copia para Navicat: `C:\Users\Porris\Documents\manual_soat_2026.db`)
- Excel organizado: `soat2026/salida/manual_soat_2026.xlsx`
- Todo se regenera con `soat2026/actualizar.sh` (~30 s); `salida/` no va al repositorio.

## Flujo

```
PDF ──extraer.py──> salida/items.csv (elementos en el orden del PDF) + avisos_extraccion.txt
                         │
ajustes.csv ─────────────┴──etl.py──> manual_soat_2026.db ──exportar_excel.py──> .xlsx
                                      (16 controles; si alguno falla, termina con error)
pruebas.py: 18 pruebas con valores leídos a mano en el PDF
```

`extraer.py` lee el texto nativo del PDF por la posición de cada palabra (no usa OCR): código en el
margen izquierdo, descripción en letra 7,4 (el código va alineado con su última línea), grupo
quirúrgico en el capítulo III y las seis columnas de valor desde el capítulo IV. Descarta el
encabezado y pie del editor, sus anotaciones al margen («RECUERDE FACTURAR», «ARTICULO. 48 - 1»...)
y los errores de hoja de cálculo que trae el PDF (`#N/D`, `#######`, `#¡VALOR!`).

## Tablas

| Tabla | Contenido |
|---|---|
| `capitulos` | I a V con su título (I, II y IV no traen título en el PDF) |
| `articulos` | 89 artículos: `numero`, `capitulo_id`, `nombre` (corto, para menús), `texto` (del PDF), `tipo_tarifa` (`grupo_quirurgico` / `smldv_uvt_uvb` / vacío si es solo texto), `n_procedimientos` |
| `agrupadores` | 636 títulos y subtítulos: `articulo`, `padre_id`, `nivel`, `numeral` («1», «a»...), `nombre`. Es la ruta con sus hijos: p. ej. `ÓRGANOS INTRACRANEALES > CRANEOTOMÍAS PARA ...` |
| `procedimientos` | 3.281 códigos únicos: `descripcion`, `articulo`, `agrupador_id` (el más profundo), `grupo_quirurgico` (cap. III, 1.771) o `factor_smldv`, `valor_smldv`, `factor_uvt`, `valor_uvt`, `factor_uvb`, `valor_uvb` (cap. IV y V, 1.510); `descripcion_busqueda` sin tildes |
| `notas` | 137 textos: `tipo` = `paragrafo`, `inciso` (texto que sigue a un parágrafo), `literal`, `nota`, `texto`, `titulo`, `titulo_seccion`, `preambulo`; con artículo y agrupador |
| `parametros` | SMLMV 1.750.905, SMLDV 58.363, UVT 52.374, UVB 12.110 (portada del PDF) |
| `tarifas_grupo` | Por grupo quirúrgico, el código de cirujano, anestesiólogo, ayudante (grupo 6+), sala (art. 49) y materiales (art. 55, grupos 2-13): 72 filas, base del cotizador |
| `observaciones_pdf` | Datos del propio PDF que no cuadran (ver abajo) |
| `ajustes` | Ajustes manuales aplicados desde `ajustes.csv` |
| `validacion` | Resultado de los controles del ETL |

## Vistas

| Vista | Para qué |
|---|---|
| `v_tarifas` | Lista única de tarifas: capítulo, artículo, ruta de agrupadores, código, descripción, grupo o valores |
| `v_cirugias` | Cirugías del cap. III con el valor UVB de cirujano, anestesiólogo, ayudante, sala y materiales de su grupo |
| `v_tarifas_grupo` | Tabla de valores por grupo quirúrgico y concepto |
| `v_agrupadores_ruta` | Ruta completa de cada agrupador, con número de hijos y de procedimientos |
| `v_articulos` | Artículos con conteos (procedimientos, agrupadores, parágrafos) |
| `v_notas` | Notas y parágrafos con su artículo y ruta |
| `v_manual_completo` | Todo el manual en el orden del PDF (capítulos, artículos, agrupadores, procedimientos, notas) |
| `v_validacion`, `v_observaciones_pdf` | Controles y observaciones |

## Controles (etl.py)

Cobertura (los 3.291 códigos del margen izquierdo del PDF = 3.281 procedimientos + 10 citados en el
parágrafo 3 del art. 23), artículos 1 a 89, grupos válidos (1-13 y 20-23), cap. III todo con grupo,
agrupadores sin vacíos y del mismo artículo, tarifas por grupo completas, aritmética
`factor x unidad ≈ valor` (redondeo a la centena del art. 89), proporción UVB/SMLDV (3,7695 en toda
la tabla), **relectura** del PDF por otro método (código, descripción, factor y valor UVB de cada
procedimiento aparecen en su página) y dos cruces externos:

- Grupos contra el Decreto 780 (`soat/soat_grupos.csv`): 1.770 en común, **0 distintos**
  (15110 «Sutura herida, excepto cara», grupo 5, solo está en este PDF).
- Factor UVB contra la tabla SOAT 2026 del proyecto (.xlsb): 1.427 en común, 1 distinto.

## Observaciones del PDF (se dejan como vienen)

| Código | Qué pasa |
|---|---|
| 23106 Bloqueo de nervios pudendos | Sin tarifa: SMLDV «$ -», UVT 0,00, UVB 0 |
| 25123, 25128 | Columna UVT vacía (0,00 y «$ -»); SMLDV y UVB sí tienen valor |
| 39205 Sala grupo 03 | El PDF dice 22,52 UVB; la tabla .xlsb dice 22,50 |

## Ajustes manuales (`ajustes.csv`)

Una fila por texto del PDF que la regla automática clasifica mal: `pagina`, `texto_inicio`,
`accion=tipo`, `valor` (`titulo`, `texto`, `ignorar`, o el tipo de agrupador `numerado`,
`mayusculas`, `dos_puntos`, `literal`) y `motivo`. Hoy son 2 (rótulo «ESTANCIAS» del art. 47 y el
subtítulo de departamentos del art. 64). Si un ajuste deja de coincidir, el ETL falla.

Los nombres cortos de algunos artículos (`NOMBRES` en `etl.py`) son etiquetas para menús; el texto
del artículo queda tal cual en `articulos.texto`.

## Menú en la web (`./web.sh`)

Grupo **«Manual SOAT 2026 (UVB)»** en el menú lateral (solo aparece si la BD existe):

- **Resumen y descarga Excel** (`#/soat2026`): conteos, valores 2026 (SMLMV, SMLDV, UVT, UVB),
  capítulos, estado de la validación, botón **Descargar Excel** (el mismo libro de
  `exportar_excel.py`, generado al momento: `/api/soat2026/excel`) y el PDF de origen (ver/descargar).
- Vistas consultables, cada una con búsqueda por código o texto y Excel filtrado o completo:
  Tarifas SOAT 2026, Cirugías por grupo, Valores por grupo quirúrgico, Capítulos y artículos,
  Agrupadores (rutas), Parágrafos y notas, Manual SOAT completo, Observaciones del PDF y Validación.
- La columna «Pág. PDF» abre el PDF SOAT en esa página (`/fuentes/soat2026#page=N`).

En `web/app.py` estas vistas llevan `bd="soat2026"` y el nombre real de la vista en `vista`
(los ids empiezan por `s26_`); `BASES` dice qué archivo abre cada `bd`.

## Cotizador (`cotizar.py`, web «Cotizar SOAT 2026»)

```bash
uv run soat2026/cotizar.py 19001 21101x2                       # procedimientos con valor
uv run soat2026/cotizar.py 1102 1101:diferente_via --region META
uv run soat2026/cotizar.py 13350:incruenta 1101:bilateral:sin_ayudante --uvb 11552
uv run soat2026/pruebas_cotizar.py                              # 19 pruebas calculadas a mano
```

Una cotización es un paciente y un acto. Valor = factor UVB x UVB (por defecto $12.110), ajustado
a la centena (art. 89).

| Caso | Cómo se liquida |
|---|---|
| Procedimiento con valor | Factor UVB x UVB x cantidad. `bilateral` +75 % (art. 70 par. 2; conjuntos art. 64 par. 3); `anestesia` +50 % de la tarifa (art. 48 a.2) |
| Cirugía (grupo) | Cirujano + anestesiólogo + ayudante (desde el grupo 06) + sala (art. 49) + materiales (art. 55; grupos 20-23 a precio de catálogo, no se cotizan). Opciones: `bilateral` (honorarios +75 %, sala +50 %, materiales +75 %), `sin_anestesiologo`, `sin_ayudante`, `perfusionista` (39129, grupos 20-23), `incruenta` (art. 52: sala 45 %, materiales 39305) |
| Varias cirugías | La mayor (mayor honorario de cirujano) al 100 %. Adicional `igual_via` (art. 71): honorarios 50 %; `diferente_via` (art. 72): honorarios 75 %, sala 50 %, materiales 75 %; `otra_especialidad` (art. 73): cirujano 100 %, anestesiólogo 75 %, ayudante 50 % solo de la adicional de mayor grupo, sala 50 % |
| Varios conjuntos (art. 64 par. 4 b) | El mayor al 100 %; cada otro 25 % (igual vía) o 70 % (diferente vía u otra especialidad) |
| Región (art. 86) | +25 % honorarios de cirugía, consultas, valoraciones y cuidado intrahospitalario (literal a); +15 % capítulo IV (literal b). No en Arauca, Florencia, Riohacha, Sincelejo, Villavicencio ni Yopal |

**Interpretaciones aprobadas por el usuario (2026-11-20):** incruenta = 45 % de la sala del grupo (como en la auditoría
SOAT); en igual vía y en otra especialidad no se suman sala ni materiales de la adicional (los arts.
49 y 55 solo nombran «distinta región» y «diferente región»); el bilateral se aplica antes del
porcentaje de adicional; el +25 % del art. 86 a no se aplica a sala, materiales, perfusionista,
junta médica (39144) ni sutura (39146); un conjunto con cirugías sueltas va como mayor y las
cirugías como adicionales (art. 64 par. 4 a) según la relación que se elija.
