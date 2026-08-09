#!/usr/bin/env python3
"""Probe a Remnawave staging node through every canary subscription transport."""

import asyncio
import base64
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

import aiohttp

from bot.services.panels.remnawave import RemnawaveClient


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("ARCVPN_DB_PATH", ROOT / "database/vpn_bot.db"))
XRAY_BIN = os.getenv("ARCVPN_XRAY_BIN", "/usr/local/x-ui/bin/xray-linux-amd64")
CANARY_USERNAME = os.getenv("REMNAWAVE_CANARY_USERNAME", "arc-staging-canary")
DOWNLOAD_URL = os.getenv("REMNAWAVE_PROBE_URL", "https://speed.cloudflare.com/__down?bytes=524288")


def panel_config():
    return {
        "host": "staging.invalid", "port": 443, "panel_type": "remnawave",
        "panel_api_url": os.environ["REMNAWAVE_PANEL_URL"],
        "panel_api_token": os.environ["REMNAWAVE_API_TOKEN"],
        "panel_node_uuid": os.environ["REMNAWAVE_NODE_UUID"],
        "panel_squad_uuid": os.environ["REMNAWAVE_SQUAD_UUID"],
        "panel_write_mode": "disabled",
    }


def outbound(link):
    parsed = urllib.parse.urlsplit(link)
    query = {key: values[0] for key, values in urllib.parse.parse_qs(parsed.query).items()}
    auth = urllib.parse.unquote(parsed.username or "")
    if parsed.scheme == "vless":
        return {
            "protocol": "vless",
            "settings": {"vnext": [{"address": parsed.hostname, "port": parsed.port, "users": [{
                "id": auth, "encryption": "none", "flow": query.get("flow", ""),
            }]}]},
            "streamSettings": {"network": "tcp", "security": "reality", "realitySettings": {
                "fingerprint": query["fp"], "serverName": query["sni"],
                "publicKey": query["pbk"], "shortId": query["sid"],
            }},
        }
    if parsed.scheme == "hysteria2":
        return {
            "protocol": "hysteria", "settings": {
                "address": parsed.hostname, "port": parsed.port, "version": 2,
            },
            "streamSettings": {
                "network": "hysteria", "security": "tls",
                "hysteriaSettings": {"auth": auth, "version": 2},
                "tlsSettings": {"serverName": query["sni"], "alpn": ["h3"], "fingerprint": "firefox"},
                "finalmask": {"quicParams": {"congestion": "bbr", "debug": False}},
            },
        }
    raise ValueError(f"unsupported canary protocol: {parsed.scheme}")


def probe_link(link, socks_port):
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"listen": "127.0.0.1", "port": socks_port, "protocol": "socks", "settings": {"udp": True}}],
        "outbounds": [outbound(link)],
    }
    path = None
    process = None
    started = time.monotonic()
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as handle:
            json.dump(config, handle)
            path = handle.name
        checked = subprocess.run([XRAY_BIN, "run", "-test", "-config", path], timeout=10, check=False)
        if checked.returncode:
            return {"ok": False, "https_ms": None, "download_mbps": None}
        process = subprocess.Popen(
            [XRAY_BIN, "run", "-config", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        curl = subprocess.run([
            "curl", "-fsS", "--max-time", "20", "--socks5-hostname", f"127.0.0.1:{socks_port}",
            "-o", "/dev/null", "-w", "%{size_download} %{time_total}", DOWNLOAD_URL,
        ], capture_output=True, text=True, timeout=24, check=False)
        if curl.returncode:
            return {"ok": False, "https_ms": None, "download_mbps": None}
        size, elapsed = (float(value) for value in curl.stdout.split())
        return {
            "ok": True,
            "https_ms": round((time.monotonic() - started) * 1000, 2),
            "download_mbps": round(size * 8 / max(0.001, elapsed) / 1_000_000, 2),
        }
    finally:
        if process:
            process.terminate()
            try:
                process.wait(3)
            except subprocess.TimeoutExpired:
                process.kill()
        if path:
            Path(path).unlink(missing_ok=True)


async def run():
    client = RemnawaveClient(panel_config())
    try:
        status = await client.get_server_status()
        nodes = status.get("nodes") or []
        node = nodes[0] if nodes else {}
        user = await client.get_user(CANARY_USERNAME)
        if not user or not user.get("subscriptionUrl"):
            raise RuntimeError("staging canary subscription is missing")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(user["subscriptionUrl"], headers={"User-Agent": "Happ/1.0"}) as response:
                raw = await response.text()
                response.raise_for_status()
        links = [line for line in base64.b64decode(raw + "===").decode().splitlines() if "://" in line]
        probes = [probe_link(link, 18880 + index) for index, link in enumerate(links)]
        healthy = bool(status.get("online")) and len(probes) >= 2 and all(item["ok"] for item in probes)
        stats = ((node.get("system") or {}).get("stats") or {})
        info = ((node.get("system") or {}).get("info") or {})
        memory_total = float(info.get("memoryTotal") or 0)
        memory_used = float(stats.get("memoryUsed") or 0)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO server_health_samples(
                  host,state,online_count,clients_count,latency_ms,cpu_pct,mem_pct,inbound_count,
                  xray_state,telemetry_available,source,load_1m,uptime_seconds,xui_active,
                  hysteria_active,https_ms,download_mbps,probed_at
                ) VALUES(?,?,?,?,?,?,?,?,?,1,'remnawave-staging',?,?,?,?,?,?,?)
            """, (
                str(node.get("address") or "fr2.sfxu.ru"), "healthy" if healthy else "degraded",
                int(node.get("usersOnline") or 0), 1, max((item["https_ms"] or 0) for item in probes),
                None, round(memory_used / memory_total * 100, 2) if memory_total else None,
                len(node.get("configProfile", {}).get("activeInbounds") or []),
                "running" if node.get("isConnected") else "down", int(bool(node.get("isConnected"))),
                float((stats.get("loadAvg") or [0])[0]), int(stats.get("uptime") or 0),
                int(probes[0]["ok"] if probes else False),
                int(probes[1]["ok"] if len(probes) > 1 else False),
                max((item["https_ms"] or 0) for item in probes),
                min((item["download_mbps"] or 0) for item in probes), int(time.time()),
            ))
        print(json.dumps({"healthy": healthy, "node_online": status.get("online"), "probes": probes}))
        return 0 if healthy else 2
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
