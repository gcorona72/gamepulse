from datetime import UTC, datetime

from gamepulse.ingestion.steam_reviews_batch import parse_reviews
from gamepulse.ingestion.steam_store_batch import parse_store

TS = datetime(2026, 10, 2, tzinfo=UTC)
APP = {"appid": 271590, "name": "GTA V"}


def test_parse_store_en_rebaja():
    data = {
        "name": "Grand Theft Auto V",
        "type": "game",
        "is_free": False,
        "price_overview": {
            "currency": "EUR", "initial": 2999, "final": 1499, "discount_percent": 50
        },
        "genres": [{"id": "1", "description": "Acción"}],
        "release_date": {"coming_soon": False, "date": "13 ABR 2015"},
    }
    r = parse_store(APP, data, TS)
    assert (r["final_price"], r["discount_percent"], r["genres"]) == (1499, 50, ["Acción"])
    assert r["available"] is True


def test_parse_store_gratis_y_no_disponible():
    assert parse_store(APP, {"is_free": True}, TS)["discount_percent"] == 0
    r = parse_store(APP, None, TS)
    assert r["available"] is False and r["name"] == "GTA V" and r["final_price"] is None


def test_parse_reviews_incremental():
    page = {
        "reviews": [
            {"recommendationid": "3", "timestamp_created": 300, "voted_up": True, "review": "top",
             "author": {"playtime_at_review": 120}},
            {"recommendationid": "2", "timestamp_created": 200, "voted_up": False, "review": "meh"},
        ]
    }
    recs, reached_old = parse_reviews(271590, page, since=200, ts=TS)
    assert [r["recommendationid"] for r in recs] == ["3"]
    assert reached_old is True and recs[0]["playtime_at_review_min"] == 120
    recs, reached_old = parse_reviews(271590, page, since=0, ts=TS)
    assert len(recs) == 2 and reached_old is False
