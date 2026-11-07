# Estado del trabajo (validación BD vs PDF)

1. `extraer_pdf.py` -> `pdf_tablas.csv` (6.444 filas) y `pdf_textos.csv`.
   `control_extraccion.py`: 100 % igual a `pdf_referencia.csv` en REF, código, valor y PB.
2. `validar_completo.py` -> `validacion_completa.csv`. Quedan 23 diferencias, todas revisadas
   (aceptar) en `correcciones.csv`: 11 falsos positivos de agrupador de la extracción,
   903046 (el PDF omite "TRANSFERRINA") y 11 textos del PDF que no van como notas
   (10 leyendas SOD/NCOC, ahora en la tabla `abreviaturas`, y el cierre de la pág. 207).
3. `etl.py`: aplica `correcciones.csv` (eliminar / cambiar / agregar / aceptar), compara todos
   los campos y falla con `diferencias_pendientes.csv` si hay algo sin revisar.
4. `correcciones_propuestas.csv` aprobado por el usuario (2026-11-05) y fusionado en
   `correcciones.csv` (414 filas). Generador: `proponer_correcciones.py`.
5. `auditoria_visual.py` (semilla 256): págs. 12, 46, 64, 81, 95, 98, 112, 119, 129, 135;
   406 filas revisadas a ojo, 0 diferencias sin explicar -> `auditoria_visual.csv`.

6. `RE_REF` en `etl.py` ahora separa notas de 1 a 4 dígitos (aprobado 2026-11-05):
   50 procedimientos pasan "(1)".."(9)" de la descripción a `ref_nota`.

7. README escrito.
8. Mejoras de modelo: `agrupadores.padre_id` y `nivel` (jerarquia_agrupadores.csv,
   proponer_jerarquia.py; 11 subtítulos que el Excel tenía como nota pasan a agrupador) y
   tabla `abreviaturas`. Ajustes manuales revisados contra el PDF (2026-11-05): 5 títulos
   (págs. 13, 43, 119, 148, 169); la TAC (pág. 116) va bajo RADIOLOGIA por su numeración REF.
9. Vistas: v_tarifas, v_laboratorio, v_imagenes, v_paquetes, v_paquete_componentes,
   v_agrupadores_ruta (y desde el punto 14: v_manual_completo, v_ajustes_valor). Cotizador: cotizar.py (suma tarifas en pesos; avisa, sin aplicar,
   parágrafos de recargos/descuentos, notas y paquetes).

10. cotizar.py aplica recargos/descuentos con opción explícita, desde reglas_tarifas.csv
    (aprobadas 2026-11-05: arts. 25 par. 3, 26 par. 1, 27 pars. 4/12/16, 95 par. 6).
    Art. 134 (aprobado 2026-11-05): --region-134 DEPTO:MUNICIPIO, +15% Capítulo II y +14%
    conjuntos, al final y sobre lo efectivamente pagado; excepciones del par. 2 validadas.
    pruebas_cotizar.py: 20/20 con resultados calculados a mano.

11. Capítulos II-IV pasan a notas tipo `capitulo` (`cambiar tipo` en correcciones.csv).
    Exploración inicial archivada en archivo/exploracion/. `.gitignore` y primer commit.

12. Pruebas y consultas: `consultas_prueba.sql` + `probar_bd.py` (46/46), `consultas_ver.sql` +
    `consultar.py` (ficha por código, paquetes, búsqueda, ajustes de valor, manual completo en
    el orden del Excel). `PROMPT_ACTUALIZACION.md`: prompt para cuando cambie el Excel o el PDF.
    Commits: a949530 (base) y 7700267 (consultas y prompt). Sin remoto configurado.
13. `actualizar.sh` (todo en un comando), `rutas.py` (scripts desde cualquier carpeta; error
    claro si falta la BD), columna `procedimientos.descripcion_busqueda` (búsqueda sin tildes)
    y `validar.py` termina con error si hay hallazgos.
14. Vistas `v_manual_completo` (manual en el orden del Excel, componentes con su paquete) y
    `v_ajustes_valor` (valores con novedad Excel → PDF).
15. Interfaz web `./web.sh` (web/app.py + web/static): menú por vista, búsqueda por código o texto,
    búsqueda global con conteo por vista, detalle por fila y Excel filtrado o completo. Paleta y
    logo SIAIS (#1dbb99, #6d5eac).
16. Despliegue en Render (`render.yaml`, plan gratuito) con clave HTTP Basic (`WEB_CLAVE`,
    usuario `revisor`); probado en un clon limpio: el build genera una BD idéntica a la local.
    Publicado: https://manual-iss-2001.onrender.com (repo PORRIS/manual-iss, se publica con cada push).
17. Novedades completas: `ajustes_pdf` gana `texto_excel` (fila original del Excel) y `pagina_pdf`;
    vistas v_novedades (371) y por categoría (eliminadas 11, texto 280, valor 37, estructura 20,
    aceptadas 23); grupo "Novedades (Excel → PDF)" en la web.
18. Validación consultable: etl.py crea `validacion_resumen` (12 controles, todos OK) y
    `auditoria_visual`; vistas v_validacion_resumen, v_auditoria_visual, v_abreviaturas.
    `control_extraccion.controlar()` reutilizable. Web: grupo "Validación", página "PDF y Excel
    originales" (ver/descargar, SHA-256) y número de página del PDF como enlace.

19. Cotizador: art. 95 par. 7 (`--mismo-acto igual|diferente`, reglas R95P7A/B/C);
    `regiones_134.csv` (departamentos, región de Urabá y ciudades exceptuadas del art. 134) en
    vez de listas fijas en cotizar.py; tablas y vistas v_reglas_tarifas y v_regiones_134;
    página web "Cotizar" (POST /api/cotizar, exportar a Excel). pruebas_cotizar.py 28/28.
    `.idea/` en .gitignore.

20. Auditoría de facturas: `auditar.py` (RIPS JSON y XML DIAN, o líneas digitadas), estados
    sugeridos Conforme/Glosa/Revisar, doble cobro conjunto-componente, notas del procedimiento,
    adicionales por paciente asignados a su línea. Web: "Auditar factura" con decisión del auditor,
    observación e informe Excel. Ejemplos ficticios en `ejemplos/`; pruebas_auditar.py 15/15.
    Lector RIPS con todos los campos (Res. 2275 y 948), episodios, insumos/medicamentos aparte
    (arts. 87-88), contrato "ISS + %", homologacion.csv, repetidos por misma fecha y hora.
    Art. 134 literal a (+30 %, R134A). `examples/` (facturas reales) en .gitignore.
21. Relación CUPS 2026 -> ISS 2001: tabla homologacion_cups y vista v_homologacion_cups desde
    «Relación Manual ISS - CUPS 2026.xlsx» (sin modificarlo); auditar.py la usa para las líneas
    de RIPS; homologacion.csv tiene prioridad. Pruebas: BD 54/54, auditoría 17/17.
22. Revisión de la relación CUPS -> ISS (revision_relacion_cups.py, en el ETL): 210 posibles
    inconsistencias (mismo código en el Manual 53, descripción contenida 48, grupo distinto 86,
    descripción muy distinta 23) como novedad (v_novedades_relacion_revision; v_novedades = 583) y
    en homologacion.csv con estado por_revisar (no se aplican). Auditoría: alerta "Relación
    dudosa" (Revisar). Pruebas: BD 56/56, auditoría 19/19.

23. SOAT 2026 y tarifas propias (tarifarios.py): tablas soat_* y tarifa_* con PK/FK, catálogo
    tarifarios, vistas y menú propio. Auditoría con tarifario a elegir (ISS, SOAT, propia), UVB
    ajustable y contrato %. Con los RIPS reales: CLI38853 cuadra con SOAT 2026 + 4 % (glosa
    sugerida $4.638 contra $72 millones con ISS); FE4158410 con SOAT − 5 % aprox. (o UVB 2025).
    Pruebas: BD 57/57, auditoría 25/25. Dependencia nueva: pyxlsb (lee el .xlsb).

24. Manuales de tarifas propias (HU de parametrización y versionamiento): tarifas_propias.py con
    tarifa_manuales / tarifa_versiones / tarifa_archivos / tarifa_items en la base TARIFAS_DB_URL
    (PostgreSQL externo; SQLite local si no está). Web: página «Manuales de tarifas propias»
    (subir con vista previa, versiones, estado, descargar original, plantilla) y elección de
    manual/versión en la auditoría. Liquidación por manual y por fila (valor fijo o factor sobre
    SOAT/ISS). Decisiones del usuario: SQLite por ahora, cualquiera con la clave administra,
    el auditor elige la versión. Pruebas auditoría 27/27. Dependencia: psycopg[binary].

25. Cirugía SOAT: extraer_soat_grupos.py (OCR de dígitos sobre el PDF escaneado del Decreto 780) ->
    soat/soat_grupos.csv (1.770 procedimientos con grupo; 81 revisados a ojo sin errores);
    tablas soat_grupos, soat_grupo_componentes, soat_reglas_cirugia; auditoría por escenarios
    (completa, adicional igual/otra vía/otra región, bilateral, componente suelto). En FE4158410
    (UVB 2025 = 11.552) 21 de 24 cirugías quedan Conforme. Pruebas: BD 58/58, auditoría 29/29.

26. Sala del grupo 03 (39205) calculada con el decreto (22,50 UVB; proporción UVB/SMLDV 3,7696,
    estable en toda la tabla) y versiones de la tarifa SOAT (soat_versiones.py): SOAT 2026 por
    defecto, subir otros años con vista previa, elegir la versión al auditar. Pruebas: BD 59/59,
    auditoría 30/30.

27. Cirugías ISS en UVR (uvr.py): honorarios (arts. 59-63), derechos de sala (arts. 77-81),
    materiales (art. 85), bilateral (art. 64), múltiples (arts. 65-67), excepciones del art. 65 y
    +30 % del art. 134 literal a; auditoría por escenarios como la cirugía SOAT. En los RIPS reales
    las 60 líneas en UVR ya se comparan (antes ninguna). Pruebas: auditoría 37/37.

## Entorno
- BD: `salida/manual_iss.db`; desde Windows: `\\wsl.localhost\Ubuntu\home\porris\develop\manual_iss\salida\manual_iss.db`.
- Navicat (Windows) no puede abrirla por `\\wsl.localhost` ("database is locked": SQLite no
  tiene bloqueos sobre esa ruta de red). Se usa una copia:
  `C:\Users\Porris\Documents\manual_iss.db`, que `./actualizar.sh` actualiza en cada corrida
  (si Navicat la tiene abierta, la copia falla: cerrarla y repetir).
- No está instalado el cliente `sqlite3`: usar `uv run consultar.py "<SQL>"` o un archivo .sql.
- Los scripts encuentran el proyecto y la BD desde cualquier carpeta (`rutas.py`). Con `uv`, desde
  otra carpeta: `uv run --project ~/develop/manual_iss ~/develop/manual_iss/consultar.py ...`.

## Pendiente
- Confirmar (hoy funcionan así): el +15 % del art. 134 también se aplica a los adicionales por
  paciente del Capítulo II (tecnecio, radioaerosoles); Urabá se declara `URABA:municipio`
  (el Manual no enumera sus municipios).
- Art. 95 par. 7, pendiente de consulta (hoy da error, no calcula): con igual vía y 3 o más
  conjuntos, ¿qué se paga del tercero en adelante? ¿El +55 % bilateral va antes o después de
  los porcentajes del par. 7? El +14 % regional se calcula sobre lo que se paga de cada conjunto
  (ya con el 25 % / 70 %).
- No automatizado en cotizar.py: art. 95 par. 22 (anestesia general en hemodinamia/radiología intervencionista: falta la lista de
  conjuntos a los que aplica).
- Art. 134 literal a (+30 %): aplicado a los arts. 75-76. Pendiente de consulta: 399601
  (perfusionista) y 890503 (junta médica por otro profesional), las consultas de P y P del art. 90
  y los honorarios/derechos de sala del Capítulo I (en UVR, aún sin liquidar en el cotizador).
- Auditoría con RIPS reales (examples/, fuera de git): los valores facturados son 3 a 8 veces la
  tarifa ISS 2001 y la proporción cambia por línea: falta saber con qué tarifa/contrato se liquidan
  (ISS + %, SOAT, propia). Relación CUPS 2026 -> ISS cargada (homologacion_cups): con ella se
  comparan 291/291, 1.351/1.395 y 830/874 líneas de los 3 RIPS reales. Por revisar en la relación:
  210 relaciones por revisar en homologacion.csv (estado por_revisar -> aprobada/rechazada), entre
  ellas la glucometría CUPS 903883 -> ISS 903840 "Glucosa en orina" (sugerido M19275 GLUCOMETRÍA);
  ISS 012205 y 783001 no están en el Manual: registrados como novedad (v_novedades_relacion_cups;
  783001 viene de la fila 3466 del Excel, eliminada porque no está en el PDF pág. 65; 012205 no
  está ni en el Excel ni en el PDF). El doble cobro se sugiere como Revisar (confirmado por el usuario).
- SOAT: no modelado: procedimientos incruentos en sala especial (num. 51, 45 %), perfusionista
  en grupos 20-23 (num. 47.2), anestesia en procedimientos de diagnóstico (50 %, num. 47.1.3), regla
  72.2 del ayudante con distinta especialidad. Confirmar tolerancias ($100 por código, $500 por
  cirugía) y la regla de varias opciones SOAT por CUPS.
- Tarifas propias y versiones SOAT subidas: por decisión del usuario se guardan en SQLite
  (datos/tarifas_propias.db). En Render gratuito ese archivo se borra en cada despliegue o reinicio:
  lo subido allí se pierde (la SOAT 2026 por defecto no, porque viene en el repositorio). Para conservarlos: base PostgreSQL (Neon o Supabase) en la variable TARIFAS_DB_URL.
- ISS UVR, no modelado: sala de recuperación (art. 84, depende de complejidad y de pasar 6 horas),
  materiales de cirugías de más de 170 UVR (según consumo), derechos de sala en cirugías múltiples
  por diferente vía (la norma no los fija), descuentos del art. 77 par. 4 (instrumentación o
  enfermería a cargo de la EPS) y accesorios del par. 7. El cotizador aún no suma cirugías en UVR.
- liquidar.py (no se modifica por instrucción del usuario) no reconoce «UNI Ó BILATERAL» con tilde y
  aplicaría el +75 % bilateral a esos códigos (ej. 797501); uvr.py sí lo reconoce.
- Opcional: exportar el manual completo a Excel (ya disponible desde la web).

## Orden para regenerar
```bash
./actualizar.sh          # ETL + validaciones + copia para Navicat
./actualizar.sh --pdf    # además extrae el PDF (solo si cambió el PDF o el extractor)
```
Si cambia el Excel o el PDF: usar PROMPT_ACTUALIZACION.md.
