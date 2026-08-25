"""Fail-closed cleanup for inactive users who have never paid."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .connection import get_connection


def cleanup_candidates(conn: sqlite3.Connection, *, created_before: str, excluded_telegram_ids: Iterable[int] = ()) -> list[dict]:
    """Return eligible users without exposing referral/subscription tokens."""
    excluded = tuple(int(value) for value in excluded_telegram_ids)
    excluded_clause = ""
    if excluded:
        placeholders = ",".join("?" for _ in excluded)
        excluded_clause = f"AND u.telegram_id NOT IN ({placeholders})"
    rows = conn.execute(
        f"""
        SELECT u.id, u.telegram_id, u.username, u.created_at, u.used_trial
        FROM users u
        WHERE COALESCE(u.is_active, 1) = 0
          AND u.created_at < ?
          {excluded_clause}
          AND NOT EXISTS (
              SELECT 1 FROM payments p WHERE p.user_id = u.id
                AND p.status = 'paid' AND COALESCE(p.payment_type, '') != 'trial'
          )
          AND NOT EXISTS (
              SELECT 1 FROM vpn_keys k WHERE k.user_id = u.id
                AND k.expires_at > CURRENT_TIMESTAMP
          )
        ORDER BY u.id
        """,
        (created_before, *excluded),
    ).fetchall()
    return [dict(row) for row in rows]


def apply_cleanup(*, created_before: str, backup_path: Path, confirmation: str, excluded_telegram_ids: Iterable[int] = ()) -> int:
    """Backup then delete the exact re-evaluated cohort in one transaction."""
    conn = get_connection()
    try:
        candidates = cleanup_candidates(conn, created_before=created_before, excluded_telegram_ids=excluded_telegram_ids)
        expected = f"DELETE {len(candidates)} USERS"
        if confirmation != expected:
            raise ValueError(f"confirmation must be exactly: {expected}")
        if not candidates:
            return 0

        backup_path = Path(backup_path).resolve()
        if backup_path.exists():
            raise FileExistsError(f"backup already exists: {backup_path}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup_path) as backup:
            conn.backup(backup)

        ids = [row["id"] for row in candidates]
        placeholders = ",".join("?" for _ in ids)
        conn.execute("BEGIN IMMEDIATE")
        locked = cleanup_candidates(conn, created_before=created_before, excluded_telegram_ids=excluded_telegram_ids)
        if [row["id"] for row in locked] != ids:
            raise RuntimeError("cleanup cohort changed after backup; rerun dry-run")

        conn.execute(f"UPDATE users SET referred_by = NULL WHERE referred_by IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM notification_log WHERE vpn_key_id IN (SELECT id FROM vpn_keys WHERE user_id IN ({placeholders}))", ids)
        conn.execute(f"DELETE FROM referral_stats WHERE referrer_id IN ({placeholders}) OR referral_id IN ({placeholders})", (*ids, *ids))
        conn.execute(f"DELETE FROM payments WHERE user_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM vpn_keys WHERE user_id IN ({placeholders})", ids)
        cursor = conn.execute(f"DELETE FROM users WHERE id IN ({placeholders})", ids)
        if cursor.rowcount != len(ids):
            raise RuntimeError("deleted user count does not match dry-run")
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
