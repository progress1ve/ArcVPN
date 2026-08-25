import sqlite3

from database.migrations import migration_55


def _schema() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            price_cents INTEGER NOT NULL DEFAULT 0,
            price_stars INTEGER NOT NULL DEFAULT 0,
            price_rub INTEGER NOT NULL DEFAULT 0,
            external_id INTEGER,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            traffic_limit_gb INTEGER DEFAULT 500,
            group_id INTEGER DEFAULT 1
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            lte_quota_gb INTEGER NOT NULL DEFAULT 20,
            lte_used_bytes INTEGER NOT NULL DEFAULT 0,
            device_limit INTEGER NOT NULL DEFAULT 2,
            traffic_monthly_limit_gb INTEGER NOT NULL DEFAULT 500,
            entitlements_updated_at DATETIME
        );
        INSERT INTO tariffs(name,duration_days,price_cents,price_stars,price_rub,
                            display_order,is_active,traffic_limit_gb,group_id)
        VALUES ('1 месяц',30,0,0,125,10,1,500,1);
        INSERT INTO users(id,telegram_id,lte_quota_gb,lte_used_bytes)
        VALUES (1,1001,20,1234);
    """)
    return conn


def test_product_catalog_is_idempotent_and_preserves_legacy_data():
    conn = _schema()
    migration_55(conn)
    migration_55(conn)

    products = conn.execute("""SELECT product_code, period_months, price_rub,
        traffic_limit_gb, device_limit, lte_quota_gb
        FROM tariffs WHERE product_code IS NOT NULL
        ORDER BY product_code, period_months""").fetchall()
    assert len(products) == 12
    standard_year = next(
        row for row in products
        if row["product_code"] == "standard" and row["period_months"] == 12
    )
    assert dict(standard_year) == {
        "product_code": "standard",
        "period_months": 12,
        "price_rub": 1469,
        "traffic_limit_gb": 1024,
        "device_limit": 3,
        "lte_quota_gb": 45,
    }
    family = next(row for row in products if row["product_code"] == "family")
    assert family["traffic_limit_gb"] == 0
    legacy = conn.execute(
        "SELECT id,is_active FROM tariffs WHERE name='1 месяц'"
    ).fetchone()
    assert legacy["id"] == 1
    assert legacy["is_active"] == 0
    user = conn.execute(
        "SELECT lte_quota_gb,lte_used_bytes,lte_cycle_reset_at FROM users WHERE id=1"
    ).fetchone()
    assert user["lte_quota_gb"] == 20
    assert user["lte_used_bytes"] == 1234
    assert user["lte_cycle_reset_at"] is not None


def test_lte_usage_is_raw_and_cycle_reset_is_independent(tmp_path, monkeypatch):
    from database import connection
    from database.db_webapp import add_lte_usage, refresh_lte_cycle

    db_path = tmp_path / "lte.sqlite"
    monkeypatch.setattr(connection, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            lte_quota_gb INTEGER NOT NULL,
            lte_used_bytes INTEGER NOT NULL,
            lte_cycle_started_at DATETIME,
            lte_cycle_reset_at DATETIME
        );
        INSERT INTO users VALUES (1,1001,45,0,datetime('now'),datetime('now','+30 days'));
    """)
    conn.close()

    usage = add_lte_usage(1001, 1024)
    assert usage["lte_used_bytes"] == 1024
    assert usage["lte_remaining_bytes"] == 45 * 1024**3 - 1024

    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE users SET lte_cycle_reset_at=datetime('now','-1 second')")
    conn.commit()
    conn.close()
    reset = refresh_lte_cycle(1001)
    assert reset["lte_used_bytes"] == 0
    assert reset["lte_remaining_bytes"] == 45 * 1024**3


def test_paid_order_applies_product_entitlements(tmp_path, monkeypatch):
    from database import connection
    from database.db_webapp import apply_payment_entitlements

    db_path = tmp_path / "payment.sqlite"
    monkeypatch.setattr(connection, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, device_limit INTEGER, lte_quota_gb INTEGER,
            lte_used_bytes INTEGER, traffic_monthly_limit_gb INTEGER,
            lte_cycle_started_at DATETIME, lte_cycle_reset_at DATETIME,
            entitlements_updated_at DATETIME
        );
        CREATE TABLE tariffs (
            id INTEGER PRIMARY KEY, device_limit INTEGER, lte_quota_gb INTEGER,
            traffic_limit_gb INTEGER
        );
        CREATE TABLE payments (
            order_id TEXT PRIMARY KEY, user_id INTEGER, tariff_id INTEGER,
            status TEXT, requested_device_limit INTEGER,
            requested_lte_quota_gb INTEGER, addons_applied_at DATETIME
        );
        INSERT INTO users VALUES (1,2,20,999,500,NULL,NULL,NULL);
        INSERT INTO tariffs VALUES (7,10,115,0);
        INSERT INTO payments VALUES ('paid-family',1,7,'paid',NULL,NULL,NULL);
    """)
    conn.close()

    applied = apply_payment_entitlements("paid-family")
    assert applied == {"device_limit": 10, "lte_quota_gb": 115}
    conn = sqlite3.connect(db_path)
    row = conn.execute("""SELECT device_limit,lte_quota_gb,lte_used_bytes,
        traffic_monthly_limit_gb,lte_cycle_reset_at FROM users""").fetchone()
    assert row[:4] == (10, 115, 0, 0)
    assert row[4] is not None
    conn.close()
