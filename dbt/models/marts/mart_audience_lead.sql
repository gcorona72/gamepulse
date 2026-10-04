-- Pregunta 1 del TFG: ¿los picos de audiencia en Twitch preceden a los de jugadores en Steam?
-- Correlación entre espectadores en la hora t y jugadores en la hora t + lag (0 a 12 h), por juego.
with base as (
    select game_key, game_name, hour_ts, avg_viewers, avg_players
    from {{ ref('mart_twitch_vs_steam_hourly') }}
),

lags as (
    select range as lag_hours from range(0, 13)
),

pairs as (
    select
        a.game_key,
        a.game_name,
        l.lag_hours,
        a.avg_viewers,
        p.avg_players
    from base as a
    cross join lags as l
    inner join base as p
        on p.game_key = a.game_key
        and p.hour_ts = a.hour_ts + to_hours(l.lag_hours)
)

select
    game_key,
    any_value(game_name) as game_name,
    lag_hours,
    count(*) as n_hours,
    round(corr(avg_viewers, avg_players), 4) as correlation
from pairs
group by game_key, lag_hours
having count(*) >= 24
