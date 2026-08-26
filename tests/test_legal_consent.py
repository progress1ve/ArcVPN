import sqlite3

from database import connection
from database.db_legal_consent import get_legal_consent, record_legal_consent
from database.migrations import migration_57


def test_versioned_legal_consent_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "legal.db"
    monkeypatch.setattr(connection, "DB_PATH", path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE,
            normal_used_bytes INTEGER DEFAULT 0, lte_used_bytes INTEGER DEFAULT 0,
            traffic_cycle_started_at DATETIME, traffic_cycle_reset_at DATETIME,
            lte_cycle_started_at DATETIME, lte_cycle_reset_at DATETIME
        );
        CREATE TABLE vpn_keys (id INTEGER PRIMARY KEY, user_id INTEGER, created_at DATETIME);
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO users(id,telegram_id) VALUES(1,1001);
    """)
    migration_57(conn)
    conn.commit()
    conn.close()

    assert record_legal_consent(1001, "2026-08-26", "telegram-channel-gate")
    assert record_legal_consent(1001, "2026-08-26", "telegram-channel-gate")
    assert get_legal_consent(1001) == {
        "version": "2026-08-26",
        "source": "telegram-channel-gate",
        "accepted_at": get_legal_consent(1001)["accepted_at"],
    }
    with connection.get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM legal_consents").fetchone()[0] == 1
