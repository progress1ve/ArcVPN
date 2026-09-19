#!/usr/bin/env python3
"""Bind Germany's public REALITY metadata to runtime config without printing it."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import DOMAIN, PROFILE_NAME, TCP_TAG, items


STATE_PATH = Path(".secrets/germany-runtime-metadata.json")
CONFIG_PATH = Path("config.py")


def set_assignment(text: str, name: str, value) -> str:
    line = f"{name} = {value!r}"
    pattern = re.compile(rf"^{re.escape(name)}\s*=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(line, text)
    return text.rstrip() + "\n" + line + "\n"


async def configure(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        profile = next((item for item in profiles if item.get("name") == PROFILE_NAME), None)
        if not profile:
            raise RuntimeError("Germany config profile is missing")
        if not apply:
            return {"apply": False, "profile_exists": True, "metadata_exists": STATE_PATH.exists()}

        if STATE_PATH.exists():
            metadata = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        else:
            config = profile["config"]
            inbound = next(item for item in config["inbounds"] if item.get("tag") == TCP_TAG)
            reality = inbound["streamSettings"]["realitySettings"]
            keypairs = await client._request("GET", "/api/system/tools/x25519/generate")
            keypair = keypairs["keypairs"][0]
            reality["privateKey"] = keypair["privateKey"]
            reality["target"] = "127.0.0.1:8443"
            reality["serverNames"] = [DOMAIN]
            await client._request("PATCH", "/api/config-profiles", json={
                "uuid": profile["uuid"], "config": config,
            })
            metadata = {
                "profile_uuid": profile["uuid"],
                "public_key": keypair["publicKey"],
                "short_id": reality["shortIds"][0],
            }
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            os.chmod(STATE_PATH, 0o600)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = CONFIG_PATH.with_name(f"config.py.pre-germany-{stamp}")
        shutil.copy2(CONFIG_PATH, backup)
        text = CONFIG_PATH.read_text(encoding="utf-8")
        text = set_assignment(text, "REMNAWAVE_GERMANY_ENABLED", True)
        text = set_assignment(text, "REMNAWAVE_GERMANY_PUBLIC_KEY", metadata["public_key"])
        text = set_assignment(text, "REMNAWAVE_GERMANY_SHORT_ID", metadata["short_id"])
        CONFIG_PATH.write_text(text, encoding="utf-8")
        return {"apply": True, "profile_updated": True, "runtime_configured": True}
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(configure(args.apply))))


if __name__ == "__main__":
    main()
