from datetime import UTC, datetime

from gamepulse.ingestion.game_map_batch import build_game_map

TS = datetime(2026, 10, 1, tzinfo=UTC)
TOP = [
    {"id": "32982", "name": "Grand Theft Auto V", "igdb_id": "1020"},
    {"id": "509658", "name": "Just Chatting", "igdb_id": ""},
    {"id": "33214", "name": "Fortnite", "igdb_id": "1905"},
]
EXTERNAL = [
    {"game": 1020, "uid": "271590", "external_game_source": 1},  # Steam
    {"game": 1020, "uid": "999999", "external_game_source": 1},  # otra edición en Steam
    {"game": 1020, "uid": "abc", "external_game_source": 5},  # otra tienda
    {"game": 1905, "uid": "fortnite", "category": 26},  # no está en Steam (campo antiguo)
]


def test_cruce_twitch_steam():
    rows = build_game_map(TOP, EXTERNAL, TS)
    by_name = {r["game_name"]: r for r in rows}
    assert by_name["Grand Theft Auto V"]["steam_appid"] == 271590  # el menor appid
    assert by_name["Fortnite"]["steam_appid"] is None
    assert by_name["Just Chatting"]["igdb_id"] is None
    assert [r["twitch_rank"] for r in rows] == [1, 2, 3]


def test_campo_antiguo_category():
    rows = build_game_map(TOP[:1], [{"game": 1020, "uid": "271590", "category": 1}], TS)
    assert rows[0]["steam_appid"] == 271590
