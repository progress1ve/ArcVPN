"""Deactivate only proven synthetic probe slots; default is a read-only audit."""
import argparse
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.connection import DB_PATH, get_db


def synthetic_slot(row):
    token = hashlib.sha256(
        ("arcvpn-direct-import-v1:" + row["sub_id"]).encode()
    ).hexdigest()
    return row["device_token_hash"] == hashlib.sha256(token.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.id, d.device_token_hash, k.sub_id FROM user_devices d
               JOIN vpn_keys k ON k.id=d.vpn_key_id
               WHERE d.browser='generic' AND d.platform='unknown'
                 AND COALESCE(d.model,'')='' AND COALESCE(d.screen_size,'')=''
                 AND d.display_name='Приложение не определено'
                 AND COALESCE(d.is_active,1)=1"""
        ).fetchall()
        ids = [r["id"] for r in rows if synthetic_slot(r)]
        print("verified_active_synthetic_slots", len(ids))
        print("unmatched_rows_preserved", len(rows) - len(ids))
        if not args.apply or not ids:
            return
        backup_dir = DB_PATH.parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_dir / f"before-generic-device-repair-{stamp}.db"
        fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(backup_path) as backup:
            conn.backup(backup)
        keys_before = conn.execute(
            "SELECT id, sub_id, client_uuid FROM vpn_keys ORDER BY id"
        ).fetchall()
        for device_id in ids:
            conn.execute(
                """UPDATE user_devices SET is_active=0,
                   revoked_at=CURRENT_TIMESTAMP WHERE id=?""", (device_id,)
            )
        assert keys_before == conn.execute(
            "SELECT id, sub_id, client_uuid FROM vpn_keys ORDER BY id"
        ).fetchall()
        print("deactivated", len(ids), "key_identities_unchanged", True)


if __name__ == "__main__":
    main()
