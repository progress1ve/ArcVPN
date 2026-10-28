import json
from unittest.mock import patch

import subscription_api as api


def test_json_profiles_route_russian_services_and_preserve_proxy_exceptions():
    key = api.ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
    links = "\n".join([
        "vless://11111111-1111-1111-1111-111111111111@ee.example:443?security=none&type=tcp#Estonia",
        "vless://22222222-2222-2222-2222-222222222222@cdn-de.arccnet.space:443?security=tls&type=xhttp#LTE",
    ])
    with patch("subscription_api._catalog_overrides", return_value={}), patch("monitoring.lithuania_canary.load", return_value=None):
        profiles = json.loads(api._build_happ_json_subscription(key, links))
    assert profiles
    for profile in profiles:
        routing = profile["routing"]
        assert routing["domainStrategy"] == "IPOnDemand"
        rules = routing["rules"]
        direct = next(i for i, r in enumerate(rules) if "domain:kari.com" in r.get("domain", []))
        assert "domain:megastroy.com" in rules[direct]["domain"]
        assert rules[direct]["outboundTag"] == "direct"
        ru_ip = next(i for i, r in enumerate(rules) if "geoip:ru" in r.get("ip", []))
        for expected in (api.TIKTOK_PROXY_SITES, api.YOUTUBE_PROXY_SITES, api.TELEGRAM_PROXY_SITES):
            priority = next(i for i, r in enumerate(rules) if r.get("domain") == expected)
            assert priority < ru_ip
            assert rules[priority].get("outboundTag") != "direct"
        assert ru_ip < len(rules) - 1


def test_plain_happ_routing_profile_includes_store_domains_and_telegram():
    p = api._build_happ_routing_profile()
    assert {"domain:kari.com", "domain:megastroy.com"} <= set(p["DirectSites"])
    assert set(api.TELEGRAM_PROXY_SITES) <= set(p["ProxySites"])
