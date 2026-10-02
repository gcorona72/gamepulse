"""Prueba las transformaciones de Spark en local, sin Kafka ni MinIO (necesita Java 21 o 21)."""

import json
import shutil
from datetime import datetime

import pytest

pytest.importorskip("pyspark")
pytestmark = pytest.mark.skipif(shutil.which("java") is None, reason="Java no instalado")


@pytest.fixture(scope="module")
def spark():
    from pyspark.sql import SparkSession

    s = (
        SparkSession.builder.master("local[1]")
        .appName("tests")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield s
    s.stop()


def _kafka_df(spark, payloads):
    rows = [
        (b"k", p.encode(), "twitch.streams.snapshots", 0, i, datetime(2026, 9, 25, 18, 30))
        for i, p in enumerate(payloads)
    ]
    return spark.createDataFrame(
        rows,
        "key binary, value binary, topic string, partition int, offset long, timestamp timestamp",
    )


EVENT = {
    "event_version": 1,
    "event_id": "1-2026-09-25T18:30:00+00:00",
    "snapshot_ts": "2026-09-25T18:30:00+00:00",
    "game_id": "32982",
    "game_name": "GTA V",
    "igdb_id": "1020",
    "stream_id": "1",
    "user_id": "9",
    "user_login": "x",
    "viewer_count": 1500,
    "language": "es",
    "started_at": "2026-09-25T18:00:00Z",
    "is_mature": False,
}


def test_bronze_keeps_raw_payload(spark):
    from gamepulse.spark.transforms import kafka_to_bronze

    out = kafka_to_bronze(_kafka_df(spark, [json.dumps(EVENT)])).collect()[0]
    assert json.loads(out.payload) == EVENT
    assert str(out.event_date) == "2026-09-25"


def test_silver_parses_filters_and_dedupes(spark):
    from gamepulse.spark.transforms import kafka_to_bronze, twitch_bronze_to_silver

    payloads = [
        json.dumps(EVENT),
        json.dumps(EVENT),
        "no-es-json",
        json.dumps({**EVENT, "event_id": "2-x", "viewer_count": -5}),
    ]
    silver = twitch_bronze_to_silver(kafka_to_bronze(_kafka_df(spark, payloads)))
    rows = {r.event_id: r for r in silver.collect()}
    assert set(rows) == {"1-2026-09-25T18:30:00+00:00", "2-x"}  # duplicado y basura fuera
    assert rows["2-x"].viewer_count == 0  # negativos saneados
    assert isinstance(rows["2-x"].snapshot_ts, datetime)


def test_steam_players_silver_dedupes(spark):
    from gamepulse.spark.transforms import steam_players_to_silver

    rows = [("2026-10-02T10:00:00+00:00", 730, "CS2", 1000)] * 2 + [
        ("2026-10-02T11:00:00+00:00", 730, "CS2", None)
    ]
    schema = "snapshot_ts string, appid long, name string, player_count long"
    df = spark.createDataFrame(rows, schema)
    out = steam_players_to_silver(df).collect()
    assert len(out) == 2 and str(out[0].snapshot_date) == "2026-10-02"


def test_steam_store_silver_latest_per_day_and_euros(spark):
    from gamepulse.spark.schemas import STEAM_STORE_SCHEMA
    from gamepulse.spark.transforms import steam_store_to_silver

    base = dict(name="GTA V", available=True, type="game", is_free=False, currency="EUR",
                initial_price=2999, genres=["Acción"], release_date="2015", coming_soon=False)
    data = [
        {**base, "captured_at": "2026-10-02T08:00:00+00:00", "appid": 1, "final_price": 2999,
         "discount_percent": 0},
        {**base, "captured_at": "2026-10-02T20:00:00+00:00", "appid": 1, "final_price": 1499,
         "discount_percent": 50},
    ]
    df = spark.createDataFrame(data, STEAM_STORE_SCHEMA)
    out = steam_store_to_silver(df).collect()
    assert len(out) == 1
    assert float(out[0].final_price_eur) == 14.99 and out[0].on_sale is True


def test_steam_reviews_silver_keeps_last_edit_and_drops_empty(spark):
    from gamepulse.spark.schemas import STEAM_REVIEWS_SCHEMA
    from gamepulse.spark.transforms import steam_reviews_to_silver

    def r(rid, text, updated, voted_up=True):
        return {"captured_at": "2026-10-02T08:00:00+00:00", "appid": 1, "recommendationid": rid,
                "language": "spanish", "review": text, "voted_up": voted_up, "votes_up": 0,
                "weighted_vote_score": "0.5", "timestamp_created": 1759300000,
                "timestamp_updated": updated, "playtime_at_review_min": 60,
                "steam_purchase": True, "received_for_free": False,
                "written_during_early_access": False}

    data = [r("1", "malo", 1759300000, False), r("1", "bueno", 1759400000), r("2", "   ", 1)]
    df = spark.createDataFrame(data, STEAM_REVIEWS_SCHEMA)
    out = steam_reviews_to_silver(df).collect()
    assert len(out) == 1 and out[0].review == "bueno" and out[0].voted_up is True
    assert out[0].weighted_vote_score == 0.5
