
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select fecha_vencimiento
from `portfolio-analytics-eng`.`mercado_financiero_dev`.`fct_tasas_sinteticas`
where fecha_vencimiento is null



  
  
      
    ) dbt_internal_test