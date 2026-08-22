#!/usr/bin/env python3
"""Reconcile stored YooKassa amounts with provider-authoritative RUB values."""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def provider_amount_kopecks(shop_id: str, secret_key: str, payment_id: str) -> int:
    auth = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    request = urllib.request.Request(
        f"https://api.yookassa.ru/v3/payments/{payment_id}",
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.load(response)
    return int(round(float((payload.get("amount") or {}).get("value") or 0) * 100))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("database/vpn_bot.db"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row
    settings = {
        row["key"]: row["value"]
        for row in connection.execute(
            "SELECT key,value FROM settings WHERE key IN ('yookassa_shop_id','yookassa_secret_key')"
        )
    }
    shop_id = settings.get("yookassa_shop_id", "").strip()
    secret_key = settings.get("yookassa_secret_key", "").strip()
    if not shop_id or not secret_key:
        raise RuntimeError("YooKassa credentials are not configured")

    rows = connection.execute("""
        SELECT id,yookassa_payment_id,amount_cents
        FROM payments
        WHERE status IN ('paid','succeeded')
          AND yookassa_payment_id IS NOT NULL
          AND yookassa_payment_id != ''
        ORDER BY id
    """).fetchall()
    checked = changed = failed = 0
    updates: list[tuple[int, int]] = []
    for row in rows:
        try:
            expected = provider_amount_kopecks(shop_id, secret_key, row["yookassa_payment_id"])
            checked += 1
            if expected != int(row["amount_cents"] or 0):
                updates.append((expected, int(row["id"])))
                changed += 1
        except Exception:
            failed += 1

    backup = None
    if args.apply and failed:
        connection.close()
        print(json.dumps({
            "apply": False, "checked": checked, "changed": changed,
            "failed": failed, "backup_created": False,
        }))
        return 1
    if args.apply and updates:
        backup_dir = args.db.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = backup_dir / f"vpn_bot.before_yookassa_reconcile_{stamp}.db"
        shutil.copy2(args.db, backup)
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany("UPDATE payments SET amount_cents=? WHERE id=?", updates)
        connection.commit()
    connection.close()
    print(json.dumps({
        "apply": args.apply,
        "checked": checked,
        "changed": changed,
        "failed": failed,
        "backup_created": bool(backup),
    }))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
