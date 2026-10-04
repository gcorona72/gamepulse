-- Pregunta 2 del TFG: ¿cuánto aumentan los jugadores durante una rebaja?
-- Cada rebaja = días consecutivos con descuento. Se compara la media de jugadores durante
-- la rebaja con la de los 7 días anteriores a su inicio.
with daily_players as (
    select appid, date_day, avg(avg_players) as avg_players
    from {{ ref('fct_steam_players_hourly') }}
    group by appid, date_day
),

daily as (
    select
        pr.game_key,
        pr.appid,
        pr.date_day,
        pr.discount_percent,
        pr.discount_percent > 0 as on_discount,
        p.avg_players
    from {{ ref('fct_steam_price_daily') }} as pr
    left join daily_players as p using (appid, date_day)
),

islands as (
    select
        *,
        sum(case when on_discount then 0 else 1 end)
            over (partition by appid order by date_day) as grp
    from daily
),

sales as (
    select
        any_value(game_key) as game_key,
        appid,
        min(date_day) as sale_start,
        max(date_day) as sale_end,
        count(*) as sale_days,
        max(discount_percent) as max_discount_percent,
        avg(avg_players) as avg_players_during_sale
    from islands
    where on_discount
    group by appid, grp
),

baseline as (
    select s.appid, s.sale_start, avg(b.avg_players) as avg_players_baseline
    from sales as s
    left join daily as b
        on b.appid = s.appid
        and b.date_day between s.sale_start - interval 7 day and s.sale_start - interval 1 day
        and not b.on_discount
    group by s.appid, s.sale_start
)

select
    s.game_key,
    s.appid,
    s.sale_start,
    s.sale_end,
    s.sale_days,
    s.max_discount_percent,
    round(s.avg_players_during_sale) as avg_players_during_sale,
    round(b.avg_players_baseline) as avg_players_baseline_7d,
    round(
        100.0 * (s.avg_players_during_sale - b.avg_players_baseline)
        / nullif(b.avg_players_baseline, 0),
        2
    ) as uplift_pct
from sales as s
left join baseline as b using (appid, sale_start)
