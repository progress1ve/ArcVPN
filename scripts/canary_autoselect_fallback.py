#!/usr/bin/env python3
"""Test the generated AutoSelect chain without touching live nodes.

Reads an existing active subscription on the control plane. Credentials stay
inside a mode-0700 temporary directory and are removed after each probe.
"""
from __future__ import annotations

import copy
import json
import logging
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import subscription_api as api
from database.connection import DB_PATH

XRAY = Path("/tmp/arcvpn-canary-xray")
SOCKS_PORT = 18083


def _profile() -> dict:
    logging.getLogger("subscription_api").disabled = True
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("""SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id
            WHERE k.expires_at>datetime('now') AND k.sub_id IS NOT NULL
              AND COALESCE(u.lte_quota_gb,0)>0
            ORDER BY k.last_online_at DESC LIMIT 50""").fetchall()
    client = api.app.test_client()
    for (sub_id,) in rows:
        response = client.get(f"/sub/{sub_id}?format=json", headers={"User-Agent": "Happ"})
        profiles = response.get_json(silent=True)
        if not isinstance(profiles, list):
            continue
        auto = next((item for item in profiles if str(item.get("remarks", "")).startswith("Автовыбор")), None)
        if not auto:
            continue
        tags = {item.get("tag") for item in auto.get("outbounds", [])}
        if {"proxy-main-1", "proxy-reserve-de", "proxy-stage-2", "proxy-back-1"} <= tags:
            return auto
    raise RuntimeError("No eligible AutoSelect canary profile with all three paths")


def _probe(profile: dict, mode: str) -> None:
    config = copy.deepcopy(profile)
    config.pop("meta", None)
    config["log"] = {"loglevel": "warning"}
    config["inbounds"] = [{
        "listen": "127.0.0.1", "port": SOCKS_PORT, "protocol": "socks",
        "settings": {"auth": "noauth", "udp": False},
    }]
    outbounds = {item["tag"]: item for item in config["outbounds"]}
    if mode in {"germany", "cdn"}:
        target = outbounds["proxy-main-1"]["settings"]["vnext"][0]
        target.update(address="127.0.0.1", port=9)
    if mode == "cdn":
        target = outbounds["proxy-reserve-de"]["settings"]["vnext"][0]
        target.update(address="127.0.0.1", port=9)
    with tempfile.TemporaryDirectory(prefix="arcvpn-auto-canary-") as folder:
        path = Path(folder) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        subprocess.run([str(XRAY), "run", "-test", "-c", str(path)],
                       check=True, capture_output=True, timeout=15)
        with (Path(folder) / "xray.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(XRAY), "run", "-c", str(path)],
                                       stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 100
                while time.monotonic() < deadline:
                    time.sleep(5)
                    result = subprocess.run([
                        "curl", "-ksS", "--max-time", "8", "--socks5-hostname",
                        f"127.0.0.1:{SOCKS_PORT}", "-o", "/dev/null", "-w", "%{http_code}",
                        "https://www.google.com/generate_204",
                    ], capture_output=True, text=True, timeout=12)
                    if result.returncode == 0 and result.stdout.strip() == "204":
                        print(json.dumps({"mode": mode, "tunnel": "passed", "http": 204}))
                        return
                raise RuntimeError(f"AutoSelect {mode} tunnel did not reach HTTP 204")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()


def main() -> None:
    if not XRAY.is_file():
        raise RuntimeError("Canary Xray binary is missing")
    profile = _profile()
    for mode in ("estonia", "germany", "cdn"):
        _probe(profile, mode)


if __name__ == "__main__":
    main()
