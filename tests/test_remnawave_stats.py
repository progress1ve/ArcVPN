import unittest
from unittest.mock import AsyncMock, patch

from bot.services.remnawave_stats import get_remnawave_network_stats


class RemnawaveStatsTests(unittest.IsolatedAsyncioTestCase):
    async def test_normalizes_authoritative_node_telemetry(self):
        client = AsyncMock()
        client.get_inbounds.return_value = [{
            "name": "Netherlands",
            "isConnected": True,
            "isDisabled": False,
            "usersOnline": 7,
            "trafficUsedBytes": 3 * 1024 ** 3,
        }]
        client._request.return_value = {"total": 42}

        with patch("bot.services.remnawave_stats._credentials", return_value={}), \
             patch("bot.services.remnawave_stats.RemnawaveClient", return_value=client):
            result = await get_remnawave_network_stats()

        self.assertEqual(result["users"], 42)
        self.assertEqual(result["nodes"][0]["users_online"], 7)
        self.assertEqual(result["nodes"][0]["traffic_gb"], 3)
        client.close.assert_awaited_once()
