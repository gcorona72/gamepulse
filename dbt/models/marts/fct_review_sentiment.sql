-- Una fila por reseña con la predicción del modelo de sentimiento (XLM-RoBERTa).
-- Las predicciones las escribe src/gamepulse/ml/predict_sentiment.py en ml.review_sentiment.
with latest as (
    -- por seguridad, si una reseña se puntuó dos veces, quedarse con la predicción más reciente
    select *
    from {{ source('ml', 'review_sentiment') }}
    qualify row_number() over (partition by recommendationid order by scored_at desc) = 1
)

select
    r.recommendationid,
    r.game_key,
    r.appid,
    r.date_day,
    r.language,
    r.voted_up,
    s.sentiment_pred = 1 as pred_positive,
    s.sentiment_score,
    (s.sentiment_pred = 1) = r.voted_up as model_agrees,
    s.model_version
from {{ ref('fct_reviews') }} as r
inner join latest as s using (recommendationid)
