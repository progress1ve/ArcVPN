"""Evidence and deduplicated alerts for restricted mobile-network checks.

The transport adapter must supply measurements from real operator networks.
No server-side ping or ordinary TCP reachability is treated as a tunnel gate.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

OPERATORS = frozenset({"t2", "t_mobile", "megafon", "beeline", "mts"})


@dataclass(frozen=True)
class Attempt:
    operator: str
    target_path: str
    test_kind: str
    provider: str
    region: str | None
    allowed_control_ok: bool | None
    blocked_control_ok: bool | None
    target_ok: bool | None
    rtt_ms: float | None = None
    reason: str | None = None

    @property
    def restriction_state(self) -> str:
        if self.allowed_control_ok is True and self.blocked_control_ok is False:
            return "confirmed"
        if self.allowed_control_ok is True and self.blocked_control_ok is True:
            return "unconfirmed"
        return "unknown"

    @property
    def outcome(self) -> str:
        return "unknown" if self.target_ok is None else "ok" if self.target_ok else "failed"


def classify_batch(attempts: list[Attempt]) -> str:
    """Require three usable attempts under confirmed restrictions for a verdict."""
    eligible = [item for item in attempts if item.restriction_state == "confirmed"
                and item.target_ok is not None and item.test_kind == "client_tunnel"]
    if len(eligible) < 3:
        return "unknown"
    return "ok" if sum(item.target_ok is True for item in eligible) >= 2 else "failed"


def record_batch(conn: sqlite3.Connection, batch_id: str, node_host: str,
                 attempts: list[Attempt], checked_at: str | None = None) -> dict | None:
    """Persist one operator/path batch and return its alert/recovery transition."""
    if not attempts or len(attempts) > 12 or not batch_id or not node_host:
        raise ValueError("invalid_batch")
    identity = {(item.operator, item.target_path, item.test_kind) for item in attempts}
    if len(identity) != 1 or any(item.operator not in OPERATORS or item.test_kind not in {"tcp", "tls", "client_tunnel"} for item in attempts):
        raise ValueError("mixed_or_invalid_batch")
    operator, path, kind = next(iter(identity))
    checked_at = checked_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if conn.execute("""SELECT 1 FROM lte_operator_probe_results
        WHERE batch_id=? AND node_host=? AND operator=? AND target_path=? AND test_kind=? LIMIT 1""",
        (batch_id, node_host, operator, path, kind)).fetchone():
        return None
    for item in attempts:
        conn.execute("""INSERT INTO lte_operator_probe_results
            (batch_id,node_host,operator,target_path,test_kind,restriction_state,
             allowed_control_ok,blocked_control_ok,region,outcome,rtt_ms,reason,provider,checked_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (batch_id, node_host, item.operator, item.target_path, item.test_kind,
             item.restriction_state, item.allowed_control_ok, item.blocked_control_ok,
             item.region, item.outcome, item.rtt_ms, item.reason, item.provider, checked_at))
    verdict = classify_batch(attempts)
    if verdict == "unknown":
        return None
    row = conn.execute("""SELECT * FROM lte_operator_alert_state
        WHERE node_host=? AND operator=? AND target_path=? AND test_kind=?""",
        (node_host, operator, path, kind)).fetchone()
    previous = dict(row) if row else {}
    failures = int(previous.get("consecutive_failures") or 0)
    successes = int(previous.get("consecutive_successes") or 0)
    alerted = bool(previous.get("alert_sent"))
    started = previous.get("incident_started_at")
    event = None
    if verdict == "failed":
        failures += 1
        successes = 0
        started = started or checked_at
        if not alerted:
            event = {"type": "alert", "node_host": node_host, "operator": operator,
                     "target_path": path, "incident_started_at": started}
            alerted = True
    else:
        successes += 1
        failures = 0
        if alerted and successes >= 2:
            event = {"type": "recovery", "node_host": node_host, "operator": operator,
                     "target_path": path, "incident_started_at": started}
            alerted = False
            started = None
    conn.execute("""INSERT INTO lte_operator_alert_state
        (node_host,operator,target_path,test_kind,consecutive_failures,consecutive_successes,
         incident_started_at,alert_sent,last_checked_at)
        VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(node_host,operator,target_path,test_kind) DO UPDATE SET
        consecutive_failures=excluded.consecutive_failures,
        consecutive_successes=excluded.consecutive_successes,
        incident_started_at=excluded.incident_started_at,
        alert_sent=excluded.alert_sent,last_checked_at=excluded.last_checked_at""",
        (node_host, operator, path, kind, failures, successes, started, int(alerted), checked_at))
    return event
