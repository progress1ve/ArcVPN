"""Append-only administrative audit trail."""
import json
from typing import Any, Optional

from .connection import get_db


def append_admin_audit(
    action: str,
    outcome: str,
    *,
    actor_type: str = "admin_console",
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    safe_metadata = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with get_db() as conn:
        conn.execute("""INSERT INTO admin_audit_events(
            actor_type,actor_id,action,target_type,target_id,outcome,metadata_json
        ) VALUES(?,?,?,?,?,?,?)""", (
            str(actor_type)[:32], str(actor_id)[:128] if actor_id is not None else None,
            str(action)[:96], str(target_type)[:64] if target_type else None,
            str(target_id)[:128] if target_id else None, str(outcome)[:32], safe_metadata[:4096],
        ))


def list_admin_audit(limit: int = 100) -> list[dict[str, Any]]:
    bounded_limit = min(500, max(1, int(limit)))
    with get_db() as conn:
        rows = conn.execute("""SELECT id,actor_type,actor_id,action,target_type,target_id,
            outcome,metadata_json,created_at FROM admin_audit_events
            ORDER BY id DESC LIMIT ?""", (bounded_limit,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        except (TypeError, ValueError):
            item["metadata"] = {}
        result.append(item)
    return result
