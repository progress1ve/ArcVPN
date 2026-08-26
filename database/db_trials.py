"""Durable trial entitlement lifecycle and Standard tariff resolution."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .connection import get_db
from .db_settings import get_trial_tariff_id

__all__ = [
    "acquire_trial_entitlement",
    "activate_trial_entitlement",
    "fail_trial_entitlement",
    "get_trial_entitlement",
    "get_standard_trial_tariff",
    "get_trial_key_by_panel_email",
]


def get_trial_key_by_panel_email(user_id: int, panel_email: str) -> Optional[Dict[str, Any]]:
    """Find a prior partial provisioning result for retry-safe activation."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM vpn_keys WHERE user_id = ? AND panel_email = ? ORDER BY id LIMIT 1",
            (int(user_id), str(panel_email)),
        ).fetchone()
        return dict(row) if row else None


def get_standard_trial_tariff() -> Optional[Dict[str, Any]]:
    """Resolve the configured active Standard tariff, failing closed otherwise."""
    configured_id = get_trial_tariff_id()
    with get_db() as conn:
        if configured_id is not None:
            row = conn.execute(
                "SELECT * FROM tariffs WHERE id = ? AND is_active = 1",
                (configured_id,),
            ).fetchone()
            if row and _is_standard_name(row["name"]):
                return dict(row)

        rows = conn.execute(
            "SELECT * FROM tariffs WHERE is_active = 1 ORDER BY display_order, id"
        ).fetchall()
        row = next((item for item in rows if _is_standard_name(item["name"])), None)
        return dict(row) if row else None


def _is_standard_name(name: object) -> bool:
    normalized = str(name or "").strip().casefold()
    return "standard" in normalized or "стандарт" in normalized


def get_trial_entitlement(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM trial_entitlements WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def acquire_trial_entitlement(user_id: int, tariff_id: int) -> Dict[str, Any]:
    """Atomically acquire provisioning; stale/failed attempts may be retried."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trial_entitlements (user_id, tariff_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                tariff_id = excluded.tariff_id,
                status = 'provisioning',
                attempt_count = trial_entitlements.attempt_count + 1,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE trial_entitlements.status = 'failed'
               OR (trial_entitlements.status = 'provisioning'
                   AND trial_entitlements.updated_at <= datetime('now', '-10 minutes'))
            """,
            (user_id, tariff_id),
        )
        row = conn.execute(
            "SELECT * FROM trial_entitlements WHERE user_id = ?", (user_id,)
        ).fetchone()
        result = dict(row)
        result["acquired"] = cursor.rowcount == 1
        return result


def activate_trial_entitlement(user_id: int, vpn_key_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE trial_entitlements
            SET status = 'active', vpn_key_id = ?, last_error = NULL,
                activated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND status = 'provisioning'
            """,
            (vpn_key_id, user_id),
        )
        if cursor.rowcount:
            conn.execute("UPDATE users SET used_trial = 1 WHERE id = ?", (user_id,))
        return cursor.rowcount == 1


def fail_trial_entitlement(user_id: int, error: str) -> bool:
    safe_error = str(error or "trial provisioning failed")[:500]
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE trial_entitlements
            SET status = 'failed', last_error = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND status = 'provisioning'
            """,
            (safe_error, user_id),
        )
        return cursor.rowcount == 1
