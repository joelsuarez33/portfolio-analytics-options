-- Este test asegura que no existan opciones con días al vencimiento negativos o cero.
-- Si el query devuelve resultados, dbt marcará el test como fallido.

SELECT
    strike,
    fecha_vencimiento,
    dias_al_vencimiento
FROM {{ ref('fct_tasas_sinteticas') }}
WHERE dias_al_vencimiento <= 0