import sqlite3
import asyncio
from contextlib import contextmanager

from bot.handlers.user.start import create_onboarding_kb, trial_welcome_text
from bot.handlers.user.trial import provision_trial_for_user
from bot.utils.payment_flow_ui import build_tariff_catalog_text


class FakeRemnawave:
    def __init__(self, existing=None):
        self.existing = existing
        self.add_calls = 0
        self.update_calls = 0
        self.closed = False

    async def get_user(self, username):
        return self.existing

    async def add_client(self, **kwargs):
        self.add_calls += 1
        return {"vlessUuid": "11111111-1111-1111-1111-111111111111"}

    async def update_client_full(self, **kwargs):
        self.update_calls += 1
        return True

    async def close(self):
        self.closed = True


def test_trial_provisions_exactly_one_native_remnawave_user(monkeypatch):
    import database.requests as requests
    import database.connection as connection
    import bot.services.vpn_api as vpn_api

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE vpn_keys (id INTEGER PRIMARY KEY, user_id INTEGER, panel_email TEXT)")

    @contextmanager
    def fake_db():
        yield conn

    client = FakeRemnawave()
    monkeypatch.setattr(connection, "get_db", fake_db)
    monkeypatch.setattr(requests, "get_trial_days", lambda: 7)
    monkeypatch.setattr(requests, "get_standard_trial_tariff", lambda: {
        "id": 3, "device_limit": 3, "traffic_limit_gb": 1024,
    })
    monkeypatch.setattr(requests, "acquire_trial_entitlement", lambda *_: {"status": "provisioning", "acquired": True})
    monkeypatch.setattr(requests, "get_all_servers", lambda: [
        {"id": 1, "is_active": 1, "panel_type": "xui"},
        {"id": 9, "is_active": 1, "panel_type": "remnawave"},
    ])
    monkeypatch.setattr(requests, "fail_trial_entitlement", lambda *_: True)
    monkeypatch.setattr(requests, "activate_trial_entitlement", lambda *_: True)

    def create_key(**kwargs):
        conn.execute(
            "INSERT INTO vpn_keys(user_id, panel_email) VALUES (?, ?)",
            (kwargs["user_id"], kwargs["panel_email"]),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    monkeypatch.setattr(requests, "create_vpn_key_admin", create_key)
    monkeypatch.setattr(vpn_api, "get_client_from_server_data", lambda _: client)
    monkeypatch.setattr("bot.services.lte_identity.provision_lte_identity", lambda *_, **__: _noop())
    monkeypatch.setattr("bot.services.billing.process_referral_trial_reward", lambda *_: _noop())

    result = asyncio.run(provision_trial_for_user({"id": 41, "telegram_id": 1001}))

    assert result["trial_days"] == 7
    assert result["trial_traffic_gb"] == 5
    assert result["created_keys"] == [{"key_id": 1, "server_name": "ArcVPN"}]
    assert client.add_calls == 1
    assert client.closed is True
    assert conn.execute("SELECT panel_email FROM vpn_keys").fetchone()[0] == "arc_user_41"


async def _noop():
    return None


def test_onboarding_is_two_actions_and_trial_copy_has_no_legacy_server_count():
    markup = create_onboarding_kb()
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == ["🚀 Подключиться", "Продолжить в боте"]
    text = trial_welcome_text({"first_name": "Alex"}, {"trial_days": 7, "trial_traffic_gb": 1024})
    assert "7 дней" in text
    assert "Серверов:" not in text


def test_tariff_catalog_always_contains_structured_products():
    tariffs = [
        {"product_code": "economy", "price_rub": 931, "period_months": 12},
        {"product_code": "standard", "price_rub": 1469, "period_months": 12},
        {"product_code": "family", "price_rub": 3389, "period_months": 12},
    ]
    text = build_tariff_catalog_text(tariffs)
    assert all(name in text for name in ("Эконом", "Стандарт", "Семейный"))
    assert "78 ₽/мес" in text
    assert "122 ₽/мес" in text
    assert "45 ГБ LTE" in text
    assert "115 ГБ обхода" in text
    assert "8 устройств" in text
