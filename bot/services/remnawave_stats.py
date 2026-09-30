"""Small read-only Remnawave telemetry helpers for Telegram reports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from bot.services.panels.remnawave import RemnawaveClient
from database.requests import get_all_servers


def remnawave_authority_config() -> dict[str, Any]:
    """Return the single control-plane config, with secrets kept out of logs/DB."""
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
        # The panel-client cache requires a stable numeric server identity.
        # The environment-backed authority is not a database row, so reserve a
        # negative ID instead of letting scheduler reconciliation crash on `id`.
        "id": -1,
        "panel_type": "remnawave",
        "panel_api_url": values.get("REMNAWAVE_PANEL_URL", ""),
        "panel_api_token": values.get("REMNAWAVE_API_TOKEN", ""),
        "panel_node_uuid": values.get("REMNAWAVE_NODE_UUID", ""),
        "panel_squad_uuid": values.get("REMNAWAVE_SQUAD_UUID", ""),
        "panel_write_mode": values.get("REMNAWAVE_WRITE_MODE", "disabled"),
    }


def _credentials() -> dict[str, Any]:
    return remnawave_authority_config()


def remnawave_authority_enabled() -> bool:
    """Whether production Remnawave credentials are present for this checkout."""
    credentials = _credentials()
    return bool(credentials.get("panel_api_url") and credentials.get("panel_api_token"))


async def get_remnawave_daily_product_traffic(day: str) -> dict[str, dict[str, int]]:
    """Sum a full UTC day of traffic for ordinary and LTE panel identities.

    Internal squads identify product identities, not disjoint physical nodes.
    A failed or incomplete pagination must never be reported as zero usage.
    """
    client = RemnawaveClient(_credentials())
    squad_names = {"main": "ArcVPN Staging", "lte": "ArcVPN LTE"}
    try:
        payload = await client._request("GET", "/api/internal-squads")
        squads = payload.get("internalSquads") if isinstance(payload, dict) else payload
        if not isinstance(squads, list):
            raise ValueError("Invalid internal-squads response")
        results: dict[str, dict[str, int]] = {}
        for product, name in squad_names.items():
            matches = [item for item in squads if isinstance(item, dict) and item.get("name") == name]
            if len(matches) != 1 or not matches[0].get("uuid"):
                raise ValueError(f"Missing or ambiguous {product} squad")
            usage: dict[int, int] = {}
            cursor: str | None = None
            for _ in range(100):
                params: dict[str, Any] = {"start": day, "end": day, "limit": 1000}
                if cursor:
                    params["cursor"] = cursor
                page = await client._request(
                    "GET",
                    f"/api/bandwidth-stats/internal-squads/{matches[0]['uuid']}/usage",
                    params=params,
                )
                if not isinstance(page, dict) or not isinstance(page.get("users"), list):
                    raise ValueError("Invalid squad usage response")
                for item in page["users"]:
                    if not isinstance(item, dict):
                        raise ValueError("Invalid squad usage item")
                    user_id = int(item["id"])
                    used = int(item["totalBytes"])
                    if user_id in usage or used < 0:
                        raise ValueError("Duplicate identity or negative traffic")
                    usage[user_id] = used
                if not page.get("hasMore"):
                    break
                next_cursor = page.get("nextCursor")
                if not next_cursor or str(next_cursor) == cursor:
                    raise ValueError("Incomplete squad usage pagination")
                cursor = str(next_cursor)
            else:
                raise ValueError("Squad usage page limit exceeded")
            results[product] = {
                "bytes": sum(usage.values()),
                "active_users": sum(value > 0 for value in usage.values()),
            }
        return results
    finally:
        await client.close()


async def get_remnawave_period_user_traffic(start: str, end: str) -> dict[str, Any]:
    """Complete inclusive UTC range usage and panel identity lookup.

    Never return a partial page as a plausible period total.
    """
    client = RemnawaveClient(_credentials())
    try:
        squads_payload = await client._request("GET", "/api/internal-squads")
        squads = squads_payload.get("internalSquads") if isinstance(squads_payload, dict) else squads_payload
        if not isinstance(squads, list):
            raise ValueError("Invalid internal-squads response")
        group_usage: dict[str, dict[int, int]] = {}
        for group, name in (("main", "ArcVPN Staging"), ("lte", "ArcVPN LTE")):
            matches = [s for s in squads if isinstance(s, dict) and s.get("name") == name and s.get("uuid")]
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous traffic squad")
            usage: dict[int, int] = {}
            cursor: str | None = None
            for _ in range(100):
                params: dict[str, Any] = {"start": start, "end": end, "limit": 1000}
                if cursor:
                    params["cursor"] = cursor
                page = await client._request(
                    "GET", f"/api/bandwidth-stats/internal-squads/{matches[0]['uuid']}/usage", params=params
                )
                if not isinstance(page, dict) or not isinstance(page.get("users"), list):
                    raise ValueError("Invalid traffic usage page")
                for item in page["users"]:
                    if not isinstance(item, dict):
                        raise ValueError("Invalid traffic usage item")
                    panel_id, amount = int(item["id"]), int(item["totalBytes"])
                    if panel_id in usage or amount < 0:
                        raise ValueError("Duplicate identity or negative traffic")
                    usage[panel_id] = amount
                if not page.get("hasMore"):
                    break
                next_cursor = page.get("nextCursor")
                if not next_cursor or str(next_cursor) == cursor:
                    raise ValueError("Incomplete traffic pagination")
                cursor = str(next_cursor)
            else:
                raise ValueError("Traffic page limit exceeded")
            group_usage[group] = usage

        panel_users: dict[int, dict[str, Any]] = {}
        offset = 0
        for _ in range(100):
            page = await client._request("GET", "/api/users", params={"start": offset, "size": 500})
            if not isinstance(page, dict) or not isinstance(page.get("users"), list):
                raise ValueError("Invalid panel users page")
            for item in page["users"]:
                if not isinstance(item, dict):
                    raise ValueError("Invalid panel user")
                panel_id = int(item["id"])
                if panel_id in panel_users:
                    raise ValueError("Duplicate panel user")
                panel_users[panel_id] = {
                    "vless_uuid": str(item.get("vlessUuid") or "").lower(),
                    "telegram_id": str(item.get("telegramId") or ""),
                }
            offset += len(page["users"])
            total = int(page["total"])
            if offset >= total:
                break
            if not page["users"]:
                raise ValueError("Incomplete panel users pagination")
        else:
            raise ValueError("Panel users page limit exceeded")
        return {"usage": group_usage, "panel_users": panel_users}
    finally:
        await client.close()


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
