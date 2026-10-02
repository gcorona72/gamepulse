select
    event_id,
    cast(snapshot_ts as timestamp) as snapshot_ts,
    game_id as twitch_game_id,
    game_name,
    try_cast(igdb_id as bigint) as igdb_id,
    stream_id,
    user_id,
    language,
    viewer_count,
    cast(started_at as timestamp) as started_at,
    is_mature
from {{ source('silver', 'twitch_streams') }}
