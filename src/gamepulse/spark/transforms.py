"""Transformaciones puras (DataFrame -> DataFrame). Se prueban sin Kafka ni MinIO."""

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from gamepulse.spark.schemas import TWITCH_EVENT_SCHEMA


def kafka_to_bronze(df: DataFrame) -> DataFrame:
    """Bronze = el mensaje tal cual llega + metadatos de Kafka. Sin interpretar el contenido,
    para poder reprocesar si cambia la lógica aguas abajo."""
    return df.select(
        F.col("key").cast("string").alias("kafka_key"),
        F.col("value").cast("string").alias("payload"),
        "topic",
        "partition",
        "offset",
        F.col("timestamp").alias("kafka_ts"),
        F.current_timestamp().alias("ingested_at"),
        F.to_date("timestamp").alias("event_date"),
    )


def twitch_bronze_to_silver(df: DataFrame) -> DataFrame:
    """Silver (semana 4): parsea el JSON, tipa columnas, descarta basura y deduplica."""
    parsed = df.select(F.from_json("payload", TWITCH_EVENT_SCHEMA).alias("e"), "kafka_ts")
    return (
        parsed.select("e.*", "kafka_ts")
        .where(F.col("event_id").isNotNull() & F.col("game_id").isNotNull())
        .withColumn("snapshot_ts", F.to_timestamp("snapshot_ts"))
        .withColumn("started_at", F.to_timestamp("started_at"))
        .withColumn("viewer_count", F.greatest(F.col("viewer_count"), F.lit(0)))
        .withColumn("snapshot_date", F.to_date("snapshot_ts"))
        .dropDuplicates(["event_id"])
    )


def _latest_per_key(df: DataFrame, keys: list[str], order_col: str) -> DataFrame:
    """Deduplica quedándose con la versión más reciente de cada clave."""
    w = Window.partitionBy(*keys).orderBy(F.col(order_col).desc())
    return df.withColumn("_rn", F.row_number().over(w)).where("_rn = 1").drop("_rn")


def steam_players_to_silver(df: DataFrame) -> DataFrame:
    """Jugadores simultáneos: tipado, sin duplicados por (juego, instante)."""
    return (
        df.withColumn("snapshot_ts", F.to_timestamp("snapshot_ts"))
        .where(F.col("appid").isNotNull() & F.col("snapshot_ts").isNotNull())
        .withColumn("snapshot_date", F.to_date("snapshot_ts"))
        .dropDuplicates(["appid", "snapshot_ts"])
    )


def steam_store_to_silver(df: DataFrame) -> DataFrame:
    """Ficha de la tienda: una fila por juego y día (la última captura), precios en euros."""
    out = (
        df.withColumn("captured_at", F.to_timestamp("captured_at"))
        .where(F.col("appid").isNotNull() & F.col("captured_at").isNotNull())
        .withColumn("capture_date", F.to_date("captured_at"))
        .withColumn("initial_price_eur", (F.col("initial_price") / 100).cast("decimal(10,2)"))
        .withColumn("final_price_eur", (F.col("final_price") / 100).cast("decimal(10,2)"))
        .withColumn("on_sale", F.coalesce(F.col("discount_percent"), F.lit(0)) > 0)
        .drop("initial_price", "final_price")
    )
    return _latest_per_key(out, ["appid", "capture_date"], "captured_at")


def steam_reviews_to_silver(df: DataFrame) -> DataFrame:
    """Reseñas: una fila por reseña (su última edición), fechas tipadas, sin textos vacíos."""
    out = (
        df.where(F.col("recommendationid").isNotNull())
        .where(F.length(F.trim(F.coalesce(F.col("review"), F.lit("")))) > 0)
        .withColumn("created_at", F.to_timestamp(F.from_unixtime("timestamp_created")))
        .withColumn("updated_at", F.to_timestamp(F.from_unixtime("timestamp_updated")))
        .withColumn("review_date", F.to_date("created_at"))
        .withColumn("weighted_vote_score", F.col("weighted_vote_score").cast("double"))
        .withColumn("captured_at", F.to_timestamp("captured_at"))
        .drop("timestamp_created", "timestamp_updated")
    )
    return _latest_per_key(out, ["recommendationid"], "updated_at")


def game_map_to_silver(df: DataFrame) -> DataFrame:
    """Cruce Twitch <-> Steam: histórico sin duplicados por (juego de Twitch, captura)."""
    return (
        df.withColumn("captured_at", F.to_timestamp("captured_at"))
        .where(F.col("twitch_game_id").isNotNull())
        .dropDuplicates(["twitch_game_id", "captured_at"])
    )
