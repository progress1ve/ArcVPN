"""Short lived AutoSelect assignments for subscription refreshes.

The client receives one main outbound at a time.  Remnawave supplies current
node population, while this table prevents a refresh from moving an active
viewer to another country and reserves capacity for simultaneous imports.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping, Optional

from .connection import get_db


COUNTRIES = ("de", "ee")
ACTIVE_GRACE = timedelta(minutes=30)
PENDING_GRACE = timedelta(minutes=2)


def _utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def choose_autoselect_country(
    key_id: int,
    candidates: set[str],
    online_counts: Optional[Mapping[str, int]],
    online_at: Optional[str],
    *,
    current_country: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Select a connected country, retaining an active viewer's assignment.

    ``online_counts`` is None when panel telemetry is unavailable.  In that
    case an existing assignment wins; a new one is spread deterministically.
    All network requests must finish before this short SQLite transaction.
    """
    available = sorted(set(candidates) & set(COUNTRIES))
    if not available:
        raise ValueError("No eligible AutoSelect country")
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    stamp = instant.strftime("%Y-%m-%d %H:%M:%S")
    pending_after = (instant - PENDING_GRACE).strftime("%Y-%m-%d %H:%M:%S")
    last_online = _utc(online_at)

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS autoselect_assignments (
            key_id INTEGER PRIMARY KEY,
            country TEXT NOT NULL CHECK(country IN ('de','ee')),
            assigned_at TEXT NOT NULL
        )""")
        row = conn.execute(
            "SELECT country,assigned_at FROM autoselect_assignments WHERE key_id=?",
            (key_id,),
        ).fetchone()
        previous = str(row["country"]) if row else None
        assigned_at = _utc(row["assigned_at"]) if row else None
        if previous in available and (online_counts is None or previous in online_counts) and (
            online_counts is None
            or (last_online is not None and instant - last_online <= ACTIVE_GRACE)
            or (assigned_at is not None and instant - assigned_at <= ACTIVE_GRACE)
        ):
            return previous

        # Only connected panel nodes may receive a *new* assignment.  If all
        # telemetry is absent, preserve the previous route or spread by key.
        connected = [country for country in available if online_counts is not None and country in online_counts]
        if not row and current_country in connected and last_online is not None and instant - last_online <= ACTIVE_GRACE:
            # Preserve the node of an already online user on the first refresh
            # after the rollout, instead of moving their ongoing video stream.
            chosen = current_country
        elif not connected:
            if previous in available:
                return previous
            chosen = available[key_id % len(available)]
        else:
            pending = {country: 0 for country in connected}
            for item in conn.execute(
                "SELECT country,COUNT(*) AS n FROM autoselect_assignments "
                "WHERE assigned_at>=? AND key_id!=? GROUP BY country",
                (pending_after, key_id),
            ):
                if item["country"] in pending:
                    pending[item["country"]] = int(item["n"])
            chosen = min(
                connected,
                key=lambda country: (
                    max(0, int(online_counts[country])) + pending[country],
                    pending[country],
                    (COUNTRIES.index(country) + key_id) % len(COUNTRIES),
                ),
            )
        conn.execute(
            "INSERT INTO autoselect_assignments(key_id,country,assigned_at) VALUES(?,?,?) "
            "ON CONFLICT(key_id) DO UPDATE SET country=excluded.country,assigned_at=excluded.assigned_at",
            (key_id, chosen, stamp),
        )
        return chosen
