import base64
import json
from unittest.mock import patch

from subscription_api import (
    ActiveKeyRecord,
    _build_happ_json_subscription,
    _build_plain_text_subscription,
    _client_dns_config,
    _response_from_prepared,
    _subscription_announce_base64,
    PreparedSubscription,
)


def _key(telegram_id=42):
    return ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "Стандарт", telegram_id)


def test_lte_announce_is_complete_and_explains_usage_bar():
    with patch("subscription_api.get_user_entitlements", return_value={
        "lte_quota_gb": 45,
        "lte_remaining_bytes": int(44.2 * 1024**3),
    }):
        text = base64.b64decode(_subscription_announce_base64(_key())).decode("utf-8")
    assert text == (
        "❗Лимит ГБ тратиться только на Обход глушилок.❗\n"
        "Не работает VPN? Жми кнопку —  🔁 Обновить подписку.\n\n"
        "🎁 Приглашайте друзей: +5 дней — за вход друга в бот\n"
        "+15 дней каждому — когда друг продлит подписку"
    )


def test_dns_v2_is_canary_gated_and_has_no_google_or_cloudflare():
    key = _key()
    with patch("subscription_api.ARCVPN_DNS_PROFILE", "legacy"), patch(
        "subscription_api.ARCVPN_DNS_CANARY_TELEGRAM_IDS", set()
    ):
        assert _client_dns_config(key)["servers"] == ["1.1.1.1", "1.0.0.1"]
    with patch("subscription_api.ARCVPN_DNS_PROFILE", "v2"):
        encoded = json.dumps(_client_dns_config(key))
    assert "77.88.8.8" in encoded
    assert "dns.quad9.net" in encoded
    assert "1.1.1.1" not in encoded and "8.8.8.8" not in encoded


def test_happ_profiles_receive_v2_dns_without_foreign_geoasset_urls():
    links = "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany"
    with patch("subscription_api.ARCVPN_DNS_PROFILE", "v2"), patch(
        "subscription_api._catalog_overrides", return_value={}
    ):
        profiles = json.loads(_build_happ_json_subscription(_key(), links))
    assert profiles
    encoded = json.dumps(profiles)
    assert "dns.quad9.net" in encoded
    assert "jsdelivr" not in encoded and "nalog.ru" not in encoded


def test_happ_subscription_hides_node_settings_in_header_and_text_metadata():
    text = _build_plain_text_subscription(
        "vless://example", None, "upload=0; download=0"
    )
    assert "#hide-settings: 1\n" in text

    response = _response_from_prepared(
        PreparedSubscription(text, "text/plain; charset=utf-8", "upload=0; download=0")
    )
    assert response.headers["hide-settings"] == "1"


def test_happ_subscription_keeps_server_catalog_order_instead_of_lowest_delay_reordering():
    text = _build_plain_text_subscription(
        "vless://example", None, "upload=0; download=0"
    )
    assert "subscription-autoconnect" not in text
    assert "subscription-autoconnect-type" not in text
    assert "subscription-ping-onopen-enabled" not in text
    assert "#subscriptions-sort-type: without\n" in text
    assert "providerid" not in text.lower()

    response = _response_from_prepared(
        PreparedSubscription(text, "text/plain; charset=utf-8", "upload=0; download=0")
    )
    assert "subscription-autoconnect" not in response.headers
    assert "subscription-autoconnect-type" not in response.headers
    assert "subscription-ping-onopen-enabled" not in response.headers
    assert response.headers["subscriptions-sort-type"] == "without"
    assert "providerid" not in response.headers
