from unittest.mock import patch

import subscription_api as api


def test_promocode_quote_is_authorized_and_does_not_consume_usage():
    promo = {
        "id": 7, "code": "SAVE10", "discount_type": "percent",
        "discount_percent": 10, "discount_rub": 0,
    }
    with patch.object(api, "_webapp_telegram_id", return_value=123), patch.object(
        api, "get_user_internal_id", return_value=5
    ), patch.object(api, "get_tariff_by_id", return_value={"id": 9, "price_rub": 759}), patch(
        "database.db_promocodes.is_promocode_valid", return_value=(True, None, promo)
    ), patch("database.db_promocodes.use_promocode") as use_promocode:
        response = api.app.test_client().post(
            "/api/promocodes/validate", json={"tariff_id": 9, "code": " save10 "}
        )
    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True, "code": "SAVE10", "base_amount_rub": 759,
        "discount_type": "percent", "discount_value": 10, "discount_label": "10%",
        "discount_rub": 75, "final_amount_rub": 684,
    }
    use_promocode.assert_not_called()


def test_promocode_quote_returns_stable_machine_error():
    with patch.object(api, "_webapp_telegram_id", return_value=123), patch.object(
        api, "get_user_internal_id", return_value=5
    ), patch.object(api, "get_tariff_by_id", return_value={"id": 9, "price_rub": 145}), patch(
        "database.db_promocodes.is_promocode_valid",
        return_value=(False, "❌ Срок действия промокода истек", None),
    ):
        response = api.app.test_client().post(
            "/api/promocodes/validate", json={"tariff_id": 9, "code": "OLD"}
        )
    assert response.status_code == 400
    assert response.get_json()["error"] == "promocode_expired"


def test_promocode_quote_requires_customer_auth():
    with patch.object(api, "_webapp_telegram_id", return_value=None):
        response = api.app.test_client().post(
            "/api/promocodes/validate", json={"tariff_id": 9, "code": "SAVE10"}
        )
    assert response.status_code == 401
