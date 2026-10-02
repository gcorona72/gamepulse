"""Batch diario: ficha de la tienda de Steam (precio, descuento, géneros) de los juegos seguidos.
Escribe JSON Lines en la zona landing del lakehouse:
  s3://lakehouse/landing/steam/store/dt=YYYY-MM-DD/HHMMSS.jsonl

Ejecutar:  uv run python -m gamepulse.ingestion.steam_store_batch
"""

import time
from datetime import UTC, datetime

from gamepulse.common.logging import get_logger
from gamepulse.common.storage import ensure_bucket, get_json, put_jsonl
from gamepulse.config import get_settings
from gamepulse.ingestion.steam_players_batch import load_apps, merge_apps
from gamepulse.sources.steam import SteamClient

log = get_logger("steam_store_batch")
STORE_PAUSE_S = 1.5  # la API de la tienda limita a unas 200 peticiones cada 5 minutos


def parse_store(app: dict, data: dict | None, ts: datetime) -> dict:
    """Aplana la ficha de la tienda. Precios en céntimos; None si no está a la venta."""
    data = data or {}
    price = data.get("price_overview") or {}
    return {
        "captured_at": ts.isoformat(timespec="seconds"),
        "appid": app["appid"],
        "name": data.get("name") or app["name"],
        "available": bool(data),
        "type": data.get("type"),
        "is_free": data.get("is_free"),
        "currency": price.get("currency"),
        "initial_price": price.get("initial"),
        "final_price": price.get("final"),
        "discount_percent": price.get("discount_percent", 0 if data.get("is_free") else None),
        "genres": [g["description"] for g in data.get("genres", [])],
        "release_date": (data.get("release_date") or {}).get("date"),
        "coming_soon": (data.get("release_date") or {}).get("coming_soon"),
    }


def main() -> None:
    settings = get_settings()
    ensure_bucket(settings)
    ts = datetime.now(UTC).replace(microsecond=0)
    client = SteamClient(settings.steam_api_key)
    apps = merge_apps(load_apps(), get_json(settings, "landing/igdb/steam_tracked_apps.json", []))
    records = []
    for app in apps:
        try:
            data = client.app_details(app["appid"])
        except Exception as exc:
            log.warning("appid %s falló: %s", app["appid"], exc)
            data = None
        records.append(parse_store(app, data, ts))
        time.sleep(STORE_PAUSE_S)
    uri = put_jsonl(settings, f"landing/steam/store/dt={ts:%Y-%m-%d}/{ts:%H%M%S}.jsonl", records)
    on_sale = sum((r["discount_percent"] or 0) > 0 for r in records)
    log.info("%s fichas (%s en rebaja) -> %s", len(records), on_sale, uri)


if __name__ == "__main__":
    main()
