import json
import urllib.error
from unittest.mock import Mock

import pytest
from bot.services import support_ai_alerts as alerts


@pytest.fixture
def incident(monkeypatch):
    data = {}
    sender = Mock(return_value=True)
    monkeypatch.setattr(alerts, "get_setting", lambda key, default: data.get(key, default))
    monkeypatch.setattr(alerts, "set_setting", lambda key, value: data.update({key: value}))
    monkeypatch.setattr(alerts, "_send", sender)
    monkeypatch.setenv("SUPPORT_AI_PROVIDER", "groq")
    monkeypatch.setattr(alerts.time, "time", lambda: 100000)
    return data, sender


@pytest.mark.parametrize("code,reason", [(401,"ключ отклонён"),(403,"доступ запрещён"),(404,"модель недоступна"),(429,"исчерпан лимит"),(503,"ошибка провайдера")])
def test_immediate_failure_alert_is_sanitized(incident, code, reason):
    data, sender = incident
    alerts.provider_health(False, urllib.error.HTTPError("https://secret.test/private",code,"secret-body-key",{},None))
    text = sender.call_args.args[0]
    assert reason in text and "groq" in text
    assert "secret" not in text and "private" not in text
    assert json.loads(data[alerts.SETTING])["down"]


def test_cooldown_survives_restart_and_recovery_is_notified_once(incident, monkeypatch):
    data, sender = incident
    alerts.provider_health(False, TimeoutError())
    monkeypatch.setattr(alerts, "_memory", {})
    alerts.provider_health(False, TimeoutError())
    assert sender.call_count == 1
    alerts.provider_health(True)
    alerts.provider_health(True)
    assert sender.call_count == 2 and "снова отвечает" in sender.call_args.args[0]
    assert not json.loads(data[alerts.SETTING])["down"]


def test_persistent_failure_reminds_after_six_hours(incident, monkeypatch):
    _, sender = incident
    alerts.provider_health(False)
    monkeypatch.setattr(alerts.time, "time", lambda: 100000+alerts.COOLDOWN+1)
    alerts.provider_health(False)
    assert sender.call_count == 2


def test_delivery_failure_is_retried_without_crashing_customer_reply(incident):
    _, sender = incident
    sender.return_value = False
    alerts.provider_health(False)
    alerts.provider_health(False)
    assert sender.call_count == 2
