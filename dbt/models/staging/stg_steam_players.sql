select
    appid,
    name,
    cast(snapshot_ts as timestamp) as snapshot_ts,
    player_count
from {{ source('silver', 'steam_players') }}
