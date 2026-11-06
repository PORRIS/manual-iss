-- Consultas para ver la data de salida/manual_iss.db.
-- Edite los valores de cada WITH y ejecute:   uv run consultar.py consultas_ver.sql
-- (o abra el archivo en DB Browser for SQLite / DBeaver).

-- ## Ficha completa de uno o varios códigos (CUPS o REF interna); ('*') = todos
WITH filtro(codigo) AS (
    VALUES ('020101'), ('549001'), ('C40402'), ('512104')
)
SELECT
    p.codigo,
    p.codigo_manual                                   AS ref,
    p.marca                                           AS pb,
    p.descripcion,
    p.ref_nota,
    p.tipo,                                           -- con_valor | componente | sin_valor
    p.valor,
    p.unidad,                                         -- UVR | pesos | pesos_por_uvr | factor
    t.honorario_cirujano,                             -- solo UVR: valor x $1.270
    CASE WHEN p.unidad = 'UVR' THEN p.valor *
         (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41201') END AS anestesia_si_aplica,
    CASE WHEN p.unidad = 'UVR' AND p.valor >= 50 THEN p.valor *
         (SELECT pesos_por_uvr FROM parametros WHERE codigo_uvr = 'S41301') END AS ayudante_si_se_causa,
    p.articulo,
    t.seccion,
    t.agrupador_ruta,                                 -- título > subtítulo > ...
    pa.codigo                                         AS paquete,
    pa.descripcion                                    AS desc_paquete,
    pa.valor                                          AS valor_paquete,
    (SELECT COUNT(*) FROM procedimientos h WHERE h.padre_id = p.id)          AS n_componentes,
    (SELECT GROUP_CONCAT(n.texto, ' | ') FROM notas n
      WHERE n.procedimiento_id = p.id)                                       AS notas,
    (SELECT GROUP_CONCAT(n.texto, ' | ') FROM notas n
      WHERE n.procedimiento_id = p.padre_id)                                 AS notas_del_paquete,
    (SELECT GROUP_CONCAT(a.accion || ' ' || a.campo || ': ' ||
                         COALESCE(a.antes, '∅') || ' → ' || COALESCE(a.despues, '∅'), '; ')
       FROM ajustes_pdf a
      WHERE CAST(a.fila_excel AS INTEGER) = p.fila_excel)                    AS ajustes_pdf,
    p.fila_excel
FROM procedimientos p
JOIN v_tarifas t           ON t.id  = p.id
LEFT JOIN procedimientos pa ON pa.id = p.padre_id
WHERE '*' IN (SELECT codigo FROM filtro)
   OR p.codigo        IN (SELECT codigo FROM filtro)
   OR p.codigo_manual IN (SELECT codigo FROM filtro)
ORDER BY p.codigo, p.fila_excel;

-- ## Paquetes (art. 95) con sus componentes y la tarifa individual de cada componente
WITH filtro(codigo) AS (
    VALUES ('C40818'), ('C40819'), ('C40402')
)
SELECT
    pa.codigo                                         AS paquete,
    pa.descripcion                                    AS desc_paquete,
    pa.valor                                          AS valor_paquete,
    c.codigo                                          AS componente,
    c.marca                                           AS pb,
    c.descripcion                                     AS desc_componente,
    (SELECT x.valor || ' ' || x.unidad || ' (art. ' || x.articulo || ')'
       FROM procedimientos x
      WHERE x.codigo = c.codigo AND x.tipo = 'con_valor'
      ORDER BY x.articulo LIMIT 1)                    AS tarifa_individual
FROM procedimientos pa
JOIN procedimientos c ON c.padre_id = pa.id
WHERE pa.codigo IN (SELECT codigo FROM filtro)
ORDER BY pa.codigo, c.fila_excel;

-- ## Buscar por texto en la descripción (sin distinguir mayúsculas ni tildes)
-- Escriba el texto con o sin tildes: 'cirugía', 'CIRUGIA' y 'cirugia' dan lo mismo.
WITH filtro(texto) AS (VALUES ('%colecistectomía%')),
     buscado(t) AS (
    SELECT UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
           REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(texto,
           'á','a'),'é','e'),'í','i'),'ó','o'),'ú','u'),'ü','u'),'ñ','n'),
           'Á','A'),'É','E'),'Í','I'),'Ó','O'),'Ú','U'),'Ü','U'),'Ñ','N'))
    FROM filtro)
SELECT codigo, ref, marca AS pb, descripcion, valor, unidad, articulo, seccion, paquete_codigo
FROM v_tarifas
WHERE descripcion_busqueda LIKE (SELECT t FROM buscado)
ORDER BY articulo, codigo;

-- ## Todo lo que hay bajo un agrupador (por su ruta), con notas
WITH filtro(ruta) AS (VALUES ('RADIOLOGIA > TORAX%'))
SELECT t.agrupador_ruta, t.codigo, t.ref, t.marca AS pb, t.descripcion, t.valor, t.unidad,
       (SELECT GROUP_CONCAT(n.texto, ' | ') FROM notas n WHERE n.procedimiento_id = t.id) AS notas
FROM v_tarifas t
WHERE t.agrupador_ruta LIKE (SELECT ruta FROM filtro)
ORDER BY t.id;

-- ## Procedimientos con ajuste de valor (Excel → PDF), con la diferencia
SELECT
    p.codigo,
    p.codigo_manual                              AS ref,
    p.descripcion,
    p.articulo,
    p.unidad,
    CAST(a.antes AS REAL)                        AS valor_excel,
    CAST(a.despues AS REAL)                      AS valor_pdf,
    ROUND(CAST(a.despues AS REAL) - CAST(a.antes AS REAL), 4) AS diferencia,
    p.valor                                      AS valor_en_bd,   -- debe ser igual a valor_pdf
    a.motivo,
    p.fila_excel
FROM ajustes_pdf a
JOIN procedimientos p ON p.fila_excel = CAST(a.fila_excel AS INTEGER)
WHERE a.campo = 'valor'
ORDER BY ABS(CAST(a.despues AS REAL) - CAST(a.antes AS REAL)) DESC;

-- ## Manual completo en el orden del Excel (artículos, capítulos, agrupadores, procedimientos y notas)
SELECT * FROM (
    SELECT a.fila_excel AS orden, 'ARTICULO' AS tipo_fila, a.numero AS articulo,
           NULL AS nivel, NULL AS agrupador_ruta, NULL AS ref, NULL AS pb, NULL AS codigo,
           a.texto AS descripcion, NULL AS ref_nota, NULL AS valor, NULL AS unidad,
           NULL AS paquete, a.fila_excel
    FROM articulos a
    UNION ALL
    SELECT g.fila_excel, 'AGRUPADOR', g.articulo, g.nivel, r.ruta, NULL, NULL, NULL,
           g.nombre, NULL, NULL, NULL, NULL, g.fila_excel
    FROM agrupadores g LEFT JOIN v_agrupadores_ruta r ON r.id = g.id
    UNION ALL
    SELECT p.fila_excel,
           CASE p.tipo WHEN 'componente' THEN 'COMPONENTE' ELSE 'PROCEDIMIENTO' END,
           p.articulo, NULL, r.ruta, p.codigo_manual, p.marca, p.codigo,
           p.descripcion, p.ref_nota, p.valor, p.unidad, pa.codigo, p.fila_excel
    FROM procedimientos p
    LEFT JOIN v_agrupadores_ruta r ON r.id = p.agrupador_id
    LEFT JOIN procedimientos pa ON pa.id = p.padre_id
    UNION ALL
    -- las 3 notas agregadas desde el PDF no tienen fila del Excel: van después de su procedimiento
    SELECT COALESCE(n.fila_excel, n.despues_de_fila + 0.5), UPPER(n.tipo), n.articulo, NULL,
           r.ruta, NULL, NULL, NULL, n.texto, NULL, NULL, NULL, NULL, n.fila_excel
    FROM notas n LEFT JOIN v_agrupadores_ruta r ON r.id = n.agrupador_id
)
ORDER BY orden;
