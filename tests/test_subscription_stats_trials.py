import sqlite3
from contextlib import contextmanager

from database import db_statistics


def test_subscription_stats_count_only_active_linked_trials(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE vpn_keys (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE trial_entitlements (
            user_id INTEGER PRIMARY KEY,
            vpn_key_id INTEGER,
            status TEXT NOT NULL
        );
        INSERT INTO vpn_keys VALUES
            (1,1,datetime('now','-2 days'),datetime('now','+5 days')),
            (2,2,datetime('now','-2 days'),datetime('now','+5 days')),
            (3,3,datetime('now','-2 days'),datetime('now','-1 day')),
            (4,4,datetime('now','-2 days'),datetime('now','+5 days'));
        INSERT INTO trial_entitlements VALUES
            (1,1,'active'),
            (2,2,'completed'),
            (3,3,'active');
    """)

    @contextmanager
    def fake_db():
        yield conn

    monkeypatch.setattr(db_statistics, "get_db", fake_db)

    stats = db_statistics.get_subscriptions_stats()

    assert stats["active"] == 3
    assert stats["trial"] == 1
    assert stats["paid"] == 2
