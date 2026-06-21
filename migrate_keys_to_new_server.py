#!/usr/bin/env python3
"""
Перенос VPN-ключей со старого сервера (панели 3X-UI) на новый — БЕЗ
переимпорта подписки у пользователей.

Как это работает:
- у каждого ключа есть стабильный sub_id (он зашит в ссылку в приложении Happ);
- мы НЕ трогаем sub_id — только пересоздаём клиента на НОВОЙ панели и
  переписываем в БД привязку ключа (server_id, inbound, email, uuid);
- Happ при следующем обновлении подписки сам подтянет конфиг нового сервера.

Сохраняется: email клиента, лимит трафика и точный срок действия (через
push_key_to_panel, который выставляет expiry/totalGB из нашей БД).

ПРЕДВАРИТЕЛЬНО:
1. Новый сервер добавлен в боте (Админка → Серверы → Добавить сервер) и прошёл
   тест подключения. На новой панели есть рабочий inbound (VLESS Reality).
2. Сделан бэкап database/vpn_bot.db.

Запуск:
  python3 migrate_keys_to_new_server.py --old-server 3 --new-server 4            # dry-run
  python3 migrate_keys_to_new_server.py --old-server 3 --new-server 4 --apply    # перенос
  # по умолчанию переносятся ВСЕ ключи с panel_email со старого сервера
  # (active + expired), чтобы на умирающем сервере ничего не осталось.
"""
import argparse
import asyncio
import logging
import sqlite3
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_keys")

DB_PATH = "database/vpn_bot.db"


def fetch_keys(conn: sqlite3.Connection, old_server, active_only: bool):
    """
    old_server: int (конкретный server_id) ИЛИ None — для осиротевших ключей
    (server_id IS NULL, например после удаления старого сервера).
    """
    conn.row_factory = sqlite3.Row
    where_active = "AND vk.expires_at > datetime('now')" if active_only else ""
    if old_server is None:
        server_cond = "vk.server_id IS NULL"
        params = ()
    else:
        server_cond = "vk.server_id = ?"
        params = (old_server,)
    return conn.execute(f"""
        SELECT vk.id, vk.user_id, vk.panel_email, vk.client_uuid, vk.panel_inbound_id,
               vk.expires_at, vk.traffic_limit, vk.traffic_used, vk.sub_id,
               u.telegram_id,
               CASE WHEN vk.expires_at > datetime('now') THEN 1 ELSE 0 END AS is_active
        FROM vpn_keys vk
        JOIN users u ON vk.user_id = u.id
        WHERE {server_cond} AND vk.panel_email IS NOT NULL {where_active}
        ORDER BY vk.id
    """, params).fetchall()


async def migrate():
    parser = argparse.ArgumentParser(description="Перенос ключей на новый сервер")
    parser.add_argument("--old-server", required=True,
                        help="ID старого сервера ИЛИ 'null' для осиротевших ключей (server_id IS NULL)")
    parser.add_argument("--new-server", type=int, required=True, help="ID нового сервера в БД")
    parser.add_argument("--apply", action="store_true", help="Реально переносить (иначе dry-run)")
    parser.add_argument("--active-only", action="store_true", help="Только активные ключи")
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    # old_server: None для режима server_id IS NULL, иначе int
    if str(args.old_server).lower() in ("null", "none", "0"):
        old_server = None
    else:
        old_server = int(args.old_server)

    if old_server == args.new_server:
        print("❌ old-server и new-server не должны совпадать")
        return

    # Проверяем, что новый сервер существует и доступен.
    from database.requests import get_server_by_id, update_vpn_key_connection
    from bot.services.vpn_api import get_client, push_key_to_panel, close_all_clients
    import config

    new_server = get_server_by_id(args.new_server)
    if not new_server:
        print(f"❌ Новый сервер id={args.new_server} не найден в БД. Сначала добавьте его в админке.")
        return

    device_limit = getattr(config, "DEFAULT_LIMIT_IP", 2)

    conn = sqlite3.connect(args.db)
    keys = fetch_keys(conn, old_server, args.active_only)

    old_label = "NULL (осиротевшие)" if old_server is None else old_server
    print("=" * 70)
    print(f"Перенос ключей: сервер {old_label} → {args.new_server} "
          f"({new_server['name']})")
    print("=" * 70)
    if not keys:
        print("Ключей для переноса не найдено.")
        conn.close()
        return
    active = sum(1 for k in keys if k["is_active"])
    for k in keys:
        mark = "🟢" if k["is_active"] else "🔴"
        print(f"  {mark} key#{k['id']:>5} tg={k['telegram_id']} email={k['panel_email']} до {k['expires_at']}")
    print("-" * 70)
    print(f"Всего: {len(keys)} (активных: {active}, истёкших: {len(keys) - active})")

    if not args.apply:
        print("\nDRY-RUN. Ничего не перенесено. Для переноса добавьте --apply.")
        print("Перед --apply сделайте бэкап database/vpn_bot.db и остановите бота.")
        conn.close()
        return

    # Готовим клиент новой панели + inbound.
    try:
        client = await get_client(args.new_server)
        inbounds = await client.get_inbounds()
    except Exception as e:
        print(f"❌ Не удалось подключиться к новой панели: {e}")
        conn.close()
        await close_all_clients()
        return
    if not inbounds:
        print("❌ На новой панели нет inbound. Создайте VLESS Reality inbound и повторите.")
        conn.close()
        await close_all_clients()
        return
    new_inbound_id = inbounds[0]["id"]
    flow = await client.get_inbound_flow(new_inbound_id)

    migrated = 0
    failed = []
    now = datetime.now()
    for k in keys:
        key_id = k["id"]
        email = k["panel_email"]
        try:
            # Срок: для активных — остаток дней (мин. 1); точное значение выставит
            # push_key_to_panel из БД ниже. Для истёкших создаём с 1 днём и тут же
            # перезапишем реальный (прошедший) срок → клиент будет отключён.
            try:
                exp = datetime.fromisoformat(k["expires_at"]) if k["expires_at"] else now
                days_left = max(1, (exp - now).days + 1)
            except (ValueError, TypeError):
                days_left = 1

            total_gb = int((k["traffic_limit"] or 0) / (1024 ** 3))

            res = await client.add_client(
                inbound_id=new_inbound_id,
                email=email,
                total_gb=total_gb,
                expire_days=days_left,
                limit_ip=device_limit,
                enable=True,
                tg_id=str(k["telegram_id"]),
                flow=flow,
            )
            new_uuid = res["uuid"]

            # Перепривязываем ключ в БД (sub_id НЕ меняется!).
            update_vpn_key_connection(key_id, args.new_server, new_inbound_id, email, new_uuid)

            # Выставляем точный срок/лимит из БД (корректно для истёкших тоже).
            await push_key_to_panel(key_id)

            migrated += 1
            logger.info("✅ key#%s перенесён (%s)", key_id, email)
        except Exception as e:
            failed.append(key_id)
            logger.error("❌ key#%s не перенесён: %s", key_id, e)

    conn.close()
    await close_all_clients()

    print("\n" + "=" * 70)
    print(f"✅ Перенесено: {migrated} из {len(keys)}")
    if failed:
        print(f"⚠️  Не удалось: {failed}")
    print("=" * 70)
    print("Старый сервер можно деактивировать/удалить в админке после проверки.")
    print("Подписки в Happ обновятся автоматически (в течение ~24ч или по ручному обновлению).")


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except KeyboardInterrupt:
        sys.exit(1)
