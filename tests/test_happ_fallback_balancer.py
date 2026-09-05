import json
import unittest
from unittest.mock import patch

try:
    from subscription_api import (
        ActiveKeyRecord,
        HAPP_ROUTING_PROFILE,
        TIKTOK_PROXY_SITES,
        _build_happ_json_subscription,
    )
except ModuleNotFoundError as exc:  # Minimal local test environment may omit Flask.
    ActiveKeyRecord = _build_happ_json_subscription = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, f"subscription API dependencies unavailable: {IMPORT_ERROR}")
class HappFallbackBalancerTests(unittest.TestCase):
    def test_tiktok_is_forced_through_vpn_before_direct_rules_in_every_profile(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany",
            "vless://22222222-2222-2222-2222-222222222222@cdn-nd.arccnet.space:443?security=tls&type=xhttp#Обход%20глушилок%20%28LTE%29%20%231",
        ])
        with patch("subscription_api._catalog_overrides", return_value={}):
            profiles = json.loads(_build_happ_json_subscription(key, links))

        self.assertEqual(HAPP_ROUTING_PROFILE["ProxySites"], TIKTOK_PROXY_SITES)
        for profile in profiles:
            rules = profile["routing"]["rules"]
            tiktok_index = next(i for i, rule in enumerate(rules) if rule.get("domain") == TIKTOK_PROXY_SITES)
            direct_index = next(i for i, rule in enumerate(rules) if rule.get("outboundTag") == "direct")
            self.assertLess(tiktok_index, direct_index)
            if profile["remarks"] == "🇷🇺 Ютуб без рекламы":
                self.assertEqual(rules[tiktok_index]["outboundTag"], "proxy")
            elif profile["remarks"].startswith(("Автовыбор", "🇪🇺 Лучший обход", "🇪🇺 Обход")):
                self.assertEqual(rules[tiktok_index]["balancerTag"], "balancer_main")
            else:
                self.assertEqual(rules[tiktok_index]["outboundTag"], "proxy")

    def test_customer_profile_order_keeps_five_bypass_balancers(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@nl.example:443?security=none&type=tcp#Нидерланды%20%231",
            "vless://11111111-1111-1111-1111-111111111111@nl.example:443?security=none&type=tcp#Ютуб%20без%20рекламы",
            "hysteria2://aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa@nl.example:8443?insecure=1#Нидерланды%20%232%20%E2%9A%A1",
            "vless://99999999-9999-4999-8999-999999999999@al.example:3342?security=reality&type=tcp#Албания%20%231",
            "hysteria2://88888888-8888-4888-8888-888888888888@al.example:3343?insecure=1#Албания%20%232",
            "vless://55555555-5555-5555-5555-555555555555@ee.example:443?security=none&type=tcp#Эстония%20%231",
            "hysteria2://eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee@ee.example:8443?insecure=1#Эстония%20%232",
            "vless://22222222-2222-2222-2222-222222222222@de.example:443?security=none&type=tcp#Германия%20%231",
            "hysteria2://bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb@de.example:8443?insecure=1#Германия%20%232%20%E2%9A%A1",
            "vless://33333333-3333-3333-3333-333333333333@cdn-nd.arccnet.space:443?security=tls&type=xhttp#Обход%20глушилок%20%234",
            "vless://44444444-4444-4444-4444-444444444444@cdn-de.arccnet.space:443?security=tls&type=xhttp#Обход%20глушилок%20%235",
        ])
        with patch("subscription_api._catalog_overrides", return_value={}):
            profiles = json.loads(_build_happ_json_subscription(key, links))
        self.assertEqual([item["remarks"] for item in profiles], [
            "Автовыбор | Самый быстрый", "🇷🇺 Ютуб без рекламы", "Эстония #1",
            "Нидерланды #1", "Албания #1", "Германия #1", "🇪🇺 Лучший обход",
            "🇪🇺 Обход глушилок #2", "🇪🇺 Обход глушилок #3",
            "🇪🇺 Обход глушилок #4", "🇪🇺 Обход глушилок #5",
        ])
        youtube = profiles[1]
        self.assertNotIn("balancers", youtube["routing"])
        self.assertEqual(youtube["outbounds"][0]["protocol"], "vless")

    def test_every_bypass_uses_whitenode_least_load_contract(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany",
            "vless://22222222-2222-2222-2222-222222222222@cdn-nd.arccnet.space:443?security=tls&type=xhttp#Обход%20глушилок%20%28LTE%29%20%231",
            "vless://33333333-3333-3333-3333-333333333333@cdn-de.arccnet.space:443?security=tls&type=xhttp#Обход%20глушилок%20%28LTE%29%20%232",
        ])

        with patch("subscription_api._catalog_overrides", return_value={}):
            built = _build_happ_json_subscription(key, links)
        auto = json.loads(built)[0]
        outbounds = {item["tag"]: item for item in auto["outbounds"]}
        balancers = {item["tag"]: item for item in auto["routing"]["balancers"]}

        self.assertNotIn("LOOPBACK_TO_BACK", outbounds)
        self.assertEqual(balancers["balancer_main"]["fallbackTag"], "proxy-back-1")
        self.assertEqual(balancers["balancer_main"]["selector"], ["proxy-main", "proxy-back"])
        self.assertEqual(balancers["balancer_main"]["strategy"], {
            "type": "leastLoad",
            "settings": {"baselines": ["1s"], "expected": 1, "maxRTT": "3s"},
        })
        self.assertEqual(auto["burstObservatory"], {
            "pingConfig": {
                "connectivity": "", "destination": "http://www.gstatic.com/generate_204",
                "httpMethod": "GET", "interval": "10s", "sampling": 6, "timeout": "5s",
            },
            "subjectSelector": ["proxy-main", "proxy-back"],
        })
        self.assertEqual(len([tag for tag in outbounds if tag.startswith("proxy-back-")]), 2)
        self.assertEqual(
            [outbounds[f"proxy-back-{index}"]["settings"]["vnext"][0]["address"] for index in (1, 2)],
            ["cdn-de.arccnet.space", "cdn-nd.arccnet.space"],
        )
        profiles = json.loads(built)
        self.assertEqual(len(profiles), 7)
        self.assertEqual([item["remarks"] for item in profiles[-5:]], [
            "🇪🇺 Лучший обход", "🇪🇺 Обход глушилок #2", "🇪🇺 Обход глушилок #3",
            "🇪🇺 Обход глушилок #4", "🇪🇺 Обход глушилок #5",
        ])
        self.assertEqual(profiles[0]["remarks"], "Автовыбор | Самый быстрый")
        for bypass in profiles[-5:]:
            bypass_outbounds = {item["tag"]: item for item in bypass["outbounds"]}
            self.assertNotIn("LOOPBACK_TO_BACK", bypass_outbounds)
            self.assertEqual(bypass["routing"]["balancers"][0]["tag"], "balancer_main")
            self.assertEqual(bypass["routing"]["balancers"][0]["selector"], ["proxy-main", "proxy-back"])

    def test_direct_cdn_links_become_hidden_fallback_outbounds_only(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany",
            "vless://22222222-2222-2222-2222-222222222222@cdn-nd.arccnet.space:443?security=tls&type=xhttp#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9E%D0%B1%D1%85%D0%BE%D0%B4%20%D0%B3%D0%BB%D1%83%D1%88%D0%B8%D0%BB%D0%BE%D0%BA%20%234",
            "vless://33333333-3333-3333-3333-333333333333@cdn-de.arccnet.space:443?security=tls&type=xhttp#%F0%9F%87%A9%F0%9F%87%AA%20%D0%9E%D0%B1%D1%85%D0%BE%D0%B4%20%D0%B3%D0%BB%D1%83%D1%88%D0%B8%D0%BB%D0%BE%D0%BA%20%235",
        ])

        with patch("subscription_api._catalog_overrides", return_value={}):
            profiles = json.loads(_build_happ_json_subscription(key, links))

        self.assertEqual(profiles[-5]["remarks"], "🇪🇺 Лучший обход")
        for profile in profiles[-5:]:
            outbounds = {item["tag"]: item for item in profile["outbounds"]}
            self.assertNotIn("proxy", outbounds)
            self.assertIn("proxy-back-1", outbounds)
            self.assertIn("proxy-back-2", outbounds)
            self.assertEqual(outbounds["proxy-back-1"]["settings"]["vnext"][0]["address"], "cdn-de.arccnet.space")
            self.assertEqual(outbounds["proxy-back-2"]["settings"]["vnext"][0]["address"], "cdn-nd.arccnet.space")
            self.assertNotIn("LOOPBACK_TO_BACK", outbounds)
            self.assertEqual(profile["routing"]["balancers"][0]["fallbackTag"], "proxy-back-1")
