import json
import sqlite3
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from bot.services import support_ai as ai
from database import db_support as db


@pytest.fixture
def support_db(tmp_path, monkeypatch):
    path = tmp_path / "support.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript("""
      CREATE TABLE users(id INTEGER PRIMARY KEY,telegram_id INTEGER);
      CREATE TABLE support_threads(id INTEGER PRIMARY KEY,user_id INTEGER,status TEXT,updated_at TEXT);
      CREATE TABLE support_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,thread_id INTEGER,sender TEXT CHECK(sender IN ('user','admin')),sender_telegram_id INTEGER,body TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,read_at TEXT);
      INSERT INTO users VALUES(1,700001);
      INSERT INTO support_threads VALUES(10,1,'open',CURRENT_TIMESTAMP);
      INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES(10,'user',700001,'VPN не подключается');
    """)
    connection.commit()
    connection.close()

    @contextmanager
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    monkeypatch.setattr(db, "get_db", connect)
    return connect


def test_disabled_without_both_explicit_flag_and_key(monkeypatch):
    monkeypatch.delenv("SUPPORT_AI_ENABLED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert not ai.queue_reply(10, 1)
    monkeypatch.setenv("SUPPORT_AI_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ai.status() == {"enabled": False, "pending": False}


def test_request_omits_identifiers_and_disables_storage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    @contextmanager
    def response(request, timeout):
        captured.update(json.loads(request.data), timeout=timeout)
        yield Mock(read=lambda n: json.dumps({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Обновите подписку в приложении."}]}]}).encode())

    monkeypatch.setattr(ai.urllib.request, "urlopen", response)
    result = ai.request_reply([{"sender": "user", "body": "https://example.test/sub/private alice@example.test +79991234567 пароль: secret 550e8400-e29b-41d4-a716-446655440000"}])
    assert result == "Обновите подписку в приложении."
    assert captured["store"] is False and captured["timeout"] == 8
    assert captured["max_output_tokens"] == 350
    text = captured["input"][0]["content"]
    assert all(value not in text for value in ("private", "alice@", "79991234567", "secret", "550e8400"))


@pytest.mark.parametrize("payload", [{"status": "incomplete"}, {"status": "completed", "output": []}])
def test_incomplete_or_empty_result_rejected(monkeypatch, payload):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    @contextmanager
    def response(*args, **kwargs):
        yield Mock(read=lambda n: json.dumps(payload).encode())
    monkeypatch.setattr(ai.urllib.request, "urlopen", response)
    with pytest.raises(ValueError):
        ai.request_reply([{"sender": "user", "body": "Помогите"}])


def test_saved_reply_is_identified_and_idempotent(support_db):
    assert db.add_assistant_support_message(10, 1, "Обновите подписку.")
    assert not db.add_assistant_support_message(10, 1, "Повтор")
    messages = db.get_support_messages(700001)["messages"]
    assert len(messages) == 2
    assert not messages[0]["is_ai"] and messages[1]["is_ai"]


@pytest.mark.parametrize("sender,status", [("user", "open"), ("admin", "open"), (None, "closed")])
def test_late_reply_never_overrides_new_turn_human_or_closed_thread(support_db, sender, status):
    with support_db() as conn:
        if sender:
            conn.execute("INSERT INTO support_messages(thread_id,sender,body) VALUES(10,?,'Позднее сообщение')", (sender,))
        conn.execute("UPDATE support_threads SET status=?", (status,))
    assert not db.add_assistant_support_message(10, 1, "Устаревший ответ")


def _run_reserved_reply(monkeypatch, message_id=1):
    slots = Mock()
    monkeypatch.setattr(ai, "_slots", slots)
    monkeypatch.setattr(ai, "_pending", {10: message_id})
    ai._reply(10, message_id)
    slots.release.assert_called_once()
    assert not ai.status(10)["pending"]


def test_provider_timeout_preserves_manager_fallback(support_db, monkeypatch):
    monkeypatch.setattr(ai, "request_reply", Mock(side_effect=TimeoutError))
    _run_reserved_reply(monkeypatch)
    assert db.get_support_messages(700001)["messages"][-1]["body"] == ai.FALLBACK


def test_payment_handoff_never_calls_provider(support_db, monkeypatch):
    with support_db() as conn:
        conn.execute("UPDATE support_messages SET body='После оплаты нет подписки'")
    provider = Mock()
    monkeypatch.setattr(ai, "request_reply", provider)
    _run_reserved_reply(monkeypatch)
    provider.assert_not_called()
    assert "менеджеру" in db.get_support_messages(700001)["messages"][-1]["body"]


def test_unauthorized_endpoint_never_queues_ai(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api, "_webapp_telegram_id", lambda: None)
    queue = Mock()
    monkeypatch.setattr(ai, "queue_reply", queue)
    client = api.app.test_client()
    assert client.post('/api/support/messages', json={"body": "Помогите"}).status_code == 401
    assert client.get('/api/support/messages').status_code == 401
    queue.assert_not_called()


def test_accepted_message_still_notifies_manager_and_returns_pending(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api, "_webapp_telegram_id", lambda: 700001)
    monkeypatch.setattr(api, "add_user_support_message", lambda user, body: {"thread_id": 10, "message": {"id": 1, "sender": "user", "body": body}})
    thread = Mock()
    monkeypatch.setattr(api.threading, "Thread", thread)
    queue = Mock(return_value=True)
    monkeypatch.setattr(ai, "queue_reply", queue)
    monkeypatch.setattr(ai, "status", lambda thread_id: {"enabled": True, "pending": True})
    result = api.app.test_client().post('/api/support/messages', json={"body": "Помогите"})
    assert result.status_code == 200 and result.json["ai"]["pending"]
    queue.assert_called_once_with(10, 1)
    assert thread.call_args.kwargs["target"] == api._notify_support_admins
    thread.return_value.start.assert_called_once()


def test_worker_limit_does_not_spawn_unbounded_threads(monkeypatch):
    monkeypatch.setattr(ai, "enabled", lambda: True)
    monkeypatch.setattr(ai, "_pending", {})
    slots = Mock()
    slots.acquire.return_value = False
    monkeypatch.setattr(ai, "_slots", slots)
    thread = Mock()
    monkeypatch.setattr(ai.threading, "Thread", thread)
    assert not ai.queue_reply(10, 1)
    thread.assert_not_called()
    slots.acquire.assert_called_once_with(blocking=False)


def test_worker_start_failure_releases_slot(monkeypatch):
    monkeypatch.setattr(ai, "enabled", lambda: True)
    monkeypatch.setattr(ai, "_pending", {})
    slots = Mock()
    slots.acquire.return_value = True
    monkeypatch.setattr(ai, "_slots", slots)
    monkeypatch.setattr(ai.threading, "Thread", Mock(side_effect=RuntimeError))
    assert not ai.queue_reply(10, 1)
    assert not ai.status(10)["pending"]
    slots.release.assert_called_once()


def test_rate_limited_message_never_requests_ai(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api, "_webapp_telegram_id", lambda: 700001)
    monkeypatch.setattr(api, "add_user_support_message", lambda user, body: {"thread_id": 10, "rate_limited": True})
    queue = Mock()
    monkeypatch.setattr(ai, "queue_reply", queue)
    assert api.app.test_client().post('/api/support/messages', json={"body": "Помогите"}).status_code == 429
    queue.assert_not_called()
