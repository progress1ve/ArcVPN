import asyncio
import sqlite3

from database import connection
from database.db_payments import grant_referral_bonus_once


def _prepare_db(tmp_path, monkeypatch, *, friend_key=True):
    path = tmp_path / "referral.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, referred_by INTEGER);
        CREATE TABLE vpn_keys (
            id INTEGER PRIMARY KEY, user_id INTEGER, expires_at TEXT,
            panel_disabled_at TEXT
        );
        CREATE TABLE referral_stats (
            id INTEGER PRIMARY KEY, referrer_id INTEGER, referral_id INTEGER,
            level INTEGER, total_payments_count INTEGER DEFAULT 0,
            total_reward_cents INTEGER DEFAULT 0,
            total_reward_days INTEGER DEFAULT 0,
            bonus_trial_granted INTEGER DEFAULT 0,
            bonus_purchase_granted INTEGER DEFAULT 0,
            UNIQUE(referrer_id, referral_id, level)
        );
        INSERT INTO users VALUES (1, NULL), (2, 1);
        INSERT INTO vpn_keys VALUES (11, 1, '2030-01-01 00:00:00', NULL);
    """)
    if friend_key:
        conn.execute("INSERT INTO vpn_keys VALUES (22, 2, '2030-01-01 00:00:00', NULL)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(connection, "DB_PATH", path)


def _state():
    with connection.get_db() as conn:
        expiries = dict(conn.execute("SELECT user_id, expires_at FROM vpn_keys"))
        stats = conn.execute(
            "SELECT total_reward_days, bonus_trial_granted, bonus_purchase_granted FROM referral_stats"
        ).fetchone()
    return expiries, tuple(stats) if stats else None


def test_referral_bonus_extends_keys_and_ledger_exactly_once(tmp_path, monkeypatch):
    _prepare_db(tmp_path, monkeypatch)
    assert grant_referral_bonus_once(1, 2, "trial", 5)
    assert grant_referral_bonus_once(1, 2, "purchase", 15)
    assert not grant_referral_bonus_once(1, 2, "trial", 5)
    assert not grant_referral_bonus_once(1, 2, "purchase", 15)
    expiries, stats = _state()
    assert expiries == {1: "2030-01-21 00:00:00", 2: "2030-01-16 00:00:00"}
    assert stats == (20, 1, 1)


def test_referral_bonus_does_not_record_without_recipient_key(tmp_path, monkeypatch):
    _prepare_db(tmp_path, monkeypatch, friend_key=False)
    assert not grant_referral_bonus_once(1, 2, "purchase", 15)
    expiries, stats = _state()
    assert expiries == {1: "2030-01-01 00:00:00"}
    assert stats is None


def test_applied_payment_replay_recovers_purchase_once(monkeypatch):
    from bot.services import billing

    order = {
        "status": "paid", "fulfillment_status": "applied",
        "operation_type": "renew", "amount_cents": 14500, "user_id": 2,
    }
    calls = []

    async def reward(user_id):
        calls.append(user_id)

    monkeypatch.setattr(billing, "find_order_by_order_id", lambda _id: order)
    monkeypatch.setattr(billing, "process_referral_reward", reward)
    result = asyncio.run(billing.apply_paid_order("order"))
    assert result[0] is True
    assert calls == [2]


def test_connection_evidence_uses_vpn_traffic_not_webapp_import():
    from bot.services.scheduler import _has_first_connection_evidence

    assert not _has_first_connection_evidence({"imported_at": "now"})
    assert _has_first_connection_evidence({"_online_devices": 1})
    assert _has_first_connection_evidence({"_new_traffic_used": 700})
    assert not _has_first_connection_evidence({"_new_traffic_used": 700, "connect_notified": 1})
