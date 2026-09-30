"""Transformaciones puras (DataFrame -> DataFrame). Se prueban sin Kafka ni MinIO."""

from pyspark.sql import DataFrame
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
