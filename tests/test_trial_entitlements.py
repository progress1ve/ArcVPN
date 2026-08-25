import sqlite3
from contextlib import contextmanager

from database import db_trials


def _connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, used_trial INTEGER DEFAULT 0);
        CREATE TABLE tariffs (id INTEGER PRIMARY KEY, name TEXT, is_active INTEGER, display_order INTEGER);
        CREATE TABLE trial_entitlements (
            user_id INTEGER PRIMARY KEY, tariff_id INTEGER, status TEXT DEFAULT 'provisioning',
            vpn_key_id INTEGER, attempt_count INTEGER DEFAULT 1, last_error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            activated_at TEXT
        );
        INSERT INTO users(id) VALUES (1);
        INSERT INTO tariffs VALUES (10, 'Стандарт', 1, 1);
    """)
    return conn


def test_trial_claim_is_idempotent_and_marks_used_only_after_activation(monkeypatch):
    conn = _connection()

    @contextmanager
    def fake_db():
        yield conn
        conn.commit()

    monkeypatch.setattr(db_trials, "get_db", fake_db)
    first = db_trials.acquire_trial_entitlement(1, 10)
    second = db_trials.acquire_trial_entitlement(1, 10)

    assert first["acquired"] is True
    assert second["acquired"] is False
    assert conn.execute("SELECT used_trial FROM users WHERE id=1").fetchone()[0] == 0
    assert db_trials.activate_trial_entitlement(1, 42) is True
    assert db_trials.activate_trial_entitlement(1, 99) is False
    row = conn.execute("SELECT status, vpn_key_id FROM trial_entitlements").fetchone()
    assert tuple(row) == ("active", 42)
    assert conn.execute("SELECT used_trial FROM users WHERE id=1").fetchone()[0] == 1


def test_failed_trial_can_be_retried(monkeypatch):
    conn = _connection()

    @contextmanager
    def fake_db():
        yield conn
        conn.commit()

    monkeypatch.setattr(db_trials, "get_db", fake_db)
    db_trials.acquire_trial_entitlement(1, 10)
    assert db_trials.fail_trial_entitlement(1, "offline") is True
    retry = db_trials.acquire_trial_entitlement(1, 10)
    assert retry["acquired"] is True
    assert retry["status"] == "provisioning"
    assert retry["attempt_count"] == 2


def test_standard_trial_tariff_falls_back_by_name(monkeypatch):
    conn = _connection()

    @contextmanager
    def fake_db():
        yield conn

    monkeypatch.setattr(db_trials, "get_db", fake_db)
    monkeypatch.setattr(db_trials, "get_trial_tariff_id", lambda: None)
    assert db_trials.get_standard_trial_tariff()["id"] == 10
