"""Server-side RBAC for the ArcVPN Business Console."""
from typing import Optional

from .connection import get_db


ROLE_PERMISSIONS = {
    "owner": {"*"},
    "operator": {"overview.read", "nodes.diagnose", "catalog.manage", "subscriptions.manage", "backups.read", "backups.create", "support.read", "support.reply", "audit.read"},
    "support": {"support.read", "support.reply"},
    "finance": {"overview.read", "expenses.manage"},
    "viewer": {"overview.read", "backups.read", "support.read"},
}


def get_assigned_admin_role(telegram_id: Optional[int]) -> Optional[str]:
    if telegram_id is None:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT role FROM admin_role_assignments WHERE telegram_id=?", (int(telegram_id),)
        ).fetchone()
    role = str(row["role"]) if row else None
    return role if role in ROLE_PERMISSIONS else None


def get_admin_role(telegram_id: Optional[int], *, default: str = "viewer") -> str:
    if telegram_id is None:
        return default
    role = get_assigned_admin_role(telegram_id) or default
    return role if role in ROLE_PERMISSIONS else "viewer"


def role_permissions(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"]))


def role_allows(role: str, permission: str) -> bool:
    permissions = role_permissions(role)
    return "*" in permissions or permission in permissions


def set_admin_role(telegram_id: int, role: str, assigned_by: Optional[int]) -> None:
    if role not in ROLE_PERMISSIONS:
        raise ValueError("invalid_role")
    with get_db() as conn:
        conn.execute("""INSERT INTO admin_role_assignments(telegram_id,role,assigned_by)
            VALUES(?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET
            role=excluded.role,assigned_by=excluded.assigned_by,updated_at=CURRENT_TIMESTAMP""",
            (int(telegram_id), role, assigned_by))


def list_admin_roles() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""SELECT telegram_id,role,assigned_by,created_at,updated_at
            FROM admin_role_assignments ORDER BY telegram_id""").fetchall()
    return [dict(row) for row in rows]
