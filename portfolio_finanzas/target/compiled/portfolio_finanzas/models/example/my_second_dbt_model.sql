-- Use the `ref` function to select from other models

select *
from `portfolio-analytics-eng`.`mercado_financiero_dev`.`my_first_dbt_model`
where id = 1