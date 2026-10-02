-- Jugadores simultáneos en Steam por juego y hora.
with game_keys as (
    select steam_appid as appid, min(game_key) as game_key
    from {{ ref('dim_game') }}
    where steam_appid is not null
    group by steam_appid
)

select
    k.game_key,
    p.appid,
    date_trunc('hour', p.snapshot_ts) as hour_ts,
    cast(date_trunc('hour', p.snapshot_ts) as date) as date_day,
    round(avg(p.player_count)) as avg_players,
    max(p.player_count) as peak_players
from {{ ref('stg_steam_players') }} as p
left join game_keys as k using (appid)
where p.player_count is not null
group by 1, 2, 3, 4
