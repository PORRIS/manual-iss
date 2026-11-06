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

-- ## Valores con novedad (Excel → PDF), de mayor a menor diferencia   (vista v_ajustes_valor)
SELECT * FROM v_ajustes_valor;

-- ## Manual completo en el orden del Excel (vista v_manual_completo); filtre con WHERE, p. ej.
--    WHERE codigo IN ('791703')   o   WHERE articulo = 95
SELECT * FROM v_manual_completo;
