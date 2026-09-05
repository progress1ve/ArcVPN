"""Запросы WebApp: устройства, настройки уведомлений, email и web-сессии."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .connection import get_db


def _iso_after(minutes: int = 0, days: int = 0) -> str:
    return (datetime.utcnow() + timedelta(minutes=minutes, days=days)).strftime("%Y-%m-%d %H:%M:%S")


def get_webapp_account(telegram_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, telegram_id, username, email, email_verified_at,
                      COALESCE(identity_source, 'telegram') identity_source,
                      email_registered_at,
                      COALESCE(notify_expiry, 1) notify_expiry,
                      COALESCE(notify_traffic, 1) notify_traffic,
                      COALESCE(notify_connection, 1) notify_connection
               FROM users WHERE telegram_id = ?""",
            (telegram_id,),
        ).fetchone()
        return dict(row) if row else None


def get_notification_preferences(telegram_id: int) -> Dict[str, bool]:
    account = get_webapp_account(telegram_id) or {}
    return {
        "expiry": bool(account.get("notify_expiry", 1)),
        "traffic": bool(account.get("notify_traffic", 1)),
        "connection": bool(account.get("notify_connection", 1)),
    }


def notification_allowed(telegram_id: int, kind: str) -> bool:
    return get_notification_preferences(telegram_id).get(kind, True)


def update_notification_preferences(telegram_id: int, values: Dict[str, bool]) -> bool:
    columns = {
        "expiry": "notify_expiry",
        "traffic": "notify_traffic",
        "connection": "notify_connection",
    }
    assignments, params = [], []
    for key, column in columns.items():
        if key in values:
            assignments.append(f"{column} = ?")
            params.append(1 if values[key] else 0)
    if not assignments:
        return False
    params.append(telegram_id)
    with get_db() as conn:
        cur = conn.execute(f"UPDATE users SET {', '.join(assignments)} WHERE telegram_id = ?", params)
        return cur.rowcount > 0


def register_import_device(
    sub_id: str,
    device_token: str,
    platform: str,
    model: str,
    display_name: str,
    browser: str = "",
    screen_size: str = "",
) -> Optional[str]:
    token_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
    with get_db() as conn:
        owner = conn.execute(
            "SELECT id, user_id FROM vpn_keys WHERE sub_id = ?",
            (sub_id,),
        ).fetchone()
        if not owner:
            return False
        existing = conn.execute(
            "SELECT device_sub_id FROM user_devices WHERE user_id = ? AND device_token_hash = ?",
            (owner["user_id"], token_hash),
        ).fetchone()
        device_sub_id = (str(existing["device_sub_id"] or "") if existing else "") or secrets.token_urlsafe(24)
        conn.execute(
            """INSERT INTO user_devices
                   (user_id, vpn_key_id, device_token_hash, platform, model,
                    display_name, browser, screen_size, device_sub_id, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, device_token_hash) DO UPDATE SET
                   vpn_key_id = excluded.vpn_key_id,
                   platform = excluded.platform,
                   model = excluded.model,
                   display_name = excluded.display_name,
                   browser = excluded.browser,
                   screen_size = excluded.screen_size,
                   first_seen_at = CASE
                       WHEN COALESCE(user_devices.is_active, 1) = 0
                       THEN CURRENT_TIMESTAMP
                       ELSE user_devices.first_seen_at
                   END,
                   is_active = 1,
                   revoked_at = NULL,
                   last_seen_at = CURRENT_TIMESTAMP,
                   imported_at = CURRENT_TIMESTAMP""",
            (
                owner["user_id"], owner["id"], token_hash, platform, model or None,
                display_name, browser or None, screen_size or None, device_sub_id,
            ),
        )
        return device_sub_id


def adopt_import_device_identity(
    sub_id: str,
    device_token: str,
    platform: str,
    model: str,
) -> bool:
    """Move one unambiguous legacy WebApp slot to Happ's stable HWID."""
    if not model or not platform or platform == "unknown":
        return False
    token_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
    with get_db() as conn:
        owner = conn.execute(
            "SELECT user_id FROM vpn_keys WHERE sub_id = ?", (sub_id,)
        ).fetchone()
        if not owner:
            return False
        if conn.execute(
            "SELECT 1 FROM user_devices WHERE user_id=? AND device_token_hash=?",
            (owner["user_id"], token_hash),
        ).fetchone():
            return True
        candidates = conn.execute(
            """SELECT id FROM user_devices
               WHERE user_id=? AND lower(COALESCE(platform,''))=lower(?)
                 AND lower(COALESCE(model,''))=lower(?)
               ORDER BY COALESCE(last_seen_at, imported_at) DESC""",
            (owner["user_id"], platform, model),
        ).fetchall()
        if len(candidates) != 1:
            return False
        conn.execute(
            """UPDATE user_devices SET device_token_hash=?, is_active=1,
                      revoked_at=NULL, last_seen_at=CURRENT_TIMESTAMP,
                      imported_at=CURRENT_TIMESTAMP WHERE id=?""",
            (token_hash, candidates[0]["id"]),
        )
        return True


def resolve_device_subscription(device_sub_id: str, limit: int) -> Optional[Dict[str, str]]:
    """Resolve a standalone device subscription id and calculate its access state."""
    with get_db() as conn:
        target = conn.execute(
            """SELECT d.id, d.user_id, COALESCE(d.is_active,1) is_active, k.sub_id,
                      d.display_name, d.platform,
                      COALESCE(u.device_limit, ?) device_limit
               FROM user_devices d JOIN vpn_keys k ON k.id=d.vpn_key_id
               JOIN users u ON u.id=d.user_id
               WHERE d.device_sub_id=?
               LIMIT 1""",
            (limit, device_sub_id),
        ).fetchone()
        if not target:
            return None
        if not bool(target["is_active"]):
            state = "revoked"
        else:
            rows = conn.execute(
                """SELECT id FROM user_devices
                   WHERE user_id=? AND COALESCE(is_active,1)=1
                   ORDER BY COALESCE(first_seen_at, imported_at) ASC, id ASC""",
                (target["user_id"],),
            ).fetchall()
            allowed_ids = [int(row["id"]) for row in rows[:max(1, int(target["device_limit"]))]]
            state = "allowed" if int(target["id"]) in allowed_ids else "limit"
        return {
            "sub_id": str(target["sub_id"]),
            "state": state,
            "display_name": str(target["display_name"] or ""),
            "platform": str(target["platform"] or ""),
        }


def get_import_device_access_state(sub_id: str, device_token: str, limit: int) -> Optional[str]:
    """Return whether this stable WebApp device belongs to the allowed device slots.

    Devices are ranked by their first import, so importing one extra phone never
    revokes access from devices that were already using the subscription.
    ``None`` means the subscription or device token is not registered yet.
    """
    token_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
    with get_db() as conn:
        owner = conn.execute(
            "SELECT user_id FROM vpn_keys WHERE sub_id = ?",
            (sub_id,),
        ).fetchone()
        if not owner:
            return None
        target = conn.execute(
            """SELECT COALESCE(is_active, 1) is_active
               FROM user_devices
               WHERE user_id = ? AND device_token_hash = ?""",
            (owner["user_id"], token_hash),
        ).fetchone()
        if target and not bool(target["is_active"]):
            return "revoked"
        rows = conn.execute(
            """SELECT device_token_hash
               FROM user_devices
               WHERE user_id = ? AND COALESCE(is_active, 1) = 1
               ORDER BY COALESCE(first_seen_at, imported_at) ASC, id ASC""",
            (owner["user_id"],),
        ).fetchall()
        hashes = [row["device_token_hash"] for row in rows]
        if token_hash not in hashes:
            return None
        return "allowed" if hashes.index(token_hash) < max(1, int(limit)) else "limit"


def import_device_is_allowed(sub_id: str, device_token: str, limit: int) -> Optional[bool]:
    """Backward-compatible boolean wrapper around the richer access state."""
    state = get_import_device_access_state(sub_id, device_token, limit)
    return None if state is None else state == "allowed"


def subscription_requires_device_token(sub_id: str) -> bool:
    """Whether legacy token-less refreshes must be replaced by a bound import."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COALESCE(u.enforce_device_tokens, 0) enforce_device_tokens
               FROM vpn_keys k JOIN users u ON u.id = k.user_id
               WHERE k.sub_id = ?""",
            (sub_id,),
        ).fetchone()
        return bool(row and row["enforce_device_tokens"])


def subscription_device_slots_full(sub_id: str) -> bool:
    """Return whether a legacy import is blocked because all paid slots are occupied."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COALESCE(u.device_limit,2) device_limit,
                      COUNT(d.id) active_devices
               FROM vpn_keys k JOIN users u ON u.id=k.user_id
               LEFT JOIN user_devices d ON d.user_id=u.id AND COALESCE(d.is_active,1)=1
               WHERE k.sub_id=? GROUP BY u.id""",
            (sub_id,),
        ).fetchone()
        return bool(row and int(row["active_devices"]) >= int(row["device_limit"]))


def get_user_entitlements(telegram_id: int) -> Dict[str, int]:
    """Return persisted commercial limits with backwards-compatible defaults."""
    refresh_lte_cycle(telegram_id)
    with get_db() as conn:
        columns = {column["name"] for column in conn.execute("PRAGMA table_info(users)")}
        bonus_expr = "COALESCE(lte_cycle_bonus_gb, 0)" if "lte_cycle_bonus_gb" in columns else "0"
        row = conn.execute(
            f"""SELECT COALESCE(device_limit, 2) device_limit,
                      COALESCE(lte_quota_gb, 0) lte_quota_gb,
                      {bonus_expr} lte_cycle_bonus_gb,
                      COALESCE(lte_used_bytes, 0) lte_used_bytes,
                      COALESCE(traffic_monthly_limit_gb, 500) traffic_monthly_limit_gb,
                      COALESCE(normal_used_bytes, 0) normal_used_bytes,
                      lte_cycle_started_at, lte_cycle_reset_at
               FROM users WHERE telegram_id = ?""",
            (telegram_id,),
        ).fetchone()
        if not row:
            return {
                "device_limit": 2,
                "lte_quota_gb": 0,
                "lte_used_bytes": 0,
                "traffic_monthly_limit_gb": 500,
                "normal_used_bytes": 0,
                "lte_remaining_bytes": 0,
                "lte_cycle_started_at": None,
                "lte_cycle_reset_at": None,
            }
        normal_used = max(0, int(row["normal_used_bytes"] or 0))
        lte_used = max(0, int(row["lte_used_bytes"] or 0))
        effective_lte_quota = max(0, int(row["lte_quota_gb"] or 0)) + max(0, int(row["lte_cycle_bonus_gb"] or 0))
        return {
            "device_limit": max(2, int(row["device_limit"] or 2)),
            "lte_quota_gb": effective_lte_quota,
            "lte_base_quota_gb": max(0, int(row["lte_quota_gb"] or 0)),
            "lte_cycle_bonus_gb": max(0, int(row["lte_cycle_bonus_gb"] or 0)),
            "lte_used_bytes": lte_used,
            "traffic_monthly_limit_gb": max(
                0,
                int(row["traffic_monthly_limit_gb"])
                if row["traffic_monthly_limit_gb"] is not None else 500,
            ),
            "normal_used_bytes": normal_used,
            "lte_cycle_started_at": row["lte_cycle_started_at"],
            "lte_cycle_reset_at": row["lte_cycle_reset_at"],
            "lte_remaining_bytes": max(
                0, effective_lte_quota * 1024**3 - lte_used
            ),
        }


def get_user_entitlements_by_id(user_id: int) -> Dict[str, int]:
    with get_db() as conn:
        columns = {column["name"] for column in conn.execute("PRAGMA table_info(users)")}
        bonus_expr = "COALESCE(lte_cycle_bonus_gb, 0)" if "lte_cycle_bonus_gb" in columns else "0"
        row = conn.execute(
            f"""SELECT COALESCE(device_limit, 2) device_limit,
                      COALESCE(lte_quota_gb, 0) lte_quota_gb,
                      {bonus_expr} lte_cycle_bonus_gb
               FROM users WHERE id = ?""",
            (user_id,),
        ).fetchone()
        return {
            "device_limit": max(2, int(row["device_limit"] or 2)) if row else 2,
            "lte_quota_gb": (max(0, int(row["lte_quota_gb"] or 0)) + max(0, int(row["lte_cycle_bonus_gb"] or 0))) if row else 0,
            "lte_base_quota_gb": max(0, int(row["lte_quota_gb"] or 0)) if row else 0,
            "lte_cycle_bonus_gb": max(0, int(row["lte_cycle_bonus_gb"] or 0)) if row else 0,
        }


def set_payment_addon(order_id: str, lte_gb: int = 0, device_units: int = 0) -> bool:
    lte_gb = max(0, int(lte_gb))
    device_units = max(0, int(device_units))
    if not lte_gb and not device_units:
        return False
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE payments SET addon_kind='combined', addon_units=?,
                      addon_lte_gb=?, addon_device_units=?
                 WHERE order_id=? AND status='pending'""",
            (lte_gb + device_units, lte_gb, device_units, order_id),
        )
        return cur.rowcount == 1


def apply_payment_addon(order_id: str) -> Optional[Dict[str, int]]:
    """Apply a paid add-on once; panel synchronization is handled by billing."""
    with get_db() as conn:
        order = conn.execute(
            """SELECT user_id,status,addon_kind,addon_units,
                      COALESCE(addon_lte_gb,CASE WHEN addon_kind='lte' THEN addon_units ELSE 0 END) addon_lte_gb,
                      COALESCE(addon_device_units,CASE WHEN addon_kind='device' THEN addon_units ELSE 0 END) addon_device_units,
                      addons_applied_at
               FROM payments WHERE order_id=?""", (order_id,),
        ).fetchone()
        if not order or order["status"] != "paid" or order["addon_kind"] not in {"lte", "device", "combined"}:
            return None
        if not order["addons_applied_at"]:
            conn.execute(
                """UPDATE users SET
                      lte_cycle_bonus_gb=COALESCE(lte_cycle_bonus_gb,0)+?,
                      device_limit=COALESCE(device_limit,0)+?,
                      entitlements_updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (int(order["addon_lte_gb"]), int(order["addon_device_units"]), int(order["user_id"])),
            )
            if int(order["addon_lte_gb"]):
                conn.execute("UPDATE users SET lte_notified_pct=100 WHERE id=?", (int(order["user_id"]),))
            conn.execute("UPDATE payments SET addons_applied_at=CURRENT_TIMESTAMP WHERE order_id=?", (order_id,))
        current = conn.execute(
            """SELECT COALESCE(device_limit,2) device_limit,
                      COALESCE(lte_quota_gb,0)+COALESCE(lte_cycle_bonus_gb,0) lte_quota_gb,
                      COALESCE(lte_quota_gb,0) lte_base_quota_gb
               FROM users WHERE id=?""", (int(order["user_id"]),),
        ).fetchone()
        return {"device_limit": int(current["device_limit"]), "lte_quota_gb": int(current["lte_quota_gb"])}


def set_payment_requested_entitlements(
    order_id: str,
    device_limit: int,
    lte_quota_gb: int,
) -> Optional[str]:
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE payments
               SET requested_device_limit = ?, requested_lte_quota_gb = ?
               WHERE order_id = ? AND status = 'pending'""",
            (max(1, int(device_limit)), max(0, int(lte_quota_gb)), order_id),
        )
        return cur.rowcount > 0


def apply_payment_entitlements(order_id: str) -> Optional[Dict[str, int]]:
    """Idempotently apply requested limits from a paid order to its owner."""
    with get_db() as conn:
        order = conn.execute(
            """SELECT p.user_id, p.status, p.requested_device_limit,
                      p.requested_lte_quota_gb, p.addons_applied_at,
                      t.device_limit tariff_device_limit,
                      t.lte_quota_gb tariff_lte_quota_gb,
                      t.traffic_limit_gb tariff_traffic_limit_gb
               FROM payments p LEFT JOIN tariffs t ON t.id=p.tariff_id
               WHERE p.order_id = ?""",
            (order_id,),
        ).fetchone()
        if not order or order["status"] != "paid":
            return None
        has_tariff_entitlements = (
            order["tariff_device_limit"] is not None
            or order["tariff_lte_quota_gb"] is not None
        )
        if (order["requested_device_limit"] is None
                and order["requested_lte_quota_gb"] is None
                and not has_tariff_entitlements):
            current = conn.execute(
                """SELECT COALESCE(device_limit, 2) device_limit,
                          COALESCE(lte_quota_gb, 0) lte_quota_gb
                   FROM users WHERE id = ?""",
                (order["user_id"],),
            ).fetchone()
            return {
                "device_limit": max(2, int(current["device_limit"] or 2)),
                "lte_quota_gb": max(0, int(current["lte_quota_gb"] or 0)),
            } if current else None
        requested_devices = order["requested_device_limit"]
        requested_lte = order["requested_lte_quota_gb"]
        device_limit = max(1, int(
            requested_devices if requested_devices is not None
            else order["tariff_device_limit"] or 2
        ))
        lte_quota_gb = max(0, int(
            requested_lte if requested_lte is not None
            else order["tariff_lte_quota_gb"] or 0
        ))
        if not order["addons_applied_at"]:
            conn.execute(
                """UPDATE users
                   SET device_limit = ?, lte_quota_gb = ?,
                       traffic_monthly_limit_gb = COALESCE(?, traffic_monthly_limit_gb),
                       lte_used_bytes = CASE WHEN lte_cycle_reset_at IS NULL
                           THEN 0 ELSE COALESCE(lte_used_bytes,0) END,
                       lte_cycle_started_at = COALESCE(lte_cycle_started_at, CURRENT_TIMESTAMP),
                       lte_cycle_reset_at = COALESCE(lte_cycle_reset_at, datetime('now','+30 days')),
                       entitlements_updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (device_limit, lte_quota_gb, order["tariff_traffic_limit_gb"], order["user_id"]),
            )
            conn.execute(
                """UPDATE payments SET addons_applied_at = CURRENT_TIMESTAMP
                   WHERE order_id = ? AND addons_applied_at IS NULL""",
                (order_id,),
            )
        return {"device_limit": device_limit, "lte_quota_gb": lte_quota_gb}


def refresh_lte_cycle(telegram_id: int) -> Dict[str, int]:
    """Return LTE counters; authoritative cycle resets run in the scheduler."""
    with get_db() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        bonus_expr = "COALESCE(lte_cycle_bonus_gb,0)" if "lte_cycle_bonus_gb" in columns else "0"
        if "traffic_cycle_anchor_at" not in columns:
            # Compatibility for pre-v57/test databases only. Production v57
            # never advances locally before the Remnawave acknowledgement.
            conn.execute(
                """UPDATE users SET lte_used_bytes=0,
                          lte_cycle_started_at=CURRENT_TIMESTAMP,
                          lte_cycle_reset_at=datetime('now','+30 days')
                   WHERE telegram_id=? AND lte_cycle_reset_at<=CURRENT_TIMESTAMP""",
                (telegram_id,),
            )
        row = conn.execute(
            f"""SELECT COALESCE(lte_quota_gb,0)+{bonus_expr} quota,
                      COALESCE(lte_used_bytes,0) used,
                      lte_cycle_reset_at reset_at
               FROM users WHERE telegram_id=?""",
            (telegram_id,),
        ).fetchone()
        quota = max(0, int(row["quota"] or 0)) if row else 0
        used = max(0, int(row["used"] or 0)) if row else 0
        return {
            "lte_quota_gb": quota,
            "lte_used_bytes": used,
            "lte_remaining_bytes": max(0, quota * 1024**3 - used),
            "traffic_cycle_reset_at": row["reset_at"] if row else None,
        }


def add_lte_usage(telegram_id: int, bytes_used: int) -> Dict[str, int]:
    """Add raw LTE bytes; LTE is never multiplied into normal traffic."""
    refresh_lte_cycle(telegram_id)
    increment = max(0, int(bytes_used))
    with get_db() as conn:
        conn.execute(
            """UPDATE users SET lte_used_bytes=COALESCE(lte_used_bytes,0)+?
               WHERE telegram_id=?""",
            (increment, telegram_id),
        )
    return refresh_lte_cycle(telegram_id)


def set_lte_usage(telegram_id: int, bytes_used: int) -> Dict[str, int]:
    """Reconcile the absolute Remnawave LTE-identity counter."""
    refresh_lte_cycle(telegram_id)
    with get_db() as conn:
        conn.execute(
            """UPDATE users SET lte_used_bytes=?, lte_usage_synced_at=CURRENT_TIMESTAMP
               WHERE telegram_id=?""",
            (max(0, int(bytes_used)), telegram_id),
        )
    return refresh_lte_cycle(telegram_id)


def get_lte_identity(telegram_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "lte_client_uuid" not in columns:
            return None
        row = conn.execute(
            """SELECT id user_id, telegram_id, lte_client_uuid,
                      lte_panel_username, lte_remnawave_user_id,
                      COALESCE(lte_quota_gb,0)+COALESCE(lte_cycle_bonus_gb,0) lte_quota_gb,
                      COALESCE(lte_used_bytes,0) lte_used_bytes
               FROM users WHERE telegram_id=?""",
            (telegram_id,),
        ).fetchone()
        return dict(row) if row else None


def save_email_registration_code(email: str, code_hash: str) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO email_registration_codes(email,code_hash,expires_at,attempts)
               VALUES(?,?,?,0)
               ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash,
                   expires_at=excluded.expires_at,attempts=0,created_at=CURRENT_TIMESTAMP""",
            (email.lower(), code_hash, _iso_after(minutes=10)),
        )


def get_email_registration_code(email: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM email_registration_codes
               WHERE email=? AND expires_at>CURRENT_TIMESTAMP""", (email.lower(),)
        ).fetchone()
        return dict(row) if row else None


def increment_email_registration_attempts(code_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE email_registration_codes SET attempts=attempts+1 WHERE id=?", (code_id,))


def create_email_user(email: str) -> Dict[str, Any]:
    """Create an email-only identity; a negative synthetic id keeps old Telegram joins safe."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE LOWER(email)=LOWER(?) AND email_verified_at IS NOT NULL", (email,)
        ).fetchone()
        if existing:
            return dict(existing)
        while True:
            synthetic_id = -(1_000_000_000_000 + secrets.randbelow(899_999_999_999))
            try:
                cur = conn.execute(
                    """INSERT INTO users(telegram_id,email,email_verified_at,identity_source,
                           email_registered_at,referral_code,used_trial)
                       VALUES(?,?,CURRENT_TIMESTAMP,'email',CURRENT_TIMESTAMP,?,0)""",
                    (synthetic_id, email.lower(), secrets.token_urlsafe(8)),
                )
                conn.execute("DELETE FROM email_registration_codes WHERE email=?", (email.lower(),))
                row = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
                return dict(row)
            except Exception as exc:
                if "UNIQUE constraint failed: users.telegram_id" in str(exc):
                    continue
                raise


def email_paid_trial_state(user_id: int) -> str:
    with get_db() as conn:
        claim = conn.execute(
            "SELECT status FROM email_paid_trial_claims WHERE user_id=?", (user_id,)
        ).fetchone()
        if claim:
            return str(claim["status"])
        row = conn.execute(
            """SELECT status FROM payments WHERE user_id=? AND offer_code='email_paid_trial'
               ORDER BY id DESC LIMIT 1""", (user_id,)
        ).fetchone()
        return str(row["status"]) if row else "available"


def acquire_email_paid_trial_claim(user_id: int, order_id: str) -> bool:
    """Reserve the offer before provider checkout; only stale failures are retryable."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO email_paid_trial_claims(user_id,order_id,status)
               VALUES(?,?,'pending')
               ON CONFLICT(user_id) DO UPDATE SET order_id=excluded.order_id,
                   status='pending',created_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP
               WHERE email_paid_trial_claims.status IN ('canceled','failed')""",
            (int(user_id), str(order_id)),
        )
        return cur.rowcount == 1


def update_email_paid_trial_claim(order_id: str, status: str) -> bool:
    if status not in {"pending", "paid", "applied", "canceled", "failed"}:
        return False
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE email_paid_trial_claims SET status=?,updated_at=CURRENT_TIMESTAMP
               WHERE order_id=?""", (status, str(order_id))
        )
        return cur.rowcount == 1


def validate_email_paid_trial_claim(user_id: int, order_id: str) -> bool:
    with get_db() as conn:
        row = conn.execute(
            """SELECT 1 FROM email_paid_trial_claims WHERE user_id=? AND order_id=?
               AND status IN ('pending','paid')""", (int(user_id), str(order_id))
        ).fetchone()
        return bool(row)


def get_lte_identity_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "lte_client_uuid" not in columns:
            return None
        row = conn.execute(
            """SELECT id user_id, telegram_id, lte_client_uuid,
                      lte_panel_username, lte_remnawave_user_id,
                      COALESCE(lte_quota_gb,0)+COALESCE(lte_cycle_bonus_gb,0) lte_quota_gb,
                      COALESCE(lte_quota_gb,0) lte_base_quota_gb
               FROM users WHERE id=?""", (user_id,),
        ).fetchone()
        return dict(row) if row else None


def list_lte_identities() -> list[Dict[str, Any]]:
    with get_db() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT id user_id, telegram_id, lte_panel_username,
                      lte_client_uuid, COALESCE(lte_quota_gb,0)+COALESCE(lte_cycle_bonus_gb,0) lte_quota_gb
               FROM users WHERE lte_panel_username IS NOT NULL
                 AND lte_client_uuid IS NOT NULL"""
        ).fetchall()]


def get_subscription_device_limit(sub_id: str, default: int = 2) -> int:
    with get_db() as conn:
        row = conn.execute(
            """SELECT COALESCE(u.device_limit, ?) device_limit
               FROM vpn_keys k JOIN users u ON u.id = k.user_id
               WHERE k.sub_id = ?""",
            (default, sub_id),
        ).fetchone()
        return max(2, int(row["device_limit"])) if row else max(2, int(default))


def get_user_devices(telegram_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id, d.platform, d.model, d.display_name, d.browser,
                      d.screen_size, d.first_seen_at, d.last_seen_at, d.imported_at,
                      k.custom_name, k.online_devices
               FROM user_devices d
               JOIN users u ON u.id = d.user_id
               LEFT JOIN vpn_keys k ON k.id = d.vpn_key_id
               WHERE u.telegram_id = ? AND COALESCE(d.is_active, 1) = 1
               ORDER BY COALESCE(d.imported_at, d.last_seen_at) DESC""",
            (telegram_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def rename_user_device(telegram_id: int, device_id: int, display_name: str) -> bool:
    name = " ".join(str(display_name or "").split()).strip()[:60]
    if len(name) < 2:
        return False
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE user_devices
               SET display_name = ?
               WHERE id = ? AND COALESCE(is_active, 1) = 1
                 AND user_id = (SELECT id FROM users WHERE telegram_id = ?)""",
            (name, int(device_id), int(telegram_id)),
        )
        return cur.rowcount > 0


def revoke_user_device(telegram_id: int, device_id: int) -> bool:
    """Release a slot while keeping a tombstone that blocks the old token."""
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE user_devices
               SET is_active = 0, revoked_at = CURRENT_TIMESTAMP,
                   last_seen_at = CURRENT_TIMESTAMP
               WHERE id = ? AND COALESCE(is_active, 1) = 1
                 AND user_id = (SELECT id FROM users WHERE telegram_id = ?)""",
            (int(device_id), int(telegram_id)),
        )
        if cur.rowcount > 0:
            conn.execute(
                "UPDATE users SET enforce_device_tokens = 1 WHERE telegram_id = ?",
                (int(telegram_id),),
            )
            return True
        return False


def save_email_code(user_id: int, email: str, purpose: str, code_hash: str) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO email_verification_codes
                   (user_id, email, purpose, code_hash, expires_at, attempts)
               VALUES (?, ?, ?, ?, ?, 0)
               ON CONFLICT(user_id, purpose) DO UPDATE SET
                   email = excluded.email,
                   code_hash = excluded.code_hash,
                   expires_at = excluded.expires_at,
                   attempts = 0,
                   created_at = CURRENT_TIMESTAMP""",
            (user_id, email.lower(), purpose, code_hash, _iso_after(minutes=10)),
        )


def get_email_code(user_id: int, purpose: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM email_verification_codes
               WHERE user_id = ? AND purpose = ? AND expires_at > CURRENT_TIMESTAMP""",
            (user_id, purpose),
        ).fetchone()
        return dict(row) if row else None


def increment_email_attempts(code_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE email_verification_codes SET attempts = attempts + 1 WHERE id = ?", (code_id,))


def link_verified_email(user_id: int, email: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET email = ?, email_verified_at = CURRENT_TIMESTAMP WHERE id = ?",
            (email.lower(), user_id),
        )
        conn.execute("DELETE FROM email_verification_codes WHERE user_id = ?", (user_id,))


def unlink_email(telegram_id: int) -> bool:
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not user:
            return False
        conn.execute("UPDATE users SET email = NULL, email_verified_at = NULL WHERE id = ?", (user["id"],))
        conn.execute("DELETE FROM email_verification_codes WHERE user_id = ?", (user["id"],))
        conn.execute("DELETE FROM web_sessions WHERE user_id = ?", (user["id"],))
        return True


def get_user_by_verified_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, telegram_id, email FROM users WHERE LOWER(email) = LOWER(?) AND email_verified_at IS NOT NULL",
            (email,),
        ).fetchone()
        return dict(row) if row else None


def create_web_session(user_id: int, token_hash: str, days: int = 30) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO web_sessions(user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_hash, _iso_after(days=days)),
        )


def telegram_id_from_session(token_hash: str) -> Optional[int]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT u.telegram_id, s.id FROM web_sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > CURRENT_TIMESTAMP""",
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE web_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
        return int(row["telegram_id"])


def revoke_web_session(token_hash: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM web_sessions WHERE token_hash = ?", (token_hash,))
