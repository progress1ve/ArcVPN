import base64

import pytest

try:
    import subscription_api as api
except Exception as exc:  # pragma: no cover - local config may be intentionally absent
    api = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


pytestmark = pytest.mark.skipif(api is None, reason=f"subscription_api unavailable: {IMPORT_ERROR}")


def _key():
    return api.ActiveKeyRecord(
        id=1,
        server_id=1,
        panel_email="arc_user",
        expires_at="2099-01-01 00:00:00",
        traffic_limit=0,
        traffic_used=0,
        tariff_name="Test",
        telegram_id=1,
        sub_id="stable-public-id",
        client_uuid="11111111-1111-4111-8111-111111111111",
    )


def test_decode_native_plain_and_base64():
    links = [
        "vless://uuid@example.com:443?security=reality#Germany",
        "hysteria2://uuid@example.com:8443?sni=example.com#Germany-HY2",
    ]
    plain = "\n".join(links)
    encoded = base64.b64encode(plain.encode()).decode()

    assert api._decode_native_subscription_links(plain) == links
    assert api._decode_native_subscription_links(encoded) == links


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://sub.example.com/opaque", True),
        ("http://sub.example.com/opaque", False),
        ("https://127.0.0.1/opaque", False),
        ("https://localhost/opaque", False),
        ("https://user:pass@sub.example.com/opaque", False),
    ],
)
def test_native_subscription_url_validation(url, expected):
    assert api._public_https_subscription_url(url) is expected


def test_native_failure_keeps_legacy_fallback_available(monkeypatch):
    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", lambda coroutine: [])
    assert api._prepare_native_remnawave_subscription(_key(), "plain") is None


def test_native_links_keep_arcvpn_happ_wrapper(monkeypatch):
    native_link = "vless://11111111-1111-4111-8111-111111111111@example.com:443?security=reality#DE"
    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", lambda coroutine: [native_link])

    prepared = api._prepare_native_remnawave_subscription(_key(), "json")

    assert prepared is not None
    assert prepared.content_type.startswith("application/json")
    assert "AutoSelect" in prepared.body
    assert "example.com" in prepared.body
