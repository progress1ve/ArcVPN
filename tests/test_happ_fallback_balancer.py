import json
import unittest

try:
    from subscription_api import ActiveKeyRecord, _build_happ_json_subscription
except ModuleNotFoundError as exc:  # Minimal local test environment may omit Flask.
    ActiveKeyRecord = _build_happ_json_subscription = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, f"subscription API dependencies unavailable: {IMPORT_ERROR}")
class HappFallbackBalancerTests(unittest.TestCase):
    def test_main_falls_through_loopback_to_all_lte_outbounds(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany",
            "vless://22222222-2222-2222-2222-222222222222@lte1.example:443?security=none&type=tcp#Обход%20глушилок%20%28LTE%29%20%231",
            "vless://33333333-3333-3333-3333-333333333333@lte2.example:443?security=none&type=tcp#Обход%20глушилок%20%28LTE%29%20%232",
        ])

        auto = json.loads(_build_happ_json_subscription(key, links))[0]
        outbounds = {item["tag"]: item for item in auto["outbounds"]}
        balancers = {item["tag"]: item for item in auto["routing"]["balancers"]}

        self.assertIn("LOOPBACK_TO_BACK", outbounds)
        self.assertEqual(outbounds["LOOPBACK_TO_BACK"]["settings"]["inboundTag"], "FROM_LOOPBACK_BACK")
        self.assertEqual(balancers["balancer_main"]["fallbackTag"], "LOOPBACK_TO_BACK")
        self.assertEqual(balancers["balancer_main"]["selector"], ["proxy-main"])
        self.assertEqual(balancers["balancer_back"]["selector"], ["proxy-back"])
        self.assertEqual(balancers["balancer_back"]["fallbackTag"], "direct")
        self.assertEqual(balancers["balancer_back"]["strategy"]["type"], "roundRobin")
        self.assertEqual(auto["burstObservatory"]["subjectSelector"], ["proxy-main"])
        self.assertEqual(len([tag for tag in outbounds if tag.startswith("proxy-back-")]), 2)
        self.assertEqual(auto["routing"]["rules"][0]["inboundTag"], ["FROM_LOOPBACK_BACK"])
        profiles = json.loads(_build_happ_json_subscription(key, links))
        self.assertEqual(len(profiles), 7)
        self.assertEqual(
            [item["remarks"] for item in profiles[-3:]],
            [
                "🇷🇺 Обход глушилок #1",
                "🇷🇺 Обход глушилок #2",
                "🇷🇺 Обход глушилок #3",
            ],
        )
        for bypass in profiles[-3:]:
            bypass_outbounds = {item["tag"]: item for item in bypass["outbounds"]}
            bypass_balancers = {item["tag"]: item for item in bypass["routing"]["balancers"]}
            self.assertEqual(bypass["burstObservatory"]["subjectSelector"], ["proxy-main"])
            self.assertEqual(bypass_balancers["balancer_main"]["fallbackTag"], "LOOPBACK_TO_BACK")
            self.assertIn("proxy-back-1", bypass_outbounds)
            self.assertIn("proxy-back-2", bypass_outbounds)

    def test_direct_cdn_profiles_are_last_and_keep_country_flags(self):
        key = ActiveKeyRecord(1, 1, "test", "2099-01-01", 0, 0, "test", 1)
        links = "\n".join([
            "vless://11111111-1111-1111-1111-111111111111@main.example:443?security=none&type=tcp#Germany",
            "vless://22222222-2222-2222-2222-222222222222@cdn-nd.example:443?security=tls&type=xhttp#%F0%9F%87%B3%F0%9F%87%B1%20%D0%9E%D0%B1%D1%85%D0%BE%D0%B4%20%D0%B3%D0%BB%D1%83%D1%88%D0%B8%D0%BB%D0%BE%D0%BA%20%234",
            "vless://33333333-3333-3333-3333-333333333333@cdn-de.example:443?security=tls&type=xhttp#%F0%9F%87%A9%F0%9F%87%AA%20%D0%9E%D0%B1%D1%85%D0%BE%D0%B4%20%D0%B3%D0%BB%D1%83%D1%88%D0%B8%D0%BB%D0%BE%D0%BA%20%235",
        ])

        profiles = json.loads(_build_happ_json_subscription(key, links))

        self.assertEqual(
            [item["remarks"] for item in profiles[-2:]],
            ["🇳🇱 Обход глушилок #4", "🇩🇪 Обход глушилок #5"],
        )
