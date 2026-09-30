from datetime import UTC, datetime

from gamepulse.ingestion.steam_players_batch import collect, load_apps


class FakeSteam:
    def current_players(self, appid):
        if appid == 570:
            raise RuntimeError("timeout")
        return 1000


def test_seed_list_loads():
    apps = load_apps()
    assert len(apps) >= 10 and apps[0]["appid"] == 730


def test_collect_survives_single_failure():
    apps = [{"appid": 730, "name": "CS2"}, {"appid": 570, "name": "Dota 2"}]
    recs = collect(FakeSteam(), apps, datetime(2026, 9, 25, tzinfo=UTC))
    assert [r["player_count"] for r in recs] == [1000, None]
