import io
import json
import asyncio
import sqlite3
import urllib.error

import pytest

from monitoring.latencylab_client import Client, LatencyLabError
from monitoring.lte_operator_worker import outcome, rows_by_operator
from monitoring import lte_operator_worker as worker
from database.migrations import migration_69


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_multiscan_uses_bearer_and_polls_without_logging_uri():
    requests = []
    replies = [{"ok": True, "req_id": "job-id", "status": "pending"},
               {"ok": True, "status": "done", "result": {"multiscan": True,
                "results": [{"operator": "mts", "ok": True, "latency_ms": 123}]}}]

    def opener(request, timeout):
        requests.append((request, timeout))
        return Response(json.dumps(replies.pop(0)).encode())

    client = Client("ll_test_private", opener=opener, sleep=lambda _: None)
    result = client.vpn_multiscan("vless://private@example.invalid", ["mts"])
    assert rows_by_operator(result)["mts"]["latency_ms"] == 123
    assert requests[0][0].get_header("Authorization") == "Bearer ll_test_private"
    assert requests[0][0].full_url.endswith("/api/lab/vpn-key")
    assert requests[1][0].full_url.endswith("/api/lab/job/job-id")
    assert outcome({"ok": False}) is False
    assert outcome({"status": "pending"}) is None


def test_http_error_redacts_body_and_request():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "private URI", {}, None)

    client = Client("ll_test_private", opener=opener)
    with pytest.raises(LatencyLabError, match="^http_403$"):
        client.vpn_multiscan("vless://private@example.invalid", ["mts"])


def test_worker_records_each_operator_and_never_alerts_on_missing_result(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as conn:
        migration_69(conn)
    monkeypatch.setattr(worker, "DB_PATH", path)
    events = []

    async def capture(items):
        events.extend(items)

    monkeypatch.setattr(worker, "notify", capture)

    class FakeClient:
        def remaining_quota(self):
            return 6

        def operators(self):
            return {"mts", "t2"}

        def control_multiscan(self, target, operators):
            return {"results": [{"operator": "mts", "ok": target == "yandex.ru"}]}

        def vpn_multiscan(self, uri, operators):
            assert uri == "private-se"
            # A concurrent telemetry write must remain possible throughout probes.
            with sqlite3.connect(path, timeout=0) as concurrent:
                concurrent.execute("CREATE TABLE IF NOT EXISTS concurrent_metrics(value INTEGER)")
                concurrent.execute("INSERT INTO concurrent_metrics VALUES(1)")
            return {"results": [{"operator": "mts", "ok": True, "latency_ms": 120}]}

    result = asyncio.run(worker.run(client=FakeClient(), links={p:"private-se" for _,p,_ in worker.NODES}))
    assert result == {"nodes": 1, "online_operators": 2, "transitions": 0}
    assert not events
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM lte_operator_probe_results").fetchone()[0] == 5
        assert conn.execute("SELECT count(*) FROM lte_operator_probe_results WHERE outcome='unknown'").fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM lte_operator_alert_state").fetchone()[0] == 1
        assert {r[0] for r in conn.execute("SELECT DISTINCT target_path FROM lte_operator_probe_results")} == {p for _,p,_ in worker.NODES}


def test_finland_events_are_dropped_before_initializing_telegram():
    # These incomplete events would fail during message rendering if not filtered.
    asyncio.run(worker.notify([
        {"node_host": "151.241.137.174", "type": "alert"},
        {"node_host": "151.241.137.174", "type": "recovery"},
    ]))
