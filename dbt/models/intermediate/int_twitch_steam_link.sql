-- Último appid de Steam conocido para cada juego de Twitch (según IGDB).
select
    twitch_game_id,
    arg_max(steam_appid, captured_at) as steam_appid
from {{ ref('stg_game_map') }}
where steam_appid is not null
group by twitch_game_id
