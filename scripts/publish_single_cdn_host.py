#!/usr/bin/env python3
"""Publish the single paid CDN hostname against the Germany XHTTP inbound."""
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

NODE_NAME = "ArcVPN Germany 1chost"
INBOUND_TAG = "DE_1CHOST_LTE_XHTTP"
PUBLIC_HOST = "cdn-de.arccnet.space"
RETIRED_HOST = "cdn-nd.arccnet.space"
REMARK = "Лучший обход"
STATE = ROOT / ".secrets" / "single-cdn-host.json"


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
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")
        node = next((value for value in nodes if value.get("name") == NODE_NAME), None)
        if not node or not node.get("isConnected"):
            raise RuntimeError("Germany node is missing or disconnected")
        profile_id = (node.get("configProfile") or {}).get("activeConfigProfileUuid")
        profile = next((value for value in profiles if value.get("uuid") == profile_id), None)
        inbound = next((value for value in (profile or {}).get("inbounds", []) if value.get("tag") == INBOUND_TAG), None)
        if not profile or not inbound:
            raise RuntimeError("Germany XHTTP inbound is missing")
        matching = [value for value in hosts if (value.get("address") or "").lower() == PUBLIC_HOST]
        retired = [value for value in hosts if (value.get("address") or "").lower() == RETIRED_HOST]
        preview = {
            "apply": apply,
            "connected": True,
            "matching_hosts": len(matching),
            "retired_hosts": len(retired),
            "retired_hosts_enabled": sum(not bool(value.get("isDisabled")) for value in retired),
            "create_needed": not matching,
            "inbound_tag": INBOUND_TAG,
            "public_host": PUBLIC_HOST,
        }
        if not apply:
            return preview
        for old in retired:
            if not old.get("isDisabled"):
                await client._request("PATCH", "/api/hosts", json={"uuid": old["uuid"], "isDisabled": True})
        payload = {
            "remark": REMARK,
            "address": PUBLIC_HOST,
            "port": 443,
            "path": "/api-test",
            "host": PUBLIC_HOST,
            "sni": PUBLIC_HOST,
            "alpn": "h2,http/1.1",
            "fingerprint": "firefox",
            "allowInsecure": False,
            "isDisabled": False,
            "isHidden": False,
            "securityLayer": "TLS",
            "nodes": [node["uuid"]],
            "inbound": {
                "configProfileUuid": profile["uuid"],
                "configProfileInboundUuid": inbound["uuid"],
            },
        }
        if matching:
            target = matching[0]
            await client._request("PATCH", "/api/hosts", json={"uuid": target["uuid"], **payload})
            host_uuid = target["uuid"]
            action = "updated"
        else:
            created = await client._request("POST", "/api/hosts", json=payload)
            host_uuid = created["uuid"]
            action = "created"
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({"host_uuid": host_uuid, "public_host": PUBLIC_HOST}, indent=2), encoding="utf-8")
        STATE.chmod(0o600)
        return {**preview, "action": action, "published": True}
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply)), ensure_ascii=False))
