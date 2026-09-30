"""Cliente mínimo de la API Helix de Twitch (autenticación app-to-app)."""

import time
from collections.abc import Iterator

import requests

from gamepulse.common.logging import get_logger

log = get_logger(__name__)

AUTH_URL = "https://id.twitch.tv/oauth2/token"
API_URL = "https://api.twitch.tv/helix"


class TwitchClient:
    def __init__(self, client_id: str, client_secret: str, session: requests.Session | None = None):
        if not client_id or not client_secret:
            raise ValueError("Faltan TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET en .env")
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at = 0.0

    # --- Autenticación (client credentials) ---
    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        resp = self.session.post(
            AUTH_URL,
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        return self._token

    # --- Petición con control de rate limit y reintentos ---
    def _get(self, path: str, params: dict, max_retries: int = 3) -> dict:
        for attempt in range(1, max_retries + 1):
            headers = {"Client-Id": self.client_id, "Authorization": f"Bearer {self._get_token()}"}
            resp = self.session.get(f"{API_URL}/{path}", params=params, headers=headers, timeout=15)

            if resp.status_code == 401:  # token caducado o revocado
                self._token = None
                continue
            if resp.status_code == 429:  # rate limit: esperar al reset
                reset = float(resp.headers.get("Ratelimit-Reset", time.time() + 5))
                wait = max(1.0, reset - time.time())
                log.warning("Rate limit de Twitch, esperando %.0fs", wait)
                time.sleep(wait)
                continue
            if resp.status_code >= 500 and attempt < max_retries:
                time.sleep(2**attempt)
                continue

            resp.raise_for_status()
            remaining = resp.headers.get("Ratelimit-Remaining")
            if remaining is not None and int(remaining) < 5:
                time.sleep(1)
            return resp.json()
        raise RuntimeError(f"Twitch {path}: agotados {max_retries} reintentos")

    def _paginate(self, path: str, params: dict, limit: int) -> Iterator[dict]:
        cursor, yielded = None, 0
        while yielded < limit:
            page_params = {**params, "first": min(100, limit - yielded)}
            if cursor:
                page_params["after"] = cursor
            data = self._get(path, page_params)
            items = data.get("data", [])
            for item in items:
                yield item
                yielded += 1
            cursor = data.get("pagination", {}).get("cursor")
            if not items or not cursor:
                break

    # --- Endpoints ---
    def top_games(self, limit: int = 50) -> list[dict]:
        """Juegos más vistos ahora. Incluye igdb_id (clave para cruzar con Steam)."""
        return list(self._paginate("games/top", {}, limit))

    def streams_for_game(self, game_id: str, limit: int = 100) -> list[dict]:
        """Directos activos de un juego, ordenados por espectadores (desc)."""
        return list(self._paginate("streams", {"game_id": game_id, "type": "live"}, limit))
