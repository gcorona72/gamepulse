-- Pregunta 4. Sentimiento por juego y día: lo que marca el autor (voted_up) frente a lo que
-- el modelo lee en el texto. Base para cruzar con rebajas, actualizaciones y jugadores.
select
    game_key,
    appid,
    date_day,
    count(*) as reviews,
    avg(cast(voted_up as int)) as pct_voted_up,
    avg(cast(pred_positive as int)) as pct_pred_positive,
    avg(sentiment_score) as avg_sentiment_score,
    avg(cast(model_agrees as int)) as agreement
from {{ ref('fct_review_sentiment') }}
group by game_key, appid, date_day
