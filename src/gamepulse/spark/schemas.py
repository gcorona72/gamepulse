"""Esquemas explícitos (nunca inferidos en producción)."""

from pyspark.sql.types import (
    BooleanType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# Contrato del topic twitch.streams.snapshots (ver ingestion/events.py)
TWITCH_EVENT_SCHEMA = StructType(
    [
        StructField("event_version", IntegerType()),
        StructField("event_id", StringType()),
        StructField("snapshot_ts", StringType()),
        StructField("game_id", StringType()),
        StructField("game_name", StringType()),
        StructField("igdb_id", StringType()),
        StructField("stream_id", StringType()),
        StructField("user_id", StringType()),
        StructField("user_login", StringType()),
        StructField("viewer_count", LongType()),
        StructField("language", StringType()),
        StructField("started_at", StringType()),
        StructField("is_mature", BooleanType()),
    ]
)
