from gamepulse.sources.twitch import TwitchClient


class FakeResp:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload or {}, headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Simula Twitch: token + dos páginas de top games."""

    def __init__(self):
        self.calls = []

    def post(self, url, **kw):
        return FakeResp(payload={"access_token": "tok", "expires_in": 3600})

    def get(self, url, params=None, headers=None, **kw):
        self.calls.append(params)
        if "after" not in params:
            return FakeResp(
                payload={"data": [{"id": "1"}, {"id": "2"}], "pagination": {"cursor": "c1"}}
            )
        return FakeResp(payload={"data": [{"id": "3"}], "pagination": {}})


def test_pagination_and_limit():
    client = TwitchClient("id", "secret", session=FakeSession())
    assert [g["id"] for g in client.top_games(limit=10)] == ["1", "2", "3"]
    assert [g["id"] for g in client.top_games(limit=2)] == ["1", "2"]


def test_missing_credentials():
    import pytest

    with pytest.raises(ValueError):
        TwitchClient("", "")
