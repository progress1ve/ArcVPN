import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

import subscription_api as api
from bot.services import vpn_api
import database.requests as database_requests


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    return api.app.test_client()


@pytest.fixture
def subscription_db(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL);
        CREATE TABLE vpn_keys (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            panel_disabled_at TEXT,
            sub_id TEXT
        );
        CREATE TABLE user_devices (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            is_active INTEGER,
            revoked_at TEXT,
            device_sub_id TEXT
        );
        INSERT INTO users VALUES (1, 700001);
        INSERT INTO vpn_keys VALUES (10, 1, datetime('now', '+30 days'), NULL, 'stable');
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


def authorize(monkeypatch, role="operator"):
    monkeypatch.setattr(api, "_admin_access_context", lambda: {"actor_id": "qa", "role": role})
    monkeypatch.setattr(api, "append_admin_audit", Mock())


def run_coro(coro, timeout=None):
    return asyncio.run(coro)


def test_disable_persists_and_requires_verified_panel_revoke(
    client, subscription_db, monkeypatch
):
    authorize(monkeypatch)
    audit = Mock()
    calls = []

    async def disable(key_id):
        calls.append(key_id)
        return True

    monkeypatch.setattr(api, "append_admin_audit", audit)
    monkeypatch.setattr(api, "disable_key_on_panel", disable)
    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", run_coro)

    response = client.patch(
        "/api/admin/users/700001/subscription", json={"action": "disable"}
    )

    assert response.status_code == 200
    assert calls == [10]
    row = subscription_db.execute(
        "SELECT expires_at,panel_disabled_at,sub_id FROM vpn_keys WHERE id=10"
    ).fetchone()
    assert row["panel_disabled_at"] is not None
    assert row["sub_id"] == "stable"
    assert audit.call_args.args[:2] == ("subscription.manage", "success")


def test_panel_revoke_failure_is_visible_and_retryable(
    client, subscription_db, monkeypatch
):
    authorize(monkeypatch)
    audit = Mock()

    async def disable(_key_id):
        return False

    monkeypatch.setattr(api, "append_admin_audit", audit)
    monkeypatch.setattr(api, "disable_key_on_panel", disable)
    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", run_coro)

    response = client.patch(
        "/api/admin/users/700001/subscription", json={"action": "disable"}
    )

    assert response.status_code == 502
    assert response.get_json()["error"] == "panel_sync_failed"
    assert subscription_db.execute(
        "SELECT panel_disabled_at FROM vpn_keys WHERE id=10"
    ).fetchone()[0] is not None
    assert audit.call_args.args[:2] == ("subscription.manage", "panel_sync_failed")


def test_activation_is_pushed_to_panel(client, subscription_db, monkeypatch):
    authorize(monkeypatch)
    pushed = []

    async def push(key_id):
        pushed.append(key_id)
        return True

    monkeypatch.setattr(api, "append_admin_audit", Mock())
    monkeypatch.setattr(api, "push_key_to_panel", push)
    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", run_coro)

    response = client.patch(
        "/api/admin/users/700001/subscription",
        json={"action": "activate_days", "days": 14},
    )

    assert response.status_code == 200
    assert pushed == [10]


def test_viewer_cannot_mutate_subscription(client, monkeypatch):
    authorize(monkeypatch, "viewer")
    response = client.patch(
        "/api/admin/users/700001/subscription", json={"action": "disable"}
    )
    assert response.status_code == 403


class FakeRemnawaveClient:
    def __init__(self):
        self.updated = None
        self.reads = 0

    async def get_user(self, _email):
        self.reads += 1
        return {"id": "remote", "status": "ACTIVE" if self.reads == 1 else "DISABLED"}

    async def update_client_full(self, **payload):
        self.updated = payload
        return True


def remnawave_key(expires_at):
    return {
        "id": 10,
        "server_id": 3,
        "server_active": 1,
        "server_name": "Remnawave",
        "panel_type": "remnawave",
        "panel_write_mode": "production",
        "panel_email": "user@example.com",
        "panel_inbound_id": 42,
        "client_uuid": "fixed-user-uuid",
        "expires_at": expires_at,
        "traffic_limit": 1024,
        "device_limit": 4,
    }


def test_remnawave_disable_updates_and_verifies_authoritative_status(monkeypatch):
    client = FakeRemnawaveClient()
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    monkeypatch.setattr(database_requests, "get_vpn_key_by_id", lambda _key_id: remnawave_key(expired))
    monkeypatch.setattr(vpn_api, "get_client_from_server_data", lambda _server: client)

    assert asyncio.run(vpn_api.disable_key_on_panel(10)) is True
    assert client.updated["enable"] is False
    assert client.updated["client_uuid"] == "fixed-user-uuid"
    assert client.updated["limit_ip"] == 4


def test_push_key_derives_active_state_and_device_limit(monkeypatch):
    class PushClient:
        updated = None

        async def update_client_full(self, **payload):
            self.updated = payload
            return True

    client = PushClient()
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    monkeypatch.setattr(database_requests, "get_vpn_key_by_id", lambda _key_id: remnawave_key(future))
    monkeypatch.setattr(vpn_api, "get_client_from_server_data", lambda _server: client)

    assert asyncio.run(vpn_api.push_key_to_panel(10)) is True
    assert client.updated["enable"] is True
    assert client.updated["limit_ip"] == 4
    assert client.updated["client_uuid"] == "fixed-user-uuid"
