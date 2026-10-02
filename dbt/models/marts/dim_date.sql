-- Calendario continuo entre la primera y la última fecha con datos.
with bounds as (
    select
        min(cast(snapshot_ts as date)) as min_d,
        max(cast(snapshot_ts as date)) as max_d
    from {{ ref('stg_twitch_streams') }}
),

days as (
    select cast(d as date) as date_day
    from bounds, generate_series(min_d, max_d, interval 1 day) as g(d)
)

select
    date_day,
    year(date_day) as year,
    month(date_day) as month,
    day(date_day) as day,
    week(date_day) as iso_week,
    isodow(date_day) as day_of_week,
    isodow(date_day) in (6, 7) as is_weekend
from days
