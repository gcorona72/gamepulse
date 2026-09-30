"""Job de Spark Structured Streaming: Kafka (twitch.streams.snapshots) -> Delta bronze en MinIO.

Ejecutar (con docker compose levantado y el productor en marcha):
  uv run python -m gamepulse.spark.twitch_stream_to_bronze
La primera ejecución descarga los conectores de Maven (unos minutos).
"""

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.spark.session import build_spark
from gamepulse.spark.transforms import kafka_to_bronze

log = get_logger("twitch_stream_to_bronze")


def main() -> None:
    settings = get_settings()
    spark = build_spark("twitch_stream_to_bronze", settings)
    table_path = f"{settings.lakehouse_uri}/bronze/twitch_streams"
    checkpoint = f"{settings.lakehouse_uri}/_checkpoints/bronze_twitch_streams"

    source = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.twitch_topic)
        .option("startingOffsets", "earliest")
        .option("maxOffsetsPerTrigger", 200_000)
        .load()
    )

    query = (
        kafka_to_bronze(source)
        .writeStream.format("delta")
        .outputMode("append")
        .option("checkpointLocation", checkpoint)  # garantiza exactly-once al reiniciar
        .partitionBy("event_date")
        .trigger(processingTime="1 minute")
        .start(table_path)
    )
    log.info("Streaming activo -> %s", table_path)
    query.awaitTermination()


if __name__ == "__main__":
    main()
