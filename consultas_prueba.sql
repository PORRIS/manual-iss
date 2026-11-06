-- Consultas de prueba de salida/manual_iss.db
-- Cada bloque empieza con la marca @prueba y, si tiene resultado conocido, la marca @esperado.
-- Ejecutar todas y comparar:   uv run probar_bd.py
-- Los bloques sin @esperado son consultas de ejemplo: se muestran las primeras filas.

-- ===================================================================== 1. CONTEOS
-- @prueba Procedimientos (6.444 filas, igual que el PDF)
-- @esperado 6444
SELECT COUNT(*) FROM procedimientos;

-- @prueba Procedimientos por tipo
-- @esperado componente=426, con_valor=5881, sin_valor=137
SELECT GROUP_CONCAT(tipo || '=' || n, ', ')
FROM (SELECT tipo, COUNT(*) n FROM procedimientos GROUP BY tipo ORDER BY tipo);

-- @prueba Procedimientos por unidad
-- @esperado UVR=3372, factor=9, pesos=3059, pesos_por_uvr=4
SELECT GROUP_CONCAT(unidad || '=' || n, ', ')
FROM (SELECT unidad, COUNT(*) n FROM procedimientos GROUP BY unidad ORDER BY unidad);

-- @prueba Artículos | agrupadores | notas | parámetros | abreviaturas
-- @esperado 147|612|1079|4|2
SELECT (SELECT COUNT(*) FROM articulos) || '|' || (SELECT COUNT(*) FROM agrupadores) || '|' ||
       (SELECT COUNT(*) FROM notas) || '|' || (SELECT COUNT(*) FROM parametros) || '|' ||
       (SELECT COUNT(*) FROM abreviaturas);

-- @prueba Artículos 1 a 147 sin huecos ni repetidos
-- @esperado 147|147|1|147
SELECT COUNT(*) || '|' || COUNT(DISTINCT numero) || '|' || MIN(numero) || '|' || MAX(numero)
FROM articulos;

-- ===================================================================== 2. INTEGRIDAD
-- @prueba Procedimientos con agrupador inexistente
-- @esperado 0
SELECT COUNT(*) FROM procedimientos p
WHERE p.agrupador_id IS NOT NULL AND p.agrupador_id NOT IN (SELECT id FROM agrupadores);

-- @prueba Procedimientos con artículo inexistente
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE articulo NOT IN (SELECT numero FROM articulos);

-- @prueba Componentes sin paquete padre
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE tipo = 'componente' AND padre_id IS NULL;

-- @prueba Padres de componentes que no existen o no tienen valor
-- @esperado 0
SELECT COUNT(*) FROM procedimientos c
LEFT JOIN procedimientos p ON p.id = c.padre_id
WHERE c.padre_id IS NOT NULL AND (p.id IS NULL OR p.tipo <> 'con_valor');

-- @prueba Notas que apuntan a un procedimiento inexistente
-- @esperado 0
SELECT COUNT(*) FROM notas
WHERE procedimiento_id IS NOT NULL AND procedimiento_id NOT IN (SELECT id FROM procedimientos);

-- @prueba Agrupadores con padre inexistente
-- @esperado 0
SELECT COUNT(*) FROM agrupadores
WHERE padre_id IS NOT NULL AND padre_id NOT IN (SELECT id FROM agrupadores);

-- @prueba Agrupadores cuyo nivel no es el de su padre + 1
-- @esperado 0
SELECT COUNT(*) FROM agrupadores h JOIN agrupadores p ON p.id = h.padre_id
WHERE h.nivel <> p.nivel + 1;

-- @prueba Agrupadores por nivel (NULL = filas de tablas de texto de los arts. 59 y 63)
-- @esperado NULL=3, 1=167, 2=394, 3=22, 4=22, 5=4
SELECT GROUP_CONCAT(COALESCE(nivel, 'NULL') || '=' || n, ', ')
FROM (SELECT nivel, COUNT(*) n FROM agrupadores GROUP BY nivel ORDER BY nivel);

-- ===================================================================== 3. REGLAS DE LOS DATOS
-- @prueba Procedimientos con valor sin valor numérico, o valores <= 0
-- @esperado 0|0
SELECT (SELECT COUNT(*) FROM procedimientos WHERE tipo = 'con_valor' AND valor IS NULL) || '|' ||
       (SELECT COUNT(*) FROM procedimientos WHERE valor <= 0);

-- @prueba Componentes o "sin valor" que sí tienen valor
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE tipo <> 'con_valor' AND valor IS NOT NULL;

-- @prueba Códigos CUPS numéricos que no tienen 6 dígitos (se perdió el cero inicial)
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE codigo GLOB '[0-9]*' AND LENGTH(codigo) <> 6;

-- @prueba Unidad incoherente con el artículo (UVR solo en arts. 1-18)
-- @esperado 0
SELECT COUNT(*) FROM procedimientos
WHERE (articulo <= 18) <> (unidad = 'UVR');

-- @prueba Descripciones vacías
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE descripcion IS NULL OR TRIM(descripcion) = '';

-- @prueba Marcas distintas de PB o vacío
-- @esperado PB,NULL
SELECT GROUP_CONCAT(DISTINCT COALESCE(marca, 'NULL')) FROM procedimientos;

-- @prueba ref_nota no numérica
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE ref_nota GLOB '*[^0-9]*';

-- @prueba Grupos de filas idénticas (legítimos: el PDF repite el código por grupo de población
--         o paquete; arts. 90, 95 y 15). Si cambia, revisar.
-- @esperado 75
SELECT COUNT(*) FROM (SELECT 1 FROM procedimientos
                      GROUP BY codigo, codigo_manual, descripcion, valor, articulo
                      HAVING COUNT(*) > 1);

-- ===================================================================== 4. CASOS VERIFICADOS EN EL PDF
-- @prueba 549001: el PDF dice 70 UVR, el Excel decía 80 (pág. 37)
-- @esperado 70
SELECT CAST(valor AS INTEGER) FROM procedimientos WHERE codigo = '549001';

-- @prueba C40584: valor partido en dos líneas en el PDF, 117.708.665 (pág. 187)
-- @esperado 40584|117708665
SELECT codigo_manual || '|' || CAST(valor AS INTEGER) FROM procedimientos WHERE codigo = 'C40584';

-- @prueba Trasplante hepático redondeado como el PDF: C40596 y C40598 (pág. 187)
-- @esperado 79993130|202680
SELECT (SELECT CAST(valor AS INTEGER) FROM procedimientos WHERE codigo = 'C40596') || '|' ||
       (SELECT CAST(valor AS INTEGER) FROM procedimientos WHERE codigo = 'C40598');

-- @prueba 020101: CUPS y REF con cero inicial (pág. 2)
-- @esperado 01100|380|PB
SELECT codigo_manual || '|' || CAST(valor AS INTEGER) || '|' || marca
FROM procedimientos WHERE codigo = '020101';

-- @prueba S55203: decimal con coma en el PDF, "0,40" (pág. 167)
-- @esperado 0.4
SELECT valor FROM procedimientos WHERE codigo = 'S55203';

-- @prueba Eliminados porque no existen en el PDF: M09181, 783001 y M23119
-- @esperado 0
SELECT COUNT(*) FROM procedimientos WHERE codigo IN ('M09181', '783001', 'M23119');

-- @prueba Penoscopia con el CUPS del PDF, 641200 (pág. 124)
-- @esperado 1|PENOSCOPIA SOD
SELECT COUNT(*) || '|' || MIN(descripcion) FROM procedimientos WHERE codigo = '641200';

-- @prueba 083300: dos notas; la última en ref_nota, la anterior en la descripción (pág. 11)
-- @esperado CORRECCIÓN DE PTOSIS PALPEBRAL, POR RESECCION EXTERNA DEL ELEVADOR SOD (4)|196
SELECT descripcion || '|' || ref_nota FROM procedimientos WHERE codigo = '083300';

-- @prueba 871182: solo la nota (349); el "(55)" del Excel no está en el PDF (pág. 112)
-- @esperado 349|0
SELECT ref_nota || '|' || (descripcion LIKE '%(55)%') FROM procedimientos WHERE codigo = '871182';

-- @prueba 115301: nota de un dígito separada en ref_nota (pág. 12)
-- @esperado 5
SELECT ref_nota FROM procedimientos WHERE codigo = '115301';

-- @prueba 903046: se conserva TRANSFERRINA (el PDF deja la primera línea vacía, pág. 107)
-- @esperado TRANSFERRINA POR NEFELOMETRÍA
SELECT descripcion FROM procedimientos WHERE codigo = '903046';

-- @prueba 993122 (fila 8130): error de redacción del PDF copiado tal cual (pág. 163)
-- @esperado VACUNACION CONTRA COMBINADA CONTRA DIFTERIA, TETANOS Y TOSFERINA(dpt)
SELECT descripcion FROM procedimientos WHERE fila_excel = 8130;

-- @prueba Valor de la UVR del cirujano, art. 59
-- @esperado 1270
SELECT CAST(pesos_por_uvr AS INTEGER) FROM parametros WHERE codigo_uvr = 'S41101';

-- @prueba Notas que faltaban en el Excel, agregadas desde el PDF (pág. 173)
-- @esperado 3
SELECT COUNT(*) FROM notas WHERE despues_de_fila IS NOT NULL;

-- @prueba Capítulos
-- @esperado CAPITULO II, CAPITULO III, CAPITULO IV, CAPITULO V
SELECT GROUP_CONCAT(texto, ', ') FROM (SELECT texto FROM notas WHERE tipo = 'capitulo'
                                       ORDER BY fila_excel);

-- @prueba Título de dos líneas unido en un agrupador (pág. 73)
-- @esperado TRATAMIENTO EN QUEMADURAS (Incluye quemadura por fricción)
SELECT nombre FROM agrupadores WHERE nombre LIKE 'TRATAMIENTO EN QUEMADURAS%';

-- @prueba Subtítulo que el Excel tenía como nota, ahora agrupador hijo (pág. 81)
-- @esperado MAXILARES, ENCIAS Y DIENTES > EXTIRPACION DE LESIONES, QUISTES Y TUMORES EN MAXILARES Y CAVIDAD BUCAL
SELECT ruta FROM v_agrupadores_ruta WHERE nombre LIKE 'EXTIRPACION DE LESIONES, QUISTES%';

-- @prueba La TAC cuelga de RADIOLOGIA (numeración REF 21xxxx, pág. 116)
-- @esperado RADIOLOGIA > TOMOGRAFIA COMPUTARIZADA O ESCANOGRAFIA
SELECT ruta FROM v_agrupadores_ruta WHERE nombre = 'TOMOGRAFIA COMPUTARIZADA O ESCANOGRAFIA';

-- @prueba Abreviaturas de las leyendas del PDF
-- @esperado NCOC=No Clasificable bajo Otro Concepto; SOD=Sin Otra Denominación
SELECT GROUP_CONCAT(abreviatura || '=' || significado, '; ')
FROM (SELECT * FROM abreviaturas ORDER BY abreviatura);

-- ===================================================================== 5. VISTAS
-- @prueba Filas por vista: tarifas | laboratorio | imágenes | paquetes | componentes | rutas | honorarios
-- @esperado 6444|787|506|263|421|612|3372
SELECT (SELECT COUNT(*) FROM v_tarifas) || '|' || (SELECT COUNT(*) FROM v_laboratorio) || '|' ||
       (SELECT COUNT(*) FROM v_imagenes) || '|' || (SELECT COUNT(*) FROM v_paquetes) || '|' ||
       (SELECT COUNT(*) FROM v_paquete_componentes) || '|' ||
       (SELECT COUNT(*) FROM v_agrupadores_ruta) || '|' || (SELECT COUNT(*) FROM v_honorarios_cirugia);

-- @prueba Manual completo | valores con novedad | novedades cuyo valor en BD no es el del PDF
-- @esperado 8282|37|0
SELECT (SELECT COUNT(*) FROM v_manual_completo) || '|' || (SELECT COUNT(*) FROM v_ajustes_valor) || '|' ||
       (SELECT COUNT(*) FROM v_ajustes_valor WHERE valor_en_bd <> valor_pdf);

-- @prueba Novedades: total | eliminadas | texto | valor | estructura | aceptadas | relación CUPS
-- @esperado 583|11|280|37|20|23|2
SELECT (SELECT COUNT(*) FROM v_novedades) || '|' || (SELECT COUNT(*) FROM v_novedades_eliminadas) || '|' ||
       (SELECT COUNT(*) FROM v_novedades_texto) || '|' || (SELECT COUNT(*) FROM v_ajustes_valor) || '|' ||
       (SELECT COUNT(*) FROM v_novedades_estructura) || '|' || (SELECT COUNT(*) FROM v_novedades_aceptadas) || '|' ||
       (SELECT COUNT(*) FROM v_novedades_relacion_cups);

-- @prueba Relación CUPS por revisar: total | glucometría 903883 sugerida | por_revisar en homologacion.csv
-- @esperado 210|M19275|210
SELECT (SELECT COUNT(*) FROM v_novedades_relacion_revision) || '|' ||
       (SELECT codigo_sugerido FROM v_novedades_relacion_revision WHERE cups = '903883') || '|' ||
       (SELECT COUNT(*) FROM v_novedades_relacion_revision WHERE estado_revision = 'por_revisar');

-- @prueba Relación CUPS sin código en el PDF: 783001 viene de la fila 3466 del Excel; 012205 de ninguna
-- @esperado 012205:-|783001:3466
SELECT GROUP_CONCAT(codigo_iss || ':' || COALESCE(fila_excel, '-'), '|') FROM v_novedades_relacion_cups;

-- @prueba Fila eliminada 3466: contenido original del Excel y página del PDF
-- @esperado 13900 | 783001 | TRANSPOSICIÓN ÓSEA EN HUESOS LARGOS CON COLOCACIÓN DE TUTOR EXTERNO | 200|65
SELECT texto_excel || '|' || pagina_pdf FROM v_novedades_eliminadas WHERE fila_excel = 3466;

-- @prueba Resumen de validación: controles | en REVISAR | procedimientos PDF=BD | artículos PDF=BD
-- @esperado 12|0|6444=6444|147=147
SELECT (SELECT COUNT(*) FROM v_validacion_resumen) || '|' ||
       (SELECT COUNT(*) FROM v_validacion_resumen WHERE resultado <> 'OK') || '|' ||
       (SELECT pdf || '=' || bd FROM v_validacion_resumen WHERE control LIKE 'Procedimientos (filas%') || '|' ||
       (SELECT pdf || '=' || bd FROM v_validacion_resumen WHERE control = 'Artículos');

-- @prueba Auditoría visual: páginas | filas revisadas | sin explicar ; abreviaturas
-- @esperado 10|406|0|2
SELECT COUNT(*) || '|' || SUM(filas_revisadas) || '|' || SUM(diferencias_sin_explicar) || '|' ||
       (SELECT COUNT(*) FROM v_abreviaturas) FROM v_auditoria_visual;

-- @prueba Componente 791703: paquete, valor del paquete
-- @esperado C40467|1121360
SELECT paquete || '|' || CAST(valor_paquete AS INTEGER) FROM v_manual_completo
WHERE codigo = '791703' AND tipo_fila = 'COMPONENTE';

-- @prueba Honorarios de 020101 (380 UVR): cirujano 1.270, anestesia 960, ayudante 360 por UVR
-- @esperado 482600|364800|136800
SELECT CAST(cirujano AS INTEGER) || '|' || CAST(anestesia_si_aplica AS INTEGER) || '|' ||
       CAST(ayudante_si_se_causa AS INTEGER)
FROM v_honorarios_cirugia WHERE codigo = '020101';

-- @prueba ¿Qué paquete cubre la colecistectomía laparoscópica 512104?
-- @esperado C40402|1806670
SELECT paquete_codigo || '|' || CAST(paquete_valor AS INTEGER)
FROM v_paquete_componentes WHERE componente_codigo = '512104';

-- @prueba Paquete más caro
-- @esperado C40584|117708665
SELECT codigo || '|' || CAST(valor AS INTEGER) FROM v_paquetes ORDER BY valor DESC LIMIT 1;

-- ===================================================================== 6. AUDITORÍA
-- @prueba Correcciones aplicadas por acción (tabla ajustes_pdf)
-- @esperado aceptar=23, agregar=3, cambiar=334, eliminar=11
SELECT GROUP_CONCAT(accion || '=' || n, ', ')
FROM (SELECT accion, COUNT(*) n FROM ajustes_pdf GROUP BY accion ORDER BY accion);

-- @prueba Los 37 ajustes de valor del PDF
-- @esperado 37
SELECT COUNT(*) FROM ajustes_pdf WHERE campo = 'valor';

-- ===================================================================== 7. EJEMPLOS DE USO (sin esperado)
-- @prueba Buscar por texto en la descripción
SELECT codigo, articulo, seccion, descripcion, valor, unidad
FROM v_tarifas WHERE descripcion LIKE '%COLECISTECTOM%' ORDER BY articulo;

-- @prueba Tarifa de un código con su ruta de agrupadores y notas
SELECT t.codigo, t.descripcion, t.valor, t.unidad, t.agrupador_ruta,
       (SELECT GROUP_CONCAT(n.texto, ' / ') FROM notas n WHERE n.procedimiento_id = t.id) AS notas
FROM v_tarifas t WHERE t.codigo = '903801';

-- @prueba Exámenes de laboratorio por área: cantidad, mínimo y máximo
--         (el art. 25 es una lista alfabética sin títulos en el PDF: no tiene área)
SELECT COALESCE(area, seccion || ' (lista alfabética)') AS area, COUNT(*) AS n,
       MIN(valor) AS minimo, MAX(valor) AS maximo
FROM v_laboratorio GROUP BY 1 ORDER BY n DESC;

-- @prueba Imágenes por modalidad
SELECT modalidad, COUNT(*) AS n, MIN(valor) AS minimo, MAX(valor) AS maximo
FROM v_imagenes GROUP BY modalidad;

-- @prueba Cotizador: reglas | aprobadas | regiones con incremento | ciudades exceptuadas
-- @esperado 14|14|15|6
SELECT (SELECT COUNT(*) FROM v_reglas_tarifas) || '|' ||
       (SELECT COUNT(*) FROM v_reglas_tarifas WHERE estado = 'aprobada') || '|' ||
       (SELECT COUNT(*) FROM regiones_134 WHERE clase <> 'ciudad_exceptuada') || '|' ||
       (SELECT COUNT(*) FROM regiones_134 WHERE clase = 'ciudad_exceptuada');

-- @prueba Relación CUPS 2026 -> ISS: filas | con código ISS en el Manual | glucometría 903883 -> ISS
-- @esperado 9379|9377|903840
SELECT (SELECT COUNT(*) FROM v_homologacion_cups) || '|' ||
       (SELECT COUNT(*) FROM homologacion_cups WHERE existe_en_manual = 1) || '|' ||
       (SELECT codigo_iss FROM v_homologacion_cups WHERE cups = '903883');

-- @prueba Los 5 paquetes con más componentes
SELECT codigo, descripcion, valor, n_componentes FROM v_paquetes
ORDER BY n_componentes DESC LIMIT 5;

-- @prueba Árbol de agrupadores de un artículo (art. 27, imagenología)
SELECT nivel, ruta FROM v_agrupadores_ruta WHERE articulo = 27 ORDER BY id;
