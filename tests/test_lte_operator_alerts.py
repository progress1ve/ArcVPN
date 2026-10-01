import sqlite3

from database.migrations import migration_69
from monitoring.lte_operator_alerts import Attempt, classify_batch, record_batch


def _attempt(target_ok, allowed=True, blocked=False, kind="client_tunnel"):
    return Attempt("t2", "/api-fin", kind, "test-provider", "Москва",
                   allowed, blocked, target_ok)


def test_only_completed_real_tunnel_has_a_verdict():
    assert classify_batch([_attempt(None)]) == "unknown"
    assert classify_batch([_attempt(False, kind="tcp")]) == "unknown"
    assert classify_batch([_attempt(False, blocked=True)]) == "failed"
    assert classify_batch([_attempt(False)]) == "failed"
    assert classify_batch([_attempt(True), _attempt(False), _attempt(True)]) == "ok"


def test_three_failed_checks_alert_once_and_two_good_checks_recover():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    migration_69(conn)
    failure = [_attempt(False)]
    success = [_attempt(True)]
    first = record_batch(conn, "batch-1", "203.0.113.9", failure)
    assert first is None
    assert record_batch(conn, "batch-1", "203.0.113.9", failure) is None
    assert record_batch(conn, "batch-2", "203.0.113.9", failure) is None
    alert = record_batch(conn, "batch-3", "203.0.113.9", failure)
    assert alert and alert["type"] == "alert"
    assert record_batch(conn, "batch-4", "203.0.113.9", success) is None
    recovered = record_batch(conn, "batch-5", "203.0.113.9", success)
    assert recovered and recovered["type"] == "recovery"
    assert conn.execute("SELECT COUNT(*) FROM lte_operator_probe_results").fetchone()[0] == 5


def test_unknown_batch_does_not_change_alert_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    migration_69(conn)
    for index in range(3):
        record_batch(conn, f"batch-{index}", "203.0.113.9", [_attempt(False)])
    assert record_batch(conn, "batch-unknown", "203.0.113.9", [_attempt(None)]) is None
    row = conn.execute("SELECT alert_sent,consecutive_failures FROM lte_operator_alert_state").fetchone()
    assert tuple(row) == (1, 3)
