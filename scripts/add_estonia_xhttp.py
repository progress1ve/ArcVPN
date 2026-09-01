#!/usr/bin/env python3
"""Add an Estonia XHTTP origin to the existing Remnawave LTE topology.

Preview is the default.  The operation clones the proven Netherlands XHTTP
inbound shape, changes only its tag, activates it on Estonia and authorizes it
through the existing ArcVPN LTE squad.  No user or host identifiers are
printed.
"""
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


EE_NODE = "ArcVPN Estonia 1chost"
NL_TAG = "NL_DHOST_LTE_XHTTP"
EE_TAG = "EE_1CHOST_LTE_XHTTP"
LTE_SQUAD = "ArcVPN LTE"
BACKUP = ROOT / ".secrets" / "estonia-xhttp-remnawave-backup.json"


def response_list(payload: object, key: str) -> list[dict]:
    if isinstance(payload, dict):
        value = payload.get(key, payload.get("response", []))
        if isinstance(value, list):
            return value
    if isinstance(payload, list):
        return payload
    return []


async def run(apply: bool) -> dict:
    cfg = {**remnawave_authority_config(), "panel_write_mode": "production"}
    client = RemnawaveClient(cfg)
    try:
        nodes = response_list(await client._request("GET", "/api/nodes"), "nodes")
        profiles = response_list(
            await client._request("GET", "/api/config-profiles"), "configProfiles"
        )
        squads = response_list(
            await client._request("GET", "/api/internal-squads"), "internalSquads"
        )

        ee_node = next((n for n in nodes if n.get("name") == EE_NODE), None)
        if not ee_node:
            raise RuntimeError("Estonia node is missing")
        ee_profile_id = (ee_node.get("configProfile") or {}).get("activeConfigProfileUuid")
        ee_profile = next((p for p in profiles if p.get("uuid") == ee_profile_id), None)
        if not ee_profile:
            raise RuntimeError("Estonia config profile is missing")
        lte_squad = next((s for s in squads if s.get("name") == LTE_SQUAD), None)
        if not lte_squad:
            raise RuntimeError("ArcVPN LTE squad is missing")

        nl_inbound = None
        for profile in profiles:
            for inbound in (profile.get("config") or {}).get("inbounds") or []:
                if inbound.get("tag") == NL_TAG:
                    nl_inbound = inbound
                    break
        if not nl_inbound:
            raise RuntimeError("Netherlands XHTTP baseline is missing")

        config = copy.deepcopy(ee_profile.get("config") or {})
        inbounds = config.setdefault("inbounds", [])
        existing = next((i for i in inbounds if i.get("tag") == EE_TAG), None)
        changed_profile = existing is None
        if changed_profile:
            cloned = copy.deepcopy(nl_inbound)
            cloned["tag"] = EE_TAG
            cloned["listen"] = "127.0.0.1"
            cloned["port"] = 10001
            settings = cloned.setdefault("settings", {})
            settings["clients"] = []
            inbounds.append(cloned)

        active = [i.get("uuid") for i in (ee_node.get("configProfile") or {}).get("activeInbounds", [])]
        squad_ids = [i.get("uuid") for i in lte_squad.get("inbounds") or []]
        preview = {
            "apply": apply,
            "profile_change_needed": changed_profile,
            "node_multiplier": ee_node.get("consumptionMultiplier", ee_node.get("nodeConsumptionMultiplier")),
            "estonia_connected": bool(ee_node.get("isConnected")),
            "active_inbound_count_before": len([x for x in active if x]),
            "lte_inbound_count_before": len([x for x in squad_ids if x]),
        }
        if not apply:
            return preview

        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_text(
            json.dumps({"profile": ee_profile, "node": ee_node, "squad": lte_squad}, indent=2),
            encoding="utf-8",
        )
        BACKUP.chmod(0o600)

        if changed_profile:
            await client._request(
                "PATCH", "/api/config-profiles",
                json={"uuid": ee_profile["uuid"], "config": config},
            )
            profiles = response_list(
                await client._request("GET", "/api/config-profiles"), "configProfiles"
            )
            ee_profile = next((p for p in profiles if p.get("uuid") == ee_profile_id), None)
        ee_inbound = next(
            (i for i in (ee_profile or {}).get("inbounds", []) if i.get("tag") == EE_TAG), None
        )
        if not ee_inbound or not ee_inbound.get("uuid"):
            raise RuntimeError("Estonia XHTTP inbound was not created")
        ee_id = ee_inbound["uuid"]

        if ee_id not in active:
            await client._request(
                "PATCH", "/api/nodes",
                json={
                    "uuid": ee_node["uuid"],
                    "consumptionMultiplier": 1.0,
                    "configProfile": {
                        "activeConfigProfileUuid": ee_profile_id,
                        "activeInbounds": [x for x in active if x] + [ee_id],
                    },
                },
            )
        if ee_id not in squad_ids:
            await client._request(
                "PATCH", "/api/internal-squads",
                json={"uuid": lte_squad["uuid"], "inbounds": [x for x in squad_ids if x] + [ee_id]},
            )
        return {**preview, "applied": True, "backup_created": True}
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
