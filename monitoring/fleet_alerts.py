"""Stateful RemnaNode outage and regional reachability detection."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from monitoring.deep_node_diagnostics import run as direct_probe
from monitoring.remnawave_fleet_monitor import load_env, tcp_ports

ROOT = Path(__file__).resolve().parents[1]
CHECK_HOST_BASE = "https://check-host.net"
FAILURE_THRESHOLD = 3
RECOVERY_THRESHOLD = 2
MOSCOW_TZ = timezone(timedelta(hours=3), name="MSK")
EXCLUDED_NODE_NAMES = {
    "arcvpn finland",
    "arcvpn finland lte",
    "arcvpn albania wcloud",
    "arcvpn moscow bridge",
}


@dataclass(frozen=True)
class Observation:
    status: str
    details: dict


def classify(panel_connected: bool, direct: dict, external: dict | None) -> Observation:
    failed_ports = [item.get("port") for item in direct.get("ports", []) if not item.get("ok")]
    if not panel_connected:
        return Observation("server_down", {
            "panel_connected": panel_connected,
            "failed_ports": failed_ports,
            "external": external or {},
        })
    completed = int((external or {}).get("completed", 0))
    successes = int((external or {}).get("success", 0))
    if completed < 2:
        return Observation("unknown", {"reason": "external_probe_incomplete", "external": external or {}})
    if not direct.get("ok"):
        if successes > 0:
            return Observation("healthy", {
                "panel_connected": True, "failed_ports": failed_ports, "external": external or {}
            })
        return Observation("server_down", {
            "panel_connected": True, "failed_ports": failed_ports, "external": external or {}
        })
    if successes == 0:
        return Observation("possible_ip_block", {"panel_connected": True, "failed_ports": [], "external": external})
    return Observation("healthy", {"panel_connected": True, "failed_ports": [], "external": external})


def should_monitor(node: dict) -> bool:
    name = str(node.get("name") or "").strip().casefold()
    return not node.get("isDisabled") and name not in EXCLUDED_NODE_NAMES


def format_moscow_time(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M МСК")
    except (TypeError, ValueError):
        return str(value)


def _json_get(url: str, timeout: int = 12) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ArcVPN-Fleet-Monitor/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def russian_probe_nodes(limit: int = 3) -> list[str]:
    payload = _json_get(f"{CHECK_HOST_BASE}/nodes/hosts")
    result = []
    for name, item in (payload.get("nodes") or {}).items():
        location = item.get("location") or []
        if location and str(location[0]).lower() == "ru":
            result.append(str(name))
    return sorted(result)[:limit]


def check_host_tcp(host: str, port: int, nodes: list[str]) -> dict:
    if len(nodes) < 2:
        return {"completed": 0, "success": 0, "requested": len(nodes), "provider": "check-host"}
    query = [("host", f"{host}:{port}")] + [("node", node) for node in nodes]
    started = _json_get(f"{CHECK_HOST_BASE}/check-tcp?{urllib.parse.urlencode(query)}")
    request_id = str(started.get("request_id") or "")
    if not request_id:
        return {"completed": 0, "success": 0, "requested": len(nodes), "provider": "check-host"}
    results = {}
    for _ in range(4):
        time.sleep(1.5)
        results = _json_get(f"{CHECK_HOST_BASE}/check-result/{urllib.parse.quote(request_id)}")
        if sum(value is not None for value in results.values()) >= 2:
            break
    completed = 0
    success = 0
    for node in nodes:
        value = results.get(node)
        if value is None:
            continue
        completed += 1
        records = value if isinstance(value, list) else [value]
        if any(isinstance(record, dict) and record.get("time") is not None and not record.get("error") for record in records):
            success += 1
    return {"completed": completed, "success": success, "requested": len(nodes), "provider": "check-host"}


def fetch_remnawave_nodes() -> list[dict]:
    env = load_env(ROOT / ".env.remnawave-staging")
    request = urllib.request.Request(
        f"{env['REMNAWAVE_PANEL_URL'].rstrip('/')}/api/nodes",
        headers={"Authorization": f"Bearer {env['REMNAWAVE_API_TOKEN']}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, list) else payload.get("response", payload.get("nodes", []))


def update_state(conn: sqlite3.Connection, node_key: str, node_name: str, observation: Observation,
                 now: str | None = None) -> dict | None:
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute("SELECT * FROM fleet_alert_state WHERE node_key=?", (node_key,)).fetchone()
    previous = dict(row) if row else None
    details_json = json.dumps(observation.details, ensure_ascii=False, separators=(",", ":"))
    if observation.status == "unknown":
        if previous:
            conn.execute("UPDATE fleet_alert_state SET node_name=?,last_details_json=?,last_checked_at=? WHERE node_key=?",
                         (node_name, details_json, now, node_key))
        return None

    if observation.status == "healthy":
        successes = (int(previous["consecutive_successes"]) + 1) if previous else 1
        event = None
        if previous and previous["alert_sent"] and successes >= RECOVERY_THRESHOLD:
            event = {"type": "recovery", "node_name": node_name, "previous_status": previous["status"],
                     "incident_started_at": previous["incident_started_at"], "details": observation.details}
        conn.execute("""INSERT INTO fleet_alert_state
            (node_key,node_name,status,consecutive_failures,consecutive_successes,incident_started_at,alert_sent,last_details_json,last_checked_at)
            VALUES (?,?,?,0,?,NULL,0,?,?) ON CONFLICT(node_key) DO UPDATE SET
            node_name=excluded.node_name,
            status=CASE WHEN fleet_alert_state.alert_sent=1 AND excluded.consecutive_successes<? THEN fleet_alert_state.status ELSE 'healthy' END,
            consecutive_failures=0,
            consecutive_successes=excluded.consecutive_successes,
            incident_started_at=CASE WHEN fleet_alert_state.alert_sent=1 AND excluded.consecutive_successes<? THEN fleet_alert_state.incident_started_at ELSE NULL END,
            alert_sent=CASE WHEN fleet_alert_state.alert_sent=1 AND excluded.consecutive_successes<? THEN 1 ELSE 0 END,
            last_details_json=excluded.last_details_json,last_checked_at=excluded.last_checked_at""",
            (node_key, node_name, "healthy", successes, details_json, now,
             RECOVERY_THRESHOLD, RECOVERY_THRESHOLD, RECOVERY_THRESHOLD))
        return event

    same_failure = previous and previous["status"] == observation.status
    failures = int(previous["consecutive_failures"]) + 1 if same_failure else 1
    incident_started = previous["incident_started_at"] if same_failure and previous else now
    already_sent = bool(previous and same_failure and previous["alert_sent"])
    should_alert = failures >= FAILURE_THRESHOLD and not already_sent
    conn.execute("""INSERT INTO fleet_alert_state
        (node_key,node_name,status,consecutive_failures,consecutive_successes,incident_started_at,alert_sent,last_details_json,last_checked_at)
        VALUES (?,?,?, ?,0,?,?,?,?) ON CONFLICT(node_key) DO UPDATE SET
        node_name=excluded.node_name,status=excluded.status,consecutive_failures=excluded.consecutive_failures,
        consecutive_successes=0,incident_started_at=excluded.incident_started_at,
        alert_sent=excluded.alert_sent,last_details_json=excluded.last_details_json,last_checked_at=excluded.last_checked_at""",
        (node_key, node_name, observation.status, failures, incident_started, int(already_sent or should_alert), details_json, now))
    if should_alert:
        return {"type": "alert", "node_name": node_name, "status": observation.status,
                "incident_started_at": incident_started, "details": observation.details}
    return None


def collect_events(db_path: str | None = None, external_probe: Callable[[str, int, list[str]], dict] = check_host_tcp,
                   dry_run: bool = False) -> dict:
    nodes = [node for node in fetch_remnawave_nodes() if should_monitor(node)]
    try:
        ru_nodes = russian_probe_nodes()
    except Exception:
        ru_nodes = []
    path = db_path or os.getenv("ARCVPN_DB_PATH", str(ROOT / "database" / "vpn_bot.db"))
    events = []
    observations = []
    for node in nodes:
        host = str(node.get("address") or "").strip()
        ports = tcp_ports(node)
        if not host:
            continue
        direct = direct_probe(host, ports) if ports else {
            "ok": bool(node.get("isConnected")), "ports": [], "note": "panel-only UDP node"
        }
        external = None
        if ports:
            try:
                external = external_probe(host, ports[0], ru_nodes)
            except Exception:
                external = None
        observations.append((node, classify(bool(node.get("isConnected")), direct, external)))

    with sqlite3.connect(path, timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        for node, observation in observations:
            host = str(node.get("address") or "").strip()
            event = None if dry_run else update_state(
                conn, str(node.get("uuid") or host), str(node.get("name") or host), observation
            )
            if event:
                events.append(event)
        if not dry_run:
            conn.commit()
    return {"checked": len(observations), "events": events, "external_nodes": len(ru_nodes)}
