-- Historial de precios de Steam (SCD tipo 2) a partir del snapshot snap_steam_price:
-- una fila por cada periodo en que un juego mantuvo el mismo precio y descuento.
with game_keys as (
    select steam_appid as appid, min(game_key) as game_key
    from {{ ref('dim_game') }}
    where steam_appid is not null
    group by steam_appid
)

select
    k.game_key,
    s.appid,
    s.name as game_name,
    s.currency,
    s.initial_price_eur,
    s.final_price_eur,
    coalesce(s.discount_percent, 0) as discount_percent,
    coalesce(s.discount_percent, 0) > 0 as on_sale,
    s.dbt_valid_from as valid_from,
    s.dbt_valid_to as valid_to,
    s.dbt_valid_to is null as is_current
from {{ ref('snap_steam_price') }} as s
left join game_keys as k using (appid)
