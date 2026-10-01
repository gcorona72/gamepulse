"""Batch diario: tabla de correspondencia Twitch <-> IGDB <-> Steam.

Para los juegos más vistos en Twitch obtiene su `igdb_id` y, vía IGDB, su `appid` de Steam.
Escribe JSON Lines en la zona landing del lakehouse:
  s3://lakehouse/landing/igdb/game_map/dt=YYYY-MM-DD/HHMMSS.jsonl

Además mantiene la lista acumulada de juegos de Steam a seguir (nunca se borra ninguno,
para no cortar su histórico):  s3://lakehouse/landing/igdb/steam_tracked_apps.json
La usa el batch de jugadores de Steam junto con config/steam_apps.csv.

Ejecutar:  uv run python -m gamepulse.ingestion.game_map_batch
"""

from datetime import UTC, datetime

from gamepulse.common.logging import get_logger
from gamepulse.common.storage import ensure_bucket, get_json, put_json, put_jsonl
from gamepulse.config import get_settings
from gamepulse.ingestion.steam_players_batch import load_apps
from gamepulse.sources.igdb import IgdbClient, is_steam
from gamepulse.sources.twitch import TwitchClient

log = get_logger("game_map_batch")
TRACKED_KEY = "landing/igdb/steam_tracked_apps.json"


def build_game_map(top_games: list[dict], external: list[dict], ts: datetime) -> list[dict]:
    """Une los juegos de Twitch con su appid de Steam. Sin appid -> None (no es de Steam)."""
    steam_by_igdb: dict[int, int] = {}
    for ext in external:
        if is_steam(ext) and str(ext.get("uid", "")).isdigit():
            # si un juego tiene varios appid (ediciones), nos quedamos con el menor (el original)
            appid = int(ext["uid"])
            gid = int(ext["game"])
            steam_by_igdb[gid] = min(appid, steam_by_igdb.get(gid, appid))
    records = []
    for rank, g in enumerate(top_games, start=1):
        igdb_id = int(g["igdb_id"]) if str(g.get("igdb_id") or "").isdigit() else None
        records.append(
            {
                "captured_at": ts.isoformat(timespec="seconds"),
                "twitch_rank": rank,
                "twitch_game_id": g["id"],
                "game_name": g["name"],
                "igdb_id": igdb_id,
                "steam_appid": steam_by_igdb.get(igdb_id) if igdb_id else None,
            }
        )
    return records


def merge_tracked(existing: list[dict], records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Añade a la lista acumulada los juegos con appid de Steam que aún no estaban.
    Devuelve (lista completa, nuevos)."""
    known = {a["appid"] for a in existing}
    new = []
    for r in records:
        if r["steam_appid"] and r["steam_appid"] not in known:
            known.add(r["steam_appid"])
            new.append(
                {"appid": r["steam_appid"], "name": r["game_name"], "first_seen": r["captured_at"]}
            )
    return existing + new, new


def main() -> None:
    settings = get_settings()
    ensure_bucket(settings)
    ts = datetime.now(UTC).replace(microsecond=0)
    twitch = TwitchClient(settings.twitch_client_id, settings.twitch_client_secret)
    top = twitch.top_games(settings.twitch_top_games)
    igdb_ids = [int(g["igdb_id"]) for g in top if str(g.get("igdb_id") or "").isdigit()]
    records = build_game_map(top, IgdbClient(twitch).external_games(igdb_ids), ts)

    key = f"landing/igdb/game_map/dt={ts:%Y-%m-%d}/{ts:%H%M%S}.jsonl"
    uri = put_jsonl(settings, key, records)
    with_steam = [r for r in records if r["steam_appid"]]
    log.info("%s/%s juegos de Twitch con appid de Steam -> %s", len(with_steam), len(records), uri)

    seed = {a["appid"] for a in load_apps()}
    existing = [a for a in get_json(settings, TRACKED_KEY, default=[]) if a["appid"] not in seed]
    tracked, new = merge_tracked(existing, [r for r in records if r["steam_appid"] not in seed])
    if new:
        put_json(settings, TRACKED_KEY, tracked)
    for a in new:
        log.info("Nuevo juego seguido en Steam: %s (appid %s)", a["name"], a["appid"])
    log.info("Juegos seguidos en Steam: %s fijos + %s descubiertos en Twitch",
             len(seed), len(tracked))


if __name__ == "__main__":
    main()
