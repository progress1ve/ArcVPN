"""Versioned acceptance records for the public ArcVPN legal agreement."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .connection import get_db


def record_legal_consent(telegram_id: int, version: str, source: str) -> bool:
    """Idempotently record acceptance and update the user's current consent."""
    normalized_version = str(version or "").strip()
    normalized_source = str(source or "").strip()
    if not normalized_version or not normalized_source:
        return False
    with get_db() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE telegram_id=?", (int(telegram_id),)
        ).fetchone()
        if not user:
            return False
        conn.execute(
            """INSERT INTO legal_consents(user_id,version,source)
               VALUES(?,?,?)
               ON CONFLICT(user_id,version) DO NOTHING""",
            (user["id"], normalized_version, normalized_source),
        )
        accepted = conn.execute(
            """SELECT source, accepted_at FROM legal_consents
               WHERE user_id=? AND version=?""",
            (user["id"], normalized_version),
        ).fetchone()
        conn.execute(
            """UPDATE users SET legal_consent_version=?, legal_consent_source=?,
                      legal_consent_at=?
               WHERE id=?""",
            (normalized_version, accepted["source"], accepted["accepted_at"], user["id"]),
        )
        return True


def get_legal_consent(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Return the latest consent summary without exposing unrelated user data."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT legal_consent_version version, legal_consent_source source,
                      legal_consent_at accepted_at
               FROM users WHERE telegram_id=?""",
            (int(telegram_id),),
        ).fetchone()
        if not row or not row["version"]:
            return None
        return dict(row)
