"""Provision the separate Remnawave identity used only by LTE/XHTTP profiles."""
from __future__ import annotations

from datetime import datetime, timezone

from database.connection import get_db


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


async def provision_lte_identity(
    client,
    *,
    user: dict,
    expires_at: datetime,
    quota_gb: int,
    device_limit: int,
    persist_base_quota: bool = True,
) -> dict:
    """Create/update one LTE identity without touching the stable main UUID."""
    payload = await client._request("GET", "/api/internal-squads")
    squads = payload.get("internalSquads", []) if isinstance(payload, dict) else payload
    squad = next((item for item in squads or [] if item.get("name") == "ArcVPN LTE"), None)
    if not squad or not squad.get("uuid"):
        raise RuntimeError("ArcVPN LTE squad is unavailable")

    username = f"arc_lte_{int(user['id'])}"
    current = await client.get_user(username)
    limit_bytes = max(0, int(quota_gb)) * 1024**3
    created = not current
    if current:
        verified = await client.set_user_squads_and_limit(
            username,
            [str(squad["uuid"])],
            limit_bytes,
            expiry_at=_iso_utc(expires_at),
            enabled=quota_gb > 0,
            device_limit=device_limit,
        )
    else:
        verified = await client._request("POST", "/api/users", json={
            "username": username,
            "status": "ACTIVE" if quota_gb > 0 else "DISABLED",
            "trafficLimitBytes": limit_bytes,
            "trafficLimitStrategy": "NO_RESET",
            "expireAt": _iso_utc(expires_at),
            "hwidDeviceLimit": max(1, int(device_limit)),
            "telegramId": int(user["telegram_id"]),
            "activeInternalSquads": [str(squad["uuid"])],
            "description": f"ArcVPN LTE entitlement for user {int(user['id'])}",
        })
    lte_uuid = str((verified or {}).get("vlessUuid") or "")
    if not lte_uuid:
        raise RuntimeError("LTE identity has no vlessUuid")

    with get_db() as conn:
        conn.execute(
            """UPDATE users SET lte_quota_gb=CASE WHEN ? THEN ? ELSE lte_quota_gb END,
                      lte_used_bytes=CASE WHEN ? THEN 0 ELSE lte_used_bytes END,
                      lte_client_uuid=?,lte_panel_username=?,lte_remnawave_user_id=?
                 WHERE id=?""",
            (
                int(persist_base_quota), max(0, int(quota_gb)), int(created), lte_uuid, username,
                str((verified or {}).get("id") or ""), int(user["id"]),
            ),
        )
    return verified


def lte_expiry_patch(identity: dict, panel_user: dict, now: datetime | None = None) -> dict:
    """Align expiry only; preserve exhausted/disabled access and traffic counters."""
    now = now or datetime.now(timezone.utc)
    raw = identity.get("subscription_expires_at")
    if not raw or identity.get("is_banned") or not panel_user.get("id"):
        return {}
    expiry = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    expiry = expiry.replace(tzinfo=expiry.tzinfo or timezone.utc)
    if expiry <= now:
        return {}
    current = datetime.fromisoformat(str(panel_user["expireAt"]).replace("Z", "+00:00"))
    current = current.replace(tzinfo=current.tzinfo or timezone.utc)
    patch = {}
    if abs((expiry-current).total_seconds()) >= 1:
        patch["expireAt"] = _iso_utc(expiry)
    quota = int(panel_user.get("trafficLimitBytes") or 0)
    used = int((panel_user.get("userTraffic") or {}).get("usedTrafficBytes") or 0)
    if (panel_user.get("status") == "EXPIRED" and expiry > now
            and int(identity.get("lte_quota_gb") or 0) > 0 and quota > used):
        patch["status"] = "ACTIVE"
    return {"id": panel_user["id"], **patch} if patch else {}
