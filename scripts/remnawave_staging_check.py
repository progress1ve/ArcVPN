#!/usr/bin/env python3
"""Non-destructive Remnawave readiness check; optional synthetic-user lifecycle."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient


def config_from_env(write: bool) -> dict:
    return {
        "id": -9001,
        "name": "Remnawave staging",
        "host": "staging.invalid",
        "port": 443,
        "panel_api_url": os.getenv("REMNAWAVE_PANEL_URL", ""),
        "panel_api_token": os.getenv("REMNAWAVE_API_TOKEN", ""),
        "panel_squad_uuid": os.getenv("REMNAWAVE_SQUAD_UUID", ""),
        "panel_node_uuid": os.getenv("REMNAWAVE_NODE_UUID", ""),
        "panel_write_mode": "shadow" if write else "disabled",
        "panel_type": "remnawave",
    }


async def run(write: bool) -> int:
    config = config_from_env(write)
    missing = [name for name, value in (
        ("REMNAWAVE_PANEL_URL", config["panel_api_url"]),
        ("REMNAWAVE_API_TOKEN", config["panel_api_token"]),
    ) if not value]
    if missing:
        print(json.dumps({"ready": False, "missing": missing}, ensure_ascii=False))
        return 2
    client = RemnawaveClient(config)
    try:
        status = await client.get_server_status()
        result = {"ready": True, "panel": True, "node_online": status["online"]}
        if write:
            username = f"arc-staging-{os.getpid()}"
            user = await client.add_client(0, username, total_gb=1, expire_days=1, limit_ip=1)
            fetched = await client.get_client_stats(username)
            await client.reset_client_traffic(0, username)
            # Delete is deliberately not automated until the panel exposes a stable ID
            # contract in the installed release; disable the synthetic account instead.
            await client.update_client_full(0, user.get("vlessUuid", ""), username, 0, 1 << 30, enable=False)
            result.update({"synthetic_user": username, "lifecycle": bool(fetched), "disabled": True})
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-synthetic", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.write_synthetic)))
