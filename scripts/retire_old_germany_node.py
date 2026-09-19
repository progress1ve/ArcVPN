#!/usr/bin/env python3
"""Retire the superseded Germany DHost node without touching unrelated hosts."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import NODE_NAME as NEW_NODE_NAME, items


OLD_NODE_NAME = "ArcVPN Germany DHost"
OLD_PROFILE_NAME = "ArcVPN Germany DHost"


def node_ids(host: dict) -> set[str]:
    result: set[str] = set()
    for value in host.get("nodes") or []:
        result.add(str(value.get("uuid")) if isinstance(value, dict) else str(value))
    return result


async def retire(apply: bool, delete_profile: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")

        old_node = next((value for value in nodes if value.get("name") == OLD_NODE_NAME), None)
        new_node = next((value for value in nodes if value.get("name") == NEW_NODE_NAME), None)
        if not new_node or not new_node.get("isConnected"):
            raise RuntimeError("Replacement Germany node is missing or disconnected")

        old_node_id = str(old_node["uuid"]) if old_node else ""
        old_profile = next((value for value in profiles if value.get("name") == OLD_PROFILE_NAME), None)
        old_profile_id = str((old_profile or {}).get("uuid") or "")
        old_inbound_ids = {str(value["uuid"]) for value in (old_profile or {}).get("inbounds", [])}

        matched_hosts = []
        for host in hosts:
            inbound = host.get("inbound") or {}
            if (old_node_id and old_node_id in node_ids(host)) or (
                old_profile_id and str(inbound.get("configProfileUuid")) == old_profile_id
            ):
                matched_hosts.append(host)

        affected_squads = []
        for squad in squads:
            current = [str(value["uuid"]) for value in squad.get("inbounds", [])]
            remaining = [value for value in current if value not in old_inbound_ids]
            if remaining != current:
                affected_squads.append((squad, remaining))

        result = {
            "apply": apply,
            "old_node_exists": bool(old_node),
            "old_node_connected": bool(old_node and old_node.get("isConnected")),
            "replacement_connected": True,
            "matched_hosts": len(matched_hosts),
            "hosts_already_disabled": sum(bool(value.get("isDisabled")) for value in matched_hosts),
            "affected_squads": len(affected_squads),
            "profile_found": bool(old_profile),
        }
        if not apply:
            return result

        for host in matched_hosts:
            if not host.get("isDisabled"):
                await client._request("PATCH", "/api/hosts", json={
                    "uuid": host["uuid"], "isDisabled": True,
                })
        for squad, remaining in affected_squads:
            await client._request("PATCH", "/api/internal-squads", json={
                "uuid": squad["uuid"], "inbounds": remaining,
            })

        if old_node:
            await client._request("DELETE", f"/api/nodes/{old_node_id}")
        profile_deleted = False
        if delete_profile and old_profile:
            refreshed_nodes = items(await client._request("GET", "/api/nodes"), "nodes")
            profile_in_use = any(
                str((value.get("configProfile") or {}).get("activeConfigProfileUuid") or "") == old_profile_id
                for value in refreshed_nodes
            )
            if not profile_in_use:
                await client._request("DELETE", f"/api/config-profiles/{old_profile_id}")
                profile_deleted = True

        result.update({
            "retired": True,
            "disabled_hosts": len(matched_hosts),
            "detached_squads": len(affected_squads),
            "profile_deleted": profile_deleted,
        })
        return result
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delete-profile", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(retire(args.apply, args.delete_profile))))


if __name__ == "__main__":
    main()
