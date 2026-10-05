"""Private DB snapshot and safe invariant verification; never outputs identifiers."""
import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "database/vpn_bot.db"


def fingerprint(conn, table, columns, max_id=None):
    available = {r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")}
    selected = [c for c in columns if c in available]
    # Exclude volatile payment/access/usage data; compare only persistent identity and attribution.
    digest = hashlib.sha256()
    rows = conn.execute("SELECT " + ",".join(selected) + " FROM " + table +
                        (" WHERE id<=?" if max_id is not None else "") + " ORDER BY id",
                        (max_id,) if max_id is not None else ())
    count = 0
    highest = 0
    for row in rows:
        digest.update(json.dumps(list(row), separators=(",", ":")).encode())
        count += 1
        highest = max(highest, row[0])
    return {"count": count, "sha256": digest.hexdigest(), "max_id":highest}


def state(conn, prior=None):
    return {"users": fingerprint(conn, "users", ["id","telegram_id","referral_code","referred_by","lte_client_uuid"],
                                prior["users"]["max_id"] if prior else None),
            "keys": fingerprint(conn, "vpn_keys", ["id","user_id","client_uuid","uuid","sub_id","access_token"],
                               prior["keys"]["max_id"] if prior else None)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["before", "after"])
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    directory = ROOT / ".secrets"
    directory.mkdir(mode=0o700, exist_ok=True)
    snapshot = (directory / args.snapshot).resolve()
    if snapshot.parent != directory.resolve() or not snapshot.name.endswith(".json"):
        raise RuntimeError("Snapshot must be a .json basename in private .secrets")
    with sqlite3.connect(DB) as conn:
        current = state(conn)
        if args.mode == "before":
            if snapshot.exists():
                raise RuntimeError("Snapshot exists; refusing overwrite")
            backup = snapshot.with_suffix(".sqlite")
            if backup.exists():
                raise RuntimeError("Backup exists; refusing overwrite")
            with sqlite3.connect(backup) as target:
                conn.backup(target)
            os.chmod(backup, 0o600)
            snapshot.write_text(json.dumps({"state":current, "created_at":datetime.now(timezone.utc).isoformat()}))
            os.chmod(snapshot, 0o600)
            print("Private database backup and identity/attribution snapshot created.")
        else:
            prior = json.loads(snapshot.read_text())["state"]
            current = state(conn, prior)
            if current != prior:
                raise RuntimeError("Identity/attribution cohort changed; inspect private snapshot before proceeding")
            print("PASS: persistent customer identities, subscription identifiers and referral attribution unchanged.")
            for table in ("partner_clients","partner_ledger"):
                count = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                print(table + " rows: " + str(count))


if __name__ == "__main__":
    main()
