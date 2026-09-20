#!/usr/bin/env python3
"""Exercise the staged Moscow REALITY entry without publishing its Host."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

from canary_germany_reality import XRAY, reality_link

STATE_PATH = Path(".secrets/moscow-managed-bridge.json")
CHECK_URL = os.environ.get("ARCVPN_CANARY_URL", "https://cp.cloudflare.com/generate_204")
EXPECT_BODY = os.environ.get("ARCVPN_CANARY_EXPECT_BODY", "")


def main() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    user = urllib.parse.urlsplit(reality_link()).username
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{"listen": "127.0.0.1", "port": 18081, "protocol": "socks", "settings": {"auth": "noauth", "udp": False}}],
        "outbounds": [{
            "tag": "proxy", "protocol": "vless",
            "settings": {"vnext": [{"address": "ru.arccnet.space", "port": 443, "users": [{
                "id": user, "encryption": "none", "flow": "xtls-rprx-vision",
            }]}]},
            "streamSettings": {"network": "tcp", "security": "reality", "realitySettings": {
                "serverName": "ru.arccnet.space", "fingerprint": "firefox",
                "password": state["ru_public_key"], "shortId": state["ru_short_id"],
            }},
        }],
    }
    with tempfile.TemporaryDirectory(prefix="arcvpn-ru-canary-") as temp:
        path = Path(temp) / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        log_path = Path(temp) / "xray.log"
        log_file = log_path.open("w", encoding="utf-8")
        process = subprocess.Popen([str(XRAY), "run", "-c", str(path)], stdout=log_file, stderr=log_file)
        try:
            time.sleep(1.5)
            curl = [
                "curl", "-fsS", "--max-time", "20", "--socks5-hostname", "127.0.0.1:18081",
            ]
            if EXPECT_BODY:
                curl.append(CHECK_URL)
            else:
                curl.extend(["-o", "/dev/null", "-w", "%{http_code}", CHECK_URL])
            result = subprocess.run(curl, capture_output=True, text=True, timeout=25)
            passed = not result.returncode and (EXPECT_BODY in result.stdout if EXPECT_BODY else result.stdout.strip() == "204")
            if not passed:
                log_file.flush()
                tail = " | ".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-8:])
                raise RuntimeError(f"Moscow managed bridge canary failed curl={result.returncode} {result.stderr.strip()[:200]}; {tail}")
            print(json.dumps({"tunnel": "passed", "check": "body" if EXPECT_BODY else "http-204", "hostname": "ru.arccnet.space"}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            log_file.close()


if __name__ == "__main__":
    main()


