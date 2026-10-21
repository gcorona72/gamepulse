"""Mantenimiento del lakehouse: VACUUM de las tablas silver.

silver_build reescribe las tablas cada hora (overwrite / replaceWhere). Delta Lake no borra
los ficheros sustituidos: los marca como obsoletos en el _delta_log para permitir time travel
y siguen ocupando disco. VACUUM elimina los ficheros que ya no pertenecen a la versión actual
y son más antiguos que el periodo de retención. Los datos actuales no se tocan.

Bronze no se limpia: es append-only (streaming), así que no genera ficheros obsoletos.

Ejecutar:  uv run python -m gamepulse.spark.maintenance [--retain-hours 24] [--dry-run]
"""

import argparse

from delta.tables import DeltaTable

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.spark.session import build_spark
from gamepulse.spark.silver_build import LANDING_TABLES

log = get_logger("maintenance")

SILVER_TABLES = ["twitch_streams", *LANDING_TABLES]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--retain-hours",
        type=int,
        default=24,
        help="horas de historial (time travel) que se conservan; por defecto 24",
    )
    parser.add_argument("--dry-run", action="store_true", help="solo lista lo que borraría")
    args = parser.parse_args()

    settings = get_settings()
    spark = build_spark("lakehouse_maintenance", settings)
    # Delta exige 168 h por defecto; con un pipeline horario y lectores que solo usan la
    # versión actual, 24 h es seguro. Se desactiva la comprobación solo en esta sesión.
    spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")

    root = settings.lakehouse_uri
    for table in SILVER_TABLES:
        path = f"{root}/silver/{table}"
        if not DeltaTable.isDeltaTable(spark, path):
            log.warning("silver.%s: no existe, se omite", table)
            continue
        dry = " DRY RUN" if args.dry_run else ""
        result = spark.sql(f"VACUUM delta.`{path}` RETAIN {args.retain_hours} HOURS{dry}")
        if args.dry_run:
            log.info("silver.%s: %s ficheros se borrarían", table, result.count())
        else:
            log.info("silver.%s: VACUUM completado (retención %s h)", table, args.retain_hours)
    spark.stop()


if __name__ == "__main__":
    main()
