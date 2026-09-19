#!/usr/bin/env python3
"""Run a credential-safe real TCP REALITY canary for the replacement Germany node."""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database.connection import DB_PATH


DOMAIN = os.environ.get("ARCVPN_CANARY_DOMAIN", "de.arccnet.space")
CONNECT_HOST = os.environ.get("ARCVPN_CANARY_CONNECT_HOST", "")
CONNECT_PORT = int(os.environ.get("ARCVPN_CANARY_CONNECT_PORT", "0") or 0)
XRAY = Path(os.environ.get("ARCVPN_CANARY_XRAY", "/tmp/arcvpn-canary-xray"))


def subscription_lines() -> list[str]:
    with sqlite3.connect(str(DB_PATH)) as db:
        rows = db.execute(
            "SELECT sub_id FROM vpn_keys WHERE expires_at > datetime('now') "
            "AND sub_id IS NOT NULL AND length(sub_id) > 10 "
            "ORDER BY last_online_at DESC LIMIT 100"
        ).fetchall()
    if not rows:
        raise RuntimeError("No active canary subscription is available")
    last_lines = []
    for row in rows:
        request = urllib.request.Request(
            f"http://127.0.0.1:8080/sub/{row[0]}?format=plain",
            headers={"User-Agent": "Happ/1.0"},
        )
        body = urllib.request.urlopen(request, timeout=15).read().decode().strip()
        if "vless://" not in body:
            body = base64.b64decode(body + "=" * (-len(body) % 4)).decode()
        last_lines = [line.strip() for line in body.splitlines() if line.startswith("vless://")]
        if any(urllib.parse.urlsplit(line).hostname == DOMAIN for line in last_lines):
            return last_lines
    return last_lines


def reality_link() -> str:
    available = []
    for line in subscription_lines():
        parsed = urllib.parse.urlsplit(line)
        query = urllib.parse.parse_qs(parsed.query)
        available.append({
            "hostname": parsed.hostname,
            "security": query.get("security", [""])[0],
            "name": urllib.parse.unquote(parsed.fragment),
        })
        if parsed.hostname == DOMAIN and query.get("security") == ["reality"]:
            return line
    raise RuntimeError(
        f"REALITY link for {DOMAIN} is absent from subscription output; "
        + json.dumps(available, ensure_ascii=False)
    )


def main() -> None:
    if not XRAY.is_file():
        raise RuntimeError("Canary Xray binary is missing")
    parsed = urllib.parse.urlsplit(reality_link())
    query = urllib.parse.parse_qs(parsed.query)
    user = urllib.parse.unquote(parsed.username or "")
    if not user or not query.get("pbk") or not query.get("sid"):
        raise RuntimeError(f"REALITY link for {DOMAIN} is incomplete")
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1", "port": 18080, "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False},
        }],
        "outbounds": [{
            "tag": "proxy", "protocol": "vless",
            "settings": {"vnext": [{
                "address": CONNECT_HOST or parsed.hostname, "port": CONNECT_PORT or parsed.port or 443,
                "users": [{
                    "id": user, "encryption": "none",
                    **({"flow": query["flow"][0]} if query.get("flow") else {}),
                }],
            }]},
            "streamSettings": {
                "network": query.get("type", ["raw"])[0], "security": "reality",
                "realitySettings": {
                    "serverName": query.get("sni", [DOMAIN])[0],
                    "fingerprint": "firefox",
                    "password": query["pbk"][0],
                    "shortId": query["sid"][0],
                },
            },
        }],
    }
    with tempfile.TemporaryDirectory(prefix="arcvpn-de-canary-") as temp:
        path = Path(temp) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        process = subprocess.Popen(
            [str(XRAY), "run", "-c", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(1.5)
            result = subprocess.run([
                "curl", "-fsS", "--max-time", "15", "--socks5-hostname",
                "127.0.0.1:18080", "-o", "/dev/null", "-w", "%{http_code}",
                "https://www.google.com/generate_204",
            ], capture_output=True, text=True, timeout=20)
            if result.returncode or result.stdout.strip() != "204":
                raise RuntimeError(f"REALITY tunnel canary failed for {DOMAIN}")
            print(json.dumps({"tunnel": "passed", "http": 204, "hostname": DOMAIN}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
