#!/usr/bin/env python3
"""Compare direct Germany REALITY with the managed Moscow-to-Germany bridge."""
from __future__ import annotations

import json
import statistics
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

from canary_germany_reality import XRAY, reality_link


STATE_PATH = Path(".secrets/moscow-managed-bridge.json")
DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=10000000"
RUNS = 5


def configs() -> dict[str, dict]:
    parsed = urllib.parse.urlsplit(reality_link())
    query = urllib.parse.parse_qs(parsed.query)
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    user = urllib.parse.unquote(parsed.username or "")
    if not user or not query.get("pbk") or not query.get("sid"):
        raise RuntimeError("Direct Germany REALITY link is incomplete")

    def base(port: int, address: str, server_name: str, password: str, short_id: str) -> dict:
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "listen": "127.0.0.1", "port": port, "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False},
            }],
            "outbounds": [{
                "tag": "proxy", "protocol": "vless",
                "settings": {"vnext": [{
                    "address": address, "port": 443,
                    "users": [{"id": user, "encryption": "none", "flow": "xtls-rprx-vision"}],
                }]},
                "streamSettings": {
                    "network": "tcp", "security": "reality",
                    "realitySettings": {
                        "serverName": server_name, "fingerprint": "firefox",
                        "password": password, "shortId": short_id,
                    },
                },
            }],
        }

    return {
        "direct": base(18080, parsed.hostname or "de.arccnet.space", query.get("sni", ["de.arccnet.space"])[0], query["pbk"][0], query["sid"][0]),
        "bridge": base(18081, "ru.arccnet.space", "ru.arccnet.space", state["ru_public_key"], state["ru_short_id"]),
    }


def measure(port: int) -> dict[str, float | int]:
    result = subprocess.run([
        "curl", "-fsS", "--max-time", "45", "--socks5-hostname", f"127.0.0.1:{port}",
        "-o", "/dev/null", "-w", "%{http_code} %{time_connect} %{time_starttransfer} %{time_total} %{speed_download}",
        DOWNLOAD_URL,
    ], capture_output=True, text=True, timeout=50)
    if result.returncode:
        raise RuntimeError(f"curl failed on SOCKS port {port}: {result.stderr.strip()[:160]}")
    code, connect, start, total, speed = result.stdout.strip().split()
    if code != "200":
        raise RuntimeError(f"benchmark endpoint returned HTTP {code}")
    return {
        "connect_ms": round(float(connect) * 1000, 1),
        "ttfb_ms": round(float(start) * 1000, 1),
        "total_s": round(float(total), 3),
        "mbps": round(float(speed) * 8 / 1_000_000, 2),
    }


def median(samples: list[dict[str, float | int]]) -> dict[str, float | int]:
    return {
        key: round(statistics.median(float(item[key]) for item in samples), 2)
        for key in ("connect_ms", "ttfb_ms", "total_s", "mbps")
    }


def main() -> None:
    if not XRAY.is_file():
        raise RuntimeError("Canary Xray binary is missing")
    definitions = configs()
    results: dict[str, list[dict[str, float | int]]] = {"direct": [], "bridge": []}
    with tempfile.TemporaryDirectory(prefix="arcvpn-bridge-benchmark-") as temp:
        processes = []
        logs = []
        try:
            for name, config in definitions.items():
                path = Path(temp) / f"{name}.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                log = (Path(temp) / f"{name}.log").open("w", encoding="utf-8")
                logs.append(log)
                processes.append(subprocess.Popen([str(XRAY), "run", "-c", str(path)], stdout=log, stderr=log))
            time.sleep(1.5)
            for run in range(RUNS):
                order = ("direct", "bridge") if run % 2 == 0 else ("bridge", "direct")
                for name in order:
                    port = 18080 if name == "direct" else 18081
                    results[name].append(measure(port))
                    time.sleep(0.4)
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            for log in logs:
                log.close()

    summary = {name: median(samples) for name, samples in results.items()}
    direct = float(summary["direct"]["mbps"])
    bridge = float(summary["bridge"]["mbps"])
    summary["comparison"] = {
        "bridge_speed_vs_direct_pct": round(bridge / direct * 100, 1) if direct else 0,
        "samples_per_path": RUNS,
        "bytes_per_sample": 10_000_000,
        "measurement_source": "control-plane",
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
