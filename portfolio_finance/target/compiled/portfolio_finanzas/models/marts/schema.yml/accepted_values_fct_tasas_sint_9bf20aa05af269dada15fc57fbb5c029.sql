
    
    

with all_values as (

    select
        dias_al_vencimiento as value_field,
        count(*) as n_records

    from `portfolio-analytics-eng`.`mercado_financiero_dev`.`fct_tasas_sinteticas`
    group by dias_al_vencimiento

)

select *
from all_values
where value_field not in (
    > 0
)


