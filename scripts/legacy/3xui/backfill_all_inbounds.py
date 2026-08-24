#!/usr/bin/env python3
"""
Разовый бэкфилл: домиррорить уже существующих клиентов во ВСЕ inbound сервера.

Зачем: ключи, перенесённые ранее, лежат только в одном inbound (VLESS). Чтобы у
текущих пользователей в подписке появились все конфиги (VLESS + Hysteria2 + ...),
этот скрипт добавляет того же клиента (тот же uuid/email, тот же срок/лимит) в те
inbound сервера, где его ещё нет. Рабочий VLESS-инбаунд НЕ трогаем.

Как это работает:
- по каждому ключу сервера читаем client_uuid/panel_email/срок/лимит из БД;
- provision_client_all_inbounds(only_missing=True) добавляет клиента ТОЛЬКО в
  недостающие inbound, переиспользуя client_uuid как секрет (id для VLESS,
  password для Hysteria2);
- push_key_to_panel выставляет точный срок/лимит из БД во ВСЕХ inbound.

sub_id ключа НЕ меняется — переимпорт подписки пользователю не нужен.

ПРЕДВАРИТЕЛЬНО:
1. На сервере должны быть нужные inbound (VLESS + Hysteria2 и т.п.).
2. Бэкап x-ui.db на сервере (панель) и database/vpn_bot.db.

Запуск:
  python3 scripts/legacy/3xui/backfill_all_inbounds.py --server 10               # dry-run
  python3 scripts/legacy/3xui/backfill_all_inbounds.py --server 10 --apply       # бэкфилл
  python3 scripts/legacy/3xui/backfill_all_inbounds.py --server 10 --apply --active-only
"""
import argparse
import asyncio
import logging
import sqlite3
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_all_inbounds")

DB_PATH = "database/vpn_bot.db"


def fetch_keys(conn: sqlite3.Connection, server_id: int, active_only: bool):
    conn.row_factory = sqlite3.Row
    where_active = "AND vk.expires_at > datetime('now')" if active_only else ""
    return conn.execute(f"""
        SELECT vk.id, vk.user_id, vk.panel_email, vk.client_uuid, vk.panel_inbound_id,
               vk.expires_at, vk.traffic_limit,
               u.telegram_id,
               CASE WHEN vk.expires_at > datetime('now') THEN 1 ELSE 0 END AS is_active
        FROM vpn_keys vk
        JOIN users u ON vk.user_id = u.id
        WHERE vk.server_id = ? AND vk.panel_email IS NOT NULL
              AND vk.client_uuid IS NOT NULL {where_active}
        ORDER BY vk.id
    """, (server_id,)).fetchall()


async def backfill():
    parser = argparse.ArgumentParser(description="Бэкфилл клиентов во все inbound сервера")
    parser.add_argument("--server", type=int, default=10, help="ID сервера в БД (по умолчанию 10)")
    parser.add_argument("--apply", action="store_true", help="Реально домиррорить (иначе dry-run)")
    parser.add_argument("--active-only", action="store_true", help="Только активные ключи")
    parser.add_argument("--no-push", action="store_true", help="Не выставлять точный срок через push_key_to_panel")
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    import config
    from database.requests import get_server_by_id
    from bot.services.vpn_api import get_client, push_key_to_panel, close_all_clients

    server = get_server_by_id(args.server)
    if not server:
        print(f"❌ Сервер id={args.server} не найден в БД.")
        return

    device_limit = getattr(config, "DEFAULT_LIMIT_IP", 2)

    conn = sqlite3.connect(args.db)
    keys = fetch_keys(conn, args.server, args.active_only)

    print("=" * 70)
    print(f"Бэкфилл клиентов во все inbound сервера {args.server} ({server['name']})")
    print("=" * 70)
    if not keys:
        print("Ключей для бэкфилла не найдено.")
        conn.close()
        return

    # Показываем, какие inbound есть на сервере.
    try:
        client = await get_client(args.server)
        inbounds = await client.get_inbounds()
        print("Inbound на сервере:")
        for ib in inbounds:
            print(f"  - id={ib.get('id')} [{ib.get('protocol')}] {ib.get('remark')}")
    except Exception as e:
        print(f"❌ Не удалось подключиться к панели: {e}")
        conn.close()
        await close_all_clients()
        return
    print("-" * 70)

    active = sum(1 for k in keys if k["is_active"])
    for k in keys:
        mark = "🟢" if k["is_active"] else "🔴"
        print(f"  {mark} key#{k['id']:>5} tg={k['telegram_id']} email={k['panel_email']} до {k['expires_at']}")
    print("-" * 70)
    print(f"Всего: {len(keys)} (активных: {active}, истёкших: {len(keys) - active})")

    if not args.apply:
        print("\nDRY-RUN. Ничего не изменено. Для бэкфилла добавьте --apply.")
        print("Перед --apply сделайте бэкап x-ui.db (панель) и database/vpn_bot.db.")
        conn.close()
        await close_all_clients()
        return

    done = 0
    failed = []
    now = datetime.now()
    for k in keys:
        key_id = k["id"]
        email = k["panel_email"]
        try:
            try:
                exp = datetime.fromisoformat(k["expires_at"]) if k["expires_at"] else now
                days_left = max(1, (exp - now).days + 1)
            except (ValueError, TypeError):
                days_left = 1

            total_gb = int((k["traffic_limit"] or 0) / (1024 ** 3))

            # Добавляем клиента ТОЛЬКО в недостающие inbound, переиспользуя
            # client_uuid как секрет. Рабочий VLESS-инбаунд не трогаем.
            await client.provision_client_all_inbounds(
                email=email,
                total_gb=total_gb,
                expire_days=days_left,
                limit_ip=device_limit,
                enable=k["is_active"] == 1,
                tg_id=str(k["telegram_id"]),
                secret=k["client_uuid"],
                only_missing=True,
            )

            # Выставляем точный срок/лимит из БД во всех inbound (фан-аут).
            if not args.no_push:
                await push_key_to_panel(key_id)

            done += 1
            logger.info("✅ key#%s домиррорен (%s)", key_id, email)
        except Exception as e:
            failed.append(key_id)
            logger.error("❌ key#%s не домиррорен: %s", key_id, e)

    conn.close()
    await close_all_clients()

    print("\n" + "=" * 70)
    print(f"✅ Домирроррено: {done} из {len(keys)}")
    if failed:
        print(f"⚠️  Не удалось: {failed}")
    print("=" * 70)
    print("Пользователям переимпорт не нужен — sub_id не менялся. Конфиги появятся")
    print("в Happ при следующем обновлении подписки (или сразу по ручному обновлению).")


if __name__ == "__main__":
    try:
        asyncio.run(backfill())
    except KeyboardInterrupt:
        sys.exit(1)
