"""Productor de streaming: cada N segundos toma una 'foto' de los directos de los juegos
más vistos de Twitch y publica un evento por directo en Kafka.

Ejecutar:  uv run python -m gamepulse.ingestion.twitch_producer
"""

import json
import signal
import time
from datetime import UTC, datetime

from confluent_kafka import Producer

from gamepulse.common.logging import get_logger
from gamepulse.config import get_settings
from gamepulse.ingestion.events import build_stream_event
from gamepulse.sources.twitch import TwitchClient

log = get_logger("twitch_producer")
_running = True


def _stop(*_):
    global _running
    _running = False
    log.info("Parando el productor...")


def _delivery_report(err, msg):
    if err is not None:
        log.error("Fallo al entregar el mensaje: %s", err)


def poll_once(client: TwitchClient, producer: Producer, topic: str, top_n: int) -> int:
    snapshot_ts = datetime.now(UTC).replace(microsecond=0)
    sent = 0
    for game in client.top_games(top_n):
        for stream in client.streams_for_game(game["id"], limit=100):
            event = build_stream_event(stream, game, snapshot_ts)
            producer.produce(
                topic,
                key=event["game_id"],
                value=json.dumps(event, ensure_ascii=False),
                on_delivery=_delivery_report,
            )
            sent += 1
        producer.poll(0)
    producer.flush(30)
    return sent


def main() -> None:
    settings = get_settings()
    client = TwitchClient(settings.twitch_client_id, settings.twitch_client_secret)
    producer = Producer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "enable.idempotence": True,
            "compression.type": "zstd",
            "linger.ms": 50,
        }
    )
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    log.info(
        "Publicando en '%s' cada %ss (top %s juegos)",
        settings.twitch_topic,
        settings.twitch_poll_seconds,
        settings.twitch_top_games,
    )
    while _running:
        started = time.monotonic()
        try:
            sent = poll_once(client, producer, settings.twitch_topic, settings.twitch_top_games)
            log.info("Snapshot enviado: %s eventos en %.1fs", sent, time.monotonic() - started)
        except Exception:
            log.exception("Error en el snapshot; se reintenta en el siguiente ciclo")
        # Espera hasta el siguiente ciclo sin bloquear el Ctrl+C
        while _running and time.monotonic() - started < settings.twitch_poll_seconds:
            time.sleep(0.5)
    producer.flush(30)


if __name__ == "__main__":
    main()
