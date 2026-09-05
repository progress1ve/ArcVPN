import base64
import json
import urllib.parse
from unittest.mock import patch

import pytest

try:
    import subscription_api as api
except Exception as exc:  # pragma: no cover - local config may be intentionally absent
    api = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


pytestmark = pytest.mark.skipif(api is None, reason=f"subscription_api unavailable: {IMPORT_ERROR}")


def test_estonia_profiles_sort_before_netherlands_germany_lte_and_accept_flags():
    tcp = api._subscription_inbound_order("🇳🇱 Нидерланды #1")
    hy2 = api._subscription_inbound_order("Нидерланды #2 ⚡")
    estonia_tcp = api._subscription_inbound_order("🇪🇪 Эстония #1")
    estonia_hy2 = api._subscription_inbound_order("Эстония #2")
    germany = api._subscription_inbound_order("Германия #1")
    lte = api._subscription_inbound_order("Обход глушилок (LTE, трафик ×10) #1")

    assert estonia_tcp < estonia_hy2 < tcp < hy2 < germany < lte
    assert api.NODE_INVENTORY["193.233.82.42"]["location"] == "Нидерланды"
    assert api.NODE_INVENTORY["95.85.249.187"]["provider"] == "1chost"


def test_germany_reality_fallback_uses_public_domain():
    germany = next(
        node for node in api.REMNAWAVE_PUBLIC_NODES
        if node.get("country") == "DE" and node.get("tcp_port") == 443
    )

    assert germany["host"] == "de.arccnet.space"


def test_customer_catalog_order_places_albania_after_netherlands():
    links = [
        "vless://id@host#Обход%20глушилок%20(LTE)",
        "vless://id@host#Германия%20%231",
        "vless://id@host#Нидерланды%20%232",
        "vless://id@host#Нидерланды%20%231",
        "vless://id@host#Албания%20%231",
        "hysteria2://id@host#Албания%20%232",
        "vless://id@host#Эстония%20%232",
        "vless://id@host#Эстония%20%231",
        "vless://id@host#Германия%20%232",
    ]

    names = [urllib.parse.unquote(link.rsplit("#", 1)[-1]) for link in sorted(links, key=api._subscription_link_order)]

    assert names == [
        "Эстония #1", "Эстония #2",
        "Нидерланды #1", "Нидерланды #2",
        "Албания #1", "Албания #2",
        "Германия #1", "Германия #2",
        "Обход глушилок (LTE)",
    ]


def test_customer_catalog_removes_all_hysteria_links():
    links = [
        "vless://id@host#Эстония%20%231",
        "hysteria2://id@host#Эстония%20%232",
        "hy2://id@host#Нидерланды%20%232",
    ]

    assert api._apply_subscription_catalog(links) == [links[0]]


def test_country_labels_and_manual_youtube_alias_are_normalized():
    links = [
        "vless://id@nd.arccnet.space:443?security=reality#Нидерланды%20%231",
        "hysteria2://id@nd.arccnet.space:443#Нидерланды%20%232",
        "vless://id@ee.arccnet.space:443?security=reality#Эстония",
        "hysteria2://id@ee.arccnet.space:443#Эстония%20%232",
        "vless://id@de.arccnet.space:443?security=reality#Германия",
        "hysteria2://id@de.arccnet.space:443#Германия%20⚡",
    ]
    normalized = [api._normalize_customer_profile_label(link) for link in links]
    result = sorted(api._with_youtube_without_ads_alias(normalized), key=api._subscription_link_order)
    names = [urllib.parse.unquote(link.rsplit("#", 1)[-1]) for link in result]

    assert names == [
        "🇷🇺 Ютуб без рекламы",
        "🇪🇪 Эстония #1",
        "🇪🇪 Эстония #2",
        "🇳🇱 Нидерланды #1",
        "🇳🇱 Нидерланды #2",
        "🇩🇪 Германия #1",
        "🇩🇪 Германия #2",
    ]
    assert result[0].split("#", 1)[0] == result[3].split("#", 1)[0]


def test_catalog_never_publishes_retired_finland(monkeypatch):
    monkeypatch.setattr(api, "_catalog_overrides", lambda: {})
    links = [
        "vless://id@fin.arccnet.space:443#Финляндия%20%231",
        "vless://id@195.226.92.37:443#Legacy",
        "vless://id@cdn-fi.arccnet.space:443#LTE",
        "vless://id@de.arccnet.space:443#Германия%20%231",
    ]

    result = api._apply_subscription_catalog(links)

    assert len(result) == 1
    assert "de.arccnet.space" in result[0]


def test_happ_json_never_keeps_retired_finland_as_hidden_outbound(monkeypatch):
    monkeypatch.setattr(api, "_catalog_overrides", lambda: {})
    links = "\n".join([
        "vless://00000000-0000-4000-8000-000000000001@fin.arccnet.space:443?security=reality#Финляндия%20%231",
        "vless://00000000-0000-4000-8000-000000000002@de.arccnet.space:443?security=reality#Германия%20%231",
    ])

    prepared = api._prepare_subscription(_key(), links, "json")

    assert "fin.arccnet.space" not in prepared.body.lower()
    assert "финлянд" not in prepared.body.lower()
    assert "de.arccnet.space" in prepared.body.lower()


def test_retired_canada_and_france_are_not_in_published_catalog():
    links = [
        "vless://id@example.com:443?security=reality#%F0%9F%87%A8%F0%9F%87%A6%20%D0%9A%D0%B0%D0%BD%D0%B0%D0%B4%D0%B0%20%231",
        "vless://id@example.com:443?security=reality#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9D%D0%B8%D0%B4%D0%B5%D1%80%D0%BB%D0%B0%D0%BD%D0%B4%D1%8B%20%231",
    ]
    with patch("subscription_api._catalog_overrides", return_value={}):
        published = api._apply_subscription_catalog(links)
    assert len(published) == 1
    assert "Нидерланды" in urllib.parse.unquote(published[0])


def test_all_lte_catalog_rows_use_the_eu_flag():
    assert api._profile_country_flag("Обход глушилок (LTE) #1") == "🇪🇺"
    assert api._profile_country_flag("Обход глушилок #4") == "🇪🇺"
    assert api._profile_country_flag("Обход глушилок #5") == "🇪🇺"


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


def test_native_credentials_must_match_active_user():
    expected = "11111111-1111-4111-8111-111111111111"
    matching = [
        f"vless://{expected}@example.com:443#DE",
        f"hysteria2://{expected}@example.com:8443#HY2",
    ]
    foreign = ["vless://22222222-2222-4222-8222-222222222222@example.com:443#DE"]
    notice = [f"vless://{expected}@0.0.0.0:1#No-hosts-found"]

    assert api._native_links_match_key(matching, expected)
    assert not api._native_links_match_key(foreign, expected)
    assert not api._native_links_match_key(["hysteria2://password@example.com:443#HY2"], expected)
    assert not api._native_links_match_key(notice, expected)


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
    def fake_run(coroutine):
        coroutine.close()
        return []

    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", fake_run)
    assert api._prepare_native_remnawave_subscription(_key(), "plain") is None


def test_source_resolver_does_not_call_legacy_when_native_succeeds(monkeypatch):
    prepared = api.PreparedSubscription("native", "text/plain", "upload=0; download=0")
    metrics = api.SubscriptionSourceMetrics()
    monkeypatch.setattr(api, "SUBSCRIPTION_SOURCE_METRICS", metrics)
    monkeypatch.setattr(api, "_prepare_native_remnawave_subscription", lambda *_args: prepared)
    monkeypatch.setattr(
        api,
        "_prepare_legacy_subscription_fallback",
        lambda *_args: pytest.fail("legacy generator must not run after native success"),
    )

    resolution = api._resolve_subscription_source(_key(), "plain")

    assert resolution is not None
    assert resolution.prepared is prepared
    assert resolution.source == "remnawave"
    assert resolution.fallback_reason is None
    assert metrics.snapshot()["native_success"] == 1
    assert metrics.snapshot()["legacy_fallback"] == 0


def test_source_resolver_isolates_and_counts_legacy_fallback(monkeypatch):
    prepared = api.PreparedSubscription("legacy", "text/plain", "upload=0; download=0")
    metrics = api.SubscriptionSourceMetrics()
    monkeypatch.setattr(api, "SUBSCRIPTION_SOURCE_METRICS", metrics)
    monkeypatch.setattr(api, "_native_subscription_enabled", lambda: True)
    monkeypatch.setattr(api, "_prepare_native_remnawave_subscription", lambda *_args: None)
    monkeypatch.setattr(api, "_prepare_legacy_subscription_fallback", lambda *_args: prepared)

    resolution = api._resolve_subscription_source(_key(), "plain")

    assert resolution is not None
    assert resolution.prepared is prepared
    assert resolution.source == "legacy"
    assert resolution.fallback_reason == "native_unavailable"
    assert metrics.snapshot()["fallback_reasons"] == {"native_unavailable": 1}


def test_subscription_source_health_contains_only_aggregate_state(monkeypatch):
    metrics = api.SubscriptionSourceMetrics()
    metrics.record("remnawave")
    metrics.record("legacy", "native_unavailable")
    monkeypatch.setattr(api, "SUBSCRIPTION_SOURCE_METRICS", metrics)
    monkeypatch.setattr(api, "_native_subscription_enabled", lambda: True)
    monkeypatch.setattr(api, "_admin_authorized", lambda _permission: True)

    response = api.app.test_client().get("/api/admin/subscription-sources")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["authority"] == "remnawave"
    assert payload["gateway"] == "arcvpn"
    assert payload["native_success"] == 1
    assert payload["legacy_fallback"] == 1
    assert "url" not in response.get_data(as_text=True).lower()
    assert "uuid" not in response.get_data(as_text=True).lower()


def test_native_links_keep_arcvpn_happ_wrapper(monkeypatch):
    native_link = "vless://11111111-1111-4111-8111-111111111111@example.com:443?security=reality#DE"
    def fake_run(coroutine):
        coroutine.close()
        return [native_link]

    monkeypatch.setattr(api.ASYNC_EXECUTOR, "run", fake_run)

    prepared = api._prepare_native_remnawave_subscription(_key(), "json")

    assert prepared is not None
    assert prepared.content_type.startswith("application/json")
    assert "burstObservatory" in prepared.body
    assert "example.com" in prepared.body


def test_native_dhost_lte_link_gets_happ_fingerprint_and_padding():
    link = (
        "vless://11111111-1111-4111-8111-111111111111@cdn-de.arccnet.space:443"
        "?encryption=none&type=xhttp&path=%2Fapi-test&host=cdn-de.arccnet.space"
        "&mode=packet-up&security=tls&sni=cdn-de.arccnet.space&fp=chrome#LTE"
    )

    normalized = api._normalize_native_share_link(link)
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(normalized).query)
    extra = json.loads(params["extra"][0])

    assert params["fp"] == ["firefox"]
    assert params["alpn"] == ["h2,http/1.1"]
    assert params["x_padding_bytes"] == ["100-1000"]
    assert extra["uplinkHTTPMethod"] == "OPTIONS"
    assert extra["xPaddingObfsMode"] is True


@pytest.mark.parametrize("host", ["cdn-de.arccnet.space", "cdn-nd.arccnet.space"])
def test_dhost_lte_links_use_options_transport(host):
    link = (
        f"vless://11111111-1111-4111-8111-111111111111@{host}:443"
        f"?encryption=none&type=xhttp&path=%2Fapi-test&host={host}"
        f"&mode=packet-up&security=tls&sni={host}&fp=chrome#LTE"
    )

    normalized = api._normalize_native_share_link(link)
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(normalized).query)
    extra = json.loads(params["extra"][0])

    assert params["fp"] == ["firefox"]
    assert params["mode"] == ["packet-up"]
    assert params["path"] == ["/api-test"]
    assert extra["uplinkHTTPMethod"] == "OPTIONS"
    assert extra["xPaddingKey"] == "dc"


def test_native_reality_link_replaces_chrome_fingerprint():
    link = (
        "vless://11111111-1111-4111-8111-111111111111@node.example.com:443"
        "?type=tcp&security=reality&fp=chrome&pbk=public&sid=0123456789abcdef#DE"
    )

    normalized = api._normalize_native_share_link(link)
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(normalized).query)

    assert params["fp"] == ["firefox"]


def test_exhausted_bypass_keeps_two_visible_placeholders(monkeypatch):
    links = "vless://00000000-0000-4000-8000-000000000002@example.com:443?security=reality#Estonia"
    monkeypatch.setattr(api, "get_user_entitlements", lambda _telegram_id: {
        "lte_base_quota_gb": 45, "lte_quota_gb": 45, "lte_remaining_bytes": 0,
    })
    prepared = api._prepare_subscription(_key(), links, "json")
    profiles = json.loads(prepared.body)
    notices = [profile["remarks"] for profile in profiles if (profile.get("meta") or {}).get("arcvpnAccessState") == "lte_exhausted"]
    assert notices == [
        "у вас закончился трафик на обход глушилок",
        "докупите трафик в боте или на сайте",
    ]
