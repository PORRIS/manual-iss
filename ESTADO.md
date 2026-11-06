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
   v_agrupadores_ruta. Cotizador: cotizar.py (suma tarifas en pesos; avisa, sin aplicar,
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
- No automatizado en cotizar.py: art. 95 par. 7 (varios conjuntos en un mismo acto) y
  par. 22 (anestesia general en hemodinamia/radiología intervencionista: falta la lista de
  conjuntos a los que aplica).
- Opcional: subir el repositorio a un remoto; exportar el manual completo a Excel.

## Orden para regenerar
```bash
./actualizar.sh          # ETL + validaciones + copia para Navicat
./actualizar.sh --pdf    # además extrae el PDF (solo si cambió el PDF o el extractor)
```
Si cambia el Excel o el PDF: usar PROMPT_ACTUALIZACION.md.
