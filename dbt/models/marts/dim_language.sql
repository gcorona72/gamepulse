-- Idiomas de Twitch (código ISO 639-1) y de Steam (nombre propio de Steam) unificados por código ISO.
-- La correspondencia Steam -> ISO está en el seed language_map.csv.
with steam as (
    select distinct m.iso_code
    from {{ ref('stg_steam_reviews') }} as r
    inner join {{ ref('language_map') }} as m on m.steam_language = r.language
),

twitch as (
    select distinct lower(language) as iso_code
    from {{ ref('stg_twitch_streams') }}
    where language is not null and language <> ''
),

names as (
    select iso_code, min(language_name) as language_name
    from {{ ref('language_map') }}
    group by iso_code
)

select
    coalesce(t.iso_code, s.iso_code) as language_code,
    coalesce(n.language_name, upper(coalesce(t.iso_code, s.iso_code))) as language_name,
    t.iso_code is not null as in_twitch,
    s.iso_code is not null as in_steam
from twitch as t
full outer join steam as s on s.iso_code = t.iso_code
left join names as n on n.iso_code = coalesce(t.iso_code, s.iso_code)
