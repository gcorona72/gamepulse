-- Pregunta 2 del TFG: ¿cuánto aumentan los jugadores durante una rebaja?
-- Cada rebaja = días consecutivos con descuento. Se compara la media de jugadores durante la
-- rebaja con una referencia sin descuento:
--   * 'antes':   los 7 días anteriores a su inicio (lo ideal).
--   * 'después': los 7 días posteriores a su fin, solo para rebajas que ya estaban activas al
--                empezar la captura (no conocemos su inicio real ni su "antes") y ya han terminado.
-- Se descartan las rebajas sin referencia válida y los juegos con menos de 100 jugadores de media.
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

-- Primer y último día con datos de precio de cada juego
bounds as (
    select appid, min(date_day) as first_day, max(date_day) as last_day
    from daily
    group by appid
),

baseline_before as (
    select s.appid, s.sale_start, avg(b.avg_players) as avg_before
    from sales as s
    left join daily as b
        on b.appid = s.appid
        and b.date_day between s.sale_start - interval 7 day and s.sale_start - interval 1 day
        and not b.on_discount
    group by s.appid, s.sale_start
),

baseline_after as (
    select s.appid, s.sale_start, avg(a.avg_players) as avg_after, count(a.avg_players) as days_after
    from sales as s
    left join daily as a
        on a.appid = s.appid
        and a.date_day between s.sale_end + interval 1 day and s.sale_end + interval 7 day
        and not a.on_discount
    group by s.appid, s.sale_start
),

chosen as (
    select
        s.*,
        -- si la rebaja "empieza" el primer día capturado, probablemente ya estaba activa antes
        s.sale_start > f.first_day as has_real_start,
        case when s.sale_start > f.first_day then bb.avg_before else ba.avg_after end as baseline,
        ba.days_after
    from sales as s
    inner join bounds as f using (appid)
    left join baseline_before as bb using (appid, sale_start)
    left join baseline_after as ba using (appid, sale_start)
)

select
    game_key,
    appid,
    sale_start,
    sale_end,
    sale_days,
    max_discount_percent,
    case when has_real_start then 'antes' else 'después' end as baseline_type,
    round(avg_players_during_sale) as avg_players_during_sale,
    round(baseline) as avg_players_baseline_7d,
    round(100.0 * (avg_players_during_sale - baseline) / nullif(baseline, 0), 2) as uplift_pct
from chosen
where baseline >= 100
    and (has_real_start or days_after >= 3)   -- referencia 'después': al menos 3 días tras la rebaja
