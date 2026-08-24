from unittest.mock import Mock

import pytest

import subscription_api as api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    return api.app.test_client()


def test_access_requires_admin_session(client, monkeypatch):
    monkeypatch.setattr(api, "_admin_access_context", lambda: None)
    response = client.get("/api/admin/access")
    assert response.status_code == 403


def test_support_access_exposes_only_effective_permissions(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "_admin_access_context",
        lambda: {"actor_id": "700001", "role": "support"},
    )
    response = client.get("/api/admin/access")
    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "role": "support",
        "permissions": ["support.read", "support.reply"],
    }


def test_owner_can_list_role_assignments(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "_admin_access_context",
        lambda: {"actor_id": "password-session", "role": "owner"},
    )
    monkeypatch.setattr(api, "list_admin_roles", lambda: [{"telegram_id": 7, "role": "viewer"}])
    response = client.get("/api/admin/roles")
    assert response.status_code == 200
    assert response.get_json()["assignments"] == [{"telegram_id": 7, "role": "viewer"}]


def test_owner_can_assign_existing_role(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "_admin_access_context",
        lambda: {"actor_id": "900001", "role": "owner"},
    )
    assigned = []
    monkeypatch.setattr(
        api,
        "set_admin_role",
        lambda telegram_id, role, assigned_by: assigned.append((telegram_id, role, assigned_by)),
    )
    monkeypatch.setattr(
        api,
        "list_admin_roles",
        lambda: [{"telegram_id": 700001, "role": "support"}],
    )
    monkeypatch.setattr(api, "append_admin_audit", Mock())

    response = client.post(
        "/api/admin/roles", json={"telegram_id": 700001, "role": "support"}
    )

    assert response.status_code == 200
    assert assigned == [(700001, "support", 900001)]
    assert response.get_json()["assignments"] == [
        {"telegram_id": 700001, "role": "support"}
    ]


def test_denied_role_endpoint_survives_audit_failure(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "_admin_access_context",
        lambda: {"actor_id": "700001", "role": "support"},
    )
    monkeypatch.setattr(api, "append_admin_audit", Mock(side_effect=RuntimeError("audit unavailable")))
    response = client.get("/api/admin/roles")
    assert response.status_code == 403
    assert response.get_json()["error"] == "admin_forbidden"
