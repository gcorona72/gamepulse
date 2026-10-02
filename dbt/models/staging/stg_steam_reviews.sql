select
    recommendationid,
    appid,
    language,
    review,
    voted_up,
    votes_up,
    weighted_vote_score,
    playtime_at_review_min,
    cast(created_at as timestamp) as created_at,
    review_date,
    steam_purchase,
    received_for_free,
    written_during_early_access
from {{ source('silver', 'steam_reviews') }}
