select
    cast(captured_at as timestamp) as captured_at,
    twitch_rank,
    twitch_game_id,
    game_name,
    igdb_id,
    steam_appid
from {{ source('silver', 'game_map') }}
