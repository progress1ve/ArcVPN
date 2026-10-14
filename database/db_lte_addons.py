"""Paid LTE boosts expire a calendar month after fulfillment, independently of resets."""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def active_lte_addons(conn, user_id: int, *, now: datetime | str | None = None):
    """Return receipt-derived allowance; None means the legacy schema is unavailable."""
    from .db_traffic_cycles import _utc, _sql, calendar_anniversary
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(payments)')}
    if not {'user_id', 'status', 'addon_kind', 'addon_units', 'addons_applied_at'} <= columns:
        return None
    amount = "COALESCE(NULLIF(addon_lte_gb,0),CASE WHEN addon_kind='lte' THEN addon_units ELSE 0 END,0)" if 'addon_lte_gb' in columns else "CASE WHEN addon_kind='lte' THEN COALESCE(addon_units,0) ELSE 0 END"
    rows = conn.execute(f"SELECT {amount} units,addons_applied_at FROM payments WHERE user_id=? AND status='paid' AND addons_applied_at IS NOT NULL AND ({amount})>0", (int(user_id),))
    point = _utc(now)
    total, expiry = 0, None
    for row in rows:
        try:
            start = _utc(row['addons_applied_at'])
            end = calendar_anniversary(start, 1)
            units = max(0, int(row['units']))
        except (ValueError, TypeError, OverflowError):
            logger.warning('Invalid LTE addon receipt dates/units for user=%s', user_id)
            return None  # Preserve the previous allowance until the receipt is investigated.
        if start <= point < end:
            total += units
            expiry = end if expiry is None else min(expiry, end)
    return {'bonus_gb': total, 'next_expiry_at': _sql(expiry) if expiry else None}


def reconcile_lte_addons(conn, *, user_id: int | None = None, telegram_id: int | None = None, now: datetime | str | None = None):
    """Refresh only the allowance cache; never alter counters, devices or identities."""
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)')}
    if 'lte_cycle_bonus_gb' not in columns:
        return {'checked': 0, 'changed': 0}
    if user_id is not None:
        rows = conn.execute('SELECT id,lte_cycle_bonus_gb bonus FROM users WHERE id=?', (int(user_id),)).fetchall()
    elif telegram_id is not None:
        rows = conn.execute('SELECT id,lte_cycle_bonus_gb bonus FROM users WHERE telegram_id=?', (int(telegram_id),)).fetchall()
    else:
        from .db_traffic_cycles import _utc, _sql
        payment_columns = {row['name'] for row in conn.execute('PRAGMA table_info(payments)')}
        if not {'user_id', 'status', 'addons_applied_at'} <= payment_columns:
            return {'checked': 0, 'changed': 0}
        rows = conn.execute("""SELECT id,lte_cycle_bonus_gb bonus FROM users WHERE lte_cycle_bonus_gb>0 OR EXISTS(
            SELECT 1 FROM payments p WHERE p.user_id=users.id AND p.status='paid'
              AND datetime(p.addons_applied_at)>=datetime(?,'-32 days'))""", (_sql(_utc(now)),)).fetchall()
    checked, changed = 0, 0
    for row in rows:
        grant = active_lte_addons(conn, row['id'], now=now)
        if grant is None:
            continue
        checked += 1
        if int(row['bonus'] or 0) != grant['bonus_gb']:
            notification = ',lte_notified_pct=100' if 'lte_notified_pct' in columns else ''
            conn.execute(f'UPDATE users SET lte_cycle_bonus_gb=?{notification} WHERE id=?', (grant['bonus_gb'], row['id']))
            changed += 1
    return {'checked': checked, 'changed': changed}
