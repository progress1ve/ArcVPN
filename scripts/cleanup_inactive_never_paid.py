"""Preview or explicitly apply inactive never-paid user cleanup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ADMIN_IDS
from database.connection import get_connection
from database.db_user_cleanup import apply_cleanup, cleanup_candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--created-before", required=True, help="ISO timestamp; recent users are excluded")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--confirmation")
    args = parser.parse_args()

    with get_connection() as conn:
        candidates = cleanup_candidates(conn, created_before=args.created_before, excluded_telegram_ids=ADMIN_IDS)
    print(f"eligible_users={len(candidates)}")
    print(f"confirmation=DELETE {len(candidates)} USERS")
    if not args.apply:
        print("mode=dry-run")
        return 0
    if not args.backup or not args.confirmation:
        parser.error("--apply requires --backup and --confirmation")
    deleted = apply_cleanup(
        created_before=args.created_before, backup_path=args.backup,
        confirmation=args.confirmation, excluded_telegram_ids=ADMIN_IDS,
    )
    print(f"deleted_users={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
