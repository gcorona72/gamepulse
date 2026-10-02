-- Pregunta 1 y 3 del TFG: audiencia de Twitch frente a jugadores de Steam, juego a juego y hora a hora.
-- Solo juegos presentes en las dos plataformas.
select
    g.game_key,
    g.game_name,
    g.steam_appid,
    a.hour_ts,
    a.date_day,
    a.avg_viewers,
    p.avg_players,
    round(a.avg_viewers / nullif(p.avg_players, 0), 4) as viewers_per_player
from {{ ref('fct_twitch_audience_hourly') }} as a
inner join {{ ref('fct_steam_players_hourly') }} as p
    on p.game_key = a.game_key and p.hour_ts = a.hour_ts
inner join {{ ref('dim_game') }} as g on g.game_key = a.game_key
