# Prompt para actualizar la BD cuando cambie el Excel o el PDF

Copie todo lo que está debajo de la línea, complete los datos entre corchetes y péguelo en
Claude Code abierto en la carpeta del proyecto.

---

Proyecto: base de datos del Manual Tarifario ISS 2001 (Acuerdo 256 de 2001, Colombia), ya
construida y validada contra el PDF. Entorno: WSL Ubuntu, Python con `uv` (`uv add` / `uv run`,
nunca pip). BD: `salida/manual_iss.db`; copia para Navicat en
`/mnt/c/Users/Porris/Documents/manual_iss.db`.

## Qué cambió
- Archivo nuevo: [PDF / Excel / ambos]
- Ya reemplacé el archivo con el mismo nombre: [sí / no; está en: RUTA]
- Qué sé del cambio: [p. ej. "nueva versión del manual con tarifas 2026", "corregí filas del
  Excel", "no sé"]

## Lee primero (no rehagas lo que ya está)
- `ESTADO.md`: qué está hecho y qué está pendiente.
- `README.md`: flujo, formato de `correcciones.csv` (eliminar / cambiar / agregar / aceptar) y la
  sección «Decisiones tomadas» (son decisiones mías: aplícalas igual en los casos idénticos).
- `correcciones.csv`, `reglas_tarifas.csv`, `jerarquia_agrupadores.csv` y `AJUSTES` en
  `proponer_jerarquia.py`: revisiones hechas a mano, con página y motivo.
- La versión anterior de los archivos fuente está en git (`git show HEAD:<archivo>`).

## Tareas (en este orden; resumen al terminar cada una)

0. **Respaldo.** Si hay cambios sin commit, muéstramelos y pregúntame antes de hacer un commit
   de respaldo. Si el archivo nuevo no está en su lugar, pregúntame dónde está; no lo busques
   por todo el disco.

1. **Diagnóstico del cambio. Detente al terminar y espera mi visto bueno.**
   - Si cambió el PDF: `uv run extraer_pdf.py` y compara con la versión anterior
     (`git diff` de `pdf_tablas.csv` y `pdf_textos.csv`). Resume: procedimientos nuevos,
     eliminados, con otro valor, con otra descripción o nota, y textos cambiados.
     `control_extraccion.py` compara contra el PDF viejo: úsalo como lista de cambios, no como
     error. Comprueba que la extracción sigue siendo correcta: si el diseño del PDF cambió,
     renderiza las páginas afectadas (`page.to_image()`) y míralas antes de confiar en ella.
   - Si cambió el Excel: compara la versión anterior (`git show HEAD:manual_iss.xls`) con la
     nueva, fila por fila. Resume las filas insertadas, borradas y cambiadas, y si se corrió la
     numeración (`fila_excel`).
   - Dame conteos y como máximo 20 ejemplos; el detalle va a CSV.

2. **Reubicar las correcciones existentes.** Si se corrió la numeración del Excel, propón la
   nueva `fila_excel` de cada fila de `correcciones.csv`, emparejando por código y texto, en
   `correcciones_reubicadas.csv`. Marca las que ya no aplican (el cambio ya viene en la fuente
   o la fila desapareció) y las dudosas. No modifiques `correcciones.csv` sin mi aprobación.

3. **ETL y propuesta de correcciones.** Corre `uv run etl.py`. Si falla, clasifica
   `diferencias_pendientes.csv` y genera `correcciones_propuestas.csv` en el mismo formato:
   - Casos idénticos a decisiones ya tomadas: propón la misma acción y di cuál decisión usas.
   - Casos nuevos: propón la acción con página y motivo; los ambiguos (p. ej. un error de
     redacción evidente en el PDF), márcalos «DECIDIR:» y pregúntame.
   - Muéstrame los conteos por campo, tipo (MENOR / MAYOR) y acción, y 15 ejemplos MAYOR.
   - **No fusiones nada hasta que yo apruebe.** Después de fusionar, regenera la jerarquía
     (`uv run proponer_jerarquia.py`) si cambiaron agrupadores y vuelve a correr el ETL hasta
     que termine en OK.

4. **Revisar lo que depende del PDF** (solo si cambió el PDF):
   - `reglas_tarifas.csv`: comprueba cada cifra, porcentaje y página contra el PDF nuevo.
     No cambies ninguna regla sin mostrarme el texto nuevo del parágrafo y pedirme aprobación.
     Si cambian, actualiza los valores esperados de `pruebas_cotizar.py`.
   - `AJUSTES` de `proponer_jerarquia.py`: comprueba que las páginas y los títulos sigan
     existiendo.
   - `consultas_prueba.sql`: actualiza los `@esperado` que cambien por el PDF nuevo e indica
     por qué cambia cada uno.

5. **Validación final.**
   - `./actualizar.sh` (ETL, `validar.py`, `validar_completo.py`, `probar_bd.py`,
     `pruebas_cotizar.py` y copia para Navicat): muéstrame el resumen de su salida.
   - Auditoría visual: 10 páginas con semilla fija más todas las páginas con cambios;
     compara a ojo cada fila con la BD y reporta cuántas revisaste y cualquier diferencia.
   - Actualiza `ESTADO.md` y, si cambió el flujo o hay decisiones nuevas, el README.
   - Propón el mensaje del commit y espera mi aprobación antes de hacerlo.

## Reglas
- El PDF es la fuente oficial; el Excel da la estructura. No modifiques el PDF, el XLS ni
  `manual_iss.csv` (salvo reemplazarlos por la versión nueva que yo te dé), ni `liquidar.py`.
- Nada se sobrescribe sin revisión: todo cambio de datos entra por `correcciones.csv`, con
  página del PDF y motivo.
- Si una decisión es ambigua, no la tomes tú: anótala y pregúntame.
- No cambies la estructura de las tablas sin explicarme por qué; agregar columnas está bien.
- Economía de tokens: nunca imprimas archivos completos ni miles de filas; conteos y como
  máximo 20 filas de ejemplo; el detalle va a CSV.
- Si la sesión se va a cortar, deja el avance en `ESTADO.md` para seguir después.

## Criterio de terminado
- La extracción del PDF nuevo está verificada (diff revisado y páginas con cambios vistas).
- Toda diferencia BD-PDF está resuelta o en `correcciones.csv` con página y motivo.
- `uv run etl.py` termina en OK y las cuatro validaciones pasan.
- La auditoría visual no muestra diferencias sin explicar.
- `ESTADO.md` actualizado y commit hecho con mi aprobación.
