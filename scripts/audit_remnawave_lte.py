#!/usr/bin/env python3
"""Print a non-secret Remnawave LTE topology inventory for rollout planning."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config


async def audit() -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        nodes = await client._request("GET", "/api/nodes")
        squads_payload = await client._request("GET", "/api/internal-squads")
        squads = (squads_payload.get("internalSquads", [])
                  if isinstance(squads_payload, dict) else squads_payload or [])
        return {
            "nodes": [{
                "name": node.get("name"),
                "connected": bool(node.get("isConnected")),
                "disabled": bool(node.get("isDisabled")),
                "consumption_multiplier": float(node.get("consumptionMultiplier") or 0),
                "inbounds": [{"tag": item.get("tag")}
                             for item in ((node.get("configProfile") or {}).get("activeInbounds") or [])],
            } for node in nodes],
            "squads": [{
                "name": squad.get("name"),
                "inbounds": [{"tag": item.get("tag")}
                             for item in (squad.get("inbounds") or [])],
            } for squad in squads],
        }
    finally:
        await client.close()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(audit()), ensure_ascii=False, indent=2))
