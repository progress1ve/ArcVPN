"""One worker for reviewed admin campaigns; rewards never run in test mode."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter, TelegramNetworkError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import db_admin_broadcasts as campaigns

logger = logging.getLogger(__name__)


def keyboard(payload):
    buttons = payload['buttons']
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b)] for b in buttons]) if buttons else None


async def send_payload(bot, target, payload, text):
    options = {'parse_mode': 'HTML', 'reply_markup': keyboard(payload)}
    if payload['photo_file_id']:
        return await bot.send_photo(target, payload['photo_file_id'], caption=text, **options)
    return await bot.send_message(target, text, **options)


async def send_test(bot, campaign_id, target):
    campaign, samples = campaigns.test_samples(campaign_id)
    # Full campaign review is clearly separate from the actual message.
    await bot.send_message(target, f"Тест рассылки «{campaign['title']}»\nПолучателей: {campaign['total']}.\n"
        'Бонусы и скидки не активированы. Отправка пользователям запускается отдельно в админ-панели.', parse_mode=None)
    for text in samples:
        await send_payload(bot, target, campaign['payload'], text)
    campaigns.mark_tested(campaign_id, campaign['revision'], target)
    return campaigns.detail(campaign_id)


async def process_recipient(bot, recipient, push_key):
    row = campaigns.grant_once(recipient)
    if not row:
        return
    if row['reward_state'] == 'sync_pending':
        try:
            synced = await push_key(row['key_id'])
        except Exception:
            synced = False
        if not synced:
            attempts = row['attempts'] + 1
            retry = datetime.now(timezone.utc) + timedelta(seconds=min(600, 30 * attempts))
            campaigns.update_recipient(row, attempts=attempts, retry_at=retry.isoformat(),
                error='Дни записаны; ожидается подтверждение VPN-панели')
            return
        campaigns.update_recipient(row, reward_state='applied', error=None)
    # A stopped/banned recipient must not get another delivery. Benefit already
    # granted remains recorded and is not rolled back by a message failure.
    from database.connection import get_db
    with get_db() as conn:
        eligible = conn.execute('SELECT 1 FROM users WHERE id=? AND is_banned=0 AND telegram_id=?',
            (row['user_id'], row['telegram_id'])).fetchone()
        promo = None
        if row['payload']['reward']['kind'] == 'existing_promo':
            try:
                promo = campaigns.check_offer(conn, row['payload'])
            except ValueError:
                campaigns.update_recipient(row, status='failed', error='Промокод изменён или недоступен; отправка пропущена')
                return
    if not eligible:
        campaigns.update_recipient(row, status='skipped', error='Аккаунт исключён перед отправкой')
        return
    text = campaigns.render(row['payload'], row, promo=promo)
    if not campaigns.reserve_send(row):
        return
    try:
        message = await send_payload(bot, row['telegram_id'], row['payload'], text)
    except TelegramRetryAfter as exc:
        retry = datetime.now(timezone.utc) + timedelta(seconds=exc.retry_after + 1)
        campaigns.update_recipient(row, status='pending', retry_at=retry.isoformat(), error='Лимит Telegram: повтор запланирован')
        await asyncio.sleep(min(exc.retry_after, 30))
    except TelegramForbiddenError:
        campaigns.update_recipient(row, status='blocked', error='Бот заблокирован или чат недоступен')
    except TelegramBadRequest:
        campaigns.update_recipient(row, status='failed', error='Telegram отклонил сообщение; проверьте шаблон и получателя')
    except (TelegramNetworkError, asyncio.TimeoutError):
        campaigns.update_recipient(row, status='uncertain', error='Нет подтверждения Telegram; автоматический повтор отключён')
    except Exception:
        # A transport failure can happen after Telegram has accepted the message.
        campaigns.update_recipient(row, status='uncertain', error='Результат отправки неизвестен; нужен ручной разбор')
    else:
        campaigns.update_recipient(row, status='sent', message_id=message.message_id,
            sent_at=datetime.now(timezone.utc).isoformat(), error=None)


async def run_admin_broadcast_worker(bot):
    from bot.services.vpn_api import push_key_to_panel
    campaigns.recover()
    while True:
        try:
            recipient = campaigns.next_recipient()
            if recipient:
                await process_recipient(bot, recipient, push_key_to_panel)
                await asyncio.sleep(0.5)
            else:
                campaigns.finish_ready()
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Admin broadcast worker iteration failed')
            await asyncio.sleep(5)
