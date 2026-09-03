import asyncio
from unittest.mock import patch

import pytest

import subscription_api as api


CATALOG = [
    {
        "id": family_index * 4 + period_index + 1,
        "product_code": code,
        "period_months": months,
        "price_rub": prices[period_index],
    }
    for family_index, (code, prices) in enumerate((
        ("economy", [93, 259, 499, 931]),
        ("standard", [145, 399, 759, 1469]),
        ("family", [345, 939, 1789, 3389]),
    ))
    for period_index, months in enumerate((1, 3, 6, 12))
]


@pytest.mark.parametrize("months,index", [(1, 0), (3, 1), (6, 2), (12, 3)])
def test_custom_quote_reproduces_catalog_anchors(months, index):
    selected = {"period_months": months}
    for devices, lte, prices in (
        (2, 0, [93, 259, 499, 931]),
        (3, 45, [145, 399, 759, 1469]),
        (8, 115, [345, 939, 1789, 3389]),
    ):
        quote = api._custom_tariff_quote(selected, devices, lte, CATALOG)
        expected_base = prices[index]
        assert quote["base_price_rub"] == expected_base
        assert quote["price_rub"] == expected_base


def test_custom_bypass_floor_and_non_anchor_premium():
    floor_quote = api._custom_tariff_quote({"period_months": 3}, 1, 15, CATALOG)
    assert floor_quote["price_rub"] == 300
    assert floor_quote["monthly_rub"] == 100
    custom = api._custom_tariff_quote({"period_months": 3}, 5, 75, CATALOG)
    assert custom["price_rub"] > custom["base_price_rub"]


def test_custom_quote_is_monotonic_for_supported_choices():
    selected = {"period_months": 3}
    base = api._custom_tariff_quote(selected, 1, 0, CATALOG)["price_rub"]
    more_devices = api._custom_tariff_quote(selected, 5, 0, CATALOG)["price_rub"]
    more_bypass = api._custom_tariff_quote(selected, 5, 75, CATALOG)["price_rub"]
    assert 0 < base < more_devices < more_bypass


@pytest.mark.parametrize("months", [1, 3, 6, 12])
def test_custom_quote_matrix_has_no_price_inversions(months):
    lte_choices = [0, 15, 30, 45, 75, 115]
    for devices in range(1, 16):
        prices = [api._custom_tariff_quote({"period_months": months}, devices, gb, CATALOG)["price_rub"] for gb in lte_choices]
        assert prices == sorted(prices)
    for lte in lte_choices:
        prices = [api._custom_tariff_quote({"period_months": months}, devices, lte, CATALOG)["price_rub"] for devices in range(1, 16)]
        assert prices == sorted(prices)


@pytest.mark.parametrize("devices,lte", [(0, 45), (16, 45), (3, 10), (3, 999)])
def test_custom_quote_rejects_values_outside_the_product_choices(devices, lte):
    with pytest.raises(ValueError, match="invalid_custom_entitlements"):
        api._custom_tariff_quote({"period_months": 3}, devices, lte, CATALOG)


def test_custom_quote_rejects_incomplete_catalog():
    with pytest.raises(ValueError, match="custom_catalog_incomplete"):
        api._custom_tariff_quote({"period_months": 3}, 3, 45, CATALOG[:-5])


def test_custom_payment_uses_server_quote_and_persists_entitlements():
    async def create_payment(**kwargs):
        assert kwargs["amount_rub"] == 399
        assert kwargs["description"] == "ArcVPN — свой тариф"
        return {"yookassa_payment_id": "provider-custom", "qr_url": "https://pay.example", "status": "pending"}

    def run(coro, timeout=None):
        return asyncio.run(coro)

    standard = next(item for item in CATALOG if item["product_code"] == "standard" and item["period_months"] == 3)
    with patch.object(api, "_webapp_telegram_id", return_value=123), patch.object(
        api, "get_user_internal_id", return_value=5
    ), patch.object(api, "get_tariff_by_id", return_value=standard), patch.object(
        api, "get_all_tariffs", return_value=CATALOG
    ), patch.object(api, "get_user_keys_for_display", return_value=[]), patch.object(
        api, "prepare_payment_order", return_value={"order_id": "custom-order"}
    ), patch.object(api, "set_payment_requested_entitlements", return_value=True) as entitlements, patch.object(
        api, "create_yookassa_qr_payment", create_payment
    ), patch.object(api.ASYNC_EXECUTOR, "run", side_effect=run), patch.object(
        api, "save_yookassa_payment_id"
    ):
        response = api.app.test_client().post("/api/payments/sbp", json={
            "tariff_id": standard["id"], "devices": 3, "lte_gb": 45,
            "custom": True, "auto_renew": False,
        })
    assert response.status_code == 200
    assert response.get_json()["base_amount_rub"] == 399
    assert response.get_json()["custom"] is True
    entitlements.assert_called_once_with("custom-order", 3, 45)


def test_addon_payment_uses_server_price_table():
    async def create_payment(**kwargs):
        assert kwargs["amount_rub"] == 35
        return {"yookassa_payment_id": "provider-addon", "qr_url": "https://pay.example", "status": "pending"}

    def run(coro, timeout=None):
        return asyncio.run(coro)

    with patch.object(api, "_webapp_telegram_id", return_value=123), patch.object(
        api, "get_user_internal_id", return_value=5
    ), patch.object(api, "get_user_keys_for_display", return_value=[{"id": 9, "is_active": True}]), patch.object(
        api, "prepare_payment_order", return_value={"order_id": "addon-order"}
    ) as prepare, patch.object(api, "set_payment_addon", return_value=True) as addon, patch.object(
        api, "create_yookassa_qr_payment", create_payment
    ), patch.object(api.ASYNC_EXECUTOR, "run", side_effect=run), patch.object(api, "save_yookassa_payment_id"):
        response = api.app.test_client().post("/api/payments/sbp", json={"addon": {"kind": "lte", "units": 15}})
    assert response.status_code == 200
    assert response.get_json()["amount_rub"] == 35
    prepare.assert_called_once()
    addon.assert_called_once_with("addon-order", "lte", 15)
