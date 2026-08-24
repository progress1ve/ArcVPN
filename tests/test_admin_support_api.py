import sqlite3
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

import subscription_api as api
from database.db_admin_roles import role_allows


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    monkeypatch.setitem(api.app.config, "PROPAGATE_EXCEPTIONS", False)
    return api.app.test_client()


@pytest.fixture
def support_db(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT
        );
        CREATE TABLE support_threads (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE support_messages (
            id INTEGER PRIMARY KEY,
            thread_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            read_at TEXT
        );
        INSERT INTO users VALUES (1, 700001, 'alice', 'Alice');
        INSERT INTO users VALUES (2, 700002, 'bob', 'Bob');
        INSERT INTO support_threads VALUES (10, 1, 'open', '2026-08-24 10:00:00');
        INSERT INTO support_threads VALUES (20, 2, 'closed', '2026-08-24 11:00:00');
        INSERT INTO support_messages VALUES
            (101, 10, 'user', 'Need help', '2026-08-24 09:58:00', NULL),
            (102, 10, 'admin', 'Looking into it', '2026-08-24 09:59:00', NULL),
            (103, 10, 'user', 'Any update?', '2026-08-24 10:00:00', NULL),
            (201, 20, 'user', 'Resolved', '2026-08-24 11:00:00', '2026-08-24 11:01:00');
        """
    )

    @contextmanager
    def fake_get_db():
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    monkeypatch.setattr(api, "get_db", fake_get_db)
    yield connection
    connection.close()


def authorize(monkeypatch, role):
    monkeypatch.setattr(
        api,
        "_admin_access_context",
        lambda: {"actor_id": "test-admin", "role": role},
    )
    monkeypatch.setattr(api, "append_admin_audit", Mock())


def test_thread_list_returns_open_first_with_unread_count(client, support_db, monkeypatch):
    authorize(monkeypatch, "support")

    response = client.get("/api/admin/support/threads")

    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    threads = response.get_json()["threads"]
    assert [thread["id"] for thread in threads] == [10, 20]
    assert threads[0]["last_message"] == "Any update?"
    assert threads[0]["unread"] == 2


def test_thread_detail_returns_messages_and_marks_user_messages_read(
    client, support_db, monkeypatch
):
    authorize(monkeypatch, "viewer")
    monkeypatch.setattr(
        api,
        "get_support_thread",
        lambda thread_id: {
            "id": thread_id,
            "status": "open",
            "telegram_id": 700001,
            "username": "alice",
            "first_name": "Alice",
        },
    )

    response = client.get("/api/admin/support/threads/10")

    assert response.status_code == 200
    assert [message["id"] for message in response.get_json()["messages"]] == [101, 102, 103]
    unread = support_db.execute(
        "SELECT COUNT(*) FROM support_messages "
        "WHERE thread_id=10 AND sender='user' AND read_at IS NULL"
    ).fetchone()[0]
    assert unread == 0


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_thread_returns_404(client, monkeypatch, method):
    authorize(monkeypatch, "support")
    monkeypatch.setattr(api, "get_support_thread", lambda _thread_id: None)

    response = getattr(client, method)(
        "/api/admin/support/threads/999",
        json={"body": "hello"} if method == "post" else None,
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "thread_not_found"


@pytest.mark.parametrize("body", ["", "   ", "x" * 4001])
def test_reply_rejects_empty_or_oversized_body(client, monkeypatch, body):
    authorize(monkeypatch, "support")
    monkeypatch.setattr(api, "get_support_thread", lambda _thread_id: {"id": 10})
    add_message = Mock()
    monkeypatch.setattr(api, "add_admin_support_message", add_message)

    response = client.post("/api/admin/support/threads/10", json={"body": body})

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_message"
    add_message.assert_not_called()


@pytest.mark.parametrize(
    ("role", "can_read", "can_reply"),
    [
        ("owner", True, True),
        ("operator", True, True),
        ("support", True, True),
        ("viewer", True, False),
        ("finance", False, False),
    ],
)
def test_support_permissions_match_admin_roles(role, can_read, can_reply):
    assert role_allows(role, "support.read") is can_read
    assert role_allows(role, "support.reply") is can_reply


@pytest.mark.parametrize(
    ("role", "method", "expected_status"),
    [
        ("viewer", "get", 404),
        ("viewer", "post", 403),
        ("finance", "get", 403),
        ("support", "post", 404),
    ],
)
def test_endpoint_enforces_read_and_reply_permissions(
    client, monkeypatch, role, method, expected_status
):
    authorize(monkeypatch, role)
    monkeypatch.setattr(api, "get_support_thread", lambda _thread_id: None)

    response = getattr(client, method)(
        "/api/admin/support/threads/999",
        json={"body": "hello"} if method == "post" else None,
    )

    assert response.status_code == expected_status


def test_reply_survives_telegram_delivery_failure(client, monkeypatch):
    authorize(monkeypatch, "support")
    thread = {"id": 10, "telegram_id": 700001}
    saved = {"id": 104, "sender": "admin", "body": "We can help"}
    monkeypatch.setattr(api, "get_support_thread", lambda _thread_id: thread)
    add_message = Mock(return_value=saved)
    monkeypatch.setattr(api, "add_admin_support_message", add_message)
    monkeypatch.setattr(api.config, "BOT_TOKEN", "test-token", raising=False)
    telegram = Mock(side_effect=OSError("telegram unavailable"))
    monkeypatch.setattr(api.urllib.request, "urlopen", telegram)

    response = client.post(
        "/api/admin/support/threads/10", json={"body": "  We can help  "}
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == saved
    add_message.assert_called_once_with(10, 0, "We can help")
    telegram.assert_called_once()


def test_reply_survives_audit_failure_after_message_is_persisted(client, monkeypatch):
    authorize(monkeypatch, "support")
    monkeypatch.setattr(api, "get_support_thread", lambda _thread_id: {"id": 10})
    add_message = Mock(return_value={"id": 104, "sender": "admin", "body": "Saved"})
    monkeypatch.setattr(api, "add_admin_support_message", add_message)
    monkeypatch.setattr(api, "append_admin_audit", Mock(side_effect=OSError("audit unavailable")))

    response = client.post("/api/admin/support/threads/10", json={"body": "Saved"})

    assert response.status_code == 200
    add_message.assert_called_once()
