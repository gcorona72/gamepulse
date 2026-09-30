"""Servicio de larga duración: ejecuta el batch de jugadores de Steam cada STEAM_POLL_SECONDS.
Lo usa el contenedor `steam-players` (docker compose). En la semana 7 lo sustituye Airflow.

Ejecutar en local:  uv run python -m gamepulse.ingestion.steam_players_loop
"""
import signal
import time

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.ingestion import steam_players_batch

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
    while _running:
        started = time.monotonic()
        try:
            steam_players_batch.main()
        except Exception:
            log.exception("Fallo en el batch de Steam; se reintenta en el siguiente ciclo")
        while _running and time.monotonic() - started < settings.steam_poll_seconds:
            time.sleep(1)


if __name__ == "__main__":
    main()
