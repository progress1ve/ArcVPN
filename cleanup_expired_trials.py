#!/usr/bin/env python3
"""
Аккуратное удаление ИСТЁКШИХ ПРОБНЫХ подписок, которые НИКОГДА не превращались
в платные (не продлевались).

Зачем: после перехода на модель «одна подписка» у некоторых пользователей висит
лишний истёкший пробный ключ рядом с купленным. Его нужно убрать — но НЕ трогая
те пробные ключи, которые продлили (они уже стали месячными/платными).

Ключ считается «чистым непродлённым триалом» и удаляется ТОЛЬКО если ВСЕ условия:
  1. expires_at <= now            — подписка истекла;
  2. tariff_id IS NULL            — пробные ключи создаются с tariff_id=None
     (см. bot/handlers/user/trial.py). При ЛЮБОМ продлении _apply_renew_order →
     update_key_tariff проставляет реальный платный tariff_id, поэтому такой ключ
     под фильтр уже НЕ попадёт;
  3. по ключу НЕТ ни одного оплаченного НЕ-trial платежа
     (payments.vpn_key_id = key.id AND status='paid' AND payment_type != 'trial').

Дополнительно (защита от удаления единственной подписки):
  4. у пользователя есть ХОТЯ БЫ ещё один ключ кроме этого
     (если триал — единственный ключ пользователя, не удаляем: пусть продлевает).

По умолчанию РЕЖИМ DRY-RUN: только показывает, что было бы удалено.
Чтобы реально удалить (БД + клиент на панели 3X-UI):  python cleanup_expired_trials.py --apply

Перед --apply сделайте бэкап database/vpn_bot.db.
"""
import argparse
import asyncio
import logging
import sqlite3
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleanup_trials")

DB_PATH = "database/vpn_bot.db"


def find_unconverted_expired_trials(conn: sqlite3.Connection):
    """Возвращает список ключей-кандидатов на удаление (см. критерии в докстринге модуля)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            vk.id, vk.user_id, vk.server_id, vk.panel_inbound_id,
            vk.client_uuid, vk.panel_email, vk.custom_name, vk.expires_at,
            u.telegram_id
        FROM vpn_keys vk
        JOIN users u ON vk.user_id = u.id
        WHERE vk.expires_at <= datetime('now')          -- 1) истёк
          AND vk.tariff_id IS NULL                      -- 2) непродлённый триал (tariff_id=None)
          AND NOT EXISTS (                              -- 3) нет оплаченных не-trial платежей
              SELECT 1 FROM payments p
              WHERE p.vpn_key_id = vk.id
                AND p.status = 'paid'
                AND p.payment_type != 'trial'
          )
          AND (                                         -- 4) у пользователя есть ещё ключи
              SELECT COUNT(*) FROM vpn_keys vk2 WHERE vk2.user_id = vk.user_id
          ) > 1
        ORDER BY vk.user_id, vk.id
        """
    ).fetchall()
    return rows


async def delete_panel_client(row) -> bool:
    """Удаляет клиента триала с панели 3X-UI. Возвращает True если удалён или уже отсутствует."""
    if not (row["server_id"] and row["panel_inbound_id"] and row["client_uuid"]):
        return True  # неконфигурированный ключ — на панели его нет
    try:
        from bot.services.vpn_api import get_client
        client = await get_client(row["server_id"])
        await client.delete_client(row["panel_inbound_id"], row["client_uuid"])
        logger.info("  ↳ панель: клиент %s удалён", row["panel_email"])
        return True
    except Exception as e:
        msg = str(e).lower()
        if "not found" in msg or "не найден" in msg or "no client" in msg:
            logger.info("  ↳ панель: клиент %s уже отсутствует", row["panel_email"])
            return True
        logger.warning("  ↳ панель: не удалось удалить %s: %s", row["panel_email"], e)
        return False


def delete_key_db(conn: sqlite3.Connection, key_id: int) -> None:
    """Удаляет ключ из БД, сохраняя историю платежей (отвязывает vpn_key_id)."""
    conn.execute("UPDATE payments SET vpn_key_id = NULL WHERE vpn_key_id = ?", (key_id,))
    conn.execute("DELETE FROM notification_log WHERE vpn_key_id = ?", (key_id,))
    conn.execute("DELETE FROM vpn_keys WHERE id = ?", (key_id,))


async def main():
    parser = argparse.ArgumentParser(description="Удаление истёкших непродлённых пробных подписок")
    parser.add_argument("--apply", action="store_true",
                        help="Реально удалить (по умолчанию dry-run — только показать)")
    parser.add_argument("--db", default=DB_PATH, help=f"Путь к БД (по умолчанию {DB_PATH})")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    candidates = find_unconverted_expired_trials(conn)

    print("=" * 70)
    print("Истёкшие НЕпродлённые пробные подписки (кандидаты на удаление)")
    print("=" * 70)
    if not candidates:
        print("Кандидатов не найдено — чистить нечего.")
        conn.close()
        return

    for r in candidates:
        print(f"  key#{r['id']:>5} | tg={r['telegram_id']} | "
              f"имя='{r['custom_name'] or 'Пробная подписка'}' | истёк {r['expires_at']}")
    print("-" * 70)
    print(f"Всего кандидатов: {len(candidates)}")

    if not args.apply:
        print("\nDRY-RUN. Ничего не удалено.")
        print("Для реального удаления: python cleanup_expired_trials.py --apply")
        print("(Сначала сделайте бэкап database/vpn_bot.db!)")
        conn.close()
        return

    print("\n--apply: выполняю удаление (панель + БД)...")
    deleted = 0
    panel_failed = []
    for r in candidates:
        logger.info("Удаляю key#%s (tg=%s)...", r["id"], r["telegram_id"])
        ok = await delete_panel_client(r)
        if not ok:
            # Если клиента на панели удалить не удалось — НЕ удаляем из БД,
            # чтобы не остался «осиротевший» клиент на сервере.
            panel_failed.append(r["id"])
            logger.warning("  ↳ пропускаю удаление из БД (panel delete failed)")
            continue
        delete_key_db(conn, r["id"])
        deleted += 1

    conn.commit()
    conn.close()

    # Закрываем http-клиенты панели, чтобы скрипт корректно завершился.
    try:
        from bot.services.vpn_api import close_all_clients
        await close_all_clients()
    except Exception:
        pass

    print("\n" + "=" * 70)
    print(f"✅ Удалено ключей: {deleted} из {len(candidates)}")
    if panel_failed:
        print(f"⚠️  Пропущено (ошибка панели, повторите позже): {panel_failed}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
