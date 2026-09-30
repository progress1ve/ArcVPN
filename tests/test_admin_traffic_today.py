"""Daily product traffic must reflect complete Remnawave usage, not quotas."""

import asyncio

import pytest

import subscription_api as api
from bot.services import remnawave_stats


class FakePanel:
    def __init__(self, responses):
        self.responses = responses
        self.closed = False
        self.calls = []

    async def _request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs.get("params", {})))
        if path == "/api/internal-squads":
            return {"internalSquads": [
                {"name": "ArcVPN Staging", "uuid": "ordinary-squad"},
                {"name": "ArcVPN LTE", "uuid": "lte-squad"},
            ]}
        key = (path.split("/")[-2], kwargs["params"].get("cursor"))
        return self.responses[key]

    async def close(self):
        self.closed = True


def test_daily_traffic_paginates_and_keeps_products_separate(monkeypatch):
    panel = FakePanel({
        ("ordinary-squad", None): {
            "users": [{"id": 1, "totalBytes": "120"}],
            "hasMore": True, "nextCursor": "page-2",
        },
        ("ordinary-squad", "page-2"): {
            "users": [{"id": 2, "totalBytes": "30"}], "hasMore": False,
        },
        ("lte-squad", None): {
            "users": [{"id": 3, "totalBytes": "15"}], "hasMore": False,
        },
    })
    monkeypatch.setattr(remnawave_stats, "_credentials", lambda: {})
    monkeypatch.setattr(remnawave_stats, "RemnawaveClient", lambda _: panel)
    result = asyncio.run(remnawave_stats.get_remnawave_daily_product_traffic("2026-09-30"))
    assert result == {
        "main": {"bytes": 150, "active_users": 2},
        "lte": {"bytes": 15, "active_users": 1},
    }
    assert panel.closed
    assert panel.calls[1][2]["start"] == "2026-09-30"
    assert panel.calls[2][2]["cursor"] == "page-2"


def test_incomplete_daily_usage_is_not_zero(monkeypatch):
    panel = FakePanel({
        ("ordinary-squad", None): {
            "users": [], "hasMore": True, "nextCursor": None,
        },
    })
    monkeypatch.setattr(remnawave_stats, "_credentials", lambda: {})
    monkeypatch.setattr(remnawave_stats, "RemnawaveClient", lambda _: panel)
    with pytest.raises(ValueError, match="Incomplete"):
        asyncio.run(remnawave_stats.get_remnawave_daily_product_traffic("2026-09-30"))
    assert panel.closed


def test_today_api_requires_admin(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission=None: False)
    response = api.app.test_client().get("/api/admin/traffic/today")
    assert response.status_code == 403


def test_today_api_reports_real_source_and_unavailable(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission=None: True)

    async def usage(_day):
        return {"main": {"bytes": 150, "active_users": 2},
                "lte": {"bytes": 15, "active_users": 1}}

    monkeypatch.setattr(remnawave_stats, "get_remnawave_daily_product_traffic", usage)
    response = api.app.test_client().get("/api/admin/traffic/today")
    assert response.status_code == 200
    assert response.get_json()["groups"]["lte"]["bytes"] == 15
    assert response.get_json()["timezone"] == "UTC"

    async def unavailable(_day):
        raise RuntimeError("Panel unreachable")

    monkeypatch.setattr(remnawave_stats, "get_remnawave_daily_product_traffic", unavailable)
    response = api.app.test_client().get("/api/admin/traffic/today")
    assert response.status_code == 503
    assert response.get_json()["error"] == "traffic_today_unavailable"
