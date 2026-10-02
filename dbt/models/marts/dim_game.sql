-- Dimensión de juegos: une los juegos vistos en Twitch y los seguidos en Steam.
-- Clave: tw_<id de Twitch> si el juego aparece en Twitch; st_<appid> si solo está en Steam.
with twitch as (
    select
        twitch_game_id,
        arg_max(game_name, snapshot_ts) as game_name,
        arg_max(igdb_id, snapshot_ts) as igdb_id
    from {{ ref('stg_twitch_streams') }}
    group by twitch_game_id
),

twitch_linked as (
    select t.*, l.steam_appid
    from twitch as t
    left join {{ ref('int_twitch_steam_link') }} as l using (twitch_game_id)
),

steam_store as (
    select
        appid,
        arg_max(name, captured_at) as steam_name,
        arg_max(genres, captured_at) as genres,
        arg_max(release_date, captured_at) as release_date,
        arg_max(is_free, captured_at) as is_free
    from {{ ref('stg_steam_store') }}
    group by appid
),

steam_ids as (
    select appid, arg_max(name, snapshot_ts) as players_name
    from {{ ref('stg_steam_players') }}
    group by appid
),

steam_only as (
    select s.appid, s.players_name
    from steam_ids as s
    where s.appid not in (select steam_appid from twitch_linked where steam_appid is not null)
),

unioned as (
    select
        'tw_' || twitch_game_id as game_key,
        twitch_game_id,
        game_name,
        igdb_id,
        steam_appid
    from twitch_linked
    union all
    select
        'st_' || cast(appid as varchar) as game_key,
        null as twitch_game_id,
        players_name as game_name,
        null as igdb_id,
        appid as steam_appid
    from steam_only
)

select
    u.game_key,
    u.twitch_game_id,
    coalesce(u.game_name, st.steam_name) as game_name,
    u.igdb_id,
    u.steam_appid,
    st.genres,
    st.release_date,
    st.is_free,
    u.twitch_game_id is not null as in_twitch,
    u.steam_appid is not null as in_steam
from unioned as u
left join steam_store as st on st.appid = u.steam_appid
