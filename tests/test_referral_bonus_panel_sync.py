import asyncio

from bot.services import vpn_api


class FakeClient:
    def __init__(self):
        self.calls = []

    async def update_client_full(self, **kwargs):
        self.calls.append(kwargs)
        return True


def test_push_key_accepts_remnawave_zero_inbound_and_uses_authority(monkeypatch):
    client = FakeClient()
    targets = []
    key = {
        "id": 3,
        "server_active": 1,
        "panel_email": "arc_user_example",
        "panel_inbound_id": 0,
        "client_uuid": "uuid-example",
        "expires_at": "2026-09-23 13:51:26",
        "traffic_limit": 0,
        "device_limit": 2,
        "server_id": 1,
        "server_panel_type": "xui",
    }

    monkeypatch.setattr("database.requests.get_vpn_key_by_id", lambda _key_id: key)
    monkeypatch.setattr(vpn_api, "_server_data_from_key", lambda _key: {"panel_type": "xui"})
    monkeypatch.setattr(
        "bot.services.remnawave_stats.remnawave_authority_config",
        lambda: {"panel_type": "remnawave", "panel_api_url": "https://panel.invalid", "panel_api_token": "token"},
    )
    monkeypatch.setattr(
        vpn_api,
        "get_client_from_server_data",
        lambda target: targets.append(target) or client,
    )

    assert asyncio.run(vpn_api.push_key_to_panel(3)) is True
    assert targets == [{
        "panel_type": "remnawave",
        "panel_api_url": "https://panel.invalid",
        "panel_api_token": "token",
    }]
    assert client.calls[0]["inbound_id"] == 0
