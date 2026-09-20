#!/usr/bin/env python3
"""Add an internal Germany XHTTP origin to the ArcVPN LTE topology."""
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

NODE_NAME = "ArcVPN Germany 1chost"
BASELINE_TAG = "NL_DHOST_LTE_XHTTP"
TARGET_TAG = "DE_1CHOST_LTE_XHTTP"
LTE_SQUAD = "ArcVPN LTE"
BACKUP = ROOT / ".secrets" / "germany-xhttp-remnawave-backup.json"


def items(payload: object, key: str) -> list[dict]:
    if isinstance(payload, dict):
        value = payload.get(key, payload.get("response", []))
        return value if isinstance(value, list) else []
    return payload if isinstance(payload, list) else []


async def run(apply: bool) -> dict:
    client = RemnawaveClient({**remnawave_authority_config(), "panel_write_mode": "production"})
    try:
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        node = next((x for x in nodes if x.get("name") == NODE_NAME), None)
        squad = next((x for x in squads if x.get("name") == LTE_SQUAD), None)
        if not node or not squad:
            raise RuntimeError("Germany node or LTE squad is missing")
        profile_id = (node.get("configProfile") or {}).get("activeConfigProfileUuid")
        profile = next((x for x in profiles if x.get("uuid") == profile_id), None)
        if not profile:
            raise RuntimeError("Germany config profile is missing")
        baseline = next((i for p in profiles for i in ((p.get("config") or {}).get("inbounds") or []) if i.get("tag") == BASELINE_TAG), None)
        if not baseline:
            raise RuntimeError("XHTTP baseline is missing")
        config = copy.deepcopy(profile.get("config") or {})
        inbound_list = config.setdefault("inbounds", [])
        target = next((i for i in inbound_list if i.get("tag") == TARGET_TAG), None)
        changed = target is None
        if changed:
            target = copy.deepcopy(baseline)
            target.update({"tag": TARGET_TAG, "listen": "127.0.0.1", "port": 10001})
            target.setdefault("settings", {})["clients"] = []
            inbound_list.append(target)
        active = [i.get("uuid") for i in (node.get("configProfile") or {}).get("activeInbounds", []) if i.get("uuid")]
        authorized = [i.get("uuid") for i in squad.get("inbounds") or [] if i.get("uuid")]
        result = {"apply": apply, "profile_change_needed": changed, "connected": bool(node.get("isConnected"))}
        if not apply:
            return result
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_text(json.dumps({"profile": profile, "node": node, "squad": squad}, indent=2), encoding="utf-8")
        BACKUP.chmod(0o600)
        if changed:
            await client._request("PATCH", "/api/config-profiles", json={"uuid": profile["uuid"], "config": config})
            profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
            profile = next((x for x in profiles if x.get("uuid") == profile_id), None)
        target = next((i for i in (profile or {}).get("inbounds", []) if i.get("tag") == TARGET_TAG), None)
        if not target or not target.get("uuid"):
            raise RuntimeError("Germany XHTTP inbound was not created")
        target_id = target["uuid"]
        if target_id not in active:
            await client._request("PATCH", "/api/nodes", json={"uuid": node["uuid"], "consumptionMultiplier": 1.0, "configProfile": {"activeConfigProfileUuid": profile_id, "activeInbounds": active + [target_id]}})
        if target_id not in authorized:
            await client._request("PATCH", "/api/internal-squads", json={"uuid": squad["uuid"], "inbounds": authorized + [target_id]})
        return {**result, "applied": True, "backup_created": True}
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply)), ensure_ascii=False))
