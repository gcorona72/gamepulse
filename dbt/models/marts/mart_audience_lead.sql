-- Pregunta 1 del TFG: ¿los picos de audiencia en Twitch preceden a los de jugadores en Steam?
-- Correlación entre espectadores en la hora t y jugadores en la hora t + lag (0 a 12 h), por juego.
-- Se quita antes el patrón diario: cada valor se compara con la media de ese juego a esa hora
-- del día, y se correlacionan solo las desviaciones.
with base as (
    select game_key, game_name, hour_ts, avg_viewers, avg_players
    from {{ ref('mart_twitch_vs_steam_hourly') }}
),

hourly_profile as (
    select
        game_key,
        hour(hour_ts) as hour_of_day,
        avg(avg_viewers) as typical_viewers,
        avg(avg_players) as typical_players
    from base
    group by game_key, hour(hour_ts)
),

deviations as (
    select
        b.game_key,
        b.game_name,
        b.hour_ts,
        b.avg_viewers,
        b.avg_players,
        b.avg_viewers - h.typical_viewers as viewers_dev,
        b.avg_players - h.typical_players as players_dev
    from base as b
    inner join hourly_profile as h
        on h.game_key = b.game_key and h.hour_of_day = hour(b.hour_ts)
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
        p.avg_players,
        a.viewers_dev,
        p.players_dev
    from deviations as a
    cross join lags as l
    inner join deviations as p
        on p.game_key = a.game_key
        and p.hour_ts = a.hour_ts + to_hours(l.lag_hours)
)

select
    game_key,
    any_value(game_name) as game_name,
    lag_hours,
    count(*) as n_hours,
    round(corr(viewers_dev, players_dev), 4) as correlation,
    round(corr(avg_viewers, avg_players), 4) as correlation_raw
from pairs
group by game_key, lag_hours
having count(*) >= 24
