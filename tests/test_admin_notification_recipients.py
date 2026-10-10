import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bot.services import admin_recipients as recipients


@pytest.fixture
def audience(monkeypatch):
    import config
    monkeypatch.setattr(config, "ADMIN_IDS", [11, 22])
    monkeypatch.setattr(recipients, "get_setting", lambda _: "[11]")


@pytest.mark.parametrize("setting,expected", [(None,[11,22]),('[11]',[11]),('[99]',[]),('[]',[]),('broken',[]),('{}',[])])
def test_notification_selection_never_grants_or_changes_admin_rights(audience, monkeypatch, setting, expected):
    import config
    monkeypatch.setattr(recipients, "get_setting", lambda _: setting)
    assert recipients.admin_notification_ids() == expected
    assert config.ADMIN_IDS == [11,22]


def test_read_failure_does_not_reenable_opted_out_admin(audience, monkeypatch):
    monkeypatch.setattr(recipients, "get_setting", Mock(side_effect=RuntimeError()))
    assert recipients.admin_notification_ids() == []


@pytest.mark.parametrize("document", [None,(b"report","report.txt")])
def test_regular_admin_alerts_only_reach_selected_owner(audience, document):
    from bot.services.notifications import notify_admins
    bot = SimpleNamespace(send_message=AsyncMock(),send_document=AsyncMock())
    asyncio.run(notify_admins(bot, "notice", document=document))
    method = bot.send_document if document else bot.send_message
    assert method.await_count == 1
    assert method.call_args.kwargs["chat_id"] == 11


def test_support_alert_only_reaches_selected_owner(audience, monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api, "BOT_TOKEN", "test")
    monkeypatch.setattr(api, "get_webapp_account", lambda _: {"username":"fixture"})
    sender = Mock()
    monkeypatch.setattr(api.urllib.request, "urlopen", sender)
    api._notify_support_admins(1, 3, "hello")
    assert sender.call_count == 1
    assert json.loads(sender.call_args.args[0].data)["chat_id"] == 11


@pytest.mark.parametrize("destination,expected", [("",[11]),("11",[11]),("22",[]),("bad",[])])
def test_ai_alert_destination_respects_opt_out(audience, monkeypatch, destination, expected):
    import config
    from bot.services import support_ai_alerts as alerts
    monkeypatch.setattr(config, "BOT_TOKEN", "test")
    monkeypatch.setenv("SUPPORT_AI_ALERT_CHAT_ID", destination)
    response = Mock()
    response.__enter__ = Mock(return_value=SimpleNamespace(read=lambda _: b'{"ok":true}'))
    response.__exit__ = Mock(return_value=False)
    sender = Mock(return_value=response)
    monkeypatch.setattr(alerts.urllib.request, "urlopen", sender)
    assert alerts._send("notice") == bool(expected)
    assert [json.loads(call.args[0].data)["chat_id"] for call in sender.call_args_list] == expected


def test_lte_incidents_only_reach_selected_owner(audience, monkeypatch):
    from monitoring import lte_operator_worker as worker
    import aiogram
    bot = SimpleNamespace(send_message=AsyncMock(), session=SimpleNamespace(close=AsyncMock()))
    monkeypatch.setattr(aiogram, "Bot", lambda **_: bot)
    host, path, _ = worker.NODES[0]
    asyncio.run(worker.notify([{"node_host":host,"target_path":path,"operator":"mts","type":"recovery"}]))
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == 11
