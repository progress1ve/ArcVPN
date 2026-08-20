"""Background delivery for durable broadcast jobs."""
import asyncio
import logging

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.requests import (
    claim_next_broadcast, complete_broadcast, get_pending_recipient,
    mark_broadcast_recipient, recover_interrupted_broadcasts,
)

logger = logging.getLogger(__name__)


async def run_broadcast_worker(bot):
    recovered = recover_interrupted_broadcasts()
    if recovered:
        logger.warning("Resuming %s interrupted broadcast job(s)", recovered)
    while True:
        job = claim_next_broadcast()
        if not job:
            await asyncio.sleep(2)
            continue
        while (telegram_id := get_pending_recipient(job['id'])) is not None:
            try:
                if job['photo_file_id']:
                    await bot.send_photo(telegram_id, job['photo_file_id'], caption=job['message_text'], parse_mode='HTML')
                else:
                    await bot.send_message(telegram_id, job['message_text'], parse_mode='HTML')
                mark_broadcast_recipient(job['id'], telegram_id, 'sent')
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                mark_broadcast_recipient(job['id'], telegram_id, 'blocked', str(exc)[:500])
            except Exception as exc:
                logger.exception("Broadcast %s failed for recipient", job['id'])
                mark_broadcast_recipient(job['id'], telegram_id, 'failed', str(exc)[:500])
            await asyncio.sleep(0.5)
        result = complete_broadcast(job['id'])
        try:
            await bot.send_message(
                result['created_by'],
                f"✅ <b>Рассылка #{result['id']} завершена</b>\n\n"
                f"📤 Отправлено: {result['sent_count']}/{result['total_count']}\n"
                f"🚫 Недоступны: {result['blocked_count']}\n"
                f"⚠️ Ошибки: {result['failed_count']}",
                parse_mode='HTML',
            )
        except Exception:
            logger.exception("Cannot deliver broadcast completion report for job %s", job['id'])
