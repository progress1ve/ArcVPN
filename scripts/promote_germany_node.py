#!/usr/bin/env python3
"""Publish the connected replacement Germany TCP REALITY node."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import NODE_NAME, PROFILE_NAME, STATE_PATH, TCP_TAG, items


TARGET_SQUADS = {"ArcVPN Staging", "ArcVPN LTE"}


async def main() -> None:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")
        profile = next((item for item in profiles if item.get("name") == PROFILE_NAME), None)
        node = next((item for item in nodes if item.get("name") == NODE_NAME), None)
        target_squads = [item for item in squads if item.get("name") in TARGET_SQUADS]
        if not profile or not node or {item.get("name") for item in target_squads} != TARGET_SQUADS:
            raise RuntimeError("Germany profile, node, or target squads are missing")
        if not node.get("isConnected"):
            raise RuntimeError("Replacement Germany RemnaNode is not connected")
        inbound_id = next(item["uuid"] for item in profile["inbounds"] if item["tag"] == TCP_TAG)
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        host = next((item for item in hosts if item.get("uuid") == state["tcp_host_uuid"]), None)
        if not host:
            raise RuntimeError("Replacement Germany Host is missing")
        for squad in target_squads:
            current = [item["uuid"] for item in squad.get("inbounds", [])]
            if inbound_id not in current:
                await client._request("PATCH", "/api/internal-squads", json={
                    "uuid": squad["uuid"], "inbounds": [*current, inbound_id],
                })
        if host.get("isDisabled"):
            await client._request("PATCH", "/api/hosts", json={
                "uuid": host["uuid"], "isDisabled": False,
            })
        print(json.dumps({"promoted": True, "connected": True, "tcp_only": True}))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
