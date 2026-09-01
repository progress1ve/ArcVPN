#!/usr/bin/env python3
"""Verify one active LTE subscription without printing its URL or credentials."""
from __future__ import annotations

import base64
import ast
import json
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "vpn_bot.db"


def routing_constant(name: str):
    tree = ast.parse((ROOT / "subscription_api.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"routing constant missing: {name}")


TIKTOK_PROXY_SITES = routing_constant("TIKTOK_PROXY_SITES")


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
        (lte_links if "Лучший обход" in name or "Обход глушилок" in name or "LTE" in name else main_links).append(link)
    def credentials_match(items, expected):
        return bool(items) and all(urllib.parse.urlparse(item).username == expected for item in items)
    expected_announce = "❗Лимит ГБ тратиться только на Обход глушилок.❗"
    json_url = f"http://127.0.0.1:8080/sub/{urllib.parse.quote(row['sub_id'], safe='')}?format=json"
    with urllib.request.urlopen(json_url, timeout=15) as response:
        profiles = json.loads(response.read().decode("utf-8"))
        profile_names = [item.get("remarks") for item in profiles]
    auto_hosts = []
    for outbound in profiles[0].get("outbounds", []):
        settings = outbound.get("settings") or {}
        vnext = settings.get("vnext") or []
        if vnext:
            auto_hosts.append(vnext[0].get("address"))
        elif settings.get("address"):
            auto_hosts.append(settings.get("address"))
    expected_names = [
        "Автовыбор | Самый быстрый", "🇷🇺 Ютуб без рекламы",
        "🇪🇪 Эстония #1", "🇪🇪 Эстония #2",
        "🇳🇱 Нидерланды #1", "🇳🇱 Нидерланды #2",
        "🇩🇪 Германия #1", "🇩🇪 Германия #2", "Лучший обход",
        "🇪🇺 Обход глушилок #2", "🇪🇺 Обход глушилок #3",
        "🇪🇺 Обход глушилок #4", "🇪🇺 Обход глушилок #5",
    ]
    tiktok_routing_ok = True
    for profile in profiles:
        rules = (profile.get("routing") or {}).get("rules") or []
        tiktok_indexes = [i for i, rule in enumerate(rules) if rule.get("domain") == TIKTOK_PROXY_SITES]
        direct_indexes = [i for i, rule in enumerate(rules) if rule.get("outboundTag") == "direct"]
        tiktok_routing_ok = tiktok_routing_ok and bool(tiktok_indexes) and bool(direct_indexes)
        if tiktok_indexes and direct_indexes:
            tiktok_routing_ok = tiktok_routing_ok and tiktok_indexes[0] < direct_indexes[0]
    result = {
        "ok": credentials_match(main_links, row["client_uuid"])
              and credentials_match(lte_links, row["lte_client_uuid"])
              and len(lte_links) == 5
              and f"total={int(row['lte_quota_gb']) * 1024**3}" in userinfo
              and expected_announce in announce
              and profile_names == expected_names
              and auto_hosts.count("cdn-nd.arccnet.space") == 1
              and auto_hosts.count("cdn-de.arccnet.space") == 1
              and auto_hosts.count("ee.arccnet.space") == 2
              and tiktok_routing_ok,
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
        "profile_order_ok": profile_names == expected_names,
        "profile_count": len(profile_names),
        "netherlands_cdn_fallbacks": auto_hosts.count("cdn-nd.arccnet.space"),
        "estonia_cdn_fallbacks": auto_hosts.count("cdn-de.arccnet.space"),
        "estonia_auto_outbounds": auto_hosts.count("ee.arccnet.space"),
        "tiktok_routing_ok": tiktok_routing_ok,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
