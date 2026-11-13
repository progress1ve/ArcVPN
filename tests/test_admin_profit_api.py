import sqlite3
from contextlib import contextmanager

import subscription_api as api


def test_profit_recognizes_subscription_revenue_by_month(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE payments (
          id INTEGER PRIMARY KEY, payment_type TEXT, status TEXT, period_days INTEGER,
          paid_at TEXT, yookassa_payment_id TEXT, amount_cents INTEGER,
          tariff_id INTEGER, operation_type TEXT
        );
        CREATE TABLE tariffs (id INTEGER PRIMARY KEY, duration_days INTEGER);
        INSERT INTO tariffs VALUES (1,90);
        CREATE TABLE service_expenses (
          id INTEGER PRIMARY KEY, title TEXT, category TEXT, amount_cents INTEGER,
          incurred_on TEXT, recurring_monthly INTEGER, note TEXT, created_at TEXT
        );
        INSERT INTO payments VALUES
          (1, 'yookassa', 'paid', 120, '2026-06-15 10:00:00', 'yk-1', 40000, NULL, 'new'),
          (2, 'trial', 'paid', 30, '2026-09-01 10:00:00', 'trial-1', 99900, NULL, 'trial_start'),
          (3, 'cards', 'paid', NULL, '2026-08-31 21:00:00', NULL, 39900, 1, 'renew'),
          (4, 'cards', 'pending', 90, NULL, NULL, 39900, 1, 'renew'),
          (5, 'cards', 'paid', NULL, '2026-09-02 10:00:00', 'yk-5', 10000, NULL, 'topup');
        INSERT INTO service_expenses VALUES
          (1, 'Хостинг', 'hosting', 3000, '2026-07-01', 1, NULL, CURRENT_TIMESTAMP),
          (2, 'Реклама', 'advertising', 2000, '2026-09-05', 0, NULL, CURRENT_TIMESTAMP);
        """
    )

    @contextmanager
    def db():
        yield connection
        connection.commit()

    monkeypatch.setattr(api, "get_db", db)
    monkeypatch.setattr(api, "_admin_access_context", lambda: {"actor_id": "qa", "role": "owner"})
    monkeypatch.setitem(api.app.config, "TESTING", True)

    payload = api.app.test_client().get("/api/admin/expenses?month=2026-09").get_json()

    assert payload["summary"] == {
        "month": "2026-09",
        "month_revenue_rub": 233.0,
        "month_expenses_rub": 50.0,
        "month_net_rub": 183.0,
    }
    assert payload["monthly"][-1]["month"] == "2026-09"
