import sqlite3

from database.db_user_cleanup import cleanup_candidates


def test_cleanup_candidates_excludes_paid_active_recent_and_admin_users():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, telegram_id INTEGER, username TEXT,
            created_at TEXT, used_trial INTEGER
        );
        CREATE TABLE payments (user_id INTEGER, status TEXT, payment_type TEXT);
        CREATE TABLE vpn_keys (user_id INTEGER, expires_at TEXT);
        INSERT INTO users VALUES (1, 101, 'eligible', '2024-01-01', 1);
        INSERT INTO users VALUES (2, 102, 'paid', '2024-01-01', 0);
        INSERT INTO users VALUES (3, 103, 'active_key', '2024-01-01', 0);
        INSERT INTO users VALUES (4, 104, 'recent', '2026-08-24', 0);
        INSERT INTO users VALUES (5, 105, 'admin', '2024-01-01', 0);
        INSERT INTO payments VALUES (2, 'paid', 'stars');
        INSERT INTO vpn_keys VALUES (3, '2099-01-01');
    """)

    rows = cleanup_candidates(
        conn, created_before="2026-01-01", excluded_telegram_ids=[105]
    )
    assert [row["telegram_id"] for row in rows] == [101]
