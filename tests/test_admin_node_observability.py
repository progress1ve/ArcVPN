import sqlite3
import json

import subscription_api as api
from database.migrations import migration_69, migration_70


def test_provider_metadata_requires_permission(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: False)
    assert api.app.test_client().get("/api/admin/nodes/operator-network-status").status_code == 403


def test_diagnostics_show_safe_port_facts_and_skip_empty_results(tmp_path, monkeypatch):
    path = tmp_path / "events.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE node_diagnostic_runs(id INTEGER PRIMARY KEY,host TEXT,ok INTEGER,created_at TEXT,result_json TEXT)")
        conn.execute("CREATE TABLE admin_audit_events(id INTEGER PRIMARY KEY,target_id TEXT,target_type TEXT,action TEXT,outcome TEXT,created_at TEXT)")
        for result in ({"ports": []}, {"ports": [{"port": 443, "ok": True, "latency_p50_ms": 21}], "secret": "private-marker"}):
            conn.execute("INSERT INTO node_diagnostic_runs(host,ok,created_at,result_json) VALUES(?,?,?,?)",
                         ("203.0.113.9", 1, "2026-10-01 12:00:00", json.dumps(result)))
    def db():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(api, "get_db", db)
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    response = api.app.test_client().get("/api/admin/nodes/events?host=203.0.113.9")
    assert response.status_code == 200
    events = response.get_json()["events"]
    assert len(events) == 1
    assert "TCP 443" in events[0]["summary"]
    assert "21" in events[0]["summary"]
    assert "private-marker" not in response.get_data(as_text=True)


def test_node_registry_exposes_roles_without_credential_alias(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    response = api.app.test_client().get("/api/admin/nodes/registry")
    assert response.status_code == 200
    assert any(node["role"] == "vpn-node" for node in response.get_json()["nodes"])
    assert "credential_alias" not in response.get_data(as_text=True)


def test_node_capacity_requires_permission(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: False)
    response = api.app.test_client().get("/api/admin/nodes/capacity?host=203.0.113.9")
    assert response.status_code == 403


def test_manual_lte_run_requires_role_and_same_origin(monkeypatch):
    client = api.app.test_client()
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: False)
    denied = client.post("/api/admin/nodes/operator-probes/run",
                         headers={"Origin": "https://arccnet.space"})
    assert denied.status_code == 403
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    wrong_origin = client.post("/api/admin/nodes/operator-probes/run",
                               headers={"Origin": "https://other.example"})
    assert wrong_origin.status_code == 403


def test_manual_lte_run_respects_cooldown(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    monkeypatch.setattr(api.os, "stat", lambda path: type("Stat", (), {"st_mtime": api.time.time()})())
    response = api.app.test_client().post("/api/admin/nodes/operator-probes/run",
        headers={"Origin": "https://arccnet.space"})
    assert response.status_code == 429


def test_manual_lte_run_starts_only_fixed_worker(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    monkeypatch.setattr(api.os, "stat", lambda path: type("Stat", (), {"st_mtime": 0})())
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return type("Completed", (), {"returncode": 3 if len(calls) == 1 else 0})()

    monkeypatch.setattr(api.subprocess, "run", fake_run)
    monkeypatch.setattr(api, "_append_admin_audit_best_effort", lambda *args, **kwargs: None)
    response = api.app.test_client().post("/api/admin/nodes/operator-probes/run",
        headers={"Origin": "https://arccnet.space"})
    assert response.status_code == 202
    assert calls[1] == ["/usr/bin/systemctl", "start", "--no-block", "arcvpn-lte-operator.service"]


def test_node_capacity_does_not_invent_verified_bandwidth(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    with sqlite3.connect(path) as conn:
        migration_69(conn)
        conn.execute("""CREATE TABLE server_health_samples (
            host TEXT,source TEXT,sampled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_pct REAL,mem_pct REAL,net_rx_bps REAL,net_tx_bps REAL)""")
        conn.executemany("""INSERT INTO server_health_samples
            (host,source,cpu_pct,mem_pct,net_rx_bps,net_tx_bps)
            VALUES ('203.0.113.9','agent',20,40,10000000,8000000)""", [()] * 80)
    def db():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(api, "get_db", db)
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    response = api.app.test_client().get("/api/admin/nodes/capacity?host=203.0.113.9&range=24h")
    assert response.status_code == 200
    result = response.get_json()
    assert result["network"]["rx"]["observed_p95_mbps"] == 10
    assert result["network"]["rx"]["confirmed_mbps"] is None
    assert result["network"]["rx"]["headroom_pct"] is None


def test_ssh_preflight_rejects_untrusted_origin_and_private_targets(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    client = api.app.test_client()
    payload = {"host": "127.0.0.1", "username": "root", "password": "placeholder",
               "expected_fingerprint": "SHA256:" + "A" * 43}
    bad_origin = client.post("/api/admin/nodes/preflight", json=payload,
                             headers={"Origin": "https://example.net"})
    assert bad_origin.status_code == 403
    private_target = client.post("/api/admin/nodes/preflight", json=payload,
                                 headers={"Origin": "https://arccnet.space"})
    assert private_target.status_code == 400


def test_ssh_preflight_requires_pinned_fingerprint(monkeypatch):
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    response = api.app.test_client().post("/api/admin/nodes/preflight",
        json={"host": "8.8.8.8", "username": "root", "password": "placeholder"},
        headers={"Origin": "https://arccnet.space"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "ssh_fingerprint_required"


def test_availability_api_preserves_unknown_and_failures(tmp_path, monkeypatch):
    path = tmp_path / "availability.sqlite3"
    with sqlite3.connect(path) as conn:
        migration_70(conn)
        conn.execute("""INSERT INTO node_availability_samples(node_host,status)
            VALUES ('203.0.113.9','unknown'),('203.0.113.9','server_down')""")
    def db():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(api, "get_db", db)
    monkeypatch.setattr(api, "_admin_authorized", lambda permission: True)
    response = api.app.test_client().get("/api/admin/nodes/availability?host=203.0.113.9")
    assert response.status_code == 200
    assert [row["status"] for row in response.get_json()["samples"]] == ["unknown", "server_down"]
