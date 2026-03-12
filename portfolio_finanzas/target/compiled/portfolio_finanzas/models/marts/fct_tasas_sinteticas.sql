WITH opciones_base AS (
    SELECT
        stg.ticker,
        stg.tipo,
        stg.strike,
        stg.precio,
        stg.volumen,
        stg.ingest_timestamp,
        CAST(vto.fecha_vencimiento AS DATE) AS fecha_vencimiento
    FROM `portfolio-analytics-eng`.`mercado_financiero_dev`.`stg_opciones_ggal` stg
    LEFT JOIN `portfolio-analytics-eng`.`mercado_financiero_dev`.`dim_vencimientos` vto
        ON stg.mes_vencimiento = vto.codigo_mes
),

calls AS (
    SELECT 
        strike, 
        fecha_vencimiento, 
        precio AS precio_call, 
        volumen AS vol_call,
        ingest_timestamp
    FROM opciones_base
    WHERE tipo = 'c'
),

puts AS (
    SELECT 
        strike, 
        fecha_vencimiento, 
        precio AS precio_put, 
        volumen AS vol_put
    FROM opciones_base
    WHERE tipo = 'p'
)

SELECT
    c.strike,
    c.fecha_vencimiento,
    DATE_DIFF(c.fecha_vencimiento, CURRENT_DATE('America/Argentina/Buenos_Aires'), DAY) AS dias_al_vencimiento,
    c.precio_call,
    p.precio_put,
    c.vol_call,
    p.vol_put,
    -- Ecuación de paridad Call-Put para el cálculo del Sintético
    (c.strike + c.precio_call - p.precio_put) AS precio_sintetico,
    c.ingest_timestamp
FROM calls c
INNER JOIN puts p
    ON c.strike = p.strike
    AND c.fecha_vencimiento = p.fecha_vencimiento
WHERE c.vol_call > 0 
  AND p.vol_put > 0
  AND DATE_DIFF(c.fecha_vencimiento, CURRENT_DATE('America/Argentina/Buenos_Aires'), DAY) > 0