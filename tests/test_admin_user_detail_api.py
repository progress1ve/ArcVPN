import sqlite3
from contextlib import contextmanager

import pytest

import subscription_api as api
from database import db_campaigns


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", True)
    monkeypatch.setattr(
        api, "_admin_access_context", lambda: {"actor_id": "qa", "role": "owner"}
    )
    monkeypatch.setattr(api, "_admin_live_presence", lambda: (True, {}))
    return api.app.test_client()


@pytest.fixture
def detail_db(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE users (
          id INTEGER PRIMARY KEY, telegram_id INTEGER NOT NULL, username TEXT,
          first_name TEXT, created_at TEXT, device_limit INTEGER,
          lte_quota_gb REAL, lte_cycle_bonus_gb REAL, lte_used_bytes INTEGER,
          enforce_device_tokens INTEGER, personal_balance INTEGER, referred_by INTEGER
        );
        CREATE TABLE tariffs (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE servers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE vpn_keys (
          id INTEGER PRIMARY KEY, user_id INTEGER, custom_name TEXT, expires_at TEXT,
          created_at TEXT, traffic_used INTEGER, traffic_limit INTEGER,
          online_devices INTEGER, last_online_at TEXT, panel_disabled_at TEXT,
          tariff_id INTEGER, server_id INTEGER
        );
        CREATE TABLE payments (
          id INTEGER PRIMARY KEY, user_id INTEGER, order_id TEXT, payment_type TEXT,
          operation_type TEXT, offer_code TEXT, status TEXT, period_days INTEGER, paid_at TEXT, tariff_id INTEGER,
          yookassa_payment_id TEXT, amount_cents INTEGER, amount_stars INTEGER
        );
        CREATE TABLE user_devices (
          id INTEGER PRIMARY KEY, user_id INTEGER, display_name TEXT, platform TEXT,
          model TEXT, is_active INTEGER, imported_at TEXT, last_seen_at TEXT, revoked_at TEXT
        );
        CREATE TABLE referral_stats (
          id INTEGER PRIMARY KEY, referrer_id INTEGER, referral_id INTEGER, level INTEGER,
          total_reward_days INTEGER
        );
        CREATE TABLE admin_audit_events (
          id INTEGER PRIMARY KEY, action TEXT, outcome TEXT, metadata_json TEXT,
          created_at TEXT, target_type TEXT, target_id TEXT
        );
        CREATE TABLE trial_entitlements (
          user_id INTEGER PRIMARY KEY, tariff_id INTEGER, status TEXT, vpn_key_id INTEGER
        );
        CREATE TABLE lifecycle_events (
          id INTEGER PRIMARY KEY, user_id INTEGER, event_key TEXT, answer TEXT,
          sent_at TEXT, answered_at TEXT
        );
        CREATE TABLE ad_campaigns (
          id INTEGER PRIMARY KEY, name TEXT, code TEXT, entry_bonus_days INTEGER DEFAULT 0,
          payment_bonus_days INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
          created_at TEXT, updated_at TEXT
        );
        CREATE TABLE user_campaign_attribution (
          user_id INTEGER PRIMARY KEY, campaign_id INTEGER, attributed_at TEXT
        );
        CREATE TABLE campaign_bonus_grants (
          id INTEGER PRIMARY KEY, user_id INTEGER, campaign_id INTEGER, kind TEXT,
          days INTEGER, status TEXT, attempt_count INTEGER, last_error TEXT,
          created_at TEXT, updated_at TEXT, applied_at TEXT
        );

        INSERT INTO users VALUES
          (1,700001,'owner','Owner','2026-08-01',2,5,0,0,1,0,NULL),
          (2,700002,'friend_one','Friend One','2026-08-02',2,5,0,0,0,0,1),
          (3,700003,'friend_two','Friend Two','2026-08-03',2,5,0,0,0,0,NULL);
        INSERT INTO referral_stats VALUES
          (1,1,2,1,10),
          (2,1,3,1,7),
          (3,1,3,2,99);
        INSERT INTO tariffs VALUES (1,'Стандарт');
        INSERT INTO servers VALUES (1,'ArcVPN Estonia');
        INSERT INTO payments VALUES
          (1,1,'owner-order','yookassa','new',NULL,'paid',30,'2026-08-05',1,'provider-1',29900,0),
          (2,2,'friend-order','yookassa','trial_start','email_paid_trial','succeeded',7,'2026-08-06',1,'provider-2',1000,0);
        INSERT INTO vpn_keys VALUES
          (10,1,'Primary',datetime('now','+10 days'),'2026-08-01',1024,2048,1,'2026-08-10',NULL,1,1),
          (11,2,'Trial',datetime('now','+5 days'),'2026-08-02',0,2048,0,NULL,NULL,1,1);
        INSERT INTO trial_entitlements VALUES (2,1,'active',11);
        INSERT INTO lifecycle_events VALUES
          (1,1,'trial_day1_rating','service: Не открывался YouTube','2026-08-07','2026-08-07 12:05:00'),
          (2,1,'expired_winback','expensive','2026-08-08','2026-08-08 12:05:00'),
          (3,2,'trial_day1_rating','great','2026-08-09','2026-08-09 12:05:00'),
          (4,1,'trial_day1_rating',NULL,'2026-08-10',NULL);
        INSERT INTO ad_campaigns VALUES (1,'Telegram','telegram_sep',0,0,1,'2026-08-01',NULL);
        INSERT INTO user_campaign_attribution VALUES (2,1,'2026-08-02');
        INSERT INTO user_devices VALUES
          (20,1,'iPhone','ios','iPhone',1,'2026-08-02','2026-08-10',NULL);
        """
    )

    @contextmanager
    def fake_get_db():
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    monkeypatch.setattr(api, "get_db", fake_get_db)
    monkeypatch.setattr(db_campaigns, "get_db", fake_get_db)
    yield connection
    connection.close()


def test_user_detail_exposes_purchases_and_deduplicated_direct_referrals(
    client, detail_db
):
    response = client.get("/api/admin/users/700001")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["payments"][0]["order_id"] == "owner-order"
    assert payload["payments"][0]["amount_rub"] == 299
    assert [item["answer"] for item in payload["lifecycle_answers"]] == [
        "expensive",
        "service: Не открывался YouTube",
    ]
    assert payload["referrals"]["invited_count"] == 2
    assert payload["referrals"]["paid_count"] == 0
    assert payload["referrals"]["earned_days"] == 17
    assert [item["telegram_id"] for item in payload["referrals"]["friends"]] == [
        700003,
        700002,
    ]
    assert payload["referrals"]["friends"][0]["reward_days"] == 7

    trial_response = client.get("/api/admin/users/700002")
    assert trial_response.status_code == 200
    trial_payload = trial_response.get_json()
    assert trial_payload["subscriptions"][0]["is_trial"] == 1
    assert trial_payload["user"]["online_node"] == "ArcVPN Estonia"


def test_referral_network_returns_real_deduplicated_edges(client, detail_db):
    response = client.get("/api/admin/referral-network")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total_users"] == 3
    assert payload["total_referrers"] == 1
    assert {(edge["source"], edge["target"]) for edge in payload["edges"] if edge["type"] == "referral"} == {
        ("user_1", "user_2"),
        ("user_1", "user_3"),
    }
    owner = next(user for user in payload["users"] if user["tg_id"] == 700001)
    assert owner["direct_referrals"] == 2
    assert owner["personal_spent_kopeks"] == 29900
    assert "subscription_url" not in owner
    friend = next(user for user in payload["users"] if user["tg_id"] == 700002)
    assert friend["subscription_status"] == "trial_active"
    assert payload["campaigns"][0]["name"] == "Telegram"
    assert {"source": "campaign_1", "target": "user_2", "type": "campaign"} in payload["edges"]


def test_user_detail_tolerates_database_without_lifecycle_events(client, detail_db):
    detail_db.execute("DROP TABLE lifecycle_events")

    response = client.get("/api/admin/users/700001")

    assert response.status_code == 200
    assert response.get_json()["lifecycle_answers"] == []


def test_admin_operational_registries_use_live_database(client, detail_db):
    payments = client.get("/api/admin/payments?status=paid").get_json()
    assert payments["total"] == 1
    assert payments["items"][0]["order_id"] == "owner-order"
    assert payments["items"][0]["created_at"] == "2026-08-05"

    sales = client.get("/api/admin/sales-stats").get_json()
    assert sales["active_subscriptions"] == 2
    assert {item["operation_type"] for item in sales["payments"]} == {"new", "trial_start"}

    traffic = client.get("/api/admin/traffic?sort_by=total_bytes&sort_desc=true").get_json()
    assert traffic["total"] == 3
    assert traffic["items"][0]["telegram_id"] == 700001
    assert traffic["items"][0]["total_bytes"] == 1024
