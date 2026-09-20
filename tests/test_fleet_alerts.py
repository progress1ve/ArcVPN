import sqlite3

from database.migrations import migration_63
from monitoring.fleet_alerts import Observation, classify, format_moscow_time, should_monitor, update_state


def state_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    migration_63(conn)
    return conn


def test_panel_disconnect_is_server_down_even_when_external_probe_works():
    result = classify(False, {"ok": False, "ports": [{"port": 443, "ok": False}]},
                      {"completed": 3, "success": 3})
    assert result.status == "server_down"
    assert result.details["failed_ports"] == [443]


def test_external_success_overrides_control_plane_tcp_failure():
    result = classify(True, {"ok": False, "ports": [{"port": 2443, "ok": False}]},
                      {"completed": 3, "success": 3})
    assert result.status == "healthy"


def test_failed_direct_probe_with_incomplete_external_evidence_is_unknown():
    result = classify(True, {"ok": False, "ports": [{"port": 2443, "ok": False}]},
                      {"completed": 1, "success": 0})
    assert result.status == "unknown"


def test_retired_and_bridge_nodes_are_not_monitored():
    for name in ("ArcVPN Finland", "ArcVPN Finland LTE", "ArcVPN Albania WCloud", "ArcVPN Moscow Bridge"):
        assert not should_monitor({"name": name, "isDisabled": False})
    assert should_monitor({"name": "ArcVPN Germany 1chost", "isDisabled": False})


def test_incident_time_is_rendered_in_moscow_timezone():
    assert format_moscow_time("2026-09-20 16:11:10") == "20.09.2026 19:11 МСК"


def test_healthy_locally_but_unreachable_from_russia_is_possible_block():
    result = classify(True, {"ok": True, "ports": [{"port": 443, "ok": True}]},
                      {"completed": 3, "success": 0})
    assert result.status == "possible_ip_block"


def test_incomplete_external_provider_is_unknown_not_outage():
    result = classify(True, {"ok": True, "ports": [{"port": 443, "ok": True}]},
                      {"completed": 1, "success": 0})
    assert result.status == "unknown"


def test_alert_is_emitted_once_after_three_failures():
    conn = state_db()
    down = Observation("server_down", {"failed_ports": [443], "external": {}})
    assert update_state(conn, "node-1", "Node", down, "2026-09-20 10:00:00") is None
    assert update_state(conn, "node-1", "Node", down, "2026-09-20 10:05:00") is None
    event = update_state(conn, "node-1", "Node", down, "2026-09-20 10:10:00")
    assert event["type"] == "alert"
    assert update_state(conn, "node-1", "Node", down, "2026-09-20 10:15:00") is None


def test_recovery_requires_two_successes_and_is_emitted_once():
    conn = state_db()
    down = Observation("possible_ip_block", {"external": {"completed": 3, "success": 0}})
    for minute in (0, 5, 10):
        update_state(conn, "node-1", "Node", down, f"2026-09-20 10:{minute:02d}:00")
    healthy = Observation("healthy", {"external": {"completed": 3, "success": 2}})
    assert update_state(conn, "node-1", "Node", healthy, "2026-09-20 10:15:00") is None
    event = update_state(conn, "node-1", "Node", healthy, "2026-09-20 10:20:00")
    assert event["type"] == "recovery"
    assert event["previous_status"] == "possible_ip_block"
    assert update_state(conn, "node-1", "Node", healthy, "2026-09-20 10:25:00") is None


def test_unknown_does_not_advance_recovery_or_clear_incident():
    conn = state_db()
    down = Observation("server_down", {"failed_ports": [443]})
    for minute in (0, 5, 10):
        update_state(conn, "node-1", "Node", down, f"2026-09-20 10:{minute:02d}:00")
    update_state(conn, "node-1", "Node", Observation("unknown", {}), "2026-09-20 10:15:00")
    row = conn.execute("SELECT * FROM fleet_alert_state WHERE node_key='node-1'").fetchone()
    assert row["alert_sent"] == 1
    assert row["status"] == "server_down"
