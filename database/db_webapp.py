"""Запросы WebApp: устройства, настройки уведомлений, email и web-сессии."""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .connection import get_db


def _iso_after(minutes: int = 0, days: int = 0) -> str:
    return (datetime.utcnow() + timedelta(minutes=minutes, days=days)).strftime("%Y-%m-%d %H:%M:%S")


def get_webapp_account(telegram_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT id, telegram_id, username, email, email_verified_at,
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
) -> bool:
    token_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
    with get_db() as conn:
        owner = conn.execute(
            "SELECT id, user_id FROM vpn_keys WHERE sub_id = ?",
            (sub_id,),
        ).fetchone()
        if not owner:
            return False
        conn.execute(
            """INSERT INTO user_devices
                   (user_id, vpn_key_id, device_token_hash, platform, model,
                    display_name, browser, screen_size, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, device_token_hash) DO UPDATE SET
                   vpn_key_id = excluded.vpn_key_id,
                   platform = excluded.platform,
                   model = excluded.model,
                   display_name = excluded.display_name,
                   browser = excluded.browser,
                   screen_size = excluded.screen_size,
                   last_seen_at = CURRENT_TIMESTAMP,
                   imported_at = CURRENT_TIMESTAMP""",
            (
                owner["user_id"], owner["id"], token_hash, platform, model or None,
                display_name, browser or None, screen_size or None,
            ),
        )
        return True


def import_device_is_allowed(sub_id: str, device_token: str, limit: int) -> Optional[bool]:
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
        rows = conn.execute(
            """SELECT device_token_hash
               FROM user_devices
               WHERE user_id = ?
               ORDER BY COALESCE(first_seen_at, imported_at) ASC, id ASC""",
            (owner["user_id"],),
        ).fetchall()
        hashes = [row["device_token_hash"] for row in rows]
        if token_hash not in hashes:
            return None
        return hashes.index(token_hash) < max(1, int(limit))


def get_user_devices(telegram_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id, d.platform, d.model, d.display_name, d.browser,
                      d.screen_size, d.first_seen_at, d.last_seen_at, d.imported_at,
                      k.custom_name, k.online_devices
               FROM user_devices d
               JOIN users u ON u.id = d.user_id
               LEFT JOIN vpn_keys k ON k.id = d.vpn_key_id
               WHERE u.telegram_id = ?
               ORDER BY COALESCE(d.imported_at, d.last_seen_at) DESC""",
            (telegram_id,),
        ).fetchall()
        return [dict(row) for row in rows]


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
