"""YooKassa recurring payment method storage and self-service revocation."""
from typing import Any, Dict, Optional
import json

from .connection import get_db


def save_recurring_method(
    user_id: int, payment_method_id: str, method_type: str, display_title: str = "",
    vpn_key_id: Optional[int] = None, tariff_id: Optional[int] = None,
    amount_cents: Optional[int] = None, period_days: Optional[int] = None,
) -> bool:
    if not user_id or not payment_method_id:
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE recurring_payment_methods SET active=0, disabled_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND active=1",
            (user_id,),
        )
        conn.execute("""
            INSERT INTO recurring_payment_methods
                (user_id, provider, payment_method_id, method_type, display_title, active,
                 vpn_key_id, tariff_id, amount_cents, period_days, next_charge_at)
            VALUES (?, 'yookassa', ?, ?, ?, 1, ?, ?, ?, ?,
                    (SELECT expires_at FROM vpn_keys WHERE id=?))
            ON CONFLICT(provider, payment_method_id) DO UPDATE SET
                user_id=excluded.user_id, method_type=excluded.method_type,
                display_title=excluded.display_title, active=1, disabled_at=NULL,
                vpn_key_id=COALESCE(excluded.vpn_key_id, recurring_payment_methods.vpn_key_id),
                tariff_id=COALESCE(excluded.tariff_id, recurring_payment_methods.tariff_id),
                amount_cents=COALESCE(excluded.amount_cents, recurring_payment_methods.amount_cents),
                period_days=COALESCE(excluded.period_days, recurring_payment_methods.period_days),
                next_charge_at=COALESCE(excluded.next_charge_at, recurring_payment_methods.next_charge_at),
                failure_count=0, last_error=NULL,
                updated_at=CURRENT_TIMESTAMP
        """, (user_id, payment_method_id, method_type or "bank_card", display_title or "",
              vpn_key_id, tariff_id, amount_cents, period_days, vpn_key_id))
    return True


def get_active_recurring_method(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, provider, method_type, display_title, consent_at, updated_at,
                   vpn_key_id, tariff_id, amount_cents, period_days, next_charge_at,
                   last_charge_at, failure_count, last_error
            FROM recurring_payment_methods WHERE user_id=? AND active=1
            ORDER BY id DESC LIMIT 1
        """, (user_id,)).fetchone()
        return dict(row) if row else None


def disable_recurring_methods(user_id: int) -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE recurring_payment_methods
            SET active=0, payment_method_id='', disabled_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE user_id=? AND active=1
        """, (user_id,))
        return int(cursor.rowcount or 0)


def snapshot_recurring_entitlements(order_id: str, user_id: int) -> bool:
    """Renew the current configuration, excluding temporary paid LTE boosts."""
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT device_limit,lte_quota_gb FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            return False
        devices, quota = user['device_limit'], user['lte_quota_gb']
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'").fetchone():
            key = f'personal_recurring_plan:{user_id}'
            saved = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            policy = json.loads(saved['value']) if saved else {}
            if policy.get('active'):
                changed = conn.execute("""SELECT 1 FROM payments WHERE user_id=? AND id>?
                    AND status='paid' AND operation_type IN ('new','renew','upgrade')
                    AND COALESCE(payment_type,'')!='yookassa_recurring' LIMIT 1""", (user_id,policy['source_payment_id'])).fetchone()
                order = conn.execute('SELECT tariff_id,vpn_key_id,amount_cents,period_days FROM payments WHERE order_id=? AND user_id=?', (order_id,user_id)).fetchone()
                matches = order and all(order[k] == policy[k] for k in ('tariff_id','vpn_key_id','amount_cents','period_days'))
                if changed or not matches:
                    policy['active'] = False
                    conn.execute('UPDATE settings SET value=? WHERE key=?', (json.dumps(policy),key))
                else:
                    quota = policy['lte_quota_gb']
        result = conn.execute("""UPDATE payments SET requested_device_limit=?,requested_lte_quota_gb=?,
            is_custom_tariff=CASE WHEN ?!=COALESCE((SELECT device_limit FROM tariffs WHERE id=payments.tariff_id),?)
              OR ?!=COALESCE((SELECT lte_quota_gb FROM tariffs WHERE id=payments.tariff_id),?)
              OR amount_cents!=COALESCE((SELECT price_rub*100 FROM tariffs WHERE id=payments.tariff_id),amount_cents)
              THEN 1 ELSE 0 END
            WHERE order_id=? AND user_id=? AND status='pending' AND addons_applied_at IS NULL""",
            (devices,quota,devices,devices,quota,quota,order_id,user_id))
        return result.rowcount == 1


def get_recurring_summary() -> Dict[str, int]:
    with get_db() as conn:
        row = conn.execute("""
            SELECT SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) AS active,
                   SUM(CASE WHEN active=0 THEN 1 ELSE 0 END) AS disabled
            FROM recurring_payment_methods
        """).fetchone()
        return {"active": int(row["active"] or 0), "disabled": int(row["disabled"] or 0)}


def claim_due_recurring_cycles(limit: int = 20, include_card: bool = True, include_sbp: bool = False) -> list[Dict[str, Any]]:
    """Atomically claim due card renewals; UNIQUE prevents duplicate charges."""
    claimed: list[Dict[str, Any]] = []
    with get_db() as conn:
        rows = conn.execute("""
            SELECT rpm.*, vk.id AS effective_vpn_key_id, vk.expires_at, vk.user_id AS key_user_id,
                   COALESCE(rpm.tariff_id, vk.tariff_id) AS effective_tariff_id,
                   COALESCE(rpm.amount_cents, CAST(t.price_rub * 100 AS INTEGER), t.price_cents) AS effective_amount_cents,
                   COALESCE(rpm.period_days, t.duration_days, 30) AS effective_period_days,
                   u.telegram_id
            FROM recurring_payment_methods rpm
            JOIN vpn_keys vk ON vk.id=COALESCE(rpm.vpn_key_id,
                (SELECT id FROM vpn_keys WHERE user_id=rpm.user_id ORDER BY expires_at DESC LIMIT 1))
            JOIN users u ON u.id=rpm.user_id
            LEFT JOIN tariffs t ON t.id=COALESCE(rpm.tariff_id, vk.tariff_id)
            WHERE rpm.active=1
              AND ((rpm.method_type='bank_card' AND ?=1) OR (rpm.method_type='sbp' AND ?=1))
              AND vk.expires_at BETWEEN datetime('now','-3 days') AND datetime('now','+1 day')
              AND COALESCE(rpm.amount_cents, CAST(t.price_rub * 100 AS INTEGER), t.price_cents, 0) > 0
            ORDER BY vk.expires_at LIMIT ?
        """, (int(include_card), int(include_sbp), max(1, min(100, int(limit))))).fetchall()
        for raw in rows:
            item = dict(raw)
            due_key = str(item.get("expires_at") or "")[:16]
            cursor = conn.execute("""
                INSERT OR IGNORE INTO recurring_charge_cycles(recurring_method_id,vpn_key_id,due_key)
                VALUES (?,?,?)
            """, (item["id"], item["effective_vpn_key_id"], due_key))
            if cursor.rowcount:
                item["cycle_id"] = cursor.lastrowid
                item["due_key"] = due_key
                claimed.append(item)
    return claimed


def update_recurring_cycle(cycle_id: int, status: str, order_id: str = "", provider_id: str = "", error: str = "") -> None:
    with get_db() as conn:
        conn.execute("""
            UPDATE recurring_charge_cycles SET status=?, order_id=COALESCE(NULLIF(?,''),order_id),
              yookassa_payment_id=COALESCE(NULLIF(?,''),yookassa_payment_id), error=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (status, order_id, provider_id, error[:500], cycle_id))
        if status == "submitted":
            conn.execute("UPDATE recurring_payment_methods SET last_charge_at=CURRENT_TIMESTAMP,last_error=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT recurring_method_id FROM recurring_charge_cycles WHERE id=?)", (cycle_id,))
        elif status == "failed":
            conn.execute("UPDATE recurring_payment_methods SET failure_count=failure_count+1,last_error=?,updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT recurring_method_id FROM recurring_charge_cycles WHERE id=?)", (error[:500], cycle_id))
