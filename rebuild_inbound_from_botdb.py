#!/usr/bin/env python3
"""
Аварийное восстановление VLESS+Reality инбаунда НАПРЯМУЮ в x-ui.db.

Зачем напрямую, а не через API: на этой сборке 3x-ui v2.9.4 эндпоинт addClient
молча не сохраняет клиентов (HTTP 200 с пустым телом), поэтому заливка через бота
«проходит», но клиенты не появляются. Прямая запись в SQLite — проверенный способ.

Что делает (атомарно, одним UPDATE):
1. Чинит realitySettings.dest и serverNames (после ручных правок там бывает мусор
   вроде "://google.com"), СОХРАНЯЯ валидный privateKey/shortIds инбаунда.
2. Сам выводит правильный publicKey из текущего privateKey через `xray x25519`
   (чтобы пара ключей гарантированно сошлась и подписка отдавала верный pbk).
3. Перезаписывает inbounds.settings всеми клиентами из БД бота + "decryption":"none".

После запуска с --apply ОБЯЗАТЕЛЬНО: `x-ui restart`.
Клиенты берутся из vpn_bot.db, sub_id не меняется → переимпорт пользователям не нужен.

Запуск:
  python3 rebuild_inbound_from_botdb.py                 # dry-run (ничего не пишет)
  python3 rebuild_inbound_from_botdb.py --apply         # записать и потом x-ui restart
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone


def to_ms(value) -> int:
    """ISO-дата из БД бота → epoch ms (как ждёт панель)."""
    if not value:
        return 0
    try:
        s = str(value).replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return 0


def derive_public_key(private_key: str, xray_bin: str) -> str:
    """Выводит publicKey, реально соответствующий privateKey, через `xray x25519`."""
    if not private_key:
        return ""
    try:
        out = subprocess.run(
            [xray_bin, "x25519", "-i", private_key],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  не удалось вызвать xray x25519: {e}")
        return ""
    # Форматы вывода разных версий: "Public key: X" / "Password (PublicKey): X"
    for line in out.splitlines():
        if "ublic" in line:  # Public key / PublicKey
            return line.split(":")[-1].strip()
    return ""


def main() -> None:
    p = argparse.ArgumentParser(description="Прямое восстановление инбаунда из БД бота")
    p.add_argument("--server", type=int, default=10, help="server_id в БД бота")
    p.add_argument("--inbound", type=int, default=1, help="id инбаунда в x-ui.db")
    p.add_argument("--xui-db", default="/etc/x-ui/x-ui.db")
    p.add_argument("--bot-db", default="/root/ArcVPN/database/vpn_bot.db")
    p.add_argument("--xray", default="/usr/local/x-ui/bin/xray-linux-amd64")
    p.add_argument("--flow", default="xtls-rprx-vision")
    p.add_argument("--limit-ip", type=int, default=2)
    p.add_argument("--sni", default="dl.google.com", help="SNI/serverName и dest-хост")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()

    # 1) Клиенты из БД бота
    b = sqlite3.connect(a.bot_db)
    b.row_factory = sqlite3.Row
    rows = b.execute(
        """
        SELECT vk.client_uuid, vk.panel_email, vk.expires_at, vk.traffic_limit, vk.sub_id,
               u.telegram_id,
               CASE WHEN vk.expires_at > datetime('now') THEN 1 ELSE 0 END AS act
        FROM vpn_keys vk JOIN users u ON vk.user_id = u.id
        WHERE vk.server_id = ? AND vk.panel_email IS NOT NULL AND vk.client_uuid IS NOT NULL
        ORDER BY vk.id
        """,
        (a.server,),
    ).fetchall()
    b.close()

    clients = []
    for r in rows:
        clients.append({
            "id": r["client_uuid"],
            "flow": a.flow,
            "email": r["panel_email"],
            "limitIp": a.limit_ip,
            "totalGB": int(r["traffic_limit"] or 0),
            "expiryTime": to_ms(r["expires_at"]),
            "enable": True,  # просроченные отсекутся самим expiryTime
            "tgId": str(r["telegram_id"] or ""),
            "subId": r["sub_id"] or "",
            "reset": 0,
        })
    active = sum(1 for r in rows if r["act"])
    print(f"Клиентов из БД бота (server {a.server}): {len(clients)} (активных {active})")
    if not clients:
        print("❌ В БД бота нет клиентов для этого сервера — прерываю.")
        sys.exit(1)

    # 2) Текущий инбаунд: чиним dest/serverNames, сохраняя ключи
    x = sqlite3.connect(a.xui_db)
    x.row_factory = sqlite3.Row
    row = x.execute("SELECT settings, stream_settings FROM inbounds WHERE id=?", (a.inbound,)).fetchone()
    if not row:
        print(f"❌ Инбаунд id={a.inbound} не найден в {a.xui_db}")
        sys.exit(1)

    stream = json.loads(row["stream_settings"])
    rs = stream.get("realitySettings") or {}
    priv = rs.get("privateKey", "")
    if not priv or len(priv) < 40:
        print(f"❌ В инбаунде нет валидного privateKey (got {priv!r}) — нечего восстанавливать.")
        sys.exit(1)

    pub = derive_public_key(priv, a.xray)
    if not pub:
        # фолбэк: оставить тот, что был, если уже сходился
        pub = (rs.get("settings") or {}).get("publicKey", "")
    short_ids = rs.get("shortIds") or []
    if not short_ids:
        print("⚠️  shortIds пуст — оставляю пустым (Reality допускает, но лучше задать в панели).")

    old_dest, old_sni = rs.get("dest"), rs.get("serverNames")
    rs["dest"] = f"{a.sni}:443"
    rs["serverNames"] = [a.sni]
    rs["show"] = bool(rs.get("show", False))
    rs["xver"] = rs.get("xver", 0)
    rs["shortIds"] = short_ids
    rs["settings"] = {
        "publicKey": pub,
        "fingerprint": "chrome",
        "serverName": "",
        "spiderX": "/",
    }
    stream["realitySettings"] = rs
    if "tcpSettings" not in stream:
        stream["tcpSettings"] = {"acceptProxyProtocol": False, "header": {"type": "none"}}

    print(f"dest:        {old_dest!r} -> {rs['dest']!r}")
    print(f"serverNames: {old_sni!r} -> {rs['serverNames']!r}")
    print(f"privateKey[:6]={priv[:6]}  publicKey[:6]={(pub or '')[:6]}  shortIds={short_ids}")

    new_settings = {"clients": clients, "decryption": "none", "fallbacks": []}

    if not a.apply:
        x.close()
        print("\nDRY-RUN. Ничего не записано. Запустите с --apply, затем выполните: x-ui restart")
        return

    x.execute(
        "UPDATE inbounds SET settings=?, stream_settings=? WHERE id=?",
        (json.dumps(new_settings), json.dumps(stream), a.inbound),
    )
    x.commit()
    x.close()
    print(f"\n✅ Записано: {len(clients)} клиентов + decryption:none + корректный Reality.")
    print("Теперь выполните:  x-ui restart")


if __name__ == "__main__":
    main()
