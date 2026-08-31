import hashlib
import hmac
import time
from unittest.mock import patch

import pytest

import subscription_api as api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    monkeypatch.setattr(api, "BOT_TOKEN", "123456:test-token")
    return api.app.test_client()


def signed_payload(**overrides):
    payload = {
        "id": 700001,
        "first_name": "Arc",
        "username": "arc_user",
        "auth_date": int(time.time()),
        **overrides,
    }
    data_check = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    secret = hashlib.sha256(api.BOT_TOKEN.encode()).digest()
    payload["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return payload


def test_telegram_login_issues_existing_web_session(client):
    account = {"id": 42, "telegram_id": 700001}
    with patch.object(api, "get_webapp_account", return_value=account), patch.object(api, "create_web_session") as create_session:
        response = client.post("/api/auth/telegram", json=signed_payload())

    assert response.status_code == 200
    create_session.assert_called_once()
    assert create_session.call_args.args[0] == 42
    cookie = response.headers.get("Set-Cookie", "")
    assert "Max-Age=2592000" in cookie
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie


@pytest.mark.parametrize("payload", [
    lambda: {**signed_payload(), "username": "forged"},
    lambda: signed_payload(auth_date=int(time.time()) - 601),
    lambda: {"id": 700001, "auth_date": int(time.time()), "hash": "bad"},
])
def test_telegram_login_rejects_invalid_or_stale_data(client, payload):
    with patch.object(api, "create_web_session") as create_session:
        response = client.post("/api/auth/telegram", json=payload())
    assert response.status_code == 401
    create_session.assert_not_called()


def test_telegram_login_does_not_create_unknown_identity(client):
    with patch.object(api, "get_webapp_account", return_value=None), patch.object(api, "create_web_session") as create_session:
        response = client.post("/api/auth/telegram", json=signed_payload())
    assert response.status_code == 404
    assert response.get_json()["error"] == "telegram_account_not_found"
    create_session.assert_not_called()
