import sqlite3
from contextlib import contextmanager

import pytest

from database import db_campaigns, db_promocodes
from database.migrations import migration_56

try:
    import subscription_api as api
except Exception as exc:  # pragma: no cover
    api = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@contextmanager
def _shared_connection(connection):
    yield connection
    connection.commit()


@pytest.fixture
def campaign_db(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
        CREATE TABLE users(id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE);
        CREATE TABLE payments(
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, amount_cents INTEGER,
            status TEXT, FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE promocodes(
            id INTEGER PRIMARY KEY, code TEXT UNIQUE, discount_rub INTEGER NOT NULL,
            max_uses INTEGER NOT NULL, expires_at TEXT NOT NULL, created_at TEXT,
            discount_type TEXT NOT NULL DEFAULT 'fixed', discount_percent INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE promocode_usage(
            promocode_id INTEGER NOT NULL, user_id INTEGER NOT NULL, used_at TEXT,
            UNIQUE(promocode_id,user_id)
        );
    """)
    migration_56(connection)
    monkeypatch.setattr(db_campaigns, "get_db", lambda: _shared_connection(connection))
    monkeypatch.setattr(db_promocodes, "get_db", lambda: _shared_connection(connection))
    yield connection
    connection.close()


def test_migration_56_is_idempotent_and_preserves_existing_promocodes(campaign_db):
    campaign_db.execute("""INSERT INTO promocodes
        (id,code,discount_rub,max_uses,expires_at) VALUES(1,'OLD',10,5,'2099-01-01')""")

    migration_56(campaign_db)

    row = campaign_db.execute("SELECT code,is_active FROM promocodes WHERE id=1").fetchone()
    assert dict(row) == {"code": "OLD", "is_active": 1}


def test_campaign_attribution_is_first_touch_and_stats_compare_sources(campaign_db):
    campaign_db.executemany("INSERT INTO users(id,telegram_id) VALUES(?,?)", [(1, 101), (2, 102)])
    first = db_campaigns.create_campaign("Search", code="search_one")
    second = db_campaigns.create_campaign("Influencer", code="creator_two")

    assert db_campaigns.attribute_user_to_campaign(1, "search_one")[0] is True
    assert db_campaigns.attribute_user_to_campaign(1, "creator_two")[0] is False
    assert db_campaigns.attribute_user_to_campaign(2, "creator_two")[0] is True
    campaign_db.executemany(
        "INSERT INTO payments(id,user_id,amount_cents,status) VALUES(?,?,?,?)",
        [(1, 1, 14500, "paid"), (2, 1, 39900, "paid"), (3, 2, 14500, "pending")],
    )

    stats = {item["id"]: item for item in db_campaigns.list_campaign_stats()}

    assert stats[first["id"]]["arrivals"] == 1
    assert stats[first["id"]]["paying_users"] == 1
    assert stats[first["id"]]["paid_orders"] == 2
    assert stats[first["id"]]["repeat_paid_orders"] == 1
    assert stats[first["id"]]["conversion_percent"] == 100.0
    assert stats[second["id"]]["paying_users"] == 0


def test_disabled_campaign_does_not_accept_new_attribution(campaign_db):
    campaign_db.execute("INSERT INTO users(id,telegram_id) VALUES(1,101)")
    campaign = db_campaigns.create_campaign("Paused", code="paused_one")
    db_campaigns.update_campaign(campaign["id"], is_active=False)

    attributed, _ = db_campaigns.attribute_user_to_campaign(1, "paused_one")

    assert attributed is False


def test_campaign_bonus_reservation_is_retryable_but_applies_once(campaign_db):
    campaign_db.execute("INSERT INTO users(id,telegram_id) VALUES(1,101)")
    campaign = db_campaigns.create_campaign(
        "Bonus", code="bonus_one", entry_bonus_days=3, payment_bonus_days=7,
    )
    db_campaigns.attribute_user_to_campaign(1, "bonus_one")

    first = db_campaigns.reserve_campaign_bonus(1, "entry")
    db_campaigns.finish_campaign_bonus(1, "entry", False, "no_active_key")
    retry = db_campaigns.reserve_campaign_bonus(1, "entry")
    db_campaigns.finish_campaign_bonus(1, "entry", True)

    assert first["campaign_id"] == campaign["id"]
    assert first["days"] == 3
    assert retry["status"] == "failed"
    assert db_campaigns.reserve_campaign_bonus(1, "entry") is None
    row = campaign_db.execute("""SELECT status,attempt_count,days FROM campaign_bonus_grants
        WHERE user_id=1 AND kind='entry'""").fetchone()
    assert dict(row) == {"status": "applied", "attempt_count": 2, "days": 3}


def test_disabled_promocode_is_rejected_without_recording_usage(campaign_db):
    campaign_db.execute("INSERT INTO users(id,telegram_id) VALUES(1,101)")
    promo_id = db_promocodes.create_promocode("OFF10", 10, 5, 30)
    db_promocodes.update_promocode(promo_id, is_active=False)

    valid, error, _ = db_promocodes.is_promocode_valid("OFF10", 1)

    assert valid is False
    assert "отключен" in error
    assert campaign_db.execute("SELECT COUNT(*) FROM promocode_usage").fetchone()[0] == 0


@pytest.mark.skipif(api is None, reason=f"subscription_api unavailable: {IMPORT_ERROR}")
def test_campaign_admin_api_returns_deep_links_and_aggregates(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda _permission: True)
    monkeypatch.setattr(api, "_get_bot_username", lambda: "arcvpn_test_bot")
    monkeypatch.setattr(db_campaigns, "list_campaign_stats", lambda: [{
        "id": 7, "name": "Search", "code": "search", "arrivals": 10,
        "paying_users": 3, "conversion_percent": 30.0,
    }])

    response = api.app.test_client().get("/api/admin/campaigns")

    assert response.status_code == 200
    assert response.get_json()["campaigns"][0]["link"] == (
        "https://t.me/arcvpn_test_bot?start=ad_search"
    )
