"""Preview or apply the active-subscription move to Standard without identity changes."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import get_connection


def preview(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT k.id key_id,k.tariff_id old_tariff_id,
               COALESCE(t.period_months,
                 CASE WHEN COALESCE(t.duration_days,30)>=330 THEN 12
                      WHEN COALESCE(t.duration_days,30)>=150 THEN 6
                      WHEN COALESCE(t.duration_days,30)>=75 THEN 3 ELSE 1 END) months,
               st.id standard_tariff_id
        FROM vpn_keys k
        LEFT JOIN tariffs t ON t.id=k.tariff_id
        JOIN tariffs st ON st.product_code='standard' AND st.period_months=
          COALESCE(t.period_months,
            CASE WHEN COALESCE(t.duration_days,30)>=330 THEN 12
                 WHEN COALESCE(t.duration_days,30)>=150 THEN 6
                 WHEN COALESCE(t.duration_days,30)>=75 THEN 3 ELSE 1 END)
        WHERE k.expires_at>CURRENT_TIMESTAMP
          AND COALESCE(t.product_code,'legacy')!='standard'
        ORDER BY k.id
    """).fetchall()
    return [dict(row) for row in rows]


def apply(*, backup_path: Path, confirmation: str) -> int:
    conn = get_connection()
    try:
        rows = preview(conn)
        expected = f"MIGRATE {len(rows)} ACTIVE KEYS TO STANDARD"
        if confirmation != expected:
            raise ValueError(f"confirmation must be exactly: {expected}")
        if not rows:
            return 0
        backup_path = backup_path.resolve()
        if backup_path.exists():
            raise FileExistsError(f"backup already exists: {backup_path}")
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup_path) as backup:
            conn.backup(backup)
        ids = [row["key_id"] for row in rows]
        conn.execute("BEGIN IMMEDIATE")
        locked = preview(conn)
        if locked != rows:
            raise RuntimeError("migration cohort changed after backup; rerun preview")
        for row in rows:
            conn.execute("UPDATE vpn_keys SET tariff_id=? WHERE id=?", (row["standard_tariff_id"], row["key_id"]))
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"""UPDATE users SET device_limit=3,lte_quota_gb=45,
            traffic_monthly_limit_gb=1024,entitlements_updated_at=CURRENT_TIMESTAMP,
            lte_cycle_started_at=COALESCE(lte_cycle_started_at,CURRENT_TIMESTAMP),
            lte_cycle_reset_at=COALESCE(lte_cycle_reset_at,datetime('now','+30 days'))
            WHERE id IN (SELECT DISTINCT user_id FROM vpn_keys WHERE id IN ({placeholders}))""", ids)
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--confirmation")
    args = parser.parse_args()
    with get_connection() as conn:
        rows = preview(conn)
    print(f"active_keys={len(rows)}")
    print(f"confirmation=MIGRATE {len(rows)} ACTIVE KEYS TO STANDARD")
    if not args.apply:
        print("mode=dry-run")
        return 0
    if not args.backup or not args.confirmation:
        parser.error("--apply requires --backup and --confirmation")
    print(f"migrated_keys={apply(backup_path=args.backup, confirmation=args.confirmation)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
