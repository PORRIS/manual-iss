CREATE VIEW v_honorarios_cirugia AS
SELECT p.id, p.articulo, g.nombre AS agrupador, p.codigo, p.descripcion,
       p.valor AS uvr,
       p.valor * (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41101') AS cirujano,
       p.valor * (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41201') AS anestesia_si_aplica,
       CASE WHEN p.valor >= 50
            THEN p.valor * (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41301')
       END AS ayudante_si_se_causa
FROM procedimientos p
LEFT JOIN agrupadores g ON g.id = p.agrupador_id
WHERE p.articulo <= 18 AND p.tipo = 'con_valor' AND p.unidad = 'UVR';

-- Ruta completa de cada agrupador (título > subtítulo > ...), desde agrupadores.padre_id.
-- titulo: el agrupador raíz; subtitulo: el de nivel 2 (p. ej. "Cirugía Programada").
CREATE VIEW v_agrupadores_ruta AS
WITH RECURSIVE r(id, raiz_id, titulo, subtitulo, prof, ruta) AS (
    SELECT id, id, nombre, NULL, 1, nombre FROM agrupadores WHERE padre_id IS NULL
    UNION ALL
    SELECT g.id, r.raiz_id, r.titulo, COALESCE(r.subtitulo, g.nombre), r.prof + 1,
           r.ruta || ' > ' || g.nombre
    FROM agrupadores g JOIN r ON g.padre_id = r.id
)
SELECT g.id, g.articulo, g.nombre, g.nivel, g.padre_id, r.raiz_id, r.titulo, r.subtitulo, r.ruta
FROM agrupadores g JOIN r ON r.id = g.id;

-- Lista de tarifas unificada: todos los procedimientos con su sección del Manual,
-- la ruta de agrupadores y, para los componentes, el código del paquete al que pertenecen.
-- unidad: UVR (arts. 1-18, se liquidan con liquidar.py), pesos, pesos_por_uvr (art. 59), factor (art. 91).
CREATE VIEW v_tarifas AS
SELECT p.id, p.articulo,
       CASE
           WHEN p.articulo <= 18 THEN 'Cirugía y procedimientos (UVR)'
           WHEN p.articulo = 25 THEN 'Laboratorio clínico'
           WHEN p.articulo = 26 THEN 'Anatomía patológica'
           WHEN p.articulo = 27 THEN 'Imagenología'
           WHEN p.articulo BETWEEN 28 AND 41 THEN 'Estudios y procedimientos por especialidad'
           WHEN p.articulo IN (42, 56) THEN 'Internación'
           WHEN p.articulo = 59 THEN 'Valor de la UVR'
           WHEN p.articulo BETWEEN 62 AND 86 THEN 'Servicios profesionales, salas y materiales'
           WHEN p.articulo = 89 THEN 'Unidad de nefrología'
           WHEN p.articulo = 90 THEN 'Protección específica y detección temprana'
           WHEN p.articulo = 91 THEN 'Oxígeno'
           WHEN p.articulo = 92 THEN 'Hospital de día'
           WHEN p.articulo = 93 THEN 'Traslado en ambulancia'
           WHEN p.articulo = 95 THEN 'Conjuntos de atención (paquetes)'
           ELSE 'Otros'
       END AS seccion,
       r.titulo, r.ruta AS agrupador_ruta, g.nombre AS agrupador,
       p.codigo_manual AS ref, p.codigo, p.marca, p.descripcion, p.descripcion_busqueda,
       p.ref_nota, p.tipo,
       pq.codigo AS paquete_codigo, p.unidad, p.valor,
       CASE WHEN p.unidad = 'UVR'
            THEN p.valor * (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41101')
       END AS honorario_cirujano
FROM procedimientos p
LEFT JOIN agrupadores g ON g.id = p.agrupador_id
LEFT JOIN v_agrupadores_ruta r ON r.id = p.agrupador_id
LEFT JOIN procedimientos pq ON pq.id = p.padre_id;

-- Laboratorio clínico (art. 25) y anatomía patológica (art. 26), en pesos.
CREATE VIEW v_laboratorio AS
SELECT articulo, seccion, titulo AS area, agrupador, ref, codigo, marca, descripcion, ref_nota, valor
FROM v_tarifas WHERE articulo IN (25, 26) AND tipo = 'con_valor';

-- Imagenología (art. 27), en pesos; modalidad = título raíz (RADIOLOGIA, MEDICINA NUCLEAR, ...).
CREATE VIEW v_imagenes AS
SELECT titulo AS modalidad, agrupador_ruta, ref, codigo, marca, descripcion, ref_nota, valor
FROM v_tarifas WHERE articulo = 27 AND tipo = 'con_valor';

-- Conjuntos de atención por tarifa integral (art. 95): un paquete por fila.
CREATE VIEW v_paquetes AS
SELECT p.codigo, p.descripcion, p.valor, p.titulo, p.agrupador_ruta, p.ref_nota,
       COUNT(c.id) AS n_componentes,
       GROUP_CONCAT(c.codigo, ', ') AS componentes
FROM v_tarifas p
LEFT JOIN procedimientos c ON c.padre_id = p.id
WHERE p.articulo = 95 AND p.tipo = 'con_valor'
GROUP BY p.id;

-- ¿Qué paquete cubre un procedimiento? Un componente (CUPS) por fila, con su paquete.
CREATE VIEW v_paquete_componentes AS
SELECT c.codigo AS componente_codigo, c.descripcion AS componente_descripcion,
       p.codigo AS paquete_codigo, p.descripcion AS paquete_descripcion,
       p.valor AS paquete_valor, r.ruta AS agrupador_ruta
FROM procedimientos c
JOIN procedimientos p ON p.id = c.padre_id
LEFT JOIN v_agrupadores_ruta r ON r.id = p.agrupador_id
WHERE p.articulo = 95;

-- Manual completo en el orden del Excel: artículos, agrupadores, procedimientos, componentes
-- (con código, descripción y valor de su paquete) y notas. Las 3 notas agregadas desde el PDF
-- no tienen fila del Excel: van después de su procedimiento (orden = fila + 0.5).
CREATE VIEW v_manual_completo AS
SELECT * FROM (
    SELECT a.fila_excel AS orden, 'ARTICULO' AS tipo_fila, a.numero AS articulo,
           NULL AS nivel, NULL AS agrupador_ruta, NULL AS ref, NULL AS pb, NULL AS codigo,
           a.texto AS descripcion, NULL AS ref_nota, NULL AS valor, NULL AS unidad,
           NULL AS paquete, NULL AS desc_paquete, NULL AS valor_paquete, a.fila_excel
    FROM articulos a
    UNION ALL
    SELECT g.fila_excel, 'AGRUPADOR', g.articulo, g.nivel, r.ruta, NULL, NULL, NULL,
           g.nombre, NULL, NULL, NULL, NULL, NULL, NULL, g.fila_excel
    FROM agrupadores g LEFT JOIN v_agrupadores_ruta r ON r.id = g.id
    UNION ALL
    SELECT p.fila_excel,
           CASE p.tipo WHEN 'componente' THEN 'COMPONENTE' ELSE 'PROCEDIMIENTO' END,
           p.articulo, NULL, r.ruta, p.codigo_manual, p.marca, p.codigo,
           p.descripcion, p.ref_nota, p.valor, p.unidad,
           pa.codigo, pa.descripcion, pa.valor, p.fila_excel
    FROM procedimientos p
    LEFT JOIN v_agrupadores_ruta r ON r.id = p.agrupador_id
    LEFT JOIN procedimientos pa ON pa.id = p.padre_id
    UNION ALL
    SELECT COALESCE(n.fila_excel, n.despues_de_fila + 0.5), UPPER(n.tipo), n.articulo, NULL,
           r.ruta, NULL, NULL, NULL, n.texto, NULL, NULL, NULL, NULL, NULL, NULL, n.fila_excel
    FROM notas n LEFT JOIN v_agrupadores_ruta r ON r.id = n.agrupador_id
)
ORDER BY orden;

-- Valores con novedad: procedimientos cuyo valor del Excel se corrigió con el del PDF
-- (correcciones.csv -> ajustes_pdf), de mayor a menor diferencia absoluta.
CREATE VIEW v_ajustes_valor AS
SELECT
    p.codigo,
    p.codigo_manual                                            AS ref,
    p.descripcion,
    p.articulo,
    p.unidad,
    CAST(a.antes AS REAL)                                      AS valor_excel,
    CAST(a.despues AS REAL)                                    AS valor_pdf,
    ROUND(CAST(a.despues AS REAL) - CAST(a.antes AS REAL), 4)  AS diferencia,
    p.valor                                                    AS valor_en_bd,  -- = valor_pdf
    a.motivo,
    p.fila_excel
FROM ajustes_pdf a
JOIN procedimientos p ON p.fila_excel = CAST(a.fila_excel AS INTEGER)
WHERE a.campo = 'valor'
ORDER BY ABS(CAST(a.despues AS REAL) - CAST(a.antes AS REAL)) DESC;

-- ===================================================================== NOVEDADES
-- Todo lo que la revisión cambió del Excel para dejarlo igual al PDF (correcciones.csv ->
-- ajustes_pdf). texto_excel: contenido original de la fila del Excel.
CREATE VIEW v_novedades AS
SELECT
    CASE
        WHEN a.accion = 'eliminar' THEN 'Fila eliminada'
        WHEN a.accion = 'agregar'  THEN 'Nota agregada desde el PDF'
        WHEN a.accion = 'aceptar'  THEN 'Diferencia aceptada (sin cambio)'
        WHEN a.campo  = 'valor'    THEN 'Cambio de valor'
        WHEN a.campo  = 'codigo'   THEN 'Cambio de código'
        WHEN a.campo  = 'tipo'     THEN 'Cambio de clasificación'
        ELSE 'Cambio de texto'
    END                                   AS categoria,
    a.accion,
    a.campo,
    CAST(a.fila_excel AS INTEGER)         AS fila_excel,
    a.codigo,
    a.texto_excel,
    CASE WHEN a.antes IN ('existe', 'fila del Excel') THEN NULL ELSE a.antes END AS antes,
    a.despues,
    CAST(a.pagina_pdf AS INTEGER)         AS pagina_pdf,
    a.motivo
FROM ajustes_pdf a
ORDER BY CASE WHEN a.fila_excel IS NULL THEN 1 ELSE 0 END, CAST(a.fila_excel AS INTEGER), a.campo;

-- Filas del Excel que no pasaron a la BD (no existen en el PDF, duplicadas o cabeceras).
CREATE VIEW v_novedades_eliminadas AS
SELECT fila_excel, codigo, texto_excel, pagina_pdf, motivo
FROM v_novedades WHERE accion = 'eliminar';

-- Textos corregidos con el del PDF: descripciones, notas, agrupadores y notas de referencia.
CREATE VIEW v_novedades_texto AS
SELECT CASE campo WHEN 'descripcion' THEN 'Descripción' WHEN 'texto' THEN 'Nota / texto'
                  WHEN 'nombre' THEN 'Agrupador' WHEN 'ref_nota' THEN 'Nota de referencia'
                  ELSE campo END AS que_cambio,
       fila_excel, codigo, antes AS texto_excel_original, despues AS texto_pdf, pagina_pdf, motivo
FROM v_novedades WHERE categoria = 'Cambio de texto';

-- Cambios de clasificación (nota -> agrupador o capítulo), de código y notas agregadas.
CREATE VIEW v_novedades_estructura AS
SELECT categoria, fila_excel, codigo, texto_excel, antes, despues, pagina_pdf, motivo
FROM v_novedades
WHERE categoria IN ('Cambio de clasificación', 'Cambio de código', 'Nota agregada desde el PDF');

-- Diferencias Excel/PDF revisadas que se dejaron como están (falsos positivos y textos del
-- PDF que no van en la BD).
CREATE VIEW v_novedades_aceptadas AS
SELECT campo, fila_excel, codigo, texto_excel, despues AS texto_pdf, pagina_pdf, motivo
FROM v_novedades WHERE accion = 'aceptar';

-- ===================================================================== VALIDACIÓN
-- Resumen de la validación BD vs PDF (lo calcula etl.py en cada corrida).
CREATE VIEW v_validacion_resumen AS
SELECT orden, grupo, control, pdf, bd, resultado, detalle FROM validacion_resumen ORDER BY orden;

-- Abreviaturas de las leyendas al pie de tabla del PDF.
CREATE VIEW v_abreviaturas AS
SELECT abreviatura, significado, paginas_pdf FROM abreviaturas ORDER BY abreviatura;

-- Auditoría visual: páginas al azar revisadas a ojo contra la imagen del PDF.
CREATE VIEW v_auditoria_visual AS
SELECT pagina AS pagina_pdf, filas_revisadas, diferencias_sin_explicar, observacion
FROM auditoria_visual ORDER BY pagina;
