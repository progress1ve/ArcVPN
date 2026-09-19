#!/usr/bin/env python3
"""Move Estonia REALITY fallback to its local HTTPS decoy without exposing keys."""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import items


PROFILE_NAME = "ArcVPN Estonia 1chost"
NODE_NAME = "ArcVPN Estonia 1chost"
TCP_TAG = "EE_1CHOST_VLESS_TCP"
DOMAIN = "ee.arccnet.space"
TARGET = "127.0.0.1:8443"


async def configure(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")
        profile = next((value for value in profiles if value.get("name") == PROFILE_NAME), None)
        node = next((value for value in nodes if value.get("name") == NODE_NAME), None)
        if not profile or not node:
            raise RuntimeError("Estonia profile or node is missing")
        old_inbound = next((value for value in profile.get("inbounds", []) if value.get("tag") == TCP_TAG), None)
        if not old_inbound:
            raise RuntimeError("Estonia TCP inbound is missing")

        config = copy.deepcopy(profile.get("config") or {})
        inbound = next(value for value in config.get("inbounds", []) if value.get("tag") == TCP_TAG)
        reality = (inbound.get("streamSettings") or {}).get("realitySettings") or {}
        already_configured = reality.get("target") == TARGET and DOMAIN in (reality.get("serverNames") or [])
        matching_hosts = [
            host for host in hosts
            if str((host.get("inbound") or {}).get("configProfileUuid")) == str(profile["uuid"])
            and str((host.get("inbound") or {}).get("configProfileInboundUuid")) == str(old_inbound["uuid"])
        ]
        result = {
            "apply": apply,
            "already_configured": already_configured,
            "node_connected": bool(node.get("isConnected")),
            "matching_hosts": len(matching_hosts),
        }
        if not apply:
            return result
        if already_configured and all(host.get("sni") == DOMAIN for host in matching_hosts):
            result.update({"configured": True, "reused": True})
            return result

        reality["target"] = TARGET
        reality.pop("dest", None)
        reality["serverNames"] = list(dict.fromkeys([*(reality.get("serverNames") or []), DOMAIN]))
        updated = await client._request("PATCH", "/api/config-profiles", json={
            "uuid": profile["uuid"], "name": PROFILE_NAME, "config": config,
        })
        new_inbound = next(value for value in updated.get("inbounds", []) if value.get("tag") == TCP_TAG)
        new_inbound_id = new_inbound["uuid"]
        all_inbound_ids = [value["uuid"] for value in updated.get("inbounds", [])]

        await client._request("PATCH", "/api/nodes", json={
            "uuid": node["uuid"],
            "configProfile": {
                "activeConfigProfileUuid": profile["uuid"],
                "activeInbounds": all_inbound_ids,
            },
        })
        for squad in squads:
            current = [value["uuid"] for value in squad.get("inbounds", [])]
            if old_inbound["uuid"] not in current:
                continue
            replaced = [new_inbound_id if value == old_inbound["uuid"] else value for value in current]
            await client._request("PATCH", "/api/internal-squads", json={
                "uuid": squad["uuid"], "inbounds": list(dict.fromkeys(replaced)),
            })
        for host in matching_hosts:
            await client._request("PATCH", "/api/hosts", json={
                "uuid": host["uuid"],
                "sni": DOMAIN,
                "inbound": {
                    "configProfileUuid": profile["uuid"],
                    "configProfileInboundUuid": new_inbound_id,
                },
            })
        result.update({"configured": True, "host_sni_updated": len(matching_hosts)})
        return result
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(configure(args.apply))))


if __name__ == "__main__":
    main()
