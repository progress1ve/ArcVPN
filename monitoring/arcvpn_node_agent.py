#!/usr/bin/env python3
"""Small dependency-free ArcVPN node telemetry agent."""

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path


STATE_PATH = Path(os.getenv("ARCVPN_NODE_STATE", "/var/lib/arcvpn-node-agent/state.json"))
ENDPOINT = os.getenv("ARCVPN_METRICS_URL", "https://sub.arccnet.space/api/internal/node-metrics")
TOKEN = os.getenv("ARCVPN_METRICS_TOKEN", "")
PUBLIC_HOST = os.getenv("ARCVPN_NODE_HOST", "")
NODE_NAME = os.getenv("ARCVPN_NODE_NAME", socket.gethostname())


def _read(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return default


def _service_active(name: str) -> bool:
    try:
        return subprocess.run(
            ["systemctl", "is-active", "--quiet", name],
            timeout=3, check=False,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _cpu_totals():
    values = [int(value) for value in _read("/proc/stat").splitlines()[0].split()[1:]]
    steal = values[7] if len(values) > 7 else 0
    return sum(values), values[3] + (values[4] if len(values) > 4 else 0), steal


def _network_totals():
    rx = tx = 0
    for line in _read("/proc/net/dev").splitlines()[2:]:
        if ":" not in line:
            continue
        iface, raw = line.split(":", 1)
        if iface.strip() == "lo":
            continue
        fields = raw.split()
        rx += int(fields[0])
        tx += int(fields[8])
    return rx, tx


def _memory_pct():
    values = {}
    for line in _read("/proc/meminfo").splitlines():
        key, value = line.split(":", 1)
        values[key] = int(value.strip().split()[0])
    total = max(1, values.get("MemTotal", 1))
    available = values.get("MemAvailable", values.get("MemFree", 0))
    return round((total - available) / total * 100, 2)


def _tcp_established():
    total = 0
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        total += sum(1 for line in _read(path).splitlines()[1:] if len(line.split()) > 3 and line.split()[3] == "01")
    return total


def collect():
    now = time.time()
    cpu_total, cpu_idle, cpu_steal = _cpu_totals()
    net_rx, net_tx = _network_totals()
    previous = {}
    try:
        previous = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    elapsed = max(0.001, now - float(previous.get("time", now)))
    cpu_delta = cpu_total - int(previous.get("cpu_total", cpu_total))
    idle_delta = cpu_idle - int(previous.get("cpu_idle", cpu_idle))
    steal_delta = cpu_steal - int(previous.get("cpu_steal", cpu_steal))
    cpu_pct = round((1 - idle_delta / cpu_delta) * 100, 2) if cpu_delta > 0 else None
    cpu_steal_pct = round(steal_delta / cpu_delta * 100, 2) if cpu_delta > 0 else None
    rx_bps = max(0, net_rx - int(previous.get("net_rx", net_rx))) * 8 / elapsed
    tx_bps = max(0, net_tx - int(previous.get("net_tx", net_tx))) * 8 / elapsed
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({
        "time": now, "cpu_total": cpu_total, "cpu_idle": cpu_idle, "cpu_steal": cpu_steal,
        "net_rx": net_rx, "net_tx": net_tx,
    }), encoding="utf-8")
    disk = shutil.disk_usage("/")
    xui_active = _service_active("x-ui.service")
    hysteria_active = _service_active("arcvpn-hysteria.service") or _service_active("hysteria-server.service")
    return {
        "host": PUBLIC_HOST,
        "name": NODE_NAME,
        "cpu_pct": cpu_pct,
        "cpu_steal_pct": cpu_steal_pct,
        "mem_pct": _memory_pct(),
        "load_1m": round(os.getloadavg()[0], 3),
        "disk_used_pct": round(disk.used / max(1, disk.total) * 100, 2),
        "net_rx_bps": round(rx_bps, 1),
        "net_tx_bps": round(tx_bps, 1),
        "tcp_established": _tcp_established(),
        "uptime_seconds": int(float(_read("/proc/uptime", "0").split()[0])),
        "xui_active": xui_active,
        "hysteria_active": hysteria_active,
        "xray_state": "running" if xui_active else "unknown",
        "boot_id": _read("/proc/sys/kernel/random/boot_id"),
    }


def main():
    if not TOKEN or not PUBLIC_HOST:
        raise SystemExit("ARCVPN_METRICS_TOKEN and ARCVPN_NODE_HOST are required")
    payload = json.dumps(collect(), separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT, data=payload, method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise SystemExit(f"metrics endpoint returned {response.status}")


if __name__ == "__main__":
    main()
