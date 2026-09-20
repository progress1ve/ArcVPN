#!/usr/bin/env python3
"""Create the dedicated Remnawave squad that materializes bridge inbounds."""
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
from provision_germany_node import items
from provision_moscow_managed_bridge import DE_BRIDGE_SS_TAG, DE_PROFILE, RU_PROFILE, RU_YOUTUBE_SS_TAG

SQUAD_NAME = "ArcVPN Managed Bridge"


async def run(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        de = next(value for value in profiles if value.get("name") == DE_PROFILE)
        ru = next(value for value in profiles if value.get("name") == RU_PROFILE)
        inbound_uuids = [
            next(value["uuid"] for value in de.get("inbounds", []) if value["tag"] == DE_BRIDGE_SS_TAG),
            next(value["uuid"] for value in ru.get("inbounds", []) if value["tag"] == RU_YOUTUBE_SS_TAG),
        ]
        squad = next((value for value in squads if value.get("name") == SQUAD_NAME), None)
        if apply:
            if squad:
                await client._request("PATCH", "/api/internal-squads", json={"uuid": squad["uuid"], "inbounds": inbound_uuids})
            else:
                await client._request("POST", "/api/internal-squads", json={"name": SQUAD_NAME, "inbounds": inbound_uuids})
        return {"apply": apply, "squad_exists": bool(squad), "bridge_inbounds": len(inbound_uuids)}
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply))))


