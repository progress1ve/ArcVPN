"""Calendar-anniversary cycles shared by normal and LTE traffic quotas."""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .connection import get_db


UTC_FORMAT = "%Y-%m-%d %H:%M:%S"


def _utc(value: Optional[datetime | str] = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def _sql(value: datetime) -> str:
    return _utc(value).strftime(UTC_FORMAT)


def calendar_anniversary(anchor: datetime | str, months: int) -> datetime:
    """Return an anchor-relative boundary, clamping month-end without drift."""
    origin = _utc(anchor)
    absolute = origin.year * 12 + origin.month - 1 + int(months)
    year, month0 = divmod(absolute, 12)
    month = month0 + 1
    return origin.replace(
        year=year, month=month,
        day=min(origin.day, monthrange(year, month)[1]),
    )


def next_calendar_anniversary(anchor: datetime | str, after: datetime | str) -> datetime:
    """Return the first monthly anniversary strictly after ``after``."""
    origin, point = _utc(anchor), _utc(after)
    months = max(1, (point.year - origin.year) * 12 + point.month - origin.month)
    boundary = calendar_anniversary(origin, months)
    while boundary <= point:
        months += 1
        boundary = calendar_anniversary(origin, months)
    return boundary


def start_or_preserve_traffic_cycle(
    user_id: int,
    *,
    activated_at: Optional[datetime | str] = None,
    preserve_existing: bool,
) -> Dict[str, Any]:
    """Start a new cycle after lapse, or preserve one during early renewal."""
    event = _utc(activated_at)
    with get_db() as conn:
        current = conn.execute(
            """SELECT traffic_cycle_anchor_at, traffic_cycle_reset_at
               FROM users WHERE id=?""", (int(user_id),)
        ).fetchone()
        if not current:
            raise LookupError(f"user {user_id} not found")
        if (preserve_existing and current["traffic_cycle_anchor_at"]
                and current["traffic_cycle_reset_at"]
                and _utc(current["traffic_cycle_reset_at"]) > event):
            return {
                "anchor_at": current["traffic_cycle_anchor_at"],
                "reset_at": current["traffic_cycle_reset_at"],
                "started": False,
            }

        boundary = calendar_anniversary(event, 1)
        event_sql, boundary_sql = _sql(event), _sql(boundary)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        addon_reset = ", lte_cycle_bonus_gb=0, lte_notified_pct=100" if "lte_cycle_bonus_gb" in columns else ""
        conn.execute(
            f"""UPDATE users SET traffic_cycle_anchor_at=?,
                      traffic_cycle_started_at=?, traffic_cycle_reset_at=?,
                      lte_cycle_started_at=?, lte_cycle_reset_at=?,
                      normal_used_bytes=0, lte_used_bytes=0{addon_reset}
               WHERE id=?""",
            (event_sql, event_sql, boundary_sql, event_sql, boundary_sql, int(user_id)),
        )
        return {"anchor_at": event_sql, "reset_at": boundary_sql, "started": True}


def get_due_traffic_cycles(*, now: Optional[datetime | str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """List active users whose authoritative panel reset is due."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id user_id, u.traffic_cycle_anchor_at anchor_at,
                      u.traffic_cycle_reset_at boundary_at,
                      GROUP_CONCAT(vk.id) key_ids
               FROM users u JOIN vpn_keys vk ON vk.user_id=u.id
               WHERE u.traffic_cycle_anchor_at IS NOT NULL
                 AND u.traffic_cycle_reset_at IS NOT NULL
                 AND u.traffic_cycle_reset_at <= ?
                 AND vk.expires_at > ? AND vk.panel_email IS NOT NULL
               GROUP BY u.id ORDER BY u.traffic_cycle_reset_at LIMIT ?""",
            (_sql(_utc(now)), _sql(_utc(now)), max(1, int(limit))),
        ).fetchall()
        return [{**dict(row), "key_ids": [int(v) for v in row["key_ids"].split(",")]} for row in rows]


def claim_traffic_cycle_reset(user_id: int, boundary_at: str) -> bool:
    """Claim a due boundary; stale/failed attempts remain safely retryable."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO traffic_cycle_resets(user_id,boundary_at,status)
               VALUES(?,?,'pending') ON CONFLICT(user_id,boundary_at) DO NOTHING""",
            (int(user_id), boundary_at),
        )
        cursor = conn.execute(
            """UPDATE traffic_cycle_resets SET status='processing',
                      attempt_count=attempt_count+1, last_error=NULL,
                      updated_at=CURRENT_TIMESTAMP
               WHERE user_id=? AND boundary_at=?
                 AND (status='pending'
                      OR (status='failed' AND updated_at <= datetime('now','-5 minutes'))
                      OR (status='processing' AND updated_at <= datetime('now','-15 minutes')))""",
            (int(user_id), boundary_at),
        )
        return cursor.rowcount == 1


def fail_traffic_cycle_reset(user_id: int, boundary_at: str, error: str) -> None:
    with get_db() as conn:
        conn.execute(
            """UPDATE traffic_cycle_resets SET status='failed', last_error=?,
                      updated_at=CURRENT_TIMESTAMP
               WHERE user_id=? AND boundary_at=? AND status='processing'""",
            (str(error)[:500], int(user_id), boundary_at),
        )


def complete_traffic_cycle_reset(
    user_id: int,
    boundary_at: str,
    *,
    completed_at: Optional[datetime | str] = None,
) -> bool:
    """Advance counters only after the Remnawave reset has succeeded."""
    point = _utc(completed_at)
    with get_db() as conn:
        row = conn.execute(
            """SELECT traffic_cycle_anchor_at FROM users
               WHERE id=? AND traffic_cycle_reset_at=?""",
            (int(user_id), boundary_at),
        ).fetchone()
        if not row or not row["traffic_cycle_anchor_at"]:
            return False
        anchor = _utc(row["traffic_cycle_anchor_at"])
        next_boundary = next_calendar_anniversary(anchor, point)
        next_index = ((next_boundary.year - anchor.year) * 12
                      + next_boundary.month - anchor.month)
        cycle_started = calendar_anniversary(anchor, max(0, next_index - 1))
        columns = {column["name"] for column in conn.execute("PRAGMA table_info(users)")}
        addon_reset = ", lte_cycle_bonus_gb=0, lte_notified_pct=100" if "lte_cycle_bonus_gb" in columns else ""
        cursor = conn.execute(
            f"""UPDATE users SET normal_used_bytes=0, lte_used_bytes=0{addon_reset},
                      traffic_cycle_started_at=?, traffic_cycle_reset_at=?,
                      lte_cycle_started_at=?, lte_cycle_reset_at=?
               WHERE id=? AND traffic_cycle_reset_at=?""",
            (_sql(cycle_started), _sql(next_boundary), _sql(cycle_started), _sql(next_boundary),
             int(user_id), boundary_at),
        )
        if cursor.rowcount != 1:
            return False
        conn.execute(
            """UPDATE vpn_keys SET traffic_used=0, traffic_notified_pct=100,
                      traffic_updated_at=NULL WHERE user_id=?""",
            (int(user_id),),
        )
        conn.execute(
            """UPDATE traffic_cycle_resets SET status='applied', applied_at=?,
                      updated_at=CURRENT_TIMESTAMP, last_error=NULL
               WHERE user_id=? AND boundary_at=?""",
            (_sql(point), int(user_id), boundary_at),
        )
        return True
