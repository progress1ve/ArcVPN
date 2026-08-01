"""YooKassa recurring payment method storage and self-service revocation."""
from typing import Any, Dict, Optional

from .connection import get_db


def save_recurring_method(user_id: int, payment_method_id: str, method_type: str, display_title: str = "") -> bool:
    if not user_id or not payment_method_id:
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE recurring_payment_methods SET active=0, disabled_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE user_id=? AND active=1",
            (user_id,),
        )
        conn.execute("""
            INSERT INTO recurring_payment_methods
                (user_id, provider, payment_method_id, method_type, display_title, active)
            VALUES (?, 'yookassa', ?, ?, ?, 1)
            ON CONFLICT(provider, payment_method_id) DO UPDATE SET
                user_id=excluded.user_id, method_type=excluded.method_type,
                display_title=excluded.display_title, active=1, disabled_at=NULL,
                updated_at=CURRENT_TIMESTAMP
        """, (user_id, payment_method_id, method_type or "bank_card", display_title or ""))
    return True


def get_active_recurring_method(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, provider, method_type, display_title, consent_at, updated_at
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


def get_recurring_summary() -> Dict[str, int]:
    with get_db() as conn:
        row = conn.execute("""
            SELECT SUM(CASE WHEN active=1 THEN 1 ELSE 0 END) AS active,
                   SUM(CASE WHEN active=0 THEN 1 ELSE 0 END) AS disabled
            FROM recurring_payment_methods
        """).fetchone()
        return {"active": int(row["active"] or 0), "disabled": int(row["disabled"] or 0)}
