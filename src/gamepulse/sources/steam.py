"""Cliente mínimo de las APIs públicas de Steam."""

import time

import requests

WEB_API = "https://api.steampowered.com"
STORE_API = "https://store.steampowered.com"


class SteamClient:
    def __init__(self, api_key: str = "", session: requests.Session | None = None):
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, url: str, params: dict, max_retries: int = 3) -> dict:
        for attempt in range(1, max_retries + 1):
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code in (429, 500, 502, 503) and attempt < max_retries:
                time.sleep(5 * attempt)  # la tienda de Steam limita de forma agresiva
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Steam {url}: agotados {max_retries} reintentos")

    def current_players(self, appid: int) -> int | None:
        """Jugadores simultáneos ahora mismo. None si Steam no devuelve dato."""
        data = self._get(
            f"{WEB_API}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/", {"appid": appid}
        )
        resp = data.get("response", {})
        return resp.get("player_count") if resp.get("result") == 1 else None

    def app_details(self, appid: int, country: str = "es") -> dict | None:
        """Ficha de la tienda: precio, descuento, géneros, fecha de salida... (semana 3)."""
        data = self._get(f"{STORE_API}/api/appdetails", {"appids": appid, "cc": country})
        entry = data.get(str(appid), {})
        return entry.get("data") if entry.get("success") else None

    def reviews_page(self, appid: int, cursor: str = "*", per_page: int = 100) -> dict:
        """Una página de reseñas (semana 3). Devuelve también el cursor de la siguiente."""
        return self._get(
            f"{STORE_API}/appreviews/{appid}",
            {
                "json": 1,
                "filter": "recent",
                "language": "all",
                "purchase_type": "all",
                "num_per_page": per_page,
                "cursor": cursor,
            },
        )
