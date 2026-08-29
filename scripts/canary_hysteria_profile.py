#!/usr/bin/env python3
"""Run a credential-safe real HTTP canary through a published Hysteria2 row."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "vpn_bot.db"
CONTAINER = "arcvpn-hy2-canary"


def published_link(remark: str) -> str:
    connection = sqlite3.connect(DB)
    row = connection.execute(
        """SELECT sub_id FROM vpn_keys
             WHERE expires_at > datetime('now') AND sub_id IS NOT NULL
             ORDER BY id LIMIT 1"""
    ).fetchone()
    connection.close()
    if not row:
        raise RuntimeError("no active canary identity")
    url = f"http://127.0.0.1:8080/sub/{urllib.parse.quote(row[0], safe='')}?format=plain"
    with urllib.request.urlopen(url, timeout=15) as response:
        links = response.read().decode("utf-8").splitlines()
    matches = [
        link for link in links
        if urllib.parse.urlsplit(link).scheme.lower() in {"hysteria2", "hy2"}
        and remark in urllib.parse.unquote(urllib.parse.urlsplit(link).fragment)
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one published Hysteria2 row, got {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remark", required=True)
    args = parser.parse_args()
    link = published_link(args.remark)
    parsed = urllib.parse.urlsplit(link)
    query = urllib.parse.parse_qs(parsed.query)
    pin = (query.get("pinSHA256") or query.get("pinnedPeerCertSha256") or [""])[0]
    config = {
        "server": f"{parsed.hostname}:{parsed.port or 443}",
        "auth": urllib.parse.unquote(parsed.username or ""),
        "tls": {
            "sni": (query.get("sni") or [parsed.hostname])[0],
            "insecure": True,
        },
        "socks5": {"listen": "127.0.0.1:11080"},
    }
    if pin:
        config["tls"]["pinSHA256"] = pin

    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    with tempfile.TemporaryDirectory(prefix="arcvpn-hy2-") as temp_dir:
        path = Path(temp_dir) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        path.chmod(0o600)
        started = subprocess.run(
            [
                "docker", "run", "-d", "--name", CONTAINER, "--network", "host",
                "-v", f"{path}:/etc/hysteria/config.json:ro",
                "tobyxdd/hysteria:latest", "client", "-c", "/etc/hysteria/config.json",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            print(json.dumps({"ok": False, "phase": "start"}))
            return 1
        time.sleep(3)
        try:
            result = subprocess.run(
                [
                    "curl", "--silent", "--show-error", "--output", "/dev/null",
                    "--write-out", "%{http_code}", "--max-time", "15",
                    "--socks5-hostname", "127.0.0.1:11080",
                    "https://www.gstatic.com/generate_204",
                ],
                capture_output=True,
                text=True,
            )
            ok = result.returncode == 0 and result.stdout == "204"
            print(json.dumps({
                "ok": ok,
                "phase": "tunnel",
                "http_status": result.stdout if result.stdout.isdigit() else None,
                "exit_code": result.returncode,
                "pin_present": bool(pin),
            }))
            return 0 if ok else 1
        finally:
            subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
