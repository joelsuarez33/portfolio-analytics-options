

  create or replace view `portfolio-analytics-eng`.`mercado_financiero_dev`.`fct_opciones_latest`
  OPTIONS()
  as WITH opciones_historicas AS (
    SELECT 
        stg.ticker,
        stg.tipo,
        stg.strike,
        stg.precio,
        stg.volumen,
        stg.ingest_timestamp,
        DATE_DIFF(CAST(vto.fecha_vencimiento AS DATE), CURRENT_DATE('America/Argentina/Buenos_Aires'), DAY) AS dte
    FROM `portfolio-analytics-eng`.`mercado_financiero_dev`.`stg_opciones_ggal` stg
    LEFT JOIN `portfolio-analytics-eng`.`mercado_financiero_dev`.`dim_vencimientos` vto
        ON stg.mes_vencimiento = vto.codigo_mes
)

SELECT *
FROM opciones_historicas
WHERE dte > 0 
  AND precio > 0 
  AND volumen > 0
-- QUALIFY es una función analítica de BigQuery que filtra el resultado de una Window Function.
-- Aquí particiona los datos por ticker y ordena por fecha de ingesta descendente, quedándose solo con la fila 1 (la más reciente).
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY ingest_timestamp DESC) = 1;

