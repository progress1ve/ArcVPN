#!/usr/bin/env python3
"""Prepare the Albania WCloud Remnawave node without exposing its secrets."""
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

PROFILE_NAME = "ArcVPN Albania WCloud"
NODE_NAME = "ArcVPN Albania WCloud"
NODE_ADDRESS = "al1-goykb.vpvr4ib84nuv6hdkt.ru"
NODE_PORT = 22500
TCP_TAG = "AL_WCLOUD_VLESS_RAW"
HY2_TAG = "AL_WCLOUD_HYSTERIA2"
STATE_PATH = Path(".secrets/albania-remnawave-state.json")
SECRET_PATH = Path(".secrets/albania-node-secret.txt")


def items(payload, key):
    value = payload.get("response", payload) if isinstance(payload, dict) else payload
    return value.get(key, []) if isinstance(value, dict) else value or []


async def prepare(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        existing_profile = next((x for x in profiles if x.get("name") == PROFILE_NAME), None)
        existing_node = next((x for x in nodes if x.get("name") == NODE_NAME), None)
        if not apply:
            return {"apply": False, "profile_exists": bool(existing_profile), "node_exists": bool(existing_node)}
        if existing_profile or existing_node:
            raise RuntimeError("Albania profile/node already exists; inspect before retry")

        keypairs = await client._request("GET", "/api/system/tools/x25519/generate")
        private_key = keypairs["keypairs"][0]["privateKey"]
        short_id = subprocess.check_output(["openssl", "rand", "-hex", "8"], text=True).strip()
        config = {
            "log": {"loglevel": "none"},
            "dns": {"servers": ["1.1.1.1", "1.0.0.1"]},
            "inbounds": [
                {"tag": TCP_TAG, "port": 3342, "listen": "0.0.0.0", "protocol": "vless",
                 "settings": {"clients": [], "decryption": "none"},
                 "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
                 "streamSettings": {"network": "raw", "security": "reality", "realitySettings": {
                     "xver": 0, "target": f"{NODE_ADDRESS}:443", "spiderX": "",
                     "shortIds": [short_id], "privateKey": private_key, "serverNames": [NODE_ADDRESS]}}},
                {"tag": HY2_TAG, "port": 3343, "listen": "0.0.0.0", "protocol": "hysteria",
                 "settings": {"clients": [], "version": 2},
                 "streamSettings": {"network": "hysteria", "security": "tls",
                    "finalmask": {"quicParams": {"debug": False, "congestion": "bbr"}},
                    "tlsSettings": {"alpn": ["h3"], "certificates": [{"usage": "encipherment",
                        "keyFile": "/var/lib/remnawave/configs/xray/ssl/cert.key", "oneTimeLoading": False,
                        "certificateFile": "/var/lib/remnawave/configs/xray/ssl/cert.pem"}]},
                    "hysteriaSettings": {"version": 2}}},
            ],
            "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}, {"tag": "BLOCK", "protocol": "blackhole"}],
            "routing": {"rules": [
                {"ip": ["geoip:private"], "type": "field", "outboundTag": "BLOCK"},
                {"type": "field", "domain": ["geosite:private"], "outboundTag": "BLOCK"},
                {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
            ]},
        }
        profile = await client._request("POST", "/api/config-profiles", json={"name": PROFILE_NAME, "config": config})
        inbound_ids = {x["tag"]: x["uuid"] for x in profile["inbounds"]}
        node = await client._request("POST", "/api/nodes", json={
            "name": NODE_NAME, "address": NODE_ADDRESS, "port": NODE_PORT,
            "configProfile": {"activeConfigProfileUuid": profile["uuid"],
                "activeInbounds": [inbound_ids[TCP_TAG], inbound_ids[HY2_TAG]]},
            "isTrafficTrackingActive": False, "trafficLimitBytes": 0, "notifyPercent": 0,
            "trafficResetDay": 1, "excludedInbounds": [], "countryCode": "AL",
            "consumptionMultiplier": 1.0,
        })
        secret = str(node.get("secretKey") or node.get("secret") or "")
        if not secret:
            raise RuntimeError("Remnawave did not return a node secret")
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps({"profile_uuid": profile["uuid"], "node_uuid": node["uuid"],
            "tcp_inbound_uuid": inbound_ids[TCP_TAG], "hy2_inbound_uuid": inbound_ids[HY2_TAG]}, indent=2), encoding="utf-8")
        SECRET_PATH.write_text(secret + "\n", encoding="utf-8")
        os.chmod(STATE_PATH, 0o600)
        os.chmod(SECRET_PATH, 0o600)
        return {"apply": True, "prepared": True, "connected": bool(node.get("isConnected")),
                "secret_file": str(SECRET_PATH)}
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(prepare(args.apply)), ensure_ascii=False))


if __name__ == "__main__":
    main()
