-- Ningún valor imposible: espectadores, jugadores o descuentos negativos.
select 'audience' as source, game_key from {{ ref('fct_twitch_audience_hourly') }} where avg_viewers < 0
union all
select 'players', game_key from {{ ref('fct_steam_players_hourly') }} where avg_players < 0
union all
select 'price', game_key from {{ ref('fct_steam_price_daily') }}
where discount_percent < 0 or discount_percent > 100
