"""Small read-only Remnawave telemetry helpers for Telegram reports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bot.services.panels.remnawave import RemnawaveClient
from database.requests import get_all_servers


def _credentials() -> dict[str, Any]:
    for server in get_all_servers():
        if str(server.get("panel_type") or "").lower() == "remnawave" and server.get("panel_api_token"):
            return server

    values: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[2] / ".env.remnawave-staging"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return {
        "panel_type": "remnawave",
        "panel_api_url": values.get("REMNAWAVE_PANEL_URL", ""),
        "panel_api_token": values.get("REMNAWAVE_API_TOKEN", ""),
    }


async def get_remnawave_network_stats() -> dict[str, Any]:
    """Return authoritative users/nodes data without exposing panel secrets."""
    client = RemnawaveClient(_credentials())
    try:
        nodes = await client.get_inbounds()
        users = await client._request("GET", "/api/users", params={"start": 0, "size": 1})
    finally:
        await client.close()
    return {
        "users": int((users or {}).get("total") or 0),
        "nodes": [{
            "name": node.get("name") or node.get("address") or "RemnaNode",
            "connected": bool(node.get("isConnected")),
            "disabled": bool(node.get("isDisabled")),
            "users_online": int(node.get("usersOnline") or 0),
            "traffic_gb": int(node.get("trafficUsedBytes") or 0) / 1024 ** 3,
        } for node in (nodes or [])],
    }
