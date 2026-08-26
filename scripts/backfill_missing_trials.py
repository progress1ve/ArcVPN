"""Safely preview or provision missing Standard trials through Remnawave."""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import get_connection


def preview(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT u.*
        FROM users u
        LEFT JOIN trial_entitlements te ON te.user_id = u.id
        WHERE COALESCE(u.used_trial, 0) = 0
          AND (
              te.status IS NULL OR te.status = 'failed'
              OR (te.status = 'provisioning' AND te.updated_at <= datetime('now', '-10 minutes'))
          )
          AND NOT EXISTS (
              SELECT 1 FROM vpn_keys k
              WHERE k.user_id = u.id AND k.expires_at > CURRENT_TIMESTAMP
          )
          AND NOT EXISTS (
              SELECT 1 FROM payments p
              WHERE p.user_id = u.id AND p.status = 'paid'
                AND COALESCE(p.payment_type, '') != 'trial'
          )
        ORDER BY u.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def backup_database(conn: sqlite3.Connection, target: Path) -> None:
    target = target.resolve()
    if target.exists():
        raise FileExistsError(f"backup already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as backup:
        conn.backup(backup)


async def apply(users: list[dict]) -> tuple[int, int]:
    from bot.handlers.user.trial import provision_trial_for_user

    successful = 0
    for user in users:
        if await provision_trial_for_user(user):
            successful += 1
    return successful, len(users) - successful


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--confirmation")
    args = parser.parse_args()

    conn = get_connection()
    try:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required = {"users", "vpn_keys", "payments", "trial_entitlements"}
        if not required.issubset(tables):
            print("error=database migrations must be applied before preview")
            return 3
        users = preview(conn)
        expected = f"PROVISION {len(users)} MISSING STANDARD TRIALS"
        print(f"candidates={len(users)}")
        print(f"confirmation={expected}")
        if not args.apply:
            print("mode=dry-run")
            return 0
        if not args.backup or args.confirmation != expected:
            parser.error("--apply requires --backup and the exact printed --confirmation")
        backup_database(conn, args.backup)
    finally:
        conn.close()

    successful, failed = asyncio.run(apply(users))
    print(f"provisioned={successful}")
    print(f"failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
