{# SCD tipo 2: historial de precios. Cada cambio de precio o descuento abre una fila nueva
   (dbt_valid_from / dbt_valid_to). #}
{% snapshot snap_steam_price %}
{{
    config(
        target_schema='snapshots',
        unique_key='appid',
        strategy='check',
        check_cols=['initial_price_eur', 'final_price_eur', 'discount_percent'],
    )
}}
select
    appid,
    arg_max(name, captured_at) as name,
    arg_max(currency, captured_at) as currency,
    arg_max(initial_price_eur, captured_at) as initial_price_eur,
    arg_max(final_price_eur, captured_at) as final_price_eur,
    arg_max(discount_percent, captured_at) as discount_percent
from {{ ref('stg_steam_store') }}
where available
group by appid
{% endsnapshot %}
