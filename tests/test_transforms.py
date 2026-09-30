"""Prueba las transformaciones de Spark en local, sin Kafka ni MinIO (necesita Java 17+)."""

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
