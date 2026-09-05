#!/usr/bin/env python3
"""Publish a connected Albania node into ArcVPN main delivery."""
from __future__ import annotations

import asyncio
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

from provision_albania_node import (
    HY2_TAG, NODE_ADDRESS, NODE_NAME, PROFILE_NAME, TCP_TAG, items,
)

MAIN_SQUAD = "ArcVPN Staging"


async def main(*, allow_disconnected: bool = False):
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")
        profile = next((x for x in profiles if x.get("name") == PROFILE_NAME), None)
        node = next((x for x in nodes if x.get("name") == NODE_NAME), None)
        squad = next((x for x in squads if x.get("name") == MAIN_SQUAD), None)
        if not profile or not node or not squad:
            raise RuntimeError("Albania profile, node, or main squad is missing")
        if not node.get("isConnected") and not allow_disconnected:
            raise RuntimeError("Albania RemnaNode is not connected")
        inbound_ids = {x["tag"]: x["uuid"] for x in profile.get("inbounds", [])}
        created = []
        host_specs = [
            (TCP_TAG, "Албания #1", 3342, "DEFAULT", None),
            (HY2_TAG, "Албания #2", 3343, "TLS", "h3"),
        ]
        for tag, remark, port, layer, alpn in host_specs:
            existing = next((x for x in hosts if x.get("remark") == remark), None)
            if existing:
                if existing.get("isDisabled"):
                    await client._request("PATCH", "/api/hosts", json={"uuid": existing["uuid"], "isDisabled": False})
                continue
            payload = {
                "remark": remark, "address": NODE_ADDRESS, "port": port, "path": "", "host": "",
                "sni": NODE_ADDRESS, "alpn": alpn, "fingerprint": "firefox",
                "allowInsecure": False, "isDisabled": False, "isHidden": False,
                "securityLayer": layer, "nodes": [node["uuid"]],
                "inbound": {"configProfileUuid": profile["uuid"], "configProfileInboundUuid": inbound_ids[tag]},
            }
            created.append((await client._request("POST", "/api/hosts", json=payload))["uuid"])
        current = [x["uuid"] for x in squad.get("inbounds", [])]
        wanted = [inbound_ids[TCP_TAG], inbound_ids[HY2_TAG]]
        if any(uuid not in current for uuid in wanted):
            await client._request("PATCH", "/api/internal-squads", json={
                "uuid": squad["uuid"], "inbounds": list(dict.fromkeys([*current, *wanted])),
            })
        print(json.dumps({
            "promoted": True,
            "hosts_created": len(created),
            "connected": bool(node.get("isConnected")),
        }))
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-disconnected", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(allow_disconnected=args.allow_disconnected))
