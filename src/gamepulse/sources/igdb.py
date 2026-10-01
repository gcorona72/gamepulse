"""Cliente mínimo de IGDB (misma cuenta y token que Twitch).

IGDB relaciona cada juego con sus identificadores en otras tiendas (`external_games`).
La fuente 1 es Steam: su `uid` es el `appid` de Steam.
"""

from gamepulse.sources.twitch import TwitchClient

IGDB_URL = "https://api.igdb.com/v4"
STEAM_SOURCE = 1  # id de Steam en external_game_source (antes `category`)


class IgdbClient:
    def __init__(self, twitch: TwitchClient):
        self.twitch = twitch  # reutiliza el token app-to-app de Twitch

    def _post(self, endpoint: str, query: str) -> list[dict]:
        headers = {
            "Client-ID": self.twitch.client_id,
            "Authorization": f"Bearer {self.twitch._get_token()}",
        }
        resp = self.twitch.session.post(
            f"{IGDB_URL}/{endpoint}", data=query, headers=headers, timeout=20
        )
        resp.raise_for_status()
        return resp.json()

    def external_games(self, igdb_ids: list[int]) -> list[dict]:
        """Identificadores externos (todas las tiendas) de una lista de juegos de IGDB."""
        if not igdb_ids:
            return []
        ids = ",".join(str(i) for i in sorted(set(igdb_ids)))
        query = (
            "fields game,uid,category,external_game_source;"
            f" where game = ({ids}); limit 500;"
        )
        return self._post("external_games", query)


def is_steam(ext: dict) -> bool:
    """Compatible con el campo nuevo (external_game_source) y el antiguo (category)."""
    return ext.get("external_game_source", ext.get("category")) == STEAM_SOURCE
