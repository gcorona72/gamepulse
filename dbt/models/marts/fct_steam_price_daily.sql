-- Precio y descuento de cada juego por día (la última captura del día).
with game_keys as (
    select steam_appid as appid, min(game_key) as game_key
    from {{ ref('dim_game') }}
    where steam_appid is not null
    group by steam_appid
)

select
    k.game_key,
    s.appid,
    s.capture_date as date_day,
    s.is_free,
    s.currency,
    s.initial_price_eur,
    s.final_price_eur,
    coalesce(s.discount_percent, 0) as discount_percent,
    s.on_sale
from {{ ref('stg_steam_store') }} as s
left join game_keys as k using (appid)
where s.available
