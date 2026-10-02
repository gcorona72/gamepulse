select
    appid,
    name,
    cast(captured_at as timestamp) as captured_at,
    capture_date,
    available,
    is_free,
    currency,
    initial_price_eur,
    final_price_eur,
    discount_percent,
    on_sale,
    genres,
    release_date,
    coming_soon
from {{ source('silver', 'steam_store') }}
