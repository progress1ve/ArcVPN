import unittest

from monitoring.remnawave_fleet_monitor import tcp_ports


class FleetMonitorPortTests(unittest.TestCase):
    def test_managed_bridge_is_not_a_public_health_port(self):
        node={'address':'87.251.19.197','configProfile':{'activeInbounds':[{'port':443,'network':'tcp'},{'port':2443,'network':'tcp'}]}}
        self.assertEqual(tcp_ports(node),[443])

    def test_public_probe_skips_internal_xhttp_and_udp(self):
        node = {"configProfile": {"activeInbounds": [
            {"tag": "VLESS_TCP_REALITY", "network": "raw", "port": 443},
            {"tag": "LTE_XHTTP", "network": "xhttp", "port": 10001},
            {"tag": "HYSTERIA", "network": "hysteria", "port": 443},
        ]}}

        self.assertEqual(tcp_ports(node), [443])


if __name__ == "__main__":
    unittest.main()
