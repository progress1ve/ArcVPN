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
          paid_at TEXT, yookassa_payment_id TEXT, amount_cents INTEGER
        );
        CREATE TABLE service_expenses (
          id INTEGER PRIMARY KEY, title TEXT, category TEXT, amount_cents INTEGER,
          incurred_on TEXT, recurring_monthly INTEGER, note TEXT, created_at TEXT
        );
        INSERT INTO payments VALUES
          (1, 'yookassa', 'paid', 120, '2026-06-15 10:00:00', 'yk-1', 40000),
          (2, 'trial', 'paid', 30, '2026-09-01 10:00:00', 'trial-1', 99900);
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
        "month_revenue_rub": 100.0,
        "month_expenses_rub": 50.0,
        "month_net_rub": 50.0,
    }
    assert payload["monthly"][-1]["month"] == "2026-09"
