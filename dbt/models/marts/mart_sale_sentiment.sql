-- Pregunta 4. ¿Cómo cambia la opinión de los jugadores con una rebaja?
-- Para cada rebaja (mart_sale_uplift) calcula el % de reseñas positivas en tres ventanas:
-- los 7 días anteriores, los días de la rebaja y los 7 días posteriores.
-- La referencia es la misma que en la pregunta 2: 'antes' si conocemos el inicio real de la
-- rebaja, 'después' si ya estaba activa al empezar la captura.
-- Dos medidas: lo que marca el autor (voted_up) y lo que el modelo lee en el texto.
with sales as (
    select game_key, appid, sale_start, sale_end, sale_days, max_discount_percent, uplift_pct,
           baseline_type
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
),

ref as (
    select
        s.*,
        a.* exclude (appid, sale_start),
        case when s.baseline_type = 'antes' then a.reviews_before else a.reviews_after end
            as reviews_ref,
        case when s.baseline_type = 'antes' then a.pct_positive_before else a.pct_positive_after end
            as pct_positive_ref,
        case when s.baseline_type = 'antes' then a.model_positive_before
             else a.model_positive_after end as model_positive_ref
    from sales as s
    inner join agg as a using (appid, sale_start)
)

select
    game_key,
    appid,
    sale_start,
    sale_end,
    sale_days,
    max_discount_percent,
    uplift_pct,
    baseline_type,
    reviews_before,
    reviews_during,
    reviews_after,
    reviews_ref,
    pct_positive_before,
    pct_positive_during,
    pct_positive_after,
    model_positive_before,
    model_positive_during,
    model_positive_after,
    -- cambio en puntos porcentuales (durante - referencia): > 0 = la opinión mejora con la rebaja
    round(100 * (pct_positive_during - pct_positive_ref), 2) as delta_during_pp,
    round(100 * (model_positive_during - model_positive_ref), 2) as model_delta_during_pp
from ref
