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
       p.codigo_manual AS ref, p.codigo, p.marca, p.descripcion, p.ref_nota, p.tipo,
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
