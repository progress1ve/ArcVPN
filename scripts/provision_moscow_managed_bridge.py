#!/usr/bin/env python3
"""Stage a Remnawave-managed Moscow bridge and reciprocal YouTube egress."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import items

RU_PROFILE = "ArcVPN Moscow Bridge"
RU_NODE = "ArcVPN Moscow Bridge"
RU_DOMAIN = "ru.arccnet.space"
RU_NODE_ADDRESS = "85.198.101.79"
RU_NODE_PORT = 22600
RU_PUBLIC_TAG = "RU_VLESS_REALITY"
RU_YOUTUBE_SS_TAG = "RU_SS_YOUTUBE"
RU_PUBLIC_PORT = 10443
RU_YOUTUBE_SS_PORT = 2444

DE_PROFILE = "ArcVPN Germany 1chost"
DE_NODE = "ArcVPN Germany 1chost"
DE_DOMAIN = "de.arccnet.space"
DE_BRIDGE_SS_TAG = "DE_SS_BRIDGE"
DE_BRIDGE_SS_PORT = 2443

METHOD = "chacha20-ietf-poly1305"
STATE_PATH = Path(".secrets/moscow-managed-bridge.json")


def ss_inbound(tag: str, port: int, password: str) -> dict:
    return {
        "tag": tag, "listen": "0.0.0.0", "port": port, "protocol": "shadowsocks",
        "settings": {"method": METHOD, "password": password, "network": "tcp,udp"},
    }


def ss_outbound(tag: str, address: str, port: int, password: str) -> dict:
    return {
        "tag": tag, "protocol": "shadowsocks",
        "settings": {"servers": [{"address": address, "port": port, "method": METHOD, "password": password}]},
    }


async def patch_profile(client, profile, config, nodes, squads, hosts) -> dict:
    old_by_tag = {value["tag"]: value["uuid"] for value in profile.get("inbounds", [])}
    updated = await client._request("PATCH", "/api/config-profiles", json={
        "uuid": profile["uuid"], "name": profile["name"], "config": config,
    })
    new_by_tag = {value["tag"]: value["uuid"] for value in updated.get("inbounds", [])}
    node = next(value for value in nodes if value.get("name") == DE_NODE)
    await client._request("PATCH", "/api/nodes", json={
        "uuid": node["uuid"],
        "configProfile": {"activeConfigProfileUuid": profile["uuid"], "activeInbounds": list(new_by_tag.values())},
    })
    for squad in squads:
        current = [value["uuid"] for value in squad.get("inbounds", [])]
        replaced = [
            new_by_tag.get(next((tag for tag, old in old_by_tag.items() if old == value), ""), value)
            for value in current
        ]
        if replaced != current:
            await client._request("PATCH", "/api/internal-squads", json={
                "uuid": squad["uuid"], "inbounds": list(dict.fromkeys(replaced)),
            })
    for host in hosts:
        ref = host.get("inbound") or {}
        if str(ref.get("configProfileUuid")) != str(profile["uuid"]):
            continue
        tag = next((tag for tag, old in old_by_tag.items() if old == ref.get("configProfileInboundUuid")), None)
        if tag and tag in new_by_tag:
            await client._request("PATCH", "/api/hosts", json={
                "uuid": host["uuid"],
                "inbound": {"configProfileUuid": profile["uuid"], "configProfileInboundUuid": new_by_tag[tag]},
            })
    return updated


async def provision(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles = items(await client._request("GET", "/api/config-profiles"), "configProfiles")
        nodes = items(await client._request("GET", "/api/nodes"), "nodes")
        squads = items(await client._request("GET", "/api/internal-squads"), "internalSquads")
        hosts = items(await client._request("GET", "/api/hosts"), "hosts")
        de_profile = next(value for value in profiles if value.get("name") == DE_PROFILE)
        existing_ru = next((value for value in profiles if value.get("name") == RU_PROFILE), None)
        result = {"apply": apply, "germany_found": True, "moscow_exists": bool(existing_ru)}
        if not apply:
            return result
        if existing_ru or any(value.get("name") == RU_NODE for value in nodes):
            raise RuntimeError("Moscow managed bridge already exists; inspect before retry")

        keypair = (await client._request("GET", "/api/system/tools/x25519/generate"))["keypairs"][0]
        state = {
            "node_secret": str((await client._request("GET", "/api/keygen"))["secretKey"]),
            "de_bridge_password": secrets.token_urlsafe(24),
            "ru_youtube_password": secrets.token_urlsafe(24),
            "ru_public_key": keypair["publicKey"],
            "ru_short_id": secrets.token_hex(8),
        }

        de_config = de_profile["config"]
        de_config["inbounds"] = [v for v in de_config.get("inbounds", []) if v.get("tag") != DE_BRIDGE_SS_TAG]
        de_config["inbounds"].append(ss_inbound(DE_BRIDGE_SS_TAG, DE_BRIDGE_SS_PORT, state["de_bridge_password"]))
        de_config["outbounds"] = [v for v in de_config.get("outbounds", []) if v.get("tag") != "YOUTUBE_RU"]
        de_config["outbounds"].insert(0, ss_outbound("YOUTUBE_RU", RU_DOMAIN, RU_YOUTUBE_SS_PORT, state["ru_youtube_password"]))
        rules = [v for v in de_config.setdefault("routing", {}).get("rules", []) if v.get("outboundTag") != "YOUTUBE_RU"]
        de_config["routing"]["rules"] = [{
            "type": "field", "domain": ["geosite:youtube"], "network": "tcp,udp", "outboundTag": "YOUTUBE_RU",
        }, *rules]
        de_profile = await patch_profile(client, de_profile, de_config, nodes, squads, hosts)

        ru_config = {
            "log": {"loglevel": "warning"},
            "dns": {"servers": ["1.1.1.1", "1.0.0.1"]},
            "inbounds": [
                {
                    "tag": RU_PUBLIC_TAG, "listen": "0.0.0.0", "port": RU_PUBLIC_PORT, "protocol": "vless",
                    "settings": {"clients": [], "decryption": "none"},
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
                    "streamSettings": {"network": "raw", "security": "reality", "realitySettings": {
                        "xver": 0, "target": "127.0.0.1:8444", "shortIds": [state["ru_short_id"]],
                        "privateKey": keypair["privateKey"], "serverNames": [RU_DOMAIN],
                    }},
                },
                ss_inbound(RU_YOUTUBE_SS_TAG, RU_YOUTUBE_SS_PORT, state["ru_youtube_password"]),
            ],
            "outbounds": [
                ss_outbound("DE_BRIDGE", DE_DOMAIN, DE_BRIDGE_SS_PORT, state["de_bridge_password"]),
                {"tag": "DIRECT", "protocol": "freedom"},
                {"tag": "BLOCK", "protocol": "blackhole"},
            ],
            "routing": {"rules": [
                {"type": "field", "inboundTag": [RU_YOUTUBE_SS_TAG], "outboundTag": "DIRECT"},
                {"type": "field", "domain": ["geosite:youtube"], "network": "tcp,udp", "outboundTag": "DIRECT"},
                {"type": "field", "ip": ["geoip:private"], "outboundTag": "BLOCK"},
                {"type": "field", "domain": ["geosite:private"], "outboundTag": "BLOCK"},
                {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
            ]},
        }
        ru_profile = await client._request("POST", "/api/config-profiles", json={"name": RU_PROFILE, "config": ru_config})
        ru_by_tag = {value["tag"]: value["uuid"] for value in ru_profile.get("inbounds", [])}
        node = await client._request("POST", "/api/nodes", json={
            "name": RU_NODE, "address": RU_NODE_ADDRESS, "port": RU_NODE_PORT,
            "configProfile": {"activeConfigProfileUuid": ru_profile["uuid"], "activeInbounds": list(ru_by_tag.values())},
            "isTrafficTrackingActive": False, "trafficLimitBytes": 0, "notifyPercent": 0,
            "trafficResetDay": 1, "excludedInbounds": [], "countryCode": "RU", "consumptionMultiplier": 1.0,
        })

        de_public_uuid = next(value["uuid"] for value in de_profile.get("inbounds", []) if value["tag"] == "DE_1CHOST_VLESS_TCP")
        for squad in squads:
            current = [value["uuid"] for value in squad.get("inbounds", [])]
            if de_public_uuid in current and ru_by_tag[RU_PUBLIC_TAG] not in current:
                await client._request("PATCH", "/api/internal-squads", json={
                    "uuid": squad["uuid"], "inbounds": [*current, ru_by_tag[RU_PUBLIC_TAG]],
                })
        host = await client._request("POST", "/api/hosts", json={
            "remark": "Москва (Мост)", "address": RU_DOMAIN, "port": 443, "path": "", "host": "",
            "sni": RU_DOMAIN, "alpn": None, "fingerprint": "firefox", "allowInsecure": False,
            "isDisabled": True, "isHidden": False, "securityLayer": "DEFAULT", "nodes": [node["uuid"]],
            "inbound": {"configProfileUuid": ru_profile["uuid"], "configProfileInboundUuid": ru_by_tag[RU_PUBLIC_TAG]},
        })
        state.update({"profile_uuid": ru_profile["uuid"], "node_uuid": node["uuid"], "host_uuid": host["uuid"]})
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.chmod(STATE_PATH, 0o600)
        return {"apply": True, "staged": True, "host_disabled": True, "node_connected": False}
    finally:
        await client.close()


def export_node_env(path: Path) -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    path.write_text(f"NODE_PORT={RU_NODE_PORT}\nSECRET_KEY={state['node_secret']}\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--export-node-env", type=Path)
    args = parser.parse_args()
    if args.export_node_env:
        export_node_env(args.export_node_env)
        print(json.dumps({"exported": True}))
    else:
        print(json.dumps(asyncio.run(provision(args.apply))))


if __name__ == "__main__":
    main()


