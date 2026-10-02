-- Audiencia de Twitch por juego y hora.
-- Primero se suma por snapshot (cada minuto) y después se resume la hora.
with per_snapshot as (
    select
        twitch_game_id,
        snapshot_ts,
        sum(viewer_count) as viewers,
        count(*) as streams
    from {{ ref('stg_twitch_streams') }}
    group by twitch_game_id, snapshot_ts
)

select
    'tw_' || twitch_game_id as game_key,
    date_trunc('hour', snapshot_ts) as hour_ts,
    cast(date_trunc('hour', snapshot_ts) as date) as date_day,
    round(avg(viewers)) as avg_viewers,
    max(viewers) as peak_viewers,
    round(avg(streams), 1) as avg_streams,
    count(*) as n_snapshots
from per_snapshot
group by 1, 2, 3
