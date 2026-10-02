"""Batch diario e incremental: reseñas de Steam de los juegos seguidos.

Cada ejecución solo descarga las reseñas nuevas desde la anterior (estado por juego en
landing/steam/_state/reviews.json). La primera vez trae hasta MAX_PAGES_FIRST_RUN páginas por juego.
Escribe JSON Lines:  s3://lakehouse/landing/steam/reviews/dt=YYYY-MM-DD/HHMMSS.jsonl

Las reseñas traen `voted_up` (recomienda sí/no): son las etiquetas del modelo de sentimiento.

Ejecutar:  uv run python -m gamepulse.ingestion.steam_reviews_batch
"""

import time
from datetime import UTC, datetime

from gamepulse.common.logging import get_logger
from gamepulse.common.storage import ensure_bucket, get_json, put_json, put_jsonl
from gamepulse.config import get_settings
from gamepulse.ingestion.steam_players_batch import load_apps, merge_apps
from gamepulse.sources.steam import SteamClient

log = get_logger("steam_reviews_batch")
STATE_KEY = "landing/steam/_state/reviews.json"
MAX_PAGES_FIRST_RUN = 20  # 100 reseñas por página -> hasta 2.000 por juego la primera vez
MAX_PAGES_INCREMENTAL = 50
PAGE_PAUSE_S = 1.0


def parse_reviews(appid: int, page: dict, since: int, ts: datetime) -> tuple[list[dict], bool]:
    """Convierte una página de reseñas en registros. Devuelve (registros, llegó_a_lo_ya_visto).
    `since` es el timestamp_created más reciente guardado en la ejecución anterior."""
    records, reached_old = [], False
    for r in page.get("reviews", []):
        if r.get("timestamp_created", 0) <= since:
            reached_old = True
            continue
        author = r.get("author") or {}
        records.append(
            {
                "captured_at": ts.isoformat(timespec="seconds"),
                "appid": appid,
                "recommendationid": r.get("recommendationid"),
                "language": r.get("language"),
                "review": r.get("review"),
                "voted_up": r.get("voted_up"),
                "votes_up": r.get("votes_up"),
                "weighted_vote_score": r.get("weighted_vote_score"),
                "timestamp_created": r.get("timestamp_created"),
                "timestamp_updated": r.get("timestamp_updated"),
                "playtime_at_review_min": author.get("playtime_at_review"),
                "steam_purchase": r.get("steam_purchase"),
                "received_for_free": r.get("received_for_free"),
                "written_during_early_access": r.get("written_during_early_access"),
            }
        )
    return records, reached_old


def fetch_new_reviews(client: SteamClient, appid: int, since: int, ts: datetime) -> list[dict]:
    max_pages = MAX_PAGES_FIRST_RUN if since == 0 else MAX_PAGES_INCREMENTAL
    cursor, out, seen_cursors = "*", [], set()
    for _ in range(max_pages):
        page = client.reviews_page(appid, cursor=cursor)
        records, reached_old = parse_reviews(appid, page, since, ts)
        out += records
        cursor = page.get("cursor")
        if reached_old or not page.get("reviews") or not cursor or cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        time.sleep(PAGE_PAUSE_S)
    return out


def main() -> None:
    settings = get_settings()
    ensure_bucket(settings)
    ts = datetime.now(UTC).replace(microsecond=0)
    client = SteamClient(settings.steam_api_key)
    apps = merge_apps(load_apps(), get_json(settings, "landing/igdb/steam_tracked_apps.json", []))
    state: dict[str, int] = get_json(settings, STATE_KEY, {})
    all_records = []
    for app in apps:
        key = str(app["appid"])
        try:
            records = fetch_new_reviews(client, app["appid"], state.get(key, 0), ts)
        except Exception as exc:
            log.warning("appid %s falló: %s", app["appid"], exc)
            continue
        if records:
            state[key] = max(r["timestamp_created"] for r in records)
        all_records += records
        log.info("%s: %s reseñas nuevas", app["name"], len(records))
    if all_records:
        uri = put_jsonl(
            settings, f"landing/steam/reviews/dt={ts:%Y-%m-%d}/{ts:%H%M%S}.jsonl", all_records
        )
        log.info("%s reseñas -> %s", len(all_records), uri)
    put_json(settings, STATE_KEY, state)  # después de escribir los datos: si falla, se repite


if __name__ == "__main__":
    main()
