#!/usr/bin/env python3
"""Run a credential-safe real XHTTP tunnel canary through the single CDN host."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import subscription_api as api
from database.connection import DB_PATH

XRAY = Path("/tmp/arcvpn-canary-xray")
PUBLIC_HOST = "cdn-de.arccnet.space"


def canary_outbound() -> dict:
    with sqlite3.connect(str(DB_PATH)) as db:
        rows = db.execute(
            "SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id "
            "WHERE k.expires_at>datetime('now') AND k.sub_id IS NOT NULL "
            "AND u.lte_quota_gb>0 AND u.lte_client_uuid IS NOT NULL "
            "ORDER BY k.last_online_at DESC LIMIT 100"
        ).fetchall()
    for (sub_id,) in rows:
        key = api.get_active_key_by_subscription_id(sub_id)
        if not key:
            continue
        try:
            links = api.ASYNC_EXECUTOR.run(api._native_remnawave_links(key))
        except Exception:
            continue
        link = next((value for value in links if urllib.parse.urlsplit(value).hostname == PUBLIC_HOST), None)
        if link:
            outbound = api._json_outbound_from_share_link(link, "proxy")
            if outbound:
                return outbound
    raise RuntimeError("No active credential-safe single-CDN canary identity is available")


def main() -> None:
    if not XRAY.is_file():
        raise RuntimeError("Canary Xray binary is missing")
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1", "port": 18082, "protocol": "socks",
            "settings": {"auth": "noauth", "udp": False},
        }],
        "outbounds": [canary_outbound()],
    }
    with tempfile.TemporaryDirectory(prefix="arcvpn-cdn-canary-") as temp:
        path = Path(temp) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        log_path = Path(temp) / "xray.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(XRAY), "run", "-c", str(path)], stdout=log, stderr=log)
            try:
                time.sleep(1.5)
                result = subprocess.run([
                    "curl", "-fsS", "--max-time", "30", "--socks5-hostname", "127.0.0.1:18082",
                    "-o", "/dev/null", "-w", "%{http_code}", "https://www.google.com/generate_204",
                ], capture_output=True, text=True, timeout=35)
                if result.returncode or result.stdout.strip() != "204":
                    log.flush()
                    tail = " | ".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-8:])
                    raise RuntimeError(f"single-CDN XHTTP canary failed curl={result.returncode}; {tail}")
                print(json.dumps({"tunnel": "passed", "http": 204, "hostname": PUBLIC_HOST}))
            finally:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    main()
