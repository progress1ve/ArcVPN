import asyncio

import subscription_api as api
from bot.services.panels.remnawave import RemnawaveClient


def test_subscription_userinfo_uses_only_lte_quota(monkeypatch):
    key = api.ActiveKeyRecord(1, 1, "arc_user", "2030-01-01", 500 * 1024**3,
                              99 * 1024**3, "Standard", 7, "sub", "uuid")
    monkeypatch.setattr(api, "get_user_entitlements", lambda _telegram_id: {
        "lte_used_bytes": 2 * 1024**3, "lte_quota_gb": 45,
    })
    value = api._build_subscription_userinfo(key)
    assert "download=2147483648" in value
    assert f"total={45 * 1024**3}" in value
    assert str(500 * 1024**3) not in value


def test_main_remnawave_updates_are_always_unlimited(monkeypatch):
    client = RemnawaveClient({"panel_api_url": "https://panel.test",
                              "panel_api_token": "token", "panel_write_mode": "production"})
    monkeypatch.setattr(client, "_user_for_write", lambda _email: _async({"id": "main"}))
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs.get("json")))
        return {}

    monkeypatch.setattr(client, "_request", request)
    asyncio.run(client.update_client_limit(0, "uuid", "arc_user", 500 * 1024**3))
    assert calls[-1][2]["trafficLimitBytes"] == 0


async def _async(value):
    return value
