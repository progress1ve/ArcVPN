"""
Модуль для автоматических задач.

Включает:
- Отправку суточной статистики администраторам
- Создание и отправку архива с бэкапами (БД бота + VPN панелей)
- Синхронизацию трафика с VPN-серверами (каждые 5 минут)
- Уведомления о заканчивающемся трафике
"""

import asyncio
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, time as dt_time, timedelta
from io import BytesIO
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile, FSInputFile

from config import ADMIN_IDS, GITHUB_REPO_URL
from database.requests import (
    get_all_servers, get_users_stats, get_keys_stats,
    get_daily_payments_stats, get_new_users_count_today,
    get_setting, get_expiring_keys, get_expired_keys_today, is_notification_sent_today,
    log_notification_sent, notification_allowed,
)
from database.db_statistics import (
    get_revenue_stats, get_new_users_stats, get_subscriptions_stats,
    get_conversion_stats,
)
from bot.services.vpn_api import get_client_from_server_data, VPNAPIError, format_traffic
from bot.services.notifications import send_to_user, notify_admins
from bot.services.remnawave_stats import get_remnawave_network_stats, remnawave_authority_enabled
from bot.utils.git_utils import check_for_updates
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Путь к базе данных бота
BOT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'vpn_bot.db')

# Корневая папка проекта и папка для локальных бэкапов
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backup')

# Сколько дней хранить локальные бэкапы
BACKUP_RETENTION_DAYS = 7


async def _send_lifecycle_batch(bot: Bot) -> None:
    """Send each lifecycle message once; database uniqueness prevents duplicates."""
    from database.connection import get_db

    with get_db() as conn:
        rating_users = conn.execute("""
            SELECT u.id, u.telegram_id FROM users u
            WHERE u.created_at <= datetime('now', '-5 days')
              AND u.created_at >= COALESCE((SELECT value FROM settings WHERE key='lifecycle_eligible_after'), datetime('now'))
              AND EXISTS (SELECT 1 FROM vpn_keys vk WHERE vk.user_id=u.id AND vk.expires_at > datetime('now'))
              AND NOT EXISTS (SELECT 1 FROM lifecycle_events le WHERE le.user_id=u.id AND le.event_key='day5_rating')
            LIMIT 25
        """).fetchall()
        winback_users = conn.execute("""
            SELECT u.id, u.telegram_id FROM users u
            WHERE u.created_at >= COALESCE((SELECT value FROM settings WHERE key='lifecycle_eligible_after'), datetime('now'))
              AND EXISTS (
                SELECT 1 FROM vpn_keys vk WHERE vk.user_id=u.id
                AND vk.expires_at BETWEEN datetime('now', '-10 days') AND datetime('now', '-2 days')
            )
              AND NOT EXISTS (SELECT 1 FROM vpn_keys active WHERE active.user_id=u.id AND active.expires_at > datetime('now'))
              AND NOT EXISTS (SELECT 1 FROM lifecycle_events le WHERE le.user_id=u.id AND le.event_key='expired_winback')
            LIMIT 25
        """).fetchall()

    assets = os.path.join(PROJECT_ROOT, "bot", "assets")
    for row in rating_users:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="😕 1", callback_data="lifecycle_rating:1"),
            InlineKeyboardButton(text="🙂 3", callback_data="lifecycle_rating:3"),
            InlineKeyboardButton(text="🤩 5", callback_data="lifecycle_rating:5"),
        ]])
        try:
            await bot.send_photo(
                row["telegram_id"], FSInputFile(os.path.join(assets, "arc-feedback-v1.png")),
                caption=(
                    "💙 <b>Поможете сделать ArcVPN лучше?</b>\n\n"
                    "Вы пользуетесь сервисом уже 5 дней. Как вам ArcVPN?\n\n"
                    "Поставьте оценку одним нажатием — мы читаем каждый ответ."
                ),
                reply_markup=kb,
            )
            with get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO lifecycle_events(user_id,event_key) VALUES (?, 'day5_rating')", (row["id"],))
        except Exception as exc:
            logger.warning("Lifecycle rating delivery failed for %s: %s", row["telegram_id"], exc)

    for row in winback_users:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Дорого", callback_data="lifecycle_winback:expensive")],
            [InlineKeyboardButton(text="📉 Плохо работало", callback_data="lifecycle_winback:quality")],
            [InlineKeyboardButton(text="🔄 Пользуюсь другим VPN", callback_data="lifecycle_winback:competitor")],
            [InlineKeyboardButton(text="💬 Другое", callback_data="lifecycle_winback:other")],
        ])
        try:
            await bot.send_photo(
                row["telegram_id"], FSInputFile(os.path.join(assets, "arc-winback-v1.png")),
                caption=(
                    "👋 <b>Ваша подписка закончилась</b>\n\n"
                    "Расскажите, почему не стали продлевать. За один ответ мы сразу подарим "
                    "<b>3 дня ArcVPN</b>, чтобы вы могли проверить сервис ещё раз."
                ), reply_markup=kb,
            )
            with get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO lifecycle_events(user_id,event_key) VALUES (?, 'expired_winback')", (row["id"],))
        except Exception as exc:
            logger.warning("Lifecycle winback delivery failed for %s: %s", row["telegram_id"], exc)


async def run_lifecycle_scheduler(bot: Bot) -> None:
    """Check lifecycle campaigns hourly, with a short startup delay."""
    await asyncio.sleep(90)
    while True:
        try:
            await _send_lifecycle_batch(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Lifecycle scheduler iteration failed")
        await asyncio.sleep(3600)


def _fmt_money(rev: dict) -> str:
    """Форматирует доход за период из get_revenue_stats() в строку '… ₽ · $… · ⭐…'."""
    parts = []
    rub = rev.get('total_rub', 0) or 0
    usd = rev.get('total_usd', 0) or 0
    stars = rev.get('total_stars', 0) or 0
    if rub:
        parts.append(f"{rub:g} ₽".replace('.', ','))
    if usd:
        parts.append(f"${usd:g}".replace('.', ','))
    if stars:
        parts.append(f"⭐{stars}")
    cnt = rev.get('count', 0) or 0
    money = " · ".join(parts) if parts else "0"
    return f"{money} ({cnt})"


async def collect_daily_stats() -> str:
    """
    Собирает богатый суточный отчёт для администраторов.

    Использует агрегированные функции db_statistics для бизнес-метрик и
    read-only Remnawave API для актуального состава и состояния нод.

    Returns:
        Готовый HTML-текст отчёта.
    """
    today = datetime.now().strftime("%d.%m.%Y")

    # --- собираем метрики (каждый блок защищён, чтобы один сбой не уронил отчёт) ---
    try:
        rev = get_revenue_stats()
    except Exception as e:
        logger.warning(f"daily stats: revenue error: {e}")
        rev = {}
    try:
        nu = get_new_users_stats()
    except Exception as e:
        logger.warning(f"daily stats: new users error: {e}")
        nu = {}
    try:
        users = get_users_stats()
    except Exception:
        users = {}
    try:
        subs = get_subscriptions_stats()
    except Exception as e:
        logger.warning(f"daily stats: subs error: {e}")
        subs = {}
    try:
        conv = get_conversion_stats()
    except Exception as e:
        logger.warning(f"daily stats: conversion error: {e}")
        conv = {}
    try:
        network = await get_remnawave_network_stats()
    except Exception as e:
        logger.warning(f"daily stats: Remnawave error: {e}")
        network = {"users": 0, "nodes": []}

    day_rev = rev.get('day', {}) if rev else {}
    week_rev = rev.get('week', {}) if rev else {}
    month_rev = rev.get('month', {}) if rev else {}

    # Remnawave is the production authority; the local servers table contains
    # historical 3x-ui assignments and must not be presented as fleet health.
    nodes = network.get("nodes", [])
    if nodes:
        srv_lines = []
        for node in nodes:
            mark = "🟢" if node.get("connected") else ("⚪" if node.get("disabled") else "🔴")
            srv_lines.append(
                f"  {mark} <b>{node['name']}</b>: {node.get('users_online', 0)} онлайн · "
                f"{node.get('traffic_gb', 0):.1f} ГБ"
            )
        servers_text = "\n".join(srv_lines)
    else:
        servers_text = "  Данные Remnawave временно недоступны"

    report = f"""📊 <b>Суточная статистика — {today}</b>

💰 <b>Доход (платежей):</b>
  Сегодня: {_fmt_money(day_rev)}
  За неделю: {_fmt_money(week_rev)}
  За месяц: {_fmt_money(month_rev)}

👥 <b>Пользователи:</b>
  Всего: {users.get('total', nu.get('total', 0))}
  Новых за сутки: {nu.get('day', 0)}
  За неделю: {nu.get('week', 0)}

🔑 <b>Подписки:</b>
  Активных: {subs.get('active', 0)}
  Истёкших: {subs.get('expired', 0)}
  Создано за сутки: {subs.get('day', 0)}

📈 <b>Конверсия (триал → платно):</b>
  Платящих: {conv.get('paid_users', 0)} · конверсия {conv.get('conversion_rate', 0):.0f}%

🖥️ <b>Серверы:</b>
{servers_text}
  Пользователей в Remnawave: {network.get('users', 0)}
"""
    return report


async def send_daily_stats(bot: Bot) -> None:
    """
    Отправляет суточную статистику всем администраторам.
    
    Args:
        bot: Экземпляр бота
    """
    try:
        report = await collect_daily_stats()
        await notify_admins(bot, report)
        logger.info("✅ Суточная статистика отправлена")
    except Exception as e:
        logger.error(f"Ошибка при отправке суточной статистики: {e}")


async def create_backup_archive() -> Optional[bytes]:
    """
    Создаёт ZIP-архив с бэкапами.
    
    Включает:
    - vpn_bot.db — база данных бота
    - server_NAME_x-ui.db — база каждого VPN-сервера
    
    Returns:
        Байты ZIP-архива или None при ошибке
    """
    try:
        archive_buffer = BytesIO()
        
        with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Добавляем базу данных бота
            bot_db_path = os.path.abspath(BOT_DB_PATH)
            if os.path.exists(bot_db_path):
                zf.write(bot_db_path, 'vpn_bot.db')
                logger.info(f"Добавлен в архив: vpn_bot.db ({os.path.getsize(bot_db_path)} байт)")
            else:
                logger.warning(f"База данных бота не найдена: {bot_db_path}")
            
            # Скачиваем и добавляем бэкапы VPN-серверов
            servers = get_all_servers()
            for server in servers:
                if not server.get('is_active'):
                    continue
                    
                try:
                    client = get_client_from_server_data(server)
                    backup_data = await client.get_database_backup()
                    
                    # Имя файла: server_НАЗВАНИЕ_x-ui.db
                    safe_name = server['name'].replace(' ', '_').replace('/', '_')
                    filename = f"server_{safe_name}_x-ui.db"
                    
                    zf.writestr(filename, backup_data)
                    logger.info(f"Добавлен в архив: {filename} ({len(backup_data)} байт)")
                    
                except VPNAPIError as e:
                    logger.warning(f"Не удалось скачать бэкап сервера {server['name']}: {e}")
                except Exception as e:
                    logger.error(f"Ошибка при скачивании бэкапа сервера {server['name']}: {e}")
        
        archive_buffer.seek(0)
        return archive_buffer.read()
        
    except Exception as e:
        logger.error(f"Ошибка при создании архива бэкапов: {e}")
        return None


async def save_local_backup() -> None:
    """
    Сохраняет локальные копии всех баз данных в папку backup/YYYY-MM-DD/.
    
    Файлы хранятся неархивированными (.db) для прямого доступа
    через sqlite3 из Python без необходимости распаковки.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    day_dir = os.path.join(BACKUP_DIR, today)
    
    try:
        os.makedirs(day_dir, exist_ok=True)
        
        # Сохраняем базу данных бота
        bot_db_path = os.path.abspath(BOT_DB_PATH)
        if os.path.exists(bot_db_path):
            dest = os.path.join(day_dir, 'vpn_bot.db')
            shutil.copy2(bot_db_path, dest)
            logger.info(f"Локальный бэкап: vpn_bot.db ({os.path.getsize(dest)} байт)")
        else:
            logger.warning(f"База данных бота не найдена: {bot_db_path}")
        
        # Скачиваем базы VPN-серверов
        servers = get_all_servers()
        for server in servers:
            if not server.get('is_active'):
                continue
            
            try:
                client = get_client_from_server_data(server)
                backup_data = await client.get_database_backup()
                
                safe_name = server['name'].replace(' ', '_').replace('/', '_')
                filename = f"server_{safe_name}_x-ui.db"
                dest = os.path.join(day_dir, filename)
                
                with open(dest, 'wb') as f:
                    f.write(backup_data)
                
                logger.info(f"Локальный бэкап: {filename} ({len(backup_data)} байт)")
                
            except VPNAPIError as e:
                logger.warning(f"Не удалось скачать бэкап сервера {server['name']}: {e}")
            except Exception as e:
                logger.error(f"Ошибка при скачивании бэкапа сервера {server['name']}: {e}")
        
        logger.info(f"✅ Локальные бэкапы сохранены в {day_dir}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении локальных бэкапов: {e}")


def cleanup_old_backups() -> None:
    """
    Удаляет папки с бэкапами старше BACKUP_RETENTION_DAYS (7 дней).
    
    Проверяет имена подпапок в формате YYYY-MM-DD и удаляет те,
    чья дата старше порога хранения.
    """
    if not os.path.exists(BACKUP_DIR):
        return
    
    cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    removed_count = 0
    
    try:
        for entry in os.listdir(BACKUP_DIR):
            entry_path = os.path.join(BACKUP_DIR, entry)
            if not os.path.isdir(entry_path):
                continue
            
            # Проверяем формат имени папки YYYY-MM-DD
            try:
                folder_date = datetime.strptime(entry, "%Y-%m-%d")
            except ValueError:
                continue  # Пропускаем папки с нестандартным именем
            
            if folder_date < cutoff_date:
                shutil.rmtree(entry_path)
                removed_count += 1
                logger.info(f"Удалён старый бэкап: {entry}")
        
        if removed_count > 0:
            logger.info(f"🗑️ Удалено старых бэкапов: {removed_count}")
    
    except Exception as e:
        logger.error(f"Ошибка при очистке старых бэкапов: {e}")


async def send_backup_archive(bot: Bot) -> None:
    """
    Создаёт и отправляет архив бэкапов всем администраторам.
    Также сохраняет локальные копии и чистит старые бэкапы.
    
    Args:
        bot: Экземпляр бота
    """
    try:
        # Сохраняем локальные бэкапы (неархивированные .db файлы)
        await save_local_backup()
        
        # Удаляем бэкапы старше 7 дней
        cleanup_old_backups()
        
        # Создаём ZIP-архив для отправки в Telegram
        archive_data = await create_backup_archive()
        
        if not archive_data:
            logger.error("Не удалось создать архив бэкапов")
            return
        
        # Имя файла с датой
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"backup_{today}.zip"
        
        # Отправляем админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=BufferedInputFile(archive_data, filename=filename),
                    caption=f"📦 <b>Ежедневный бэкап за {today}</b>\n\nСодержит базы данных бота и VPN-серверов.",
                    parse_mode="HTML"
                )
                logger.info(f"Бэкап отправлен админу {admin_id}")
            except Exception as e:
                logger.warning(f"Не удалось отправить бэкап админу {admin_id}: {e}")
        
        logger.info(f"✅ Бэкап отправлен ({len(archive_data)} байт)")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке бэкапа: {e}")


def _pluralize_days(n: int) -> str:
    """Возвращает правильную форму слова 'день' для числа n."""
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} день"
    if n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return f"{n} дня"
    return f"{n} дней"


def _expired_keyboard(vpn_key_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚡ Продлить подписку", callback_data=f"key_renew:{vpn_key_id}"))
    builder.row(InlineKeyboardButton(text="🔐 Моя подписка", callback_data="my_keys"))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    return builder.as_markup()


async def notify_expired_subscription(bot: Bot, vpn_key_id: int, telegram_id: int, keyname: str) -> bool:
    """
    Единое уведомление об истёкшей подписке (источник истины — планировщик трафика).

    Дедупликация — через is_notification_sent_today/log_notification_sent (7 дней).
    Вынесено в один хелпер, чтобы не дублировать логику в двух местах.
    """
    if (not telegram_id or not notification_allowed(telegram_id, "expiry")
            or is_notification_sent_today(vpn_key_id, "expired", 30)):
        return False
    from bot.services.notifications import render_template
    default_expired = (
        '🔒 <b>Подписка ArcVPN закончилась</b>\n\n'
        'VPN больше не подключается, но ваши настройки и устройства сохранены.\n\n'
        'Продлите подписку — доступ восстановится автоматически, заново настраивать Happ не нужно.'
    )
    text, photo = render_template(
        'expired_notification_text', default_expired,
        {'%имяподписки%': keyname, '%имяключа%': keyname},
    )
    ok = await send_to_user(bot, telegram_id, text, reply_markup=_expired_keyboard(vpn_key_id), photo=photo)
    if ok:
        log_notification_sent(vpn_key_id, "expired")
    return ok


async def check_and_send_expiry_notifications(bot: Bot) -> None:
    """
    Отправляет уведомления о СКОРО истекающих подписках (за N дней).

    Уведомления об УЖЕ истёкших подписках шлёт планировщик трафика
    (sync_traffic_stats → notify_expired_subscription), чтобы не дублировать.
    """
    logger.info("⏳ Запуск проверки истекающих подписок...")
    try:
        from bot.services.notifications import render_template
        days = int(get_setting('notification_days', '3'))

        default_notification = (
            '⏳ <b>ArcVPN скоро закончится</b>\n\n'
            'Осталось: <b>%дней%</b>. Продлите заранее, чтобы VPN продолжил работать без перерыва.\n\n'
            'Настройки и устройства сохранятся, повторно импортировать подписку не потребуется.'
        )

        expiring_keys = get_expiring_keys(days)
        sent_count = 0

        for key_info in expiring_keys:
            vpn_key_id = key_info['vpn_key_id']
            user_telegram_id = key_info['user_telegram_id']
            days_left = key_info['days_left']
            keyname = key_info.get('custom_name', f"Подписка #{vpn_key_id}")
            expiring_kb = _expired_keyboard(vpn_key_id)

            if not notification_allowed(user_telegram_id, "expiry"):
                continue
            stage = "expiring_1d" if days_left <= 1 else "expiring_3d"
            if is_notification_sent_today(vpn_key_id, stage, 30):
                continue

            text, photo = render_template(
                'notification_text', default_notification,
                {
                    '%дней%': _pluralize_days(days_left),
                    '%имяподписки%': keyname,
                    '%имяключа%': keyname,
                },
            )
            if await send_to_user(bot, user_telegram_id, text, reply_markup=expiring_kb, photo=photo):
                log_notification_sent(vpn_key_id, stage)
                sent_count += 1
            await asyncio.sleep(0.05)

        logger.info(f"📬 Отправлено {sent_count} уведомлений об истечении" if sent_count
                    else "Нет подписок требующих уведомления")

    except Exception as e:
        logger.error(f"Ошибка в check_and_send_expiry_notifications: {e}")


def get_seconds_until(target_hour: int, target_minute: int = 0) -> int:
    """
    Вычисляет количество секунд до указанного времени суток.
    
    Args:
        target_hour: Целевой час (0-23)
        target_minute: Целевая минута (0-59)
    
    Returns:
        Количество секунд до целевого времени
    """
    now = datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    # Если время уже прошло сегодня, планируем на завтра
    if target <= now:
        target += timedelta(days=1)
    
    return int((target - now).total_seconds())


async def refresh_exchange_rate() -> None:
    """Обновляет курс USD/RUB из ЦБ РФ и сохраняет в БД.

    Цены Stars/крипты считаются от price_rub по этому курсу (см. db_tariffs.py
    _recompute_prices), поэтому актуальность курса важна для корректных сумм.
    """
    try:
        from bot.services.exchange_rate import get_usd_rub_rate
        rate_cents = await get_usd_rub_rate()  # сам пишет в БД при успехе
        logger.info(f"💱 Курс USD/RUB обновлён: {rate_cents / 100:.2f} ₽")
    except Exception as e:
        logger.error(f"Не удалось обновить курс USD/RUB: {e}")


async def run_daily_tasks(bot: Bot) -> None:
    """
    Фоновая задача для запуска ежедневных заданий.

    Расписание (изменено на 09:00 UTC = 12:00 МСК):
    - 09:00 — Уведомления об истечении подписок
    - 09:05 — Суточная статистика
    - 09:10 — Архив с бэкапами

    Args:
        bot: Экземпляр бота
    """
    logger.info("🕐 Планировщик ежедневных задач запущен")

    # Обновляем курс валют сразу при старте (курс в БD мог устареть)
    await refresh_exchange_rate()

    while True:
        try:
            # Ждём до 09:00 UTC (12:00 МСК) вместо 03:00
            seconds_to_wait = get_seconds_until(9, 0)
            logger.info(f"Следующий запуск задач через {seconds_to_wait // 3600}ч {(seconds_to_wait % 3600) // 60}м")

            await asyncio.sleep(seconds_to_wait)

            # 09:00 - Обновляем курс валют (для актуальных цен Stars/крипты)
            await refresh_exchange_rate()
            
            # 09:00 - Отправляем уведомления пользователям (ПЕРВЫМ ДЕЛОМ!)
            logger.info("📬 Запуск отправки уведомлений об истечении подписок...")
            await check_and_send_expiry_notifications(bot)
            
            # Ждём 5 минут
            await asyncio.sleep(300)
            
            # 09:05 - Отправляем статистику
            logger.info("📊 Запуск отправки суточной статистики...")
            await send_daily_stats(bot)
            
            # Ждём 5 минут
            await asyncio.sleep(300)
            
            # 09:10 - Отправляем бэкап
            logger.info("📦 Запуск создания и отправки бэкапа...")
            await send_backup_archive(bot)
            
            # Ждём немного чтобы не запуститься повторно в ту же минуту
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("Планировщик ежедневных задач остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в планировщике ежедневных задач: {e}")
            # Ждём час и пробуем снова
            await asyncio.sleep(3600)


async def check_and_notify_updates(bot: Bot) -> None:
    """
    Проверяет обновления и уведомляет администраторов, если они есть.
    
    Args:
        bot: Экземпляр бота
    """
    logger.info("🔍 Ежедневная проверка обновлений...")
    
    # Проверяем настроен ли GitHub URL
    if not GITHUB_REPO_URL:
        logger.warning("GitHub URL не настроен, пропускаем проверку обновлений")
        return
        
    try:
        # Проверяем обновления
        success, commits_behind, log_text, has_blocking, blocking_commit, is_beta_only = check_for_updates()
        
        if success and commits_behind > 0:
            if is_beta_only:
                logger.info(f"📦 Найдено {commits_behind} новых коммитов, но все они бета-версии (начинаются с '?'). Уведомление не отправляется.")
                return
                
            logger.info(f"📦 Найдено {commits_behind} новых коммитов")
            
            # Кнопка обновления (та же callback_data, что в админке)
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text="🔄 Обновить бота", 
                    callback_data="admin_update_bot"
                )
            )
            
            kb = builder.as_markup()
            
            # Формируем текст уведомления
            notify_text = f"📦 <b>Доступно обновление!</b>\n\n{log_text}"
            
            # Если есть блокирующий коммит — добавляем предупреждение
            if has_blocking and blocking_commit:
                blocking_msg = blocking_commit['message'].lstrip('!')
                notify_text += f"\n\n⚠️ Среди обновлений есть <b>блокирующий коммит</b> — обновление нужно выполнять вручную.\n<code>{blocking_msg}</code>"
            
            # Отправляем уведомления админам
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=notify_text,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить уведомление об обновлении админу {admin_id}: {e}")
        else:
            logger.info("✅ Обновлений не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке обновлений: {e}")


async def run_update_check_scheduler(bot: Bot) -> None:
    """
    Фоновая задача для ежедневной проверки обновлений.
    
    Расписание:
    - 12:00 — Проверка обновлений
    
    Args:
        bot: Экземпляр бота
    """
    logger.info("🕐 Планировщик обновлений запущен")
    
    while True:
        try:
            # Ждём до 12:00
            seconds_to_wait = get_seconds_until(12, 0)
            logger.info(f"Следующая проверка обновлений через {seconds_to_wait // 3600}ч {(seconds_to_wait % 3600) // 60}м")
            
            await asyncio.sleep(seconds_to_wait)
            
            # Проверяем обновления
            await check_and_notify_updates(bot)
            
            # Ждём 5 минут чтобы не запуститься повторно
            await asyncio.sleep(300)
            
        except asyncio.CancelledError:
            logger.info("Планировщик обновлений остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в планировщике обновлений: {e}")
            # Ждём час и пробуем снова
            await asyncio.sleep(3600)


# ============================================================================
# СИНХРОНИЗАЦИЯ ТРАФИКА (каждые 5 минут)
# ============================================================================

# Пороги уведомлений о трафике (% оставшегося трафика)
async def reconcile_yookassa_payments(bot: Bot) -> None:
    """
    Re-check recent unfinished SBP payments with YooKassa and apply successful
    orders. This is an idempotent fallback for delayed or missing webhooks.
    """
    from bot.services.billing import (
        check_yookassa_payment_status,
        process_payment_order,
    )
    from database.requests import (
        get_reconcilable_yookassa_orders,
        get_user_by_id,
    )

    # Webhook is the primary path. The poller is only a small fallback batch;
    # it must never monopolize the bot when YooKassa has a network incident.
    orders = get_reconcilable_yookassa_orders(lookback_hours=24, limit=10)
    for order in orders:
        order_id = str(order.get("order_id") or "")
        provider_id = str(order.get("yookassa_payment_id") or "")
        if not order_id or not provider_id:
            continue

        try:
            if order.get("status") == "pending":
                provider_status = await check_yookassa_payment_status(provider_id)
                if provider_status != "succeeded":
                    continue

            success, message, applied_order = await process_payment_order(order_id)
            if not success:
                logger.warning(
                    "YooKassa reconciliation did not apply order %s: %s",
                    order_id,
                    message,
                )
                continue

            if (applied_order or {}).get("fulfillment_status") != "applied":
                continue

            user = get_user_by_id(int(order["user_id"]))
            telegram_id = (user or {}).get("telegram_id")
            if telegram_id:
                await send_to_user(
                    bot,
                    int(telegram_id),
                    (
                        "✅ <b>Оплата получена</b>\n\n"
                        "Подписка и выбранные лимиты обновлены. "
                        "Обновите подписку в VPN-приложении."
                    ),
                )
            logger.info("YooKassa order %s reconciled successfully", order_id)
        except RuntimeError as exc:
            logger.warning("YooKassa reconciliation paused after network error: %s", exc)
            break
        except Exception:
            logger.exception("YooKassa reconciliation failed for order %s", order_id)


async def run_yookassa_reconciliation_scheduler(bot: Bot) -> None:
    """Continuously recover YooKassa orders when a webhook was delayed."""
    logger.info("YooKassa reconciliation scheduler started (every 2 minutes)")
    await asyncio.sleep(20)
    while True:
        try:
            await reconcile_yookassa_payments(bot)
            await asyncio.sleep(120)
        except asyncio.CancelledError:
            logger.info("YooKassa reconciliation scheduler stopped")
            break
        except Exception:
            logger.exception("YooKassa reconciliation scheduler iteration failed")
            await asyncio.sleep(120)


async def process_due_recurring_payments(bot: Bot) -> None:
    """Create idempotent renewal charges for saved YooKassa cards/SBP accounts."""
    from database.db_recurring import claim_due_recurring_cycles, update_recurring_cycle
    from database.db_payments import prepare_payment_order, save_yookassa_payment_id
    from bot.services.billing import create_yookassa_recurring_payment

    card_ready = get_setting("yookassa_recurring_enabled", "0") == "1"
    sbp_ready = get_setting("yookassa_sbp_recurring_enabled", "0") == "1"
    if not card_ready and not sbp_ready:
        return
    cycles = claim_due_recurring_cycles(limit=20, include_card=card_ready, include_sbp=sbp_ready)
    for item in cycles:
        cycle_id = int(item["cycle_id"])
        try:
            order = prepare_payment_order(
                user_id=int(item["user_id"]),
                tariff_id=int(item["effective_tariff_id"]),
                payment_type="yookassa_recurring",
                vpn_key_id=int(item["effective_vpn_key_id"]),
                amount_cents=int(item["effective_amount_cents"]),
                operation_type="renew",
            )
            description = f"ArcVPN — автопродление на {int(item['effective_period_days'])} дней"
            payment = await create_yookassa_recurring_payment(
                amount_rub=int(item["effective_amount_cents"]) / 100,
                order_id=order["order_id"],
                payment_method_id=str(item["payment_method_id"]),
                description=description,
                metadata={"user_id": str(item["user_id"]), "cycle_id": str(cycle_id)},
            )
            provider_id = str(payment.get("id") or "")
            if not provider_id:
                raise RuntimeError("YooKassa did not return payment id")
            save_yookassa_payment_id(order["order_id"], provider_id)
            update_recurring_cycle(cycle_id, "submitted", order["order_id"], provider_id)
            logger.info("Recurring cycle %s submitted as order %s", cycle_id, order["order_id"])
        except Exception as exc:
            update_recurring_cycle(cycle_id, "failed", error=str(exc))
            logger.exception("Recurring cycle %s failed", cycle_id)
            telegram_id = item.get("telegram_id")
            if telegram_id:
                await send_to_user(bot, int(telegram_id), (
                    "⚠️ <b>Не удалось выполнить автопродление ArcVPN</b>\n\n"
                    "Проверьте баланс выбранного способа оплаты или продлите подписку вручную. "
                    "Повторного списания по этой попытке не будет."
                ))


async def run_recurring_payment_scheduler(bot: Bot) -> None:
    """Check subscriptions due for renewal every hour."""
    await asyncio.sleep(45)
    while True:
        try:
            await process_due_recurring_payments(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Recurring payment scheduler iteration failed")
        await asyncio.sleep(3600)


TRAFFIC_THRESHOLDS = [10, 5, 3, 2, 1, 0]


async def process_due_traffic_cycle_resets(*, resetter=None, now=None) -> dict:
    """Reset due users in Remnawave, then atomically advance local counters."""
    from database.db_traffic_cycles import (
        claim_traffic_cycle_reset,
        complete_traffic_cycle_reset,
        fail_traffic_cycle_reset,
        get_due_traffic_cycles,
    )
    if resetter is None:
        from bot.services.vpn_api import reset_key_traffic_if_active
        resetter = reset_key_traffic_if_active

    result = {"applied": 0, "failed": 0, "skipped": 0}
    for cycle in get_due_traffic_cycles(now=now):
        user_id, boundary = cycle["user_id"], cycle["boundary_at"]
        if not claim_traffic_cycle_reset(user_id, boundary):
            result["skipped"] += 1
            continue
        try:
            # One ArcVPN user may still have several historical key rows. Every
            # live panel identity must acknowledge the reset before local state
            # advances; repeated Remnawave resets are safe after a crash.
            for key_id in cycle["key_ids"]:
                if not await resetter(key_id):
                    raise RuntimeError(f"authoritative reset rejected key {key_id}")
            from database.db_webapp import get_lte_identity_by_id
            lte = get_lte_identity_by_id(user_id) or {}
            if lte.get("lte_panel_username"):
                from bot.services.remnawave_stats import remnawave_authority_config
                lte_client = get_client_from_server_data(remnawave_authority_config())
                try:
                    if not await lte_client.reset_client_traffic(0, lte["lte_panel_username"]):
                        raise RuntimeError("authoritative LTE reset rejected")
                finally:
                    await lte_client.close()
            if not complete_traffic_cycle_reset(user_id, boundary, completed_at=now):
                raise RuntimeError("cycle boundary changed during reset")
            result["applied"] += 1
        except Exception as exc:
            fail_traffic_cycle_reset(user_id, boundary, type(exc).__name__)
            result["failed"] += 1
            logger.warning("Traffic cycle reset failed user=%s: %s", user_id, exc)
    return result


async def reconcile_lte_usage() -> dict:
    """Mirror the isolated LTE identities into the account/announce counters."""
    from database.db_webapp import list_lte_identities, set_lte_usage
    from bot.services.remnawave_stats import remnawave_authority_config
    identities = list_lte_identities()
    result = {"updated": 0, "failed": 0}
    if not identities:
        return result
    client = get_client_from_server_data(remnawave_authority_config())
    try:
        for identity in identities:
            try:
                user = await client.get_user(identity["lte_panel_username"])
                if not user or str(user.get("vlessUuid") or "") != str(identity["lte_client_uuid"]):
                    raise RuntimeError("LTE identity mismatch")
                used = int((user.get("userTraffic") or {}).get("usedTrafficBytes") or 0)
                set_lte_usage(int(identity["telegram_id"]), used)
                result["updated"] += 1
            except Exception:
                result["failed"] += 1
                logger.exception("LTE usage reconciliation failed user=%s", identity["user_id"])
    finally:
        await client.close()
    return result


async def monthly_traffic_reset(bot: Bot) -> None:
    """
    Устаревшая ежемесячная сверка. Сброс 1-го числа отключён навсегда:
    
    1. Сброс трафика (если monthly_traffic_reset_enabled = 1)
    2. Сверка БД и панели (ВСЕГДА) — исправление расхождений expiryTime и totalGB
    
    Args:
        bot: Экземпляр бота
    """
    from database.requests import (
        get_all_active_keys_with_server,
        reset_key_traffic_notification,
        update_key_traffic_limit,
        get_tariff_by_id
    )
    from bot.services.vpn_api import push_key_to_panel
    
    # Calendar-anniversary resets are exclusively owned by
    # process_due_traffic_cycle_resets. Keep this legacy reconciliation helper
    # incapable of reviving the destructive first-of-month behavior.
    reset_enabled = False
    
    # === ЧАСТЬ 1: Сброс трафика (если включён) ===
    reset_success = 0
    reset_errors = 0
    
    if reset_enabled:
        logger.info("🔄 Запуск ежемесячного сброса трафика...")
        keys = get_all_active_keys_with_server()
        keys_with_limit = [k for k in keys if (k.get('traffic_limit', 0) or 0) > 0] if keys else []
        
        for key in keys_with_limit:
            try:
                tariff_limit = key.get('traffic_limit', 0) or 0
                tariff_id = key.get('tariff_id')
                if tariff_id:
                    tariff = get_tariff_by_id(tariff_id)
                    if tariff and (tariff.get('traffic_limit_gb', 0) or 0) > 0:
                        tariff_limit = tariff['traffic_limit_gb'] * (1024**3)
                
                # Обновляем БД
                update_key_traffic_limit(key['id'], tariff_limit)
                reset_key_traffic_notification(key['id'])
                
                # Пушим на панель (сброс up/down + правильные данные из БД)
                await push_key_to_panel(key['id'], reset_traffic=True)
                reset_success += 1
            except Exception as e:
                reset_errors += 1
                logger.error(f"Ошибка сброса трафика для ключа {key['id']}: {e}")
    else:
        logger.info("🔄 Ежемесячный сброс трафика отключён")
    
    # === ЧАСТЬ 2: Сверка БД↔панель (ВСЕГДА) ===
    logger.info("🔍 Запуск ежемесячной сверки БД↔панель...")
    sync_fixed = 0
    sync_errors = 0
    
    all_keys = get_all_active_keys_with_server()
    if all_keys:
        keys_by_server: dict = {}
        for key in all_keys:
            sid = key['server_id']
            if sid not in keys_by_server:
                keys_by_server[sid] = []
            keys_by_server[sid].append(key)
        
        servers = get_all_servers()
        server_map = {s['id']: s for s in servers}
        
        for server_id, server_keys in keys_by_server.items():
            server = server_map.get(server_id)
            if not server or not server.get('is_active'):
                continue
            try:
                client = get_client_from_server_data(server)
                inbounds = await client.get_inbounds()
                
                # Карта email → данные на панели
                panel_map = {}
                for inbound in inbounds:
                    settings = json.loads(inbound.get('settings', '{}'))
                    for cl in settings.get('clients', []):
                        panel_map[cl.get('email', '')] = {
                            'expiryTime': cl.get('expiryTime', 0),
                            'totalGB': cl.get('totalGB', 0)
                        }
                
                for key in server_keys:
                    email = key.get('panel_email')
                    if not email or email not in panel_map:
                        continue
                    
                    panel = panel_map[email]
                    needs_fix = False
                    
                    # Проверяем expiryTime
                    expires_at = key.get('expires_at')
                    panel_ms = panel['expiryTime']
                    if expires_at:
                        dt = datetime.fromisoformat(str(expires_at))
                        expected_ms = int(dt.timestamp() * 1000)
                        
                        # Расхождение > 1 день
                        if panel_ms > 0 and abs(expected_ms - panel_ms) > 86400 * 1000:
                            needs_fix = True
                        elif panel_ms == 0 and expected_ms > 0:
                            needs_fix = True
                    else:
                        expected_ms = 0
                        if panel_ms > 0:
                            needs_fix = True
                    
                    # Проверяем totalGB
                    traffic_limit = key.get('traffic_limit', 0) or 0
                    panel_total = panel['totalGB']
                    if traffic_limit > 0 and (panel_total == 0 or abs(panel_total - traffic_limit) > 1024**3):
                        needs_fix = True
                    elif traffic_limit == 0 and panel_total > 0:
                        needs_fix = True
                    
                    if needs_fix:
                        # Пропускаем те, что уже обновились при сбросе трафика
                        already_pushed = reset_enabled and (traffic_limit > 0)
                        if not already_pushed:
                            try:
                                await push_key_to_panel(key['id'])
                                sync_fixed += 1
                            except Exception as e:
                                sync_errors += 1
                                logger.error(f"Ошибка сверки ключа {key['id']} ({email}): {e}")
                        else:
                            sync_fixed += 1  # Уже исправлен при сбросе
            except Exception as e:
                logger.error(f"Ошибка сверки сервера {server.get('name', server_id)}: {e}")
    
    # === Отчёт админам ===
    report_parts = ["🔄 <b>Ежемесячное обслуживание</b>\n"]
    if reset_enabled:
        report_parts.append(f"📊 <b>Сброс трафика:</b> ✅ {reset_success}")
        if reset_errors > 0:
            report_parts.append(f"  ❌ Ошибок: {reset_errors}")
    report_parts.append(f"🔍 <b>Сверка БД↔панель:</b> 🔧 {sync_fixed}")
    if sync_errors > 0:
        report_parts.append(f"  ❌ Ошибок: {sync_errors}")
    
    report = "\n".join(report_parts)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=report, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось отправить отчёт админу {admin_id}: {e}")

async def sync_traffic_stats(bot: Bot) -> None:
    """
    Опрашивает все серверы и обновляет кеш трафика для каждого ключа.
    Проверяет пороги уведомлений и отправляет уведомления пользователям.
    Отключает истёкшие ключи на панели.
    Отправляет уведомления об истёкших подписках.
    
    Graceful degradation: при недоступности сервера — логируем WARNING,
    не обнуляем трафик, продолжаем обработку остальных серверов.
    """
    from database.requests import (
        get_all_active_keys_with_server, bulk_update_traffic,
        update_key_notified_pct, get_setting
    )
    from database.db_stats import (
        get_all_expired_keys,
        is_notification_sent_today,
        log_notification_sent,
        mark_key_panel_disabled,
    )
    from bot.services.vpn_api import disable_key_on_panel
    
    keys = get_all_active_keys_with_server()
    if not keys:
        return
    remnawave_authority = remnawave_authority_enabled()
    
    # Группируем ключи по серверам
    keys_by_server: dict = {}
    for key in keys:
        sid = key['server_id']
        if sid not in keys_by_server:
            keys_by_server[sid] = []
        keys_by_server[sid].append(key)
    
    # Получаем серверы
    servers = get_all_servers()
    server_map = {s['id']: s for s in servers}
    
    # Собираем обновления трафика
    traffic_updates = []  # (traffic_used, key_id)
    
    for server_id, server_keys in keys_by_server.items():
        server = server_map.get(server_id)
        if not server or not server.get('is_active'):
            continue
        if remnawave_authority and str(server.get('panel_type') or 'xui').lower() != 'remnawave':
            # Historical key assignments still point at the former x-ui master.
            # Remnawave reconciliation is handled by the production sync timer;
            # polling x-ui here revives stale counters and legacy side effects.
            continue
        
        try:
            client = get_client_from_server_data(server)
            inbounds = await client.get_inbounds()
            
            # Строим словарь email -> {total, used} из всех inbounds
            stats_map = {}
            for inbound in inbounds:
                for stats in inbound.get("clientStats", []):
                    email = stats.get("email")
                    if email:
                        stats_map[email] = {
                            'total': stats.get('total', 0),
                            'up': stats.get('up', 0),
                            'down': stats.get('down', 0),
                        }
            
            # Сопоставляем с ключами — «умная» формула через остаток
            for key in server_keys:
                email = key.get('panel_email')
                if email and email in stats_map:
                    s = stats_map[email]
                    used_on_server = s['up'] + s['down']
                    total_on_server = s['total']
                    traffic_limit = key.get('traffic_limit', 0) or 0

                    if traffic_limit > 0 and total_on_server > 0:
                        # Формула: сколько осталось на сервере → вычитаем из нашего лимита
                        remaining_on_server = max(0, total_on_server - used_on_server)
                        traffic_used = max(0, traffic_limit - remaining_on_server)
                    else:
                        # Безлимит или нет данных — прямой учёт
                        traffic_used = used_on_server

                    traffic_updates.append((traffic_used, key['id']))
                    key['_new_traffic_used'] = traffic_used

            # === Детект подключённых устройств (онлайн-IP по ключу) ===
            try:
                online_emails = await client.get_online_emails()
                for key in server_keys:
                    email = key.get('panel_email')
                    if not email:
                        continue
                    if email in online_emails:
                        ips = await client.get_client_ips(email)
                        devices = len(ips) if ips else 1  # онлайн, но IP-лог пуст → минимум 1
                    else:
                        devices = 0
                    key['_online_devices'] = devices
            except Exception as e:
                logger.debug(f"Не удалось получить онлайн-устройства сервера {server.get('name', server_id)}: {e}")

        except Exception as e:
            # Graceful degradation: не трогаем данные, продолжаем
            logger.warning(f"⚠️ Синхронизация трафика: сервер {server.get('name', server_id)} недоступен: {e}")
            continue
    
    # Массовое обновление трафика в БД
    if traffic_updates:
        bulk_update_traffic(traffic_updates)

    # === Сохраняем число устройств + уведомление о первом подключении ===
    from database.requests import (
        update_key_online_devices, mark_key_connect_notified, mark_keys_online,
    )
    import config as _cfg
    device_limit = getattr(_cfg, 'DEFAULT_LIMIT_IP', 2)

    # Штампуем last_online_at для всех ключей, которые сейчас онлайн (для
    # статистики активности «кто онлайн / сколько включали VPN за период»).
    online_key_ids = [
        key['id'] for key in keys
        if (key.get('_online_devices') or 0) >= 1
    ]
    if online_key_ids:
        mark_keys_online(online_key_ids)

    for key in keys:
        if '_online_devices' not in key:
            continue
        devices = key['_online_devices']
        if devices != (key.get('online_devices') or 0):
            update_key_online_devices(key['id'], devices)
        # Первое реальное подключение → одноразовое уведомление «подписка подключена».
        if devices >= 1 and not key.get('connect_notified'):
            telegram_id = key.get('telegram_id')
            keyname = key.get('custom_name') or "Подписка"
            if telegram_id:
                if notification_allowed(telegram_id, "connection"):
                    from bot.utils.text import escape_html
                    text = (
                        f"✅ <b>Подписка подключена!</b>\n\n"
                        f"🔑 {escape_html(str(keyname))}\n"
                        f"📱 Устройств подключено: <b>{devices}/{device_limit}</b>\n\n"
                        f"Приятного пользования ArcVPN!"
                    )
                    await send_to_user(bot, telegram_id, text)
            mark_key_connect_notified(key['id'])
            key['connect_notified'] = 1

    # Проверяем пороги уведомлений о трафике
    notification_text_template = get_setting(
        'traffic_notification_text',
        '⚠️ По ключу <b>{keyname}</b> осталось {percent}% трафика ({used} из {limit})'
    )

    for key in keys:
        traffic_limit = key.get('traffic_limit', 0) or 0
        if traffic_limit == 0:
            continue  # Безлимит — пропускаем

        # Используем обновлённое значение или из БД
        traffic_used = key.get('_new_traffic_used', key.get('traffic_used', 0) or 0)
        notified_pct = key.get('traffic_notified_pct', 100)

        # Вычисляем оставшийся процент
        remaining_pct = max(0, (1 - traffic_used / traffic_limit) * 100)

        # Проверяем пороги
        for threshold in TRAFFIC_THRESHOLDS:
            if remaining_pct <= threshold and notified_pct > threshold:
                telegram_id = key.get('telegram_id')
                if telegram_id:
                    if not notification_allowed(telegram_id, "traffic"):
                        break
                    if key.get('custom_name'):
                        keyname = key['custom_name']
                    elif key.get('client_uuid'):
                        uuid = key['client_uuid']
                        keyname = f"{uuid[:4]}...{uuid[-4:]}" if len(uuid) >= 8 else uuid
                    else:
                        keyname = f"Ключ #{key['id']}"

                    msg = notification_text_template.format(
                        keyname=keyname,
                        percent=threshold,
                        used=format_traffic(traffic_used),
                        limit=format_traffic(traffic_limit)
                    )
                    await send_to_user(bot, telegram_id, msg)

                # Обновляем порог в БД
                update_key_notified_pct(key['id'], threshold)
                key['traffic_notified_pct'] = threshold
                break  # Только одно уведомление за раз
    
    # === Отключаем истёкшие ключи на панели + единое уведомление об истечении ===
    try:
        expired_keys = get_all_expired_keys()
        disabled_count = 0
        notified_count = 0

        for key in expired_keys:
            # Отключаем ключ на панели
            if not remnawave_authority and key.get('server_id') and key.get('panel_email'):
                try:
                    if await disable_key_on_panel(key['id']):
                        mark_key_panel_disabled(key['id'])
                        disabled_count += 1
                except Exception as e:
                    logger.error(f"Ошибка отключения ключа {key['id']}: {e}")

            # Единое уведомление об истёкшей подписке (дедуп внутри хелпера)
            keyname = key.get('custom_name') or f"Подписка #{key['id']}"
            if await notify_expired_subscription(bot, key['id'], key.get('telegram_id'), keyname):
                notified_count += 1
                await asyncio.sleep(0.05)

        if disabled_count > 0:
            logger.info(f"🔴 Отключено истёкших ключей: {disabled_count}")
        if notified_count > 0:
            logger.info(f"📬 Отправлено уведомлений об истечении: {notified_count}")
    except Exception as e:
        logger.error(f"Ошибка при отключении истёкших ключей: {e}")
    
    logger.debug(f"Синхронизация трафика завершена: обновлено {len(traffic_updates)} ключей")


async def run_traffic_sync_scheduler(bot: Bot) -> None:
    """
    Фоновая задача для синхронизации трафика и устройств каждую минуту.
    Не заменяет существующие ежедневные задачи.
    
    Args:
        bot: Экземпляр бота
    """
    logger.info("📊 Планировщик синхронизации трафика запущен (каждую минуту)")
    
    # Не откладываем первое уведомление о подключении после рестарта бота.
    await asyncio.sleep(5)
    
    while True:
        try:
            await process_due_traffic_cycle_resets()
            await reconcile_lte_usage()
            await sync_traffic_stats(bot)
            
            # Уведомление и счётчик устройств должны быть практически свежими.
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("Планировщик синхронизации трафика остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в планировщике синхронизации трафика: {e}")
            # Ждём 2 минуты и пробуем снова
            await asyncio.sleep(120)
