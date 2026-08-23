#!/usr/bin/env python3
"""Persist a bounded synthetic diagnostic for every production RemnaNode."""
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "monitoring"))
from deep_node_diagnostics import run  # noqa: E402


def load_env(path: Path) -> dict[str, str]:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def tcp_ports(node: dict) -> list[int]:
    result = []
    for inbound in ((node.get("configProfile") or {}).get("activeInbounds") or []):
        transport = " ".join(str(inbound.get(k) or "") for k in ("network", "type", "protocol", "tag")).lower()
        # XHTTP origins intentionally bind to loopback and are reached through
        # the CDN/nginx edge. Probing their internal port on the public node IP
        # produces a false outage. LTE health is exposed separately by the
        # admin edge model and its CDN/origin checks.
        if any(marker in transport for marker in ("hysteria", "udp", "quic", "xhttp")):
            continue
        try:
            port = int(inbound.get("port"))
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            result.append(port)
    return sorted(set(result))


def main() -> int:
    env = load_env(ROOT / ".env.remnawave-staging")
    request = urllib.request.Request(
        f"{env['REMNAWAVE_PANEL_URL'].rstrip('/')}/api/nodes",
        headers={"Authorization": f"Bearer {env['REMNAWAVE_API_TOKEN']}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    nodes = payload if isinstance(payload, list) else payload.get("response", payload.get("nodes", []))
    db_path = Path(os.getenv("ARCVPN_DB_PATH", str(ROOT / "database" / "vpn_bot.db")))
    failures = 0
    checked = 0
    with sqlite3.connect(db_path) as conn:
        for node in nodes:
            if node.get("isDisabled"):
                continue
            host = str(node.get("address") or "").strip()
            if not host:
                continue
            ports = tcp_ports(node)
            diagnostic = run(host, ports) if ports else {
                "ok": bool(node.get("isConnected")), "host": host, "addresses": [], "ports": [],
                "note": "UDP-only node: panel connectivity is authoritative",
            }
            diagnostic.update({"node_uuid": node.get("uuid"), "node_name": node.get("name") or host,
                               "panel_connected": bool(node.get("isConnected"))})
            diagnostic["ok"] = bool(diagnostic["ok"] and diagnostic["panel_connected"])
            checked += 1
            failures += int(not diagnostic["ok"])
            conn.execute("INSERT INTO node_diagnostic_runs(host,result_json,ok) VALUES(?,?,?)",
                         (host, json.dumps(diagnostic, ensure_ascii=False), int(diagnostic["ok"])))
        conn.execute("DELETE FROM node_diagnostic_runs WHERE created_at < datetime('now', '-30 days')")
    print(json.dumps({"ok": failures == 0, "nodes": checked, "failures": failures}, ensure_ascii=False))
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
