WITH raw_data AS (
    SELECT
        ingest_timestamp,
        JSON_EXTRACT_ARRAY(raw_payload) AS items
    FROM `portfolio-analytics-eng.mercado_financiero.raw_opciones_ggal` 
),

unnested_data AS (
    SELECT
        ingest_timestamp,
        JSON_VALUE(item, '$.symbol') AS ticker,
        CAST(JSON_VALUE(item, '$.c') AS FLOAT64) AS precio,
        CAST(CAST(COALESCE(JSON_VALUE(item, '$.v'), '0') AS FLOAT64) AS INT64) AS volumen
    FROM raw_data, UNNEST(items) AS item
),

parsed_tickers AS (
    SELECT
        ticker,
        precio,
        volumen,
        REGEXP_EXTRACT(ticker, r'^GFG([CV])') AS tipo_opcion,
        CAST(REGEXP_EXTRACT(ticker, r'^GFG[CV](\d+)') AS FLOAT64) AS strike_raw,
        REGEXP_EXTRACT(ticker, r'([A-Z]+)$') AS mes_vencimiento,
        ingest_timestamp
    FROM unnested_data
    WHERE REGEXP_CONTAINS(ticker, r'^GFG[CV]') 
)

SELECT
    ticker,
    CASE 
        WHEN tipo_opcion = 'C' THEN 'c'
        WHEN tipo_opcion = 'V' THEN 'p'
    END AS tipo,
    CASE 
        WHEN strike_raw > 20000 THEN strike_raw / 10 
        ELSE strike_raw 
    END AS strike,
    mes_vencimiento,
    precio,
    volumen,
    ingest_timestamp
FROM parsed_tickers
WHERE precio > 0 
  AND volumen > 0