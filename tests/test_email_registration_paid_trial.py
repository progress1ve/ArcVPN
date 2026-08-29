import asyncio
import sqlite3
from unittest.mock import Mock, patch

import subscription_api as api
from database import connection
from database.db_webapp import acquire_email_paid_trial_claim, update_email_paid_trial_claim
from database.migrations import migration_60


def client():
    api.app.config["TESTING"] = True
    return api.app.test_client()


def test_email_registration_request_stores_independent_code():
    with patch.object(api, "SMTP_HOST", "smtp.example"), patch.object(
        api, "SMTP_FROM", "hello@example.com"
    ), patch.object(api, "_email_rate_allowed", return_value=True), patch.object(
        api, "get_user_by_verified_email", return_value=None
    ), patch.object(api, "save_email_registration_code") as save, patch.object(
        api, "_send_email_code", return_value=True
    ):
        response = client().post(
            "/api/auth/email/request",
            json={"email": "new@example.com", "purpose": "register"},
        )
    assert response.status_code == 200
    save.assert_called_once()
    assert save.call_args.args[0] == "new@example.com"


def test_email_registration_verify_creates_session_and_consumes_code():
    raw_code = "314159"
    record = {"id": 8, "attempts": 0, "code_hash": api._email_code_hash(raw_code, "register")}
    with patch.object(api, "get_email_registration_code", return_value=record), patch.object(
        api, "create_email_user", return_value={"id": 44, "telegram_id": -1000000000044}
    ) as create_user, patch.object(api, "create_web_session") as create_session:
        response = client().post(
            "/api/auth/email/verify",
            json={"email": "new@example.com", "purpose": "register", "code": raw_code},
        )
    assert response.status_code == 200
    assert response.get_json()["registered"] is True
    assert f"{api.WEB_SESSION_COOKIE}=" in response.headers["Set-Cookie"]
    create_user.assert_called_once_with("new@example.com")
    create_session.assert_called_once()


def test_paid_trial_is_server_priced_and_requires_recurring():
    async def create_payment(**kwargs):
        assert kwargs["amount_rub"] == 10
        assert kwargs["save_payment_method"] is True
        return {"yookassa_payment_id": "provider-1", "qr_url": "https://pay.example", "status": "pending"}

    def run(coro, timeout=None):
        return asyncio.run(coro)

    fake_db = Mock()
    fake_db.__enter__ = Mock(return_value=fake_db)
    fake_db.__exit__ = Mock(return_value=False)
    with patch.object(api, "_webapp_telegram_id", return_value=-1001), patch.object(
        api, "get_webapp_account", return_value={"id": 9, "identity_source": "email"}
    ), patch.object(api, "email_paid_trial_state", return_value="available"), patch.object(
        api, "get_setting", return_value="1"
    ), patch.object(api, "get_standard_trial_tariff", return_value={"id": 7}), patch.object(
        api, "prepare_payment_order", return_value={"order_id": "00trial"}
    ), patch.object(api, "acquire_email_paid_trial_claim", return_value=True
    ), patch.object(api, "get_db", return_value=fake_db), patch.object(
        api, "set_payment_requested_entitlements", return_value=True
    ) as entitlements, patch.object(api, "create_yookassa_qr_payment", create_payment), patch.object(
        api.ASYNC_EXECUTOR, "run", side_effect=run
    ), patch.object(api, "save_yookassa_payment_id"):
        response = client().post("/api/payments/email-trial", json={"method": "sbp"})
    assert response.status_code == 200
    assert response.get_json()["amount_rub"] == 10
    entitlements.assert_called_once_with("00trial", 3, 5)
    update = fake_db.execute.call_args.args[0]
    assert "period_days=7" in update and "offer_code='email_paid_trial'" in update


def test_paid_trial_rejects_second_checkout_before_provider_call():
    fake_db = Mock()
    fake_db.__enter__ = Mock(return_value=fake_db)
    fake_db.__exit__ = Mock(return_value=False)
    with patch.object(api, "_webapp_telegram_id", return_value=-1001), patch.object(
        api, "get_webapp_account", return_value={"id": 9, "identity_source": "email"}
    ), patch.object(api, "email_paid_trial_state", return_value="available"), patch.object(
        api, "get_setting", return_value="1"
    ), patch.object(api, "get_standard_trial_tariff", return_value={"id": 7}), patch.object(
        api, "prepare_payment_order", return_value={"order_id": "00trial-second"}
    ), patch.object(api, "acquire_email_paid_trial_claim", return_value=False), patch.object(
        api, "get_db", return_value=fake_db
    ), patch.object(api, "create_yookassa_qr_payment") as provider:
        response = client().post("/api/payments/email-trial", json={"method": "sbp"})
    assert response.status_code == 409
    assert response.get_json()["error"] == "paid_trial_payment_pending"
    provider.assert_not_called()


def test_paid_trial_claim_is_atomic_and_retryable_only_after_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "paid-trial-claim.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO users(id) VALUES(9)")
    migration_60(conn)
    conn.commit()
    conn.close()
    monkeypatch.setattr(connection, "DB_PATH", db_path)

    assert acquire_email_paid_trial_claim(9, "first-order") is True
    assert acquire_email_paid_trial_claim(9, "second-order") is False
    assert update_email_paid_trial_claim("first-order", "failed") is True
    assert acquire_email_paid_trial_claim(9, "second-order") is True
