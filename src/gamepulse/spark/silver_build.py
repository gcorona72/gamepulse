"""Batch: construye la capa silver (Delta) a partir de bronze y de la zona landing.

- twitch_streams: incremental. Reprocesa los últimos --days días de bronze y sustituye
  esas particiones (replaceWhere): idempotente, se puede repetir sin duplicar.
  Con --full (o si la tabla no existe) reprocesa todo el histórico.
- steam_players, steam_store, steam_reviews, game_map: pequeñas; se reconstruyen enteras.

Ejecutar:  uv run python -m gamepulse.spark.silver_build [--days 2] [--full]
"""

import argparse
from datetime import UTC, datetime, timedelta

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.spark import schemas, transforms
from gamepulse.spark.session import build_spark

log = get_logger("silver_build")

LANDING_TABLES = {
    # tabla silver: (carpeta en landing, esquema, transformación, columna de partición)
    "steam_players": (
        "landing/steam/current_players",
        schemas.STEAM_PLAYERS_SCHEMA,
        transforms.steam_players_to_silver,
        "snapshot_date",
    ),
    "steam_store": (
        "landing/steam/store",
        schemas.STEAM_STORE_SCHEMA,
        transforms.steam_store_to_silver,
        "capture_date",
    ),
    "steam_reviews": (
        "landing/steam/reviews",
        schemas.STEAM_REVIEWS_SCHEMA,
        transforms.steam_reviews_to_silver,
        None,
    ),
    "game_map": (
        "landing/igdb/game_map",
        schemas.GAME_MAP_SCHEMA,
        transforms.game_map_to_silver,
        None,
    ),
}


def _write_full(df: DataFrame, path: str, partition: str | None) -> None:
    writer = df.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
    if partition:
        writer = writer.partitionBy(partition)
    writer.save(path)


def build_twitch(spark: SparkSession, root: str, days: int, full: bool) -> None:
    bronze = spark.read.format("delta").load(f"{root}/bronze/twitch_streams")
    target = f"{root}/silver/twitch_streams"
    if full or not DeltaTable.isDeltaTable(spark, target):
        silver = transforms.twitch_bronze_to_silver(bronze)
        _write_full(silver, target, "snapshot_date")
        log.info("twitch_streams: reconstrucción completa")
        return
    start = (datetime.now(UTC) - timedelta(days=days - 1)).date()
    # un día más de bronze: un snapshot de las 23:59 puede llegar a Kafka pasada la medianoche
    recent = bronze.where(F.col("event_date") >= F.lit(start - timedelta(days=1)))
    silver = transforms.twitch_bronze_to_silver(recent).where(
        F.col("snapshot_date") >= F.lit(start)
    )
    (
        silver.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"snapshot_date >= '{start}'")
        .save(target)
    )
    log.info("twitch_streams: particiones desde %s actualizadas", start)


def build_landing(spark: SparkSession, root: str) -> None:
    for table, (folder, schema, transform, partition) in LANDING_TABLES.items():
        try:
            raw = spark.read.schema(schema).json(f"{root}/{folder}/dt=*/*.jsonl")
        except Exception as exc:  # aún no hay ficheros en landing
            log.warning("%s: sin datos en landing (%s)", table, type(exc).__name__)
            continue
        _write_full(transform(raw), f"{root}/silver/{table}", partition)
        log.info("%s: reconstruida", table)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2, help="días de Twitch a reprocesar")
    parser.add_argument("--full", action="store_true", help="reprocesar todo Twitch")
    args = parser.parse_args()

    settings = get_settings()
    spark = build_spark("silver_build", settings)
    root = settings.lakehouse_uri
    build_twitch(spark, root, args.days, args.full)
    build_landing(spark, root)
    for table in ["twitch_streams", *LANDING_TABLES]:
        path = f"{root}/silver/{table}"
        if DeltaTable.isDeltaTable(spark, path):
            log.info("silver.%s: %s filas", table, spark.read.format("delta").load(path).count())
    spark.stop()


if __name__ == "__main__":
    main()
