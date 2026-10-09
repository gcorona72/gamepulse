-- Pregunta 3. ¿Qué juegos se ven mucho pero se juegan poco (y al revés)?
-- Compara la cuota de atención de cada juego (su % de los espectadores de Twitch) con su cuota
-- de uso (su % de los jugadores de Steam). Así el resultado no depende de que Twitch y Steam
-- midan magnitudes distintas: attention_index = 1 significa que se ve tanto como se juega.
with per_game as (
    select
        game_key,
        game_name,
        steam_appid,
        avg(avg_viewers) as avg_viewers,
        avg(avg_players) as avg_players,
        count(*) as hours
    from {{ ref('mart_twitch_vs_steam_hourly') }}
    group by game_key, game_name, steam_appid
    having count(*) >= 24 and avg(avg_players) > 0   -- al menos un día de datos cruzados
),

shares as (
    select
        *,
        avg_viewers / sum(avg_viewers) over () as viewer_share,
        avg_players / sum(avg_players) over () as player_share
    from per_game
),

sentiment as (
    select game_key, avg(cast(voted_up as int)) as pct_positive, count(*) as reviews
    from {{ ref('fct_reviews') }}
    where game_key is not null
    group by game_key
)

select
    s.game_key,
    s.game_name,
    s.steam_appid,
    s.avg_viewers,
    s.avg_players,
    s.hours,
    s.viewer_share,
    s.player_share,
    round(s.viewer_share / s.player_share, 3) as attention_index,
    case
        when s.viewer_share / s.player_share >= 2 then 'se ve más'
        when s.viewer_share / s.player_share <= 0.5 then 'se juega más'
        else 'equilibrado'
    end as profile,
    r.pct_positive,
    r.reviews
from shares as s
left join sentiment as r on r.game_key = s.game_key
