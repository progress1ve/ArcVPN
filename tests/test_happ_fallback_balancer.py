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
        self.assertEqual(len([tag for tag in outbounds if tag.startswith("proxy-back-")]), 2)
        self.assertEqual(auto["routing"]["rules"][0]["inboundTag"], ["FROM_LOOPBACK_BACK"])
