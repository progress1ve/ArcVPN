#!/usr/bin/env python3
"""Split ArcVPN main/LTE identities and squads. Preview is the default."""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient
from bot.services.remnawave_stats import remnawave_authority_config

LTE_TAGS = {"DE_DHOST_LTE_XHTTP", "NL_DHOST_LTE_XHTTP"}
MAIN_TAGS = {"VLESS_TCP_REALITY", "DE_DHOST_HYSTERIA2", "NL_DHOST_VLESS_TCP", "NL_DHOST_HYSTERIA2"}
LTE_SQUAD_NAME = "ArcVPN LTE"


def iso_expiry(value: str) -> str:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def candidates(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.id user_id,u.telegram_id,COALESCE(u.device_limit,2) device_limit,
               COALESCE(u.lte_quota_gb,0) lte_quota_gb,u.lte_client_uuid,
               u.lte_panel_username,u.lte_remnawave_user_id,
               k.panel_email,k.client_uuid,k.expires_at
          FROM users u JOIN vpn_keys k ON k.user_id=u.id
         WHERE k.expires_at>datetime('now') AND k.client_uuid IS NOT NULL
           AND k.panel_email IS NOT NULL
         GROUP BY u.id ORDER BY u.id
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def migrate(apply: bool, db_path: Path) -> dict:
    cfg = remnawave_authority_config()
    client = RemnawaveClient({**cfg, "panel_write_mode": "production"})
    result = {"apply": apply, "selected": 0, "main_updated": 0,
              "lte_created": 0, "lte_updated": 0, "errors": []}
    conn = sqlite3.connect(db_path)
    try:
        nodes = await client._request("GET", "/api/nodes")
        inbounds = {item.get("tag"): item.get("uuid") for node in nodes
                    if node.get("isConnected") and not node.get("isDisabled")
                    for item in ((node.get("configProfile") or {}).get("activeInbounds") or [])}
        if not MAIN_TAGS.issubset(inbounds) or not LTE_TAGS.issubset(inbounds):
            raise RuntimeError("reviewed main/LTE inbound topology is incomplete")
        main_ids = [inbounds[tag] for tag in sorted(MAIN_TAGS)]
        lte_ids = [inbounds[tag] for tag in sorted(LTE_TAGS)]
        payload = await client._request("GET", "/api/internal-squads")
        squads = payload.get("internalSquads", []) if isinstance(payload, dict) else payload
        main_uuid = str(cfg.get("panel_squad_uuid") or "")
        main = next((s for s in squads if str(s.get("uuid")) == main_uuid), None)
        if not main:
            raise RuntimeError("configured main squad is missing")
        lte = next((s for s in squads if s.get("name") == LTE_SQUAD_NAME), None)
        if apply:
            await client._request("PATCH", "/api/internal-squads",
                                  json={"uuid": main_uuid, "inbounds": main_ids})
            if lte:
                await client._request("PATCH", "/api/internal-squads",
                                      json={"uuid": lte["uuid"], "inbounds": lte_ids})
            else:
                lte = await client._request("POST", "/api/internal-squads",
                                            json={"name": LTE_SQUAD_NAME, "inbounds": lte_ids})
        lte_uuid = str((lte or {}).get("uuid") or "preview-new-lte-squad")
        for row in candidates(db_path):
            result["selected"] += 1
            try:
                main_user = await client.get_user(row["panel_email"])
                if not main_user or str(main_user.get("vlessUuid")) != str(row["client_uuid"]):
                    raise RuntimeError("main identity mismatch")
                if apply:
                    await client.set_user_squads_and_limit(
                        row["panel_email"], [main_uuid], 0
                    )
                    result["main_updated"] += 1
                if int(row["lte_quota_gb"] or 0) <= 0:
                    continue
                username = row["lte_panel_username"] or f"arc_lte_{row['user_id']}"
                current = await client.get_user(username)
                if apply and current:
                    verified = await client.set_user_squads_and_limit(
                        username, [lte_uuid], int(row["lte_quota_gb"]) * 1024**3,
                        expiry_at=iso_expiry(row["expires_at"]),
                    )
                    result["lte_updated"] += 1
                elif apply:
                    verified = await client._request("POST", "/api/users", json={
                        "username": username, "status": "ACTIVE",
                        "trafficLimitBytes": int(row["lte_quota_gb"]) * 1024**3,
                        "trafficLimitStrategy": "NO_RESET", "expireAt": iso_expiry(row["expires_at"]),
                        "hwidDeviceLimit": int(row["device_limit"]),
                        "telegramId": int(row["telegram_id"]),
                        "activeInternalSquads": [lte_uuid],
                        "description": f"ArcVPN LTE entitlement for user {row['user_id']}",
                    })
                    result["lte_created"] += 1
                else:
                    verified = current or {}
                if apply:
                    lte_client_uuid = str(verified.get("vlessUuid") or "")
                    if not lte_client_uuid:
                        raise RuntimeError("LTE identity has no vlessUuid")
                    conn.execute("""UPDATE users SET lte_client_uuid=?,lte_panel_username=?,
                        lte_remnawave_user_id=? WHERE id=?""",
                        (lte_client_uuid, username, str(verified.get("id") or ""), row["user_id"]))
                    conn.commit()
            except Exception as exc:
                result["errors"].append({"user_id": row["user_id"], "error": type(exc).__name__})
    finally:
        conn.close()
        await client.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--database", default=str(ROOT / "database" / "vpn_bot.db"))
    args = parser.parse_args()
    result = asyncio.run(migrate(args.apply, Path(args.database)))
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
