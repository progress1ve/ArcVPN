"""First-touch advertising attribution and aggregate campaign reporting."""

import re
import secrets
from typing import Any, Dict, List, Optional, Tuple

from .connection import get_db


CAMPAIGN_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,40}$")


def _campaign_code(value: Optional[str] = None) -> str:
    candidate = str(value or "").strip()
    if candidate:
        if not CAMPAIGN_CODE_RE.fullmatch(candidate):
            raise ValueError("invalid_campaign_code")
        return candidate
    return secrets.token_urlsafe(9).rstrip("=")


def create_campaign(
    name: str,
    *,
    code: Optional[str] = None,
    entry_bonus_days: int = 0,
    payment_bonus_days: int = 0,
) -> Dict[str, Any]:
    name = str(name or "").strip()
    if not name or len(name) > 100:
        raise ValueError("invalid_campaign_name")
    if not 0 <= int(entry_bonus_days) <= 365 or not 0 <= int(payment_bonus_days) <= 365:
        raise ValueError("invalid_campaign_bonus")
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO ad_campaigns(name,code,entry_bonus_days,payment_bonus_days)
            VALUES(?,?,?,?)
        """, (name, _campaign_code(code), int(entry_bonus_days), int(payment_bonus_days)))
        row = conn.execute("SELECT * FROM ad_campaigns WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def update_campaign(campaign_id: int, **changes: Any) -> Optional[Dict[str, Any]]:
    allowed = {"name", "is_active", "entry_bonus_days", "payment_bonus_days"}
    values = {key: value for key, value in changes.items() if key in allowed}
    if "name" in values:
        values["name"] = str(values["name"] or "").strip()
        if not values["name"] or len(values["name"]) > 100:
            raise ValueError("invalid_campaign_name")
    if "is_active" in values:
        values["is_active"] = int(bool(values["is_active"]))
    for field in ("entry_bonus_days", "payment_bonus_days"):
        if field in values:
            values[field] = int(values[field])
            if not 0 <= values[field] <= 365:
                raise ValueError("invalid_campaign_bonus")
    with get_db() as conn:
        if values:
            assignments = ",".join(f"{field}=?" for field in values)
            conn.execute(
                f"UPDATE ad_campaigns SET {assignments},updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (*values.values(), int(campaign_id)),
            )
        row = conn.execute("SELECT * FROM ad_campaigns WHERE id=?", (int(campaign_id),)).fetchone()
    return dict(row) if row else None


def attribute_user_to_campaign(user_id: int, code: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Persist first touch only; repeated /start payloads never overwrite it."""
    if not CAMPAIGN_CODE_RE.fullmatch(str(code or "")):
        return False, None
    with get_db() as conn:
        campaign = conn.execute(
            "SELECT * FROM ad_campaigns WHERE code=? AND is_active=1", (code,)
        ).fetchone()
        if not campaign:
            return False, None
        cursor = conn.execute("""
            INSERT OR IGNORE INTO user_campaign_attribution(user_id,campaign_id)
            VALUES(?,?)
        """, (int(user_id), int(campaign["id"])))
        return cursor.rowcount > 0, dict(campaign)


def list_campaign_stats() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.*,
                   COUNT(DISTINCT a.user_id) AS arrivals,
                   COUNT(DISTINCT CASE WHEN p.status='paid' THEN a.user_id END) AS paying_users,
                   COUNT(CASE WHEN p.status='paid' THEN p.id END) AS paid_orders,
                   COALESCE(SUM(CASE WHEN p.status='paid' THEN p.amount_cents ELSE 0 END),0) AS revenue_cents
            FROM ad_campaigns c
            LEFT JOIN user_campaign_attribution a ON a.campaign_id=c.id
            LEFT JOIN payments p ON p.user_id=a.user_id
            GROUP BY c.id
            ORDER BY c.created_at DESC,c.id DESC
        """).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        arrivals = int(item.get("arrivals") or 0)
        paying = int(item.get("paying_users") or 0)
        item["conversion_percent"] = round(paying * 100 / arrivals, 2) if arrivals else 0.0
        item["repeat_paid_orders"] = max(0, int(item.get("paid_orders") or 0) - paying)
        result.append(item)
    return result


def reserve_campaign_bonus(user_id: int, kind: str) -> Optional[Dict[str, Any]]:
    """Reserve one retryable bonus grant per user/kind, snapshotting configured days."""
    if kind not in {"entry", "payment"}:
        raise ValueError("invalid_campaign_bonus_kind")
    field = "entry_bonus_days" if kind == "entry" else "payment_bonus_days"
    with get_db() as conn:
        attribution = conn.execute(f"""
            SELECT a.campaign_id,c.{field} AS days
            FROM user_campaign_attribution a
            JOIN ad_campaigns c ON c.id=a.campaign_id
            WHERE a.user_id=?
        """, (int(user_id),)).fetchone()
        if not attribution or int(attribution["days"] or 0) <= 0:
            return None
        conn.execute("""INSERT OR IGNORE INTO campaign_bonus_grants
            (user_id,campaign_id,kind,days) VALUES(?,?,?,?)""", (
            int(user_id), int(attribution["campaign_id"]), kind, int(attribution["days"]),
        ))
        row = conn.execute(
            "SELECT * FROM campaign_bonus_grants WHERE user_id=? AND kind=?",
            (int(user_id), kind),
        ).fetchone()
    return dict(row) if row and row["status"] != "applied" else None


def finish_campaign_bonus(user_id: int, kind: str, applied: bool, error: Optional[str] = None) -> None:
    with get_db() as conn:
        conn.execute("""UPDATE campaign_bonus_grants SET
            status=?,attempt_count=attempt_count+1,last_error=?,updated_at=CURRENT_TIMESTAMP,
            applied_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE applied_at END
            WHERE user_id=? AND kind=? AND status!='applied'""", (
            "applied" if applied else "failed", None if applied else str(error or "grant_failed")[:500],
            int(bool(applied)), int(user_id), kind,
        ))


__all__ = [
    "attribute_user_to_campaign", "create_campaign", "finish_campaign_bonus", "list_campaign_stats",
    "reserve_campaign_bonus", "update_campaign",
]
