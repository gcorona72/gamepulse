from datetime import UTC, datetime

from gamepulse.ingestion.events import build_stream_event

GAME = {"id": "32982", "name": "Grand Theft Auto V", "igdb_id": "1020"}
STREAM = {
    "id": "123",
    "user_id": "9",
    "user_login": "streamer",
    "viewer_count": "1500",
    "language": "es",
    "started_at": "2026-09-25T18:00:00Z",
    "is_mature": False,
}


def test_build_stream_event_contract():
    ts = datetime(2026, 9, 25, 18, 30, tzinfo=UTC)
    e = build_stream_event(STREAM, GAME, ts)
    assert e["event_id"] == "123-2026-09-25T18:30:00+00:00"
    assert e["viewer_count"] == 1500 and isinstance(e["viewer_count"], int)
    assert e["game_name"] == "Grand Theft Auto V"
    assert e["igdb_id"] == "1020"
    assert e["event_version"] == 1


def test_empty_igdb_id_becomes_none():
    e = build_stream_event(STREAM, {**GAME, "igdb_id": ""}, datetime.now(UTC))
    assert e["igdb_id"] is None
