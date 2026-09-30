"""Batch horario: jugadores simultáneos en Steam para la lista de juegos seguidos.
Escribe JSON Lines en la zona landing del lakehouse:
  s3://lakehouse/landing/steam/current_players/dt=YYYY-MM-DD/HHMMSS.jsonl

Ejecutar:  uv run python -m gamepulse.ingestion.steam_players_batch
(En la semana 7 lo programa Airflow cada hora.)
"""

import csv
from datetime import UTC, datetime
from pathlib import Path

from gamepulse.common.logging import get_logger
from gamepulse.common.storage import put_jsonl
from gamepulse.config import get_settings
from gamepulse.sources.steam import SteamClient

log = get_logger("steam_players_batch")
APPS_FILE = Path(__file__).resolve().parents[3] / "config" / "steam_apps.csv"


def load_apps(path: Path = APPS_FILE) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [{"appid": int(r["appid"]), "name": r["name"]} for r in csv.DictReader(f)]


def collect(client: SteamClient, apps: list[dict], snapshot_ts: datetime) -> list[dict]:
    records = []
    for app in apps:
        try:
            players = client.current_players(app["appid"])
        except Exception as exc:  # un juego que falla no tumba el batch
            log.warning("appid %s falló: %s", app["appid"], exc)
            players = None
        records.append(
            {
                "snapshot_ts": snapshot_ts.isoformat(timespec="seconds"),
                "appid": app["appid"],
                "name": app["name"],
                "player_count": players,
            }
        )
    return records


def main() -> None:
    settings = get_settings()
    snapshot_ts = datetime.now(UTC).replace(microsecond=0)
    records = collect(SteamClient(settings.steam_api_key), load_apps(), snapshot_ts)
    key = f"landing/steam/current_players/dt={snapshot_ts:%Y-%m-%d}/{snapshot_ts:%H%M%S}.jsonl"
    uri = put_jsonl(settings, key, records)
    ok = sum(r["player_count"] is not None for r in records)
    log.info("%s/%s juegos con dato -> %s", ok, len(records), uri)


if __name__ == "__main__":
    main()
