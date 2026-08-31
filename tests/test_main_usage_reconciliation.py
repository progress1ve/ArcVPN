import asyncio
from unittest.mock import AsyncMock, patch

from bot.services.scheduler import reconcile_main_usage


def test_main_usage_uses_authoritative_remnawave_counter_and_skips_failures():
    keys = [
        {"id": 1, "panel_email": "arc_one", "client_uuid": "uuid-1", "traffic_used": 0},
        {"id": 2, "panel_email": "arc_two", "client_uuid": "uuid-2", "traffic_used": 99},
    ]
    client = AsyncMock()
    client.get_user.side_effect = [
        {"vlessUuid": "uuid-1", "userTraffic": {"usedTrafficBytes": 123456}},
        RuntimeError("temporary outage"),
    ]
    with patch("bot.services.scheduler.remnawave_authority_enabled", return_value=True), patch(
        "bot.services.remnawave_stats.remnawave_authority_config", return_value={"panel_type": "remnawave"}
    ), patch(
        "bot.services.scheduler.get_client_from_server_data", return_value=client
    ), patch("database.requests.bulk_update_traffic") as update:
        result = asyncio.run(reconcile_main_usage(keys))
    assert result["updated"] == 1 and result["failed"] == 1
    assert result["key_ids"] == {1}
    update.assert_called_once_with([(123456, 1)])
    assert keys[1]["traffic_used"] == 99
