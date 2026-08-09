import unittest

from bot.services.panels.base import VPNAPIError
from bot.services.panels.factory import create_panel_client, panel_cache_key
from bot.services.panels.remnawave import RemnawaveClient
from bot.services.panels.xui import XUIClient


class PanelFactoryTests(unittest.TestCase):
    def test_existing_servers_stay_on_xui(self):
        server = {"id": 1, "name": "DE", "host": "127.0.0.1", "port": 2053}
        self.assertIsInstance(create_panel_client(server), XUIClient)

    def test_remnawave_is_explicit(self):
        server = {
            "id": 2, "name": "staging", "host": "example.test", "port": 443,
            "panel_type": "remnawave", "panel_api_url": "https://panel.example.test",
        }
        self.assertIsInstance(create_panel_client(server), RemnawaveClient)

    def test_cache_changes_with_panel(self):
        base = {"id": 4, "host": "127.0.0.1", "port": 443}
        self.assertNotEqual(panel_cache_key(base), panel_cache_key({**base, "panel_type": "remnawave"}))


class RemnawaveSafetyTests(unittest.TestCase):
    def make_client(self, mode="disabled"):
        return RemnawaveClient({
            "id": 5, "name": "stage", "host": "example.test", "port": 443,
            "panel_api_url": "https://panel.example.test", "panel_api_token": "secret",
            "panel_write_mode": mode,
        })

    def test_writes_disabled_by_default(self):
        with self.assertRaises(VPNAPIError):
            self.make_client()._assert_write_allowed("arc-staging-one")

    def test_shadow_only_accepts_synthetic_users(self):
        client = self.make_client("shadow")
        client._assert_write_allowed("arc-staging-one")
        with self.assertRaises(VPNAPIError):
            client._assert_write_allowed("user_customer")

    def test_username_is_api_safe(self):
        self.assertEqual(RemnawaveClient._username("user@example.com"), "user_example_com")


if __name__ == "__main__":
    unittest.main()
