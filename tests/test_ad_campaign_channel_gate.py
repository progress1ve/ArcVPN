import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from aiogram.types import Chat, Message, User

from bot.handlers.user import start
from bot.middlewares.subscription_check import (
    SubscriptionCheckMiddleware,
    advertising_start_payload,
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


def test_advertising_start_payload_accepts_bot_deep_link_only():
    assert advertising_start_payload(message("/start ad_campaign_one")) == "ad_campaign_one"
    assert advertising_start_payload(message("/start@arcvpnbot ad_campaign_two")) == "ad_campaign_two"
    assert advertising_start_payload(message("/start ref_friend")) is None
    assert advertising_start_payload(message("hello")) is None


def test_channel_gate_preserves_advertising_payload(monkeypatch):
    middleware = SubscriptionCheckMiddleware()
    state = FakeState()
    delivered = []

    async def send_required(_message):
        delivered.append(True)

    async def handler(_event, _data):
        raise AssertionError("channel gate must stop the original /start")

    monkeypatch.setattr(middleware, "send_subscription_required", send_required)
    bot = SimpleNamespace(
        get_chat_member=lambda **_kwargs: None,
    )

    async def get_chat_member(**_kwargs):
        return SimpleNamespace(status="left")

    bot.get_chat_member = get_chat_member
    asyncio.run(middleware(handler, message("/start ad_campaign_one"), {"bot": bot, "state": state}))

    assert delivered == [True]
    assert state.data["pending_start_args"] == "ad_campaign_one"


def test_channel_callback_attributes_new_user_and_consumes_payload(monkeypatch):
    state_context = FakeState({"pending_start_args": "ad_campaign_one"})
    calls = []

    def attribute(user_id, code, *, is_new_user):
        calls.append((user_id, code, is_new_user))
        return True, {"id": 7}

    monkeypatch.setattr(db_campaigns, "attribute_user_to_campaign", attribute)

    assert asyncio.run(start._attribute_pending_advertising_start(
        {"id": 42}, True, state_context,
    )) is True
    assert calls == [(42, "campaign_one", True)]
    assert state_context.data["pending_start_args"] is None
