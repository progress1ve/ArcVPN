import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from monitoring.compare_node_quality import build_report


SCHEMA = """
CREATE TABLE server_health_samples (
  host TEXT, sampled_at TEXT, source TEXT, latency_ms REAL,
  cpu_steal_pct REAL, packet_loss_pct REAL, jitter_ms REAL,
  dns_ms REAL, https_ms REAL, download_mbps REAL
)
"""


def _database(directory, rows):
    path = Path(directory) / "health.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(SCHEMA)
        conn.executemany(
            "INSERT INTO server_health_samples VALUES (?,?,?,?,?,?,?,?,?,?)", rows,
        )
        conn.commit()
    return path


class CompareNodeQualityTests(unittest.TestCase):
    def test_missing_required_metrics_fail_closed(self):
        rows = [
            ("node", "2099-01-01 18:00:00", "agent", 20, None, None, None, 10, 20, None)
            for _ in range(6)
        ]
        with tempfile.TemporaryDirectory() as directory:
            report = build_report(_database(directory, rows), 1)["nodes"]["node"]
        self.assertFalse(report["canary_ready"])
        self.assertIn("packet_loss_pct.p95=missing", report["gate_failures"])

    def test_report_includes_latency_and_evening_window(self):
        rows = [
            ("node", "2099-01-01 18:00:00", "agent", 20 + index, 1, 0, 2, 10, 20, 150)
            for index in range(6)
        ]
        with tempfile.TemporaryDirectory() as directory:
            report = build_report(_database(directory, rows), 1)["nodes"]["node"]
        self.assertEqual(report["metrics"]["latency_ms"]["p50"], 22.5)
        self.assertEqual(report["evening_utc"]["samples"], 6)
        self.assertTrue(report["canary_ready"])


if __name__ == "__main__":
    unittest.main()
