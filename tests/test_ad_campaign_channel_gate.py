import asyncio
from datetime import datetime, timezone
from aiogram.types import Chat, Message, User

from bot.handlers.user import start
from bot.middlewares.subscription_check import (
    SubscriptionCheckMiddleware,
    gated_start_payload,
)
from database import db_campaigns


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **changes):
        self.data.update(changes)


def message(text: str) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=101, type="private"),
        from_user=User(id=101, is_bot=False, first_name="New"),
        text=text,
    )


def test_gated_start_payload_accepts_attribution_deep_links_only():
    assert gated_start_payload(message("/start ad_campaign_one")) == "ad_campaign_one"
    assert gated_start_payload(message("/start@arcvpnbot ad_campaign_two")) == "ad_campaign_two"
    assert gated_start_payload(message("/start ref_friend")) == "ref_friend"
    assert gated_start_payload(message("/start buy_12")) is None
    assert gated_start_payload(message("/start ref_bad value")) is None
    assert gated_start_payload(message("hello")) is None


def test_legal_gate_preserves_advertising_payload(monkeypatch):
    middleware = SubscriptionCheckMiddleware()
    state = FakeState()
    delivered = []

    async def send_required(_message):
        delivered.append(True)

    async def handler(_event, _data):
        raise AssertionError("legal gate must stop the original /start")

    monkeypatch.setattr(middleware, "send_subscription_required", send_required)
    monkeypatch.setattr("database.db_legal_consent.get_legal_consent", lambda _user_id: None)
    monkeypatch.setattr("database.requests.get_setting", lambda _key, default: default)
    asyncio.run(middleware(handler, message("/start ad_campaign_one"), {"state": state}))

    assert delivered == [True]
    assert state.data["pending_start_args"] == "ad_campaign_one"


def test_legal_gate_preserves_referral_payload(monkeypatch):
    middleware = SubscriptionCheckMiddleware()
    state = FakeState()

    async def handler(_event, _data):
        raise AssertionError("legal gate must stop the original /start")

    monkeypatch.setattr(middleware, "send_subscription_required", lambda _message: asyncio.sleep(0))
    monkeypatch.setattr("database.db_legal_consent.get_legal_consent", lambda _user_id: None)
    monkeypatch.setattr("database.requests.get_setting", lambda _key, default: default)

    asyncio.run(middleware(handler, message("/start ref_friend"), {"state": state}))

    assert state.data["pending_start_args"] == "ref_friend"


def test_legal_callback_attributes_new_user_and_consumes_payload(monkeypatch):
    state_context = FakeState({"pending_start_args": "ad_campaign_one"})
    calls = []

    def attribute(user_id, code, *, is_new_user):
        calls.append((user_id, code, is_new_user))
        return True, {"id": 7}

    monkeypatch.setattr(db_campaigns, "attribute_user_to_campaign", attribute)

    assert asyncio.run(start._restore_pending_start_attribution(
        {"id": 42}, True, state_context,
    )) == {"advertising": True, "referral": False}
    assert calls == [(42, "campaign_one", True)]
    assert state_context.data["pending_start_args"] is None


def test_legal_callback_restores_new_user_referrer_once(monkeypatch):
    state_context = FakeState({"pending_start_args": "ref_friend"})
    links = []

    monkeypatch.setattr(start, "get_user_by_referral_code", lambda code: {"id": 7} if code == "friend" else None)
    monkeypatch.setattr(start, "set_user_referrer", lambda user_id, referrer_id: links.append((user_id, referrer_id)) or True)

    result = asyncio.run(start._restore_pending_start_attribution(
        {"id": 42}, True, state_context,
    ))

    assert result == {"advertising": False, "referral": True}
    assert links == [(42, 7)]
    assert state_context.data["pending_start_args"] is None


def test_legal_callback_does_not_rebind_existing_user(monkeypatch):
    state_context = FakeState({"pending_start_args": "ref_friend"})
    monkeypatch.setattr(start, "get_user_by_referral_code", lambda _code: {"id": 7})
    monkeypatch.setattr(start, "set_user_referrer", lambda *_args: (_ for _ in ()).throw(AssertionError("must not bind")))

    result = asyncio.run(start._restore_pending_start_attribution(
        {"id": 42}, False, state_context,
    ))

    assert result == {"advertising": False, "referral": False}
    assert state_context.data["pending_start_args"] is None


def test_current_legal_consent_does_not_require_channel_membership(monkeypatch):
    middleware = SubscriptionCheckMiddleware()
    handled = []

    monkeypatch.setattr(
        "database.db_legal_consent.get_legal_consent",
        lambda _user_id: {"version": "2026-09-10"},
    )
    monkeypatch.setattr("database.requests.get_setting", lambda _key, _default: "2026-09-10")

    async def handler(_event, _data):
        handled.append(True)
        return "ok"

    result = asyncio.run(middleware(handler, message("/start"), {}))

    assert result == "ok"
    assert handled == [True]
