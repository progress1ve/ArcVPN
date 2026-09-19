#!/usr/bin/env python3
"""Prepare the replacement Germany Remnawave node without exposing secrets.

Creates one TCP REALITY inbound and a disabled delivery Host. Promotion remains
separate until the node, decoy HTTPS site, authorization, and real tunnel pass.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config


PROFILE_NAME = "ArcVPN Germany 1chost"
NODE_NAME = "ArcVPN Germany 1chost"
DOMAIN = "de.arccnet.space"
NODE_ADDRESS = "87.121.47.203"
NODE_PORT = 22600
TCP_TAG = "DE_1CHOST_VLESS_TCP"
STATE_PATH = Path(".secrets/germany-remnawave-state.json")
SECRET_PATH = Path(".secrets/germany-node-secret.txt")


def items(payload, key):
    value = payload.get("response", payload) if isinstance(payload, dict) else payload
    return value.get(key, []) if isinstance(value, dict) else value or []


async def prepare(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        profile = next((item for item in profiles if item.get("name") == PROFILE_NAME), None)
        node = next((item for item in nodes if item.get("name") == NODE_NAME), None)
        if not apply:
            return {
                "apply": False,
                "profile_exists": bool(profile),
                "node_exists": bool(node),
                "domain": DOMAIN,
                "node_port": NODE_PORT,
            }
        if profile or node:
            if not (profile and node):
                raise RuntimeError("Germany preparation is partial; inspect before retry")
            return {
                "apply": True,
                "prepared": True,
                "connected": bool(node.get("isConnected")),
                "reused": True,
            }

        keypairs = await client._request("GET", "/api/system/tools/x25519/generate")
        private_key = keypairs["keypairs"][0]["privateKey"]
        short_id = subprocess.check_output(["openssl", "rand", "-hex", "8"], text=True).strip()
        config = {
            "log": {"loglevel": "warning"},
            "dns": {"servers": ["1.1.1.1", "1.0.0.1"]},
            "inbounds": [{
                "tag": TCP_TAG,
                "port": 443,
                "listen": "0.0.0.0",
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
                "streamSettings": {
                    "network": "raw",
                    "security": "reality",
                    "realitySettings": {
                        "xver": 0,
                        "target": "127.0.0.1:8443",
                        "shortIds": [short_id],
                        "privateKey": private_key,
                        "serverNames": [DOMAIN],
                    },
                },
            }],
            "outbounds": [
                {"tag": "DIRECT", "protocol": "freedom"},
                {"tag": "BLOCK", "protocol": "blackhole"},
            ],
            "routing": {"rules": [
                {"ip": ["geoip:private"], "type": "field", "outboundTag": "BLOCK"},
                {"type": "field", "domain": ["geosite:private"], "outboundTag": "BLOCK"},
                {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
            ]},
        }
        profile = await client._request(
            "POST", "/api/config-profiles", json={"name": PROFILE_NAME, "config": config}
        )
        inbound_id = next(item["uuid"] for item in profile["inbounds"] if item["tag"] == TCP_TAG)
        node = await client._request("POST", "/api/nodes", json={
            "name": NODE_NAME,
            "address": NODE_ADDRESS,
            "port": NODE_PORT,
            "configProfile": {
                "activeConfigProfileUuid": profile["uuid"],
                "activeInbounds": [inbound_id],
            },
            "isTrafficTrackingActive": False,
            "trafficLimitBytes": 0,
            "notifyPercent": 0,
            "trafficResetDay": 1,
            "excludedInbounds": [],
            "countryCode": "DE",
            "consumptionMultiplier": 1.0,
        })
        host = await client._request("POST", "/api/hosts", json={
            "remark": "Германия #1",
            "address": DOMAIN,
            "port": 443,
            "path": "",
            "host": "",
            "sni": DOMAIN,
            "alpn": None,
            "fingerprint": "firefox",
            "allowInsecure": False,
            "isDisabled": True,
            "isHidden": False,
            "securityLayer": "DEFAULT",
            "nodes": [node["uuid"]],
            "inbound": {
                "configProfileUuid": profile["uuid"],
                "configProfileInboundUuid": inbound_id,
            },
        })
        keygen = await client._request("GET", "/api/keygen")
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps({
            "profile_uuid": profile["uuid"],
            "node_uuid": node["uuid"],
            "tcp_inbound_uuid": inbound_id,
            "tcp_host_uuid": host["uuid"],
        }, indent=2), encoding="utf-8")
        SECRET_PATH.write_text(str(keygen["secretKey"]) + "\n", encoding="utf-8")
        os.chmod(STATE_PATH, 0o600)
        os.chmod(SECRET_PATH, 0o600)
        return {"apply": True, "prepared": True, "connected": False, "host_disabled": True}
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(prepare(args.apply)), ensure_ascii=False))


if __name__ == "__main__":
    main()
