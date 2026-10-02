-- Una fila por reseña. voted_up es la etiqueta para el modelo de sentimiento (semana 9).
with game_keys as (
    select steam_appid as appid, min(game_key) as game_key
    from {{ ref('dim_game') }}
    where steam_appid is not null
    group by steam_appid
)

select
    r.recommendationid,
    k.game_key,
    r.appid,
    r.review_date as date_day,
    r.created_at,
    r.language,
    r.voted_up,
    r.votes_up,
    r.weighted_vote_score,
    r.playtime_at_review_min,
    r.steam_purchase,
    r.received_for_free,
    r.written_during_early_access,
    length(r.review) as review_length,
    r.review
from {{ ref('stg_steam_reviews') }} as r
left join game_keys as k using (appid)
