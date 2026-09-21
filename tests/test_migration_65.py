import sqlite3

from database.migrations import migration_65


def _database():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE TABLE tariffs (id INTEGER PRIMARY KEY);
        CREATE TABLE vpn_keys (id INTEGER PRIMARY KEY);
        CREATE TABLE trial_entitlements (
            user_id INTEGER PRIMARY KEY, tariff_id INTEGER NOT NULL,
            status TEXT NOT NULL, vpn_key_id INTEGER, attempt_count INTEGER,
            last_error TEXT, created_at TEXT, updated_at TEXT, activated_at TEXT
        );
        CREATE TABLE payments (
            user_id INTEGER, status TEXT, fulfillment_status TEXT,
            operation_type TEXT, payment_type TEXT, offer_code TEXT,
            addons_applied_at TEXT
        );
        INSERT INTO users VALUES (1),(2),(3),(4);
        INSERT INTO tariffs VALUES (10);
        INSERT INTO trial_entitlements
            (user_id,tariff_id,status,attempt_count,created_at,updated_at)
        VALUES
            (1,10,'active',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
            (2,10,'active',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
            (3,10,'active',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
            (4,10,'active',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);
        INSERT INTO payments VALUES
            (1,'succeeded','manual_review','renew','yookassa_qr',NULL,CURRENT_TIMESTAMP),
            (2,'succeeded','applied','trial_start','yookassa_qr','email_paid_trial',CURRENT_TIMESTAMP),
            (3,'succeeded','pending','new','yookassa_qr',NULL,NULL),
            (4,'succeeded','applied','topup','yookassa_qr',NULL,CURRENT_TIMESTAMP);
    """)
    return conn


def test_migration_completes_only_applied_commercial_subscriptions():
    conn = _database()

    migration_65(conn)

    statuses = {
        row["user_id"]: row["status"]
        for row in conn.execute("SELECT user_id,status FROM trial_entitlements")
    }
    assert statuses == {1: "completed", 2: "active", 3: "active", 4: "active"}


def test_migrated_schema_accepts_completed_but_rejects_unknown_status():
    conn = _database()
    migration_65(conn)

    conn.execute("UPDATE trial_entitlements SET status='completed' WHERE user_id=2")
    try:
        conn.execute("UPDATE trial_entitlements SET status='unknown' WHERE user_id=3")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("trial status CHECK constraint was not preserved")
