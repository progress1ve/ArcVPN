from database import connection
from database.migrations import run_migrations
from database.db_recurring import (
    claim_due_recurring_cycles, disable_recurring_methods,
    get_active_recurring_method, save_recurring_method,
)


def test_due_queue_and_method_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, "DB_PATH", tmp_path / "billing.db")
    run_migrations()
    with connection.get_db() as db:
        tariff = db.execute("SELECT id FROM tariffs LIMIT 1").fetchone()[0]
        for uid in (101, 102):
            db.execute("INSERT INTO users(id,telegram_id) VALUES(?,?)", (uid, uid))
            db.execute("""INSERT INTO vpn_keys(id,user_id,tariff_id,expires_at)
                VALUES(?,?,?,datetime('now','+2 hours'))""", (uid, uid, tariff))
    for uid, method in ((101, "bank_card"), (102, "sbp")):
        save_recurring_method(uid, str(uid), method, vpn_key_id=uid, amount_cents=39900)
    first = claim_due_recurring_cycles(limit=1)
    assert [row["user_id"] for row in first] == [101]
    second = claim_due_recurring_cycles(limit=1, include_sbp=True)
    assert [row["user_id"] for row in second] == [102]
    assert not claim_due_recurring_cycles(include_sbp=True)
    with connection.get_db() as db:
        db.execute("UPDATE vpn_keys SET expires_at='2030-11-18 18:00:00' WHERE id=101")
    assert get_active_recurring_method(101)["next_charge_at"] == "2030-11-17T18:00:00Z"
    for uid in (101, 102):
        assert disable_recurring_methods(uid) == 1
        assert get_active_recurring_method(uid) is None
