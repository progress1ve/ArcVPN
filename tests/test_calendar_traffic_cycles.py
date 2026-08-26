import asyncio
import sqlite3
from datetime import datetime, timezone

import pytest

from database import connection
from database.db_traffic_cycles import (
    calendar_anniversary,
    get_due_traffic_cycles,
    start_or_preserve_traffic_cycle,
)
from database.migrations import migration_57


UTC = timezone.utc


@pytest.fixture()
def cycle_db(tmp_path, monkeypatch):
    path = tmp_path / "cycles.db"
    monkeypatch.setattr(connection, "DB_PATH", path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE,
            normal_used_bytes INTEGER DEFAULT 0,
            lte_used_bytes INTEGER DEFAULT 0,
            traffic_cycle_started_at DATETIME,
            traffic_cycle_reset_at DATETIME,
            lte_cycle_started_at DATETIME,
            lte_cycle_reset_at DATETIME
        );
        CREATE TABLE vpn_keys (
            id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id),
            created_at DATETIME, expires_at DATETIME, panel_email TEXT,
            traffic_used INTEGER DEFAULT 0, traffic_notified_pct INTEGER DEFAULT 100,
            traffic_updated_at DATETIME
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO users(id,telegram_id,normal_used_bytes,lte_used_bytes)
        VALUES(1,1001,123,456);
    """)
    migration_57(conn)
    conn.commit()
    conn.close()
    return path


def test_month_end_clamp_does_not_drift():
    anchor = datetime(2024, 1, 31, 14, 30, tzinfo=UTC)
    assert calendar_anniversary(anchor, 1) == datetime(2024, 2, 29, 14, 30, tzinfo=UTC)
    assert calendar_anniversary(anchor, 2) == datetime(2024, 3, 31, 14, 30, tzinfo=UTC)
    assert calendar_anniversary(anchor, 13) == datetime(2025, 2, 28, 14, 30, tzinfo=UTC)


def test_early_renewal_preserves_cycle_and_lapsed_purchase_reanchors(cycle_db):
    first = start_or_preserve_traffic_cycle(
        1, activated_at="2026-08-02 10:15:00", preserve_existing=False
    )
    assert first["reset_at"] == "2026-09-02 10:15:00"

    preserved = start_or_preserve_traffic_cycle(
        1, activated_at="2026-08-20 09:00:00", preserve_existing=True
    )
    assert not preserved["started"]
    assert preserved["reset_at"] == "2026-09-02 10:15:00"

    restarted = start_or_preserve_traffic_cycle(
        1, activated_at="2026-10-05 12:00:00", preserve_existing=False
    )
    assert restarted["reset_at"] == "2026-11-05 12:00:00"


def test_authoritative_failure_does_not_advance_or_zero(cycle_db):
    from bot.services.scheduler import process_due_traffic_cycle_resets

    start_or_preserve_traffic_cycle(
        1, activated_at="2026-07-31 08:00:00", preserve_existing=False
    )
    with connection.get_db() as conn:
        conn.execute(
            """INSERT INTO vpn_keys(id,user_id,created_at,expires_at,panel_email)
               VALUES(11,1,'2026-07-31','2026-12-01','arc_user')"""
        )
        conn.execute("UPDATE users SET normal_used_bytes=123,lte_used_bytes=456 WHERE id=1")

    async def rejected(_key_id):
        return False

    result = asyncio.run(process_due_traffic_cycle_resets(
        resetter=rejected, now="2026-08-31 08:00:00"
    ))
    assert result["failed"] == 1
    with connection.get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=1").fetchone()
        assert row["traffic_cycle_reset_at"] == "2026-08-31 08:00:00"
        assert row["normal_used_bytes"] == 123
        assert row["lte_used_bytes"] == 456


def test_success_zeros_both_quotas_and_advances_from_anchor(cycle_db):
    from bot.services.scheduler import process_due_traffic_cycle_resets

    start_or_preserve_traffic_cycle(
        1, activated_at="2026-01-31 08:00:00", preserve_existing=False
    )
    with connection.get_db() as conn:
        conn.execute(
            """INSERT INTO vpn_keys(id,user_id,created_at,expires_at,panel_email,
                                     traffic_used,traffic_notified_pct)
               VALUES(11,1,'2026-01-31','2026-12-01','arc_user',789,5)"""
        )
        conn.execute("UPDATE users SET normal_used_bytes=123,lte_used_bytes=456 WHERE id=1")

    calls = []

    async def accepted(key_id):
        calls.append(key_id)
        return True

    result = asyncio.run(process_due_traffic_cycle_resets(
        resetter=accepted, now="2026-02-28 09:00:00"
    ))
    assert result == {"applied": 1, "failed": 0, "skipped": 0}
    assert calls == [11]
    with connection.get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=1").fetchone()
        assert row["normal_used_bytes"] == row["lte_used_bytes"] == 0
        assert row["traffic_cycle_reset_at"] == "2026-03-31 08:00:00"
        assert row["lte_cycle_reset_at"] == "2026-03-31 08:00:00"
        key = conn.execute("SELECT * FROM vpn_keys WHERE id=11").fetchone()
        assert key["traffic_used"] == 0
        assert key["traffic_notified_pct"] == 100

    second = asyncio.run(process_due_traffic_cycle_resets(
        resetter=accepted, now="2026-02-28 09:01:00"
    ))
    assert second["applied"] == 0
    assert calls == [11]


def test_due_query_requires_an_active_provisioned_key(cycle_db):
    start_or_preserve_traffic_cycle(
        1, activated_at="2026-07-02 00:00:00", preserve_existing=False
    )
    assert get_due_traffic_cycles(now="2026-08-02 00:00:00") == []
