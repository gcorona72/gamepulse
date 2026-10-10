-- Pregunta 4. ¿Cómo cambia la opinión de los jugadores con una rebaja?
-- Para cada rebaja (mart_sale_uplift) compara el % de reseñas positivas en tres ventanas:
-- los 7 días anteriores, los días de la rebaja y los 7 días posteriores.
-- Dos medidas: lo que marca el autor (voted_up) y lo que el modelo lee en el texto.
with sales as (
    select game_key, appid, sale_start, sale_end, sale_days, max_discount_percent, uplift_pct
    from {{ ref('mart_sale_uplift') }}
),

windowed as (
    select
        s.appid,
        s.sale_start,
        case
            when r.date_day < s.sale_start then 'before'
            when r.date_day <= s.sale_end then 'during'
            else 'after'
        end as period,
        cast(r.voted_up as int) as author_positive,
        cast(r.pred_positive as int) as model_positive
    from sales as s
    inner join {{ ref('fct_review_sentiment') }} as r
        on r.appid = s.appid
        and r.date_day >= s.sale_start - interval 7 day
        and r.date_day <= s.sale_end + interval 7 day
),

agg as (
    select
        appid,
        sale_start,
        count(*) filter (where period = 'before') as reviews_before,
        count(*) filter (where period = 'during') as reviews_during,
        count(*) filter (where period = 'after') as reviews_after,
        avg(author_positive) filter (where period = 'before') as pct_positive_before,
        avg(author_positive) filter (where period = 'during') as pct_positive_during,
        avg(author_positive) filter (where period = 'after') as pct_positive_after,
        avg(model_positive) filter (where period = 'before') as model_positive_before,
        avg(model_positive) filter (where period = 'during') as model_positive_during,
        avg(model_positive) filter (where period = 'after') as model_positive_after
    from windowed
    group by appid, sale_start
)

select
    s.game_key,
    s.appid,
    s.sale_start,
    s.sale_end,
    s.sale_days,
    s.max_discount_percent,
    s.uplift_pct,
    a.reviews_before,
    a.reviews_during,
    a.reviews_after,
    a.pct_positive_before,
    a.pct_positive_during,
    a.pct_positive_after,
    a.model_positive_before,
    a.model_positive_during,
    a.model_positive_after,
    -- cambio en puntos porcentuales (durante - antes): > 0 = la opinión mejora con la rebaja
    round(100 * (a.pct_positive_during - a.pct_positive_before), 2) as delta_during_pp,
    round(100 * (a.model_positive_during - a.model_positive_before), 2) as model_delta_during_pp
from sales as s
inner join agg as a using (appid, sale_start)
