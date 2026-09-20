#!/usr/bin/env python3
"""Align the staged Moscow bridge with Remnawave's official service-user flow."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config
from provision_germany_node import items
from provision_moscow_managed_bridge import (
    DE_BRIDGE_SS_PORT, DE_BRIDGE_SS_TAG, DE_DOMAIN, DE_NODE, DE_PROFILE,
    RU_DOMAIN, RU_NODE, RU_PROFILE, RU_PUBLIC_TAG, RU_YOUTUBE_SS_PORT, RU_YOUTUBE_SS_TAG,
    METHOD, patch_profile, ss_outbound,
)
from configure_managed_bridge_squad import SQUAD_NAME

SERVICE_USERNAME = "arc-managed-bridge"


def official_ss_inbound(tag: str, port: int) -> dict:
    return {
        "tag": tag, "port": port, "listen": "0.0.0.0", "protocol": "shadowsocks",
        "settings": {"clients": [], "network": "tcp,udp"},
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
    }


async def fresh(client):
    return (
        items(await client._request("GET", "/api/config-profiles"), "configProfiles"),
        items(await client._request("GET", "/api/nodes"), "nodes"),
        items(await client._request("GET", "/api/internal-squads"), "internalSquads"),
        items(await client._request("GET", "/api/hosts"), "hosts"),
    )


async def run(apply: bool) -> dict:
    client = RemnawaveClient(remnawave_authority_config())
    try:
        profiles, nodes, squads, hosts = await fresh(client)
        squad = next(value for value in squads if value.get("name") == SQUAD_NAME)
        try:
            service_user = await client._request("GET", f"/api/users/by-username/{SERVICE_USERNAME}")
        except Exception as exc:
            if "HTTP 404" not in str(exc):
                raise
            service_user = None
        if not apply:
            return {
                "apply": False, "squad_found": True, "service_user_exists": bool(service_user),
                "service_user_used_bytes": int(((service_user or {}).get("userTraffic") or {}).get("usedTrafficBytes") or 0),
            }
        if not service_user:
            service_user = await client._request("POST", "/api/users", json={
                "username": SERVICE_USERNAME, "status": "ACTIVE", "trafficLimitBytes": 0,
                "trafficLimitStrategy": "NO_RESET", "expireAt": datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat(),
                "hwidDeviceLimit": 0, "vlessUuid": str(uuid.uuid4()),
                "activeInternalSquads": [squad["uuid"]], "description": "Managed RU-EU bridge service identity",
            })
        password = str(service_user.get("ssPassword") or "")
        if not password:
            raise RuntimeError("Remnawave service user has no Shadowsocks password")

        de = next(value for value in profiles if value.get("name") == DE_PROFILE)
        de_config = de["config"]
        de_config["inbounds"] = [v for v in de_config.get("inbounds", []) if v.get("tag") != DE_BRIDGE_SS_TAG]
        de_config["inbounds"].append(official_ss_inbound(DE_BRIDGE_SS_TAG, DE_BRIDGE_SS_PORT))
        de_config["outbounds"] = [v for v in de_config.get("outbounds", []) if v.get("tag") != "YOUTUBE_RU"]
        de_config["outbounds"].append(ss_outbound("YOUTUBE_RU", RU_DOMAIN, RU_YOUTUBE_SS_PORT, password))
        de_config["routing"]["rules"] = [
            {"type": "field", "domain": ["geosite:youtube"], "network": "tcp,udp", "outboundTag": "YOUTUBE_RU"},
            *[v for v in de_config.get("routing", {}).get("rules", []) if v.get("outboundTag") != "YOUTUBE_RU"],
        ]
        await patch_profile(client, de, de_config, nodes, squads, hosts)

        profiles, nodes, squads, hosts = await fresh(client)
        ru = next(value for value in profiles if value.get("name") == RU_PROFILE)
        ru_config = ru["config"]
        ru_config["inbounds"] = [v for v in ru_config.get("inbounds", []) if v.get("tag") != RU_YOUTUBE_SS_TAG]
        ru_config["inbounds"].append(official_ss_inbound(RU_YOUTUBE_SS_TAG, RU_YOUTUBE_SS_PORT))
        ru_config["outbounds"] = [v for v in ru_config.get("outbounds", []) if v.get("tag") != "DE_BRIDGE"]
        ru_config["outbounds"].append(ss_outbound("DE_BRIDGE", DE_DOMAIN, DE_BRIDGE_SS_PORT, password))
        base_rules = [v for v in ru_config.get("routing", {}).get("rules", []) if v.get("outboundTag") != "DE_BRIDGE"]
        ru_config["routing"]["rules"] = [
            *base_rules,
            {"type": "field", "inboundTag": [RU_PUBLIC_TAG], "outboundTag": "DE_BRIDGE"},
        ]
        old_by_tag = {value["tag"]: value["uuid"] for value in ru.get("inbounds", [])}
        updated_ru = await client._request("PATCH", "/api/config-profiles", json={
            "uuid": ru["uuid"], "name": ru["name"], "config": ru_config,
        })
        new_by_tag = {value["tag"]: value["uuid"] for value in updated_ru.get("inbounds", [])}
        node = next(value for value in nodes if value.get("name") == RU_NODE)
        await client._request("PATCH", "/api/nodes", json={
            "uuid": node["uuid"], "configProfile": {
                "activeConfigProfileUuid": ru["uuid"], "activeInbounds": list(new_by_tag.values()),
            },
        })
        for current_squad in squads:
            current = [value["uuid"] for value in current_squad.get("inbounds", [])]
            replaced = [new_by_tag.get(next((tag for tag, old in old_by_tag.items() if old == value), ""), value) for value in current]
            if replaced != current:
                await client._request("PATCH", "/api/internal-squads", json={
                    "uuid": current_squad["uuid"], "inbounds": list(dict.fromkeys(replaced)),
                })
        for host in hosts:
            ref = host.get("inbound") or {}
            if str(ref.get("configProfileUuid")) != str(ru["uuid"]):
                continue
            tag = next((tag for tag, old in old_by_tag.items() if old == ref.get("configProfileInboundUuid")), None)
            if tag and tag in new_by_tag:
                await client._request("PATCH", "/api/hosts", json={
                    "uuid": host["uuid"], "inbound": {
                        "configProfileUuid": ru["uuid"], "configProfileInboundUuid": new_by_tag[tag],
                    },
                })
        return {"apply": True, "official_bridge_configured": True, "host_still_disabled": True}
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply))))


