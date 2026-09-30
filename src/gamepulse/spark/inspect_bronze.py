"""Comprobación rápida de la tabla bronze: filas por día y últimos mensajes.

Ejecutar:  uv run python -m gamepulse.spark.inspect_bronze
"""

from gamepulse.config import get_settings
from gamepulse.spark.session import build_spark
from gamepulse.spark.transforms import twitch_bronze_to_silver


def main() -> None:
    settings = get_settings()
    spark = build_spark("inspect_bronze", settings)
    bronze = spark.read.format("delta").load(f"{settings.lakehouse_uri}/bronze/twitch_streams")
    bronze.groupBy("event_date").count().orderBy("event_date").show()
    (
        twitch_bronze_to_silver(bronze)
        .groupBy("snapshot_ts", "game_name")
        .sum("viewer_count")
        .orderBy("snapshot_ts", ascending=False)
        .show(20, truncate=False)
    )


if __name__ == "__main__":
    main()
