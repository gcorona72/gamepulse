"""Construcción de eventos: el contrato de datos del topic twitch.streams.snapshots."""

from datetime import datetime

EVENT_VERSION = 1


def build_stream_event(stream: dict, game: dict, snapshot_ts: datetime) -> dict:
    """Convierte un directo de la API de Twitch en un evento plano y versionado."""
    ts = snapshot_ts.isoformat(timespec="seconds")
    return {
        "event_version": EVENT_VERSION,
        "event_id": f"{stream['id']}-{ts}",
        "snapshot_ts": ts,
        "game_id": game["id"],
        "game_name": game.get("name"),
        "igdb_id": game.get("igdb_id") or None,
        "stream_id": stream["id"],
        "user_id": stream.get("user_id"),
        "user_login": stream.get("user_login"),
        "viewer_count": int(stream.get("viewer_count", 0)),
        "language": stream.get("language"),
        "started_at": stream.get("started_at"),
        "is_mature": bool(stream.get("is_mature", False)),
    }
