"""Esquemas explícitos (nunca inferidos en producción)."""

from pyspark.sql.types import (
    ArrayType,
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


# --- Zona landing (JSON Lines escritos por los batch de ingestion/) ---
STEAM_PLAYERS_SCHEMA = StructType(
    [
        StructField("snapshot_ts", StringType()),
        StructField("appid", LongType()),
        StructField("name", StringType()),
        StructField("player_count", LongType()),
    ]
)

STEAM_STORE_SCHEMA = StructType(
    [
        StructField("captured_at", StringType()),
        StructField("appid", LongType()),
        StructField("name", StringType()),
        StructField("available", BooleanType()),
        StructField("type", StringType()),
        StructField("is_free", BooleanType()),
        StructField("currency", StringType()),
        StructField("initial_price", LongType()),
        StructField("final_price", LongType()),
        StructField("discount_percent", IntegerType()),
        StructField("genres", ArrayType(StringType())),
        StructField("release_date", StringType()),
        StructField("coming_soon", BooleanType()),
    ]
)

STEAM_REVIEWS_SCHEMA = StructType(
    [
        StructField("captured_at", StringType()),
        StructField("appid", LongType()),
        StructField("recommendationid", StringType()),
        StructField("language", StringType()),
        StructField("review", StringType()),
        StructField("voted_up", BooleanType()),
        StructField("votes_up", LongType()),
        StructField("weighted_vote_score", StringType()),
        StructField("timestamp_created", LongType()),
        StructField("timestamp_updated", LongType()),
        StructField("playtime_at_review_min", LongType()),
        StructField("steam_purchase", BooleanType()),
        StructField("received_for_free", BooleanType()),
        StructField("written_during_early_access", BooleanType()),
    ]
)

GAME_MAP_SCHEMA = StructType(
    [
        StructField("captured_at", StringType()),
        StructField("twitch_rank", IntegerType()),
        StructField("twitch_game_id", StringType()),
        StructField("game_name", StringType()),
        StructField("igdb_id", LongType()),
        StructField("steam_appid", LongType()),
    ]
)
