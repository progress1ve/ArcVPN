import asyncio
import sqlite3
from contextlib import contextmanager

import database.connection
from bot.handlers.user import lifecycle
from bot.services.scheduler import _send_lifecycle_batch
from bot.utils.payment_flow_ui import tariff_product_keyboard


def _connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE vpn_keys (id INTEGER PRIMARY KEY, user_id INTEGER, expires_at TEXT);
        CREATE TABLE trial_entitlements (
            user_id INTEGER PRIMARY KEY, status TEXT NOT NULL, activated_at TEXT
        );
        CREATE TABLE lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, event_key TEXT NOT NULL,
            answer TEXT, sent_at TEXT DEFAULT CURRENT_TIMESTAMP, answered_at TEXT,
            UNIQUE(user_id, event_key)
        );
        INSERT INTO settings VALUES ('lifecycle_eligible_after', '2020-01-01 00:00:00');
        INSERT INTO users(id,telegram_id) VALUES (1,1001),(2,1002);
        INSERT INTO trial_entitlements(user_id,status,activated_at)
        VALUES (1,'active',datetime('now','-25 hours')),(2,'active',datetime('now','-23 hours'));
    """)
    return conn


class _Bot:
    def __init__(self):
        self.sent = []

    async def send_photo(self, telegram_id, photo, caption, reply_markup):
        self.sent.append((telegram_id, caption, reply_markup))


def test_trial_rating_is_sent_once_after_24_hours(monkeypatch):
    conn = _connection()

    @contextmanager
    def fake_db():
        yield conn
        conn.commit()

    monkeypatch.setattr(database.connection, "get_db", fake_db)
    bot = _Bot()
    asyncio.run(_send_lifecycle_batch(bot))
    asyncio.run(_send_lifecycle_batch(bot))

    assert [item[0] for item in bot.sent] == [1001]
    assert "работает уже день" in bot.sent[0][1]
    buttons = [button.callback_data for row in bot.sent[0][2].inline_keyboard for button in row]
    assert "lifecycle_rating:service" in buttons
    assert not any(value.endswith((":1", ":3", ":5")) for value in buttons)
    event = conn.execute("SELECT event_key FROM lifecycle_events WHERE user_id=1").fetchone()
    assert event["event_key"] == "trial_day1_rating"
    assert conn.execute("SELECT COUNT(*) FROM lifecycle_events WHERE user_id=2").fetchone()[0] == 0


def test_rating_callback_accepts_current_and_legacy_events(monkeypatch):
    conn = _connection()
    conn.executescript("""
        INSERT INTO lifecycle_events(user_id,event_key) VALUES (1,'trial_day1_rating');
        INSERT INTO lifecycle_events(user_id,event_key) VALUES (2,'day5_rating');
    """)

    @contextmanager
    def fake_db():
        yield conn
        conn.commit()

    monkeypatch.setattr(lifecycle, "get_db", fake_db)
    assert lifecycle._record_rating_answer(1001, "5") == (True, 1)
    assert lifecycle._record_rating_answer(1002, "3") == (True, 2)
    assert lifecycle._record_rating_answer(1001, "1") == (False, 1)


def test_renew_tariff_back_button_returns_to_subscription_list():
    markup = tariff_product_keyboard([{"product_code": "standard"}], key_id=42)
    assert markup.inline_keyboard[-1][0].callback_data == "my_keys"


def test_tariff_keyboard_opens_custom_builder_before_back(monkeypatch):
    monkeypatch.setenv("WEBAPP_URL", "https://arccnet.space")
    markup = tariff_product_keyboard([
        {"product_code": "economy"},
        {"product_code": "standard"},
        {"product_code": "family"},
    ], key_id=42)
    custom = markup.inline_keyboard[-2][0]
    assert custom.text == "⚙️ Создать свой тариф"
    assert custom.web_app.url == "https://arccnet.space/app?screen=custom-tariff"
    assert markup.inline_keyboard[-1][0].callback_data == "my_keys"


def test_subscription_screen_renders_after_renewal_back(monkeypatch):
    import database.requests as requests
    import bot.handlers.user.keys as keys_handler

    rendered = {}

    async def capture(message, text, **kwargs):
        rendered.update(text=text, markup=kwargs["reply_markup"])

    monkeypatch.setenv("WEBAPP_URL", "https://arccnet.space")
    monkeypatch.setattr(requests, "get_user_primary_key", lambda telegram_id: None)
    monkeypatch.setattr(keys_handler, "safe_edit_or_send", capture)
    asyncio.run(keys_handler.show_my_keys(123, object()))

    assert "Подписка ещё не оформлена" in rendered["text"]
    assert rendered["markup"].inline_keyboard[0][0].web_app.url == "https://arccnet.space/app"


def test_active_subscription_screen_renders_link_after_renewal_back(monkeypatch):
    import database.requests as requests
    import bot.handlers.user.keys as keys_handler

    rendered = {}

    async def capture(message, text, **kwargs):
        rendered.update(text=text, markup=kwargs["reply_markup"])

    monkeypatch.setenv("WEBAPP_URL", "https://arccnet.space")
    monkeypatch.setattr(requests, "get_user_primary_key", lambda telegram_id: {
        "id": 185,
        "is_active": 1,
        "expires_at": "2027-07-08T12:00:00+00:00",
        "traffic_used": 0,
        "traffic_limit": 0,
        "sub_id": "stable-test-id",
    })
    monkeypatch.setattr(requests, "get_user_entitlements", lambda telegram_id: {"device_limit": 3})
    monkeypatch.setattr(requests, "get_user_devices", lambda telegram_id: [])
    monkeypatch.setattr(requests, "is_traffic_exhausted", lambda primary: False)
    monkeypatch.setattr(keys_handler, "safe_edit_or_send", capture)
    asyncio.run(keys_handler.show_my_keys(123, object()))

    assert "stable-test-id" in rendered["text"]
    assert any(
        button.callback_data == "key_renew:185"
        for row in rendered["markup"].inline_keyboard for button in row
    )
