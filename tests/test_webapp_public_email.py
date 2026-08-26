from unittest.mock import patch

import subscription_api as api


def test_root_is_customer_app_and_admin_is_noindex():
    client = api.app.test_client()
    root = client.get("/")
    admin = client.get("/admin")
    assert root.status_code == 200
    assert admin.status_code == 200
    assert root.headers.get("X-Robots-Tag") is None
    assert admin.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_panel_host_keeps_admin_but_rejects_customer_app_shell():
    client = api.app.test_client()
    admin = client.get("/admin", headers={"Host": "panel.arccnet.space"})
    customer = client.get("/app", headers={"Host": "panel.arccnet.space"})
    assert admin.status_code == 200
    assert customer.status_code == 404


def test_unknown_login_email_has_neutral_success_and_sends_nothing():
    with patch.object(api, "SMTP_HOST", "smtp.example.test"), patch.object(
        api, "SMTP_FROM", "ArcVPN <login@example.test>"
    ), patch.object(api, "_email_rate_allowed", return_value=True), patch.object(
        api, "get_user_by_verified_email", return_value=None
    ), patch.object(api, "save_email_code") as save_code, patch.object(api, "_send_email_code") as send:
        response = api.app.test_client().post(
            "/api/auth/email/request", json={"email": "unknown@example.com", "purpose": "login"}
        )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "sent": True}
    save_code.assert_not_called()
    send.assert_not_called()


def test_successful_email_login_consumes_code_before_session():
    raw_code = "123456"
    record = {"id": 9, "attempts": 0, "code_hash": api._email_code_hash(raw_code, "login")}
    with patch.object(api, "get_user_by_verified_email", return_value={"id": 4}), patch.object(
        api, "get_email_code", return_value=record
    ), patch.object(api, "link_verified_email") as consume, patch.object(api, "create_web_session") as session:
        response = api.app.test_client().post(
            "/api/auth/email/verify",
            json={"email": "known@example.com", "purpose": "login", "code": raw_code},
        )
    assert response.status_code == 200
    consume.assert_called_once_with(4, "known@example.com")
    session.assert_called_once()
    cookie = response.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=Lax" in cookie
