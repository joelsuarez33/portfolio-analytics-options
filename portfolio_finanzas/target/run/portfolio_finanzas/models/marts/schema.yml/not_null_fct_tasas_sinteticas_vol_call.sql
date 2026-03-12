
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select vol_call
from `portfolio-analytics-eng`.`mercado_financiero_dev`.`fct_tasas_sinteticas`
where vol_call is null



  
  
      
    ) dbt_internal_test