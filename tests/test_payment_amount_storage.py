from database.db_payments import _order_amount_cents


def test_yookassa_order_uses_ruble_tariff_price_in_kopecks():
    tariff = {"price_rub": 399, "price_cents": 478}

    assert _order_amount_cents(tariff, "yookassa_qr", None) == 39900
    assert _order_amount_cents(tariff, "yookassa_qr", None, 20) == 37900


def test_non_ruble_and_explicit_amounts_preserve_their_channel_value():
    tariff = {"price_rub": 399, "price_cents": 478}

    assert _order_amount_cents(tariff, "crypto", None) == 478
    assert _order_amount_cents(tariff, "yookassa", 12345) == 12345
