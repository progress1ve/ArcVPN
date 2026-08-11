#!/usr/bin/env python3
"""Synchronize active ArcVPN identities to Remnawave without changing UUIDs."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.services.panels.remnawave import RemnawaveClient


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def active_keys(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT k.id, k.panel_email, k.client_uuid, k.expires_at,
               COALESCE(NULLIF(k.traffic_limit, 0), 536870912000) AS traffic_limit,
               u.telegram_id, COALESCE(u.device_limit, 2) AS device_limit
          FROM vpn_keys k
          JOIN users u ON u.id = k.user_id
         WHERE k.expires_at > datetime('now')
           AND k.client_uuid IS NOT NULL
           AND k.panel_email IS NOT NULL
         ORDER BY k.id
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def iso_expiry(value: str) -> str:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


async def synchronize(apply: bool, db_path: Path) -> dict:
    panel_url = os.environ.get("REMNAWAVE_PANEL_URL", "").strip()
    token = os.environ.get("REMNAWAVE_API_TOKEN", "").strip()
    squad_uuid = os.environ.get("REMNAWAVE_SQUAD_UUID", "").strip()
    if not panel_url or not token or not squad_uuid:
        raise RuntimeError("REMNAWAVE_PANEL_URL, REMNAWAVE_API_TOKEN and REMNAWAVE_SQUAD_UUID are required")

    client = RemnawaveClient({
        "panel_api_url": panel_url,
        "panel_api_token": token,
        "panel_squad_uuid": squad_uuid,
        "panel_write_mode": "production",
    })
    result = {
        "apply": apply,
        "selected": 0,
        "created": 0,
        "updated": 0,
        "verified": 0,
        "squad_inbounds_verified": 0,
        "errors": [],
    }
    try:
        # A Remnawave user only reaches inbounds attached to their internal
        # squad. Keep this declarative so adding/restarting a node can never
        # silently produce a valid-looking config with zero authorized users.
        desired_inbounds = [
            value.strip()
            for value in os.environ.get("REMNAWAVE_SQUAD_INBOUND_UUIDS", "").split(",")
            if value.strip()
        ]
        if apply and desired_inbounds:
            await client._request(
                "PATCH",
                "/api/internal-squads",
                json={"uuid": squad_uuid, "inbounds": desired_inbounds},
            )
            squad = await client._request("GET", "/api/internal-squads")
            squads = squad.get("internalSquads", []) if isinstance(squad, dict) else []
            current = next((item for item in squads if item.get("uuid") == squad_uuid), None)
            current_ids = {item.get("uuid") for item in (current or {}).get("inbounds", [])}
            if set(desired_inbounds) - current_ids:
                raise RuntimeError("Remnawave squad inbound verification failed")
            result["squad_inbounds_verified"] = len(desired_inbounds)

        for key in active_keys(db_path):
            result["selected"] += 1
            username = client._username(key["panel_email"])
            try:
                current = await client.get_user(username)
                payload = {
                    "username": username,
                    "status": "ACTIVE",
                    "trafficLimitBytes": int(key["traffic_limit"]),
                    "trafficLimitStrategy": "NO_RESET",
                    "expireAt": iso_expiry(key["expires_at"]),
                    "hwidDeviceLimit": max(0, int(key["device_limit"])),
                    "vlessUuid": str(key["client_uuid"]),
                    "telegramId": int(key["telegram_id"]),
                    "activeInternalSquads": [squad_uuid],
                    "description": f"ArcVPN key {key['id']} - zero-downtime migration",
                }
                if apply:
                    if current:
                        payload["id"] = current["id"]
                        await client._request("PATCH", "/api/users", json=payload)
                        result["updated"] += 1
                    else:
                        await client._request("POST", "/api/users", json=payload)
                        result["created"] += 1
                    verified = await client.get_user(username)
                    if str((verified or {}).get("vlessUuid")) != str(key["client_uuid"]):
                        raise RuntimeError("UUID verification failed")
                    result["verified"] += 1
            except Exception as exc:  # continue so one legacy record cannot block all users
                result["errors"].append({"key_id": key["id"], "error": str(exc)})
    finally:
        await client.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--env", default=str(ROOT / ".env.remnawave-staging"))
    parser.add_argument("--database", default=str(ROOT / "database" / "vpn_bot.db"))
    args = parser.parse_args()
    load_env(Path(args.env))
    result = asyncio.run(synchronize(args.apply, Path(args.database)))
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
