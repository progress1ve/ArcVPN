#!/usr/bin/env python3
"""Verify one active LTE subscription without printing its URL or credentials."""
from __future__ import annotations

import base64
import json
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "vpn_bot.db"


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT k.sub_id,k.client_uuid,u.lte_client_uuid,u.lte_quota_gb
          FROM vpn_keys k JOIN users u ON u.id=k.user_id
         WHERE k.expires_at>datetime('now') AND u.lte_quota_gb>0
           AND u.lte_client_uuid IS NOT NULL ORDER BY k.id LIMIT 1
    """).fetchone()
    conn.close()
    if not row:
        print(json.dumps({"ok": False, "reason": "no LTE canary candidate"}))
        return 1
    url = f"http://127.0.0.1:8080/sub/{urllib.parse.quote(row['sub_id'], safe='')}?format=plain"
    with urllib.request.urlopen(url, timeout=15) as response:
        body = response.read().decode("utf-8")
        userinfo = response.headers.get("Subscription-Userinfo", "")
        announce_header = response.headers.get("announce", "")
        announce = base64.b64decode(announce_header.removeprefix("base64:")).decode("utf-8") if announce_header else ""
    links = [line for line in body.splitlines() if line.startswith(("vless://", "hysteria2://", "hy2://"))]
    main_links, lte_links = [], []
    for link in links:
        name = urllib.parse.unquote(urllib.parse.urlparse(link).fragment)
        (lte_links if "Обход глушилок" in name or "LTE" in name else main_links).append(link)
    def credentials_match(items, expected):
        return bool(items) and all(urllib.parse.urlparse(item).username == expected for item in items)
    expected_announce = "❗Лимит ГБ тратится только на Обход глушилок.❗"
    result = {
        "ok": credentials_match(main_links, row["client_uuid"])
              and credentials_match(lte_links, row["lte_client_uuid"])
              and f"total={int(row['lte_quota_gb']) * 1024**3}" in userinfo
              and expected_announce in announce,
        "main_links": len(main_links), "lte_links": len(lte_links),
        "main_identity_ok": credentials_match(main_links, row["client_uuid"]),
        "lte_identity_ok": credentials_match(lte_links, row["lte_client_uuid"]),
        "lte_links_with_lte_identity": sum(
            urllib.parse.urlparse(item).username == row["lte_client_uuid"] for item in lte_links
        ),
        "lte_links_with_main_identity": sum(
            urllib.parse.urlparse(item).username == row["client_uuid"] for item in lte_links
        ),
        "lte_userinfo_ok": f"total={int(row['lte_quota_gb']) * 1024**3}" in userinfo,
        "announce_ok": expected_announce in announce,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
