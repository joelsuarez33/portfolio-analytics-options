
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  -- Este test asegura que no existan opciones con días al vencimiento negativos o cero.
-- Si el query devuelve resultados, dbt marcará el test como fallido.

SELECT
    strike,
    fecha_vencimiento,
    dias_al_vencimiento
FROM `portfolio-analytics-eng`.`mercado_financiero_dev`.`fct_tasas_sinteticas`
WHERE dias_al_vencimiento <= 0
  
  
      
    ) dbt_internal_test