import json
import sqlite3
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from bot.services import support_ai as ai
from database import db_support as db
ORIGINAL_HANDOFF_STATUS = db.assistant_handoff_reason


@pytest.fixture(autouse=True)
def isolated_provider_configuration(monkeypatch):
    monkeypatch.setenv("SUPPORT_AI_PROVIDER", "openai")
    monkeypatch.delenv("SUPPORT_AI_MODEL", raising=False)
    monkeypatch.setattr(ai, "provider_health", Mock())
    monkeypatch.setattr(db, 'assistant_handoff_reason', lambda thread_id: None)


@pytest.fixture
def support_db(tmp_path, monkeypatch):
    path = tmp_path / "support.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript("""
      CREATE TABLE users(id INTEGER PRIMARY KEY,telegram_id INTEGER,username TEXT,first_name TEXT);
      CREATE TABLE support_threads(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE,status TEXT DEFAULT 'open',updated_at TEXT);
      CREATE TABLE support_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,thread_id INTEGER,sender TEXT CHECK(sender IN ('user','admin')),sender_telegram_id INTEGER,body TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,read_at TEXT);
      INSERT INTO users VALUES(1,700001,'qa','QA');
      INSERT INTO support_threads VALUES(10,1,'open',CURRENT_TIMESTAMP);
      INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES(10,'user',700001,'VPN не подключается');
    """)
    from database.migrations import migration_77
    migration_77(connection)
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
    monkeypatch.setattr(db, 'assistant_handoff_reason', ORIGINAL_HANDOFF_STATUS)
    return connect


def test_disabled_without_both_explicit_flag_and_key(monkeypatch):
    monkeypatch.delenv("SUPPORT_AI_ENABLED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert not ai.queue_reply(10, 1)
    monkeypatch.setenv("SUPPORT_AI_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ai.status() == {"enabled": False, "pending": False, "handoff": False}


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


@pytest.mark.parametrize("provider,key,host", [
    ("groq", "GROQ_API_KEY", "api.groq.com"),
    ("openrouter", "OPENROUTER_API_KEY", "openrouter.ai"),
    ("gemini", "GEMINI_API_KEY", "generativelanguage.googleapis.com"),
])
def test_compatible_provider_payloads_are_bounded_and_redacted(monkeypatch, provider, key, host):
    monkeypatch.setenv("SUPPORT_AI_PROVIDER", provider)
    monkeypatch.setenv(key, "test-key")
    monkeypatch.setenv("SUPPORT_AI_ENABLED", "true")
    captured = {}
    @contextmanager
    def response(request, timeout):
        captured.update(json.loads(request.data), host=request.host, timeout=timeout)
        yield Mock(read=lambda n: json.dumps({"choices": [{"message": {"content": "Обновите подписку."}}]}).encode())
    monkeypatch.setattr(ai.urllib.request, "urlopen", response)
    assert ai.enabled()
    assert ai.request_reply([{"sender": "user", "body": "https://example.test/private"}]) == "Обновите подписку."
    assert captured["host"] == host and captured["timeout"] == 8
    assert "private" not in json.dumps(captured["messages"])
    assert "tools" not in captured
    if provider == "groq":
        assert captured["max_completion_tokens"] == 1024
        assert captured["include_reasoning"] is False


def test_failure_is_reported_after_user_fallback_has_been_saved(support_db, monkeypatch):
    monkeypatch.setattr(ai, "request_reply", Mock(side_effect=TimeoutError))
    def alert(healthy, error):
        assert not healthy and isinstance(error, TimeoutError)
        assert db.get_support_messages(700001)["messages"][-1]["body"] == ai.FALLBACK
    monkeypatch.setattr(ai, "provider_health", alert)
    _run_reserved_reply(monkeypatch)


@pytest.mark.parametrize("invented", [
    "Выберите OpenVPN или WireGuard.",
    "Найдите ArcVPN в Google Play.",
    "В App Store установите ArcVPN.",
    "Попробуйте Outline.",
])
def test_invented_clients_are_replaced_by_supported_onboarding(invented):
    answer = ai.verified_reply(invented)
    assert "Happ или INCY" in answer and "Автовыбор" in answer
    assert invented not in answer


def test_plain_chat_does_not_expose_markdown():
    assert ai.verified_reply("## Проверка\n1. **Откройте** `Happ`.\n[Инструкция](https://example.test)") == "Проверка\n1. Откройте Happ.\nИнструкция"


def test_two_failed_checks_in_one_turn_handoff_instead_of_looping():
    messages = [{'sender':'user','body':'Android, Telegram. Смена сети не помогла, перезапуск тоже не помог. Telegram всё равно не подключается.'}]
    assert 'менеджер' in ai.verified_reply('Попробуйте другую страну.', messages)


def test_known_disabled_proxy_cannot_be_recommended_again():
    messages = [{'sender':'user','body':'Telegram на Android. Прокси выключен, другие сайты открываются.'}]
    answer = ai.verified_reply('Отключите прокси и перезапустите Telegram. Какое устройство?', messages)
    assert 'Отключите' not in answer and 'медиа' in answer and 'Какое устройство' not in answer


def test_internet_word_does_not_mean_proxy_is_disabled():
    rows = [{'sender':'user','body':'Telegram не работает. Прокси включён, интернет в других приложениях есть.'}]
    assert 'прокси' in ai.verified_reply('Какое устройство?', rows).lower()


def test_entities_escaped_numbering_and_inline_steps_are_readable():
    assert ai.plain_reply('1. **Проверьте** прокси. &#x20; 2\\. Перезапустите. &amp;#x20; 3. Проверьте сайты.') == '1. Проверьте прокси.\n2. Перезапустите.\n3. Проверьте сайты.'


def test_telegram_guard_does_not_repeat_generic_location_advice():
    rows = [{'sender':'user','body':'Не работает тг с VPN'}, {'sender':'user','body':'Happ, автовыбор выбран, блокировок нет'}]
    answer = ai.verified_reply('Выберите Автовыбор и профиль обхода.',rows)
    assert 'Прокси' in answer and 'Автовыбор' not in answer and 'обход' not in answer
    rows.append({'sender':'user','body':'Прокси уже выключен, ничего не изменилось'})
    assert 'ОС' in ai.verified_reply('Какая у вас ОС?', rows)
    assert 'устройстве' in ai.verified_reply('Выберите другую страну.',rows)
    rows.append({'sender':'user','body':'После проверки другой сети всё равно не работает'})
    assert 'менеджера' in ai.verified_reply('Снова выберите Автовыбор.',rows)


def test_changed_service_does_not_reuse_old_telegram_diagnosis():
    rows=[{'sender':'user','body':'Не работает Telegram'},{'sender':'user','body':'Теперь вопрос про YouTube'}]
    assert ai.verified_reply('Что не открывается в YouTube?',rows)=='Что не открывается в YouTube?'


def test_context_is_fresh_and_never_crosses_users(support_db):
    with support_db() as c:
        c.execute("UPDATE support_messages SET body='Happ, Telegram не работает'")
        c.execute("INSERT INTO users VALUES(2,700002,'other','Other')")
        c.execute("INSERT INTO support_threads(id,user_id,status,updated_at) VALUES(20,2,'open',CURRENT_TIMESTAMP)")
        c.execute("INSERT INTO support_messages(thread_id,sender,body) VALUES(20,'user','INCY, другая проблема')")
        for i in range(9):
            c.execute("INSERT INTO support_messages(thread_id,sender,body) VALUES(10,'admin','Продолжение')")
        latest=c.execute("INSERT INTO support_messages(thread_id,sender,body) VALUES(10,'user','Теперь использую INCY')").lastrowid
    context=db.get_assistant_context(10,latest)
    assert context[0]['body']=='Happ, Telegram не работает'
    assert context[-1]['body']=='Теперь использую INCY'
    assert all('другая проблема' not in row['body'] for row in context)
    assert db.get_assistant_context(20,latest)==[]


def test_tenth_attempt_hands_off_once_even_when_transport_throttles(support_db,monkeypatch):
    result=None
    for i in range(10):
        result=db.add_user_support_message(700001,f'Сообщение {i}')
    assert result['handoff_started'] and result['ai_handoff']
    assert result['assistant_message']['body']==db.SPAM_HANDOFF
    assert db.assistant_handoff_reason(10)=='spam'
    monkeypatch.setattr(ai,'enabled',lambda:True)
    monkeypatch.setattr(ai,'_pending',{})
    provider=Mock()
    monkeypatch.setattr(ai,'request_reply',provider)
    assert not ai.queue_reply(10,result['message']['id'])
    assert not db.add_assistant_support_message(10,result['message']['id'],'Поздний ответ')
    for i in range(20):
        db.add_user_support_message(700001,'Ещё')
    with support_db() as c:
        assert c.execute('SELECT COUNT(*) FROM support_ai_attempts').fetchone()[0]==10
        assert c.execute('SELECT COUNT(*) FROM support_messages WHERE body=?',(db.SPAM_HANDOFF,)).fetchone()[0]==1
    provider.assert_not_called()


def test_rolling_window_expires_and_human_reply_resets_handoff(support_db):
    with support_db() as c:
        c.executemany("INSERT INTO support_ai_attempts(thread_id,created_at) VALUES(10,datetime('now','-6 minutes'))", [()]*9)
    result=db.add_user_support_message(700001,'Новое сообщение')
    assert not result['ai_handoff']
    with support_db() as c:
        assert c.execute('SELECT COUNT(*) FROM support_ai_attempts').fetchone()[0]==1
        c.execute("UPDATE support_threads SET ai_handoff_reason='spam'")
    assert db.add_admin_support_message(10,-1,'Менеджер здесь')
    assert db.assistant_handoff_reason(10) is None
    with support_db() as c:
        assert c.execute('SELECT COUNT(*) FROM support_ai_attempts').fetchone()[0]==0
    assert not db.get_support_messages(700001)['messages'][-1]['is_ai']


def test_closed_case_starts_fresh_context_without_erasing_history(support_db):
    with support_db() as c:
        c.execute("UPDATE support_threads SET status='closed',ai_handoff_reason='spam'")
    result=db.add_user_support_message(700001,'Совсем новый вопрос')
    assert not result['ai_handoff']
    assert db.get_assistant_context(10,result['message']['id'])==[{'sender':'user','body':'Совсем новый вопрос'}]
    assert len(db.get_support_messages(700001)['messages'])==2


def test_parallel_spam_creates_single_handoff_and_bounded_window(support_db):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda i:db.add_user_support_message(700001,f'Параллельный {i}'),range(15)))
    assert sum(bool(r.get('handoff_started')) for r in results)==1
    with support_db() as c:
        assert c.execute('SELECT COUNT(*) FROM support_ai_attempts').fetchone()[0]==10
        assert c.execute('SELECT COUNT(*) FROM support_messages WHERE body=?',(db.SPAM_HANDOFF,)).fetchone()[0]==1


def test_api_handoff_never_queues_provider_or_duplicates_manager_notice(support_db,monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:700001)
    monkeypatch.setattr(api,'add_user_support_message',db.add_user_support_message)
    queue=Mock(return_value=True)
    monkeypatch.setattr(ai,'queue_reply',queue)
    notify_thread=Mock()
    monkeypatch.setattr(api.threading,'Thread',notify_thread)
    client=api.app.test_client()
    results=[client.post('/api/support/messages',json={'body':f'Сообщение {i}'}) for i in range(10)]
    assert results[5].status_code==429
    assert results[-1].status_code==200 and results[-1].json['ai']['handoff']
    assert results[-1].json['assistant_message']['body']==db.SPAM_HANDOFF
    assert queue.call_count==5
    notice_count=notify_thread.call_count
    with support_db() as c:
        c.execute("UPDATE support_messages SET created_at=datetime('now','-2 minutes')")
    result=client.post('/api/support/messages',json={'body':'Дополнение менеджеру'})
    assert result.status_code==200
    assert notify_thread.call_count==notice_count and queue.call_count==5


def test_read_api_formats_old_ai_only_without_rewriting_history(support_db,monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:700001)
    monkeypatch.setattr(api,'get_support_messages',db.get_support_messages)
    original='**Прокси** &#x20; 2\\. Проверка'
    with support_db() as c:
        c.execute("INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES(10,'admin',0,?)",(original,))
    result=api.app.test_client().get('/api/support/messages')
    assert result.json['messages'][-1]['body']=='Прокси\n2. Проверка'
    with support_db() as c:
        assert c.execute('SELECT body FROM support_messages ORDER BY id DESC LIMIT 1').fetchone()[0]==original
