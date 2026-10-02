"""Servicio de larga duración: cada STEAM_POLL_SECONDS actualiza el cruce Twitch <-> Steam
(game_map) y captura los jugadores de Steam. Una vez al día (UTC) captura además la ficha
de la tienda (precios, descuentos) y las reseñas nuevas.
Lo usa el contenedor `steam-players` (docker compose). En la semana 7 lo sustituye Airflow.

Ejecutar en local:  uv run python -m gamepulse.ingestion.steam_players_loop
"""
import signal
import time
from datetime import UTC, datetime

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.ingestion import (
    game_map_batch,
    steam_players_batch,
    steam_reviews_batch,
    steam_store_batch,
)

log = get_logger("steam_players_loop")
_running = True


def _stop(*_):
    global _running
    _running = False


def main() -> None:
    settings = get_settings()
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    log.info("Capturando jugadores de Steam cada %ss", settings.steam_poll_seconds)
    last_daily = None
    while _running:
        started = time.monotonic()
        try:
            game_map_batch.main()  # descubre juegos nuevos del top de Twitch
        except Exception:
            log.exception("Fallo en el cruce con IGDB; se usa la última lista conocida")
        try:
            steam_players_batch.main()
        except Exception:
            log.exception("Fallo en el batch de Steam; se reintenta en el siguiente ciclo")
        today = datetime.now(UTC).date()
        if last_daily != today:  # tareas diarias: precios y reseñas
            for job in (steam_store_batch, steam_reviews_batch):
                try:
                    job.main()
                except Exception:
                    log.exception("Fallo en %s; se reintenta mañana", job.__name__)
            last_daily = today
        while _running and time.monotonic() - started < settings.steam_poll_seconds:
            time.sleep(1)


if __name__ == "__main__":
    main()
