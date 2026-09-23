"""A personal trial offer must not leak to paid users or multiple checkouts."""

import sqlite3
from contextlib import contextmanager

import database.db_trial_winback as offer
from database.migrations import migration_66


def test_offer_is_bound_to_one_trial_user_and_one_order(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE TABLE trial_entitlements (user_id INTEGER PRIMARY KEY);
        CREATE TABLE payments (
            user_id INTEGER, order_id TEXT PRIMARY KEY, status TEXT,
            payment_type TEXT, operation_type TEXT, offer_code TEXT, discount_rub INTEGER
        );
        INSERT INTO users(id) VALUES (1), (2);
        INSERT INTO trial_entitlements(user_id) VALUES (1);
        INSERT INTO payments(user_id,order_id,status) VALUES (1,'order-1','pending'),(1,'order-2','pending');
    """)
    migration_66(conn)
    conn.execute("INSERT INTO trial_winback_offers(user_id,sent_at) VALUES (1,CURRENT_TIMESTAMP)")

    @contextmanager
    def fake_db():
        yield conn
        conn.commit()

    monkeypatch.setattr(offer, "get_db", fake_db)
    tariff = {"period_months": 3}
    assert offer.offer_discount(1, tariff)
    assert not offer.offer_discount(2, tariff)
    assert not offer.offer_discount(1, {"period_months": 1})
    assert not offer.offer_discount(1, tariff, custom=True)
    assert offer.claim_offer(1, "order-1", 60)
    assert not offer.claim_offer(1, "order-2", 60)
    assert not offer.offer_discount(1, tariff)
    assert tuple(conn.execute("SELECT offer_code,discount_rub FROM payments WHERE order_id='order-1'").fetchone()) == (offer.OFFER_KEY, 60)
    offer.release_offer(1, "order-1")
    assert offer.offer_discount(1, tariff)
    assert conn.execute("SELECT status FROM payments WHERE order_id='order-1'").fetchone()[0] == "canceled"
    conn.execute("INSERT INTO payments(user_id,order_id,status) VALUES (1,'paid-1','succeeded')")
    assert not offer.offer_discount(1, tariff)
