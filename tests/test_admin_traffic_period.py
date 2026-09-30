"""The traffic console must not present cumulative counters as period usage."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import subscription_api as api
from bot.services import remnawave_stats


def test_period_cards_rows_and_group_filter(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE users (id INTEGER, telegram_id INTEGER, username TEXT,
                 first_name TEXT, device_limit INTEGER, lte_remnawave_user_id TEXT)""")
    conn.execute("""CREATE TABLE vpn_keys (user_id INTEGER, client_uuid TEXT,
                 expires_at TEXT, traffic_limit INTEGER)""")
    conn.execute("INSERT INTO users VALUES (5,123,'example','Example',2,'22')")
    conn.execute("INSERT INTO vpn_keys VALUES (5,'ordinary-uuid','2099-01-01',10000000000)")

    @contextmanager
    def fake_db():
        yield conn

    async def fake_period(start, end):
        one_day = start == end
        return {"usage": {
            "main": {11: 100 if one_day else 700},
            "lte": {22: 3 if one_day else 31},
        }, "panel_users": {
            11: {"vless_uuid": "ordinary-uuid", "telegram_id": "123"},
            22: {"vless_uuid": "lte-uuid", "telegram_id": "123"},
        }}

    monkeypatch.setattr(api, "_admin_authorized", lambda permission=None: True)
    monkeypatch.setattr(api, "get_db", fake_db)
    monkeypatch.setattr(remnawave_stats, "get_remnawave_period_user_traffic", fake_period)
    client = api.app.test_client()
    one = client.get("/api/admin/traffic/period?period=1&nodes=lte")
    week = client.get("/api/admin/traffic/period?period=7&nodes=lte")
    assert one.status_code == week.status_code == 200
    assert one.get_json()["groups"]["lte"]["bytes"] == 3
    assert week.get_json()["groups"]["lte"]["bytes"] == 31
    assert one.get_json()["items"][0]["lte_bytes"] == 3
    assert one.get_json()["items"][0]["main_bytes"] == 0
    assert one.get_json()["items"][0]["total_bytes"] == 3
    assert week.get_json()["items"][0]["total_bytes"] == 31
    assert one.get_json()["end_date"] == datetime.now(timezone.utc).date().isoformat()
    assert week.get_json()["start_date"] == (datetime.now(timezone.utc).date() - timedelta(days=6)).isoformat()
    conn.close()


def test_period_api_rejects_bad_range_and_panel_failure(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission=None: True)
    client = api.app.test_client()
    assert client.get("/api/admin/traffic/period?period=0").status_code == 400
    assert client.get("/api/admin/traffic/period?start_date=2026-09-30").status_code == 400

    async def unavailable(_start, _end):
        raise RuntimeError("Panel unavailable")

    monkeypatch.setattr(remnawave_stats, "get_remnawave_period_user_traffic", unavailable)
    response = client.get("/api/admin/traffic/period?period=1")
    assert response.status_code == 503
    assert response.get_json()["error"] == "traffic_period_unavailable"
