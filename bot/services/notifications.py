"""
Единый сервис уведомлений.

Зачем: раньше вызовы bot.send_message были разбросаны по scheduler.py с
непоследовательной обработкой ошибок (блокировка бота, rate-limit). Этот модуль
централизует отправку:
- send_to_user  — пользователю, с обработкой блокировки/лимитов;
- notify_admins — всем админам;
- render_template — единая загрузка шаблонов из settings + подстановка плейсхолдеров.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramBadRequest,
)
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup

from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Пауза между отправками в рассылках, чтобы не упираться в лимиты Telegram.
SEND_DELAY_SECONDS = 0.05


async def send_to_user(
    bot: Bot,
    telegram_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    photo: Optional[str] = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Отправляет уведомление пользователю с единой обработкой ошибок.

    - TelegramForbiddenError (бот заблокирован) → users.is_active=0, return False;
    - TelegramRetryAfter (rate-limit) → подождать и повторить один раз;
    - TelegramBadRequest / прочее → лог, return False.

    Returns:
        True если сообщение доставлено, иначе False.
    """
    for attempt in range(2):
        try:
            if photo:
                await bot.send_photo(
                    chat_id=telegram_id, photo=photo, caption=text,
                    reply_markup=reply_markup, parse_mode=parse_mode,
                )
            else:
                await bot.send_message(
                    chat_id=telegram_id, text=text,
                    reply_markup=reply_markup, parse_mode=parse_mode,
                )
            return True
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — помечаем неактивным, больше не шлём.
            try:
                from database.requests import set_user_active
                set_user_active(telegram_id, False)
            except Exception as e:
                logger.debug("Не удалось пометить %s неактивным: %s", telegram_id, e)
            logger.info("Пользователь %s заблокировал бота — помечен неактивным", telegram_id)
            return False
        except TelegramRetryAfter as e:
            if attempt == 0:
                logger.warning("Rate limit для %s, ждём %s сек", telegram_id, e.retry_after)
                await asyncio.sleep(e.retry_after)
                continue
            logger.warning("Rate limit для %s повторно — пропускаем", telegram_id)
            return False
        except TelegramBadRequest as e:
            logger.warning("BadRequest при отправке %s: %s", telegram_id, e)
            return False
        except Exception as e:
            logger.warning("Ошибка отправки уведомления %s: %s", telegram_id, e)
            return False
    return False


async def notify_admins(
    bot: Bot,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    document: Optional[tuple] = None,
    parse_mode: str = "HTML",
) -> None:
    """
    Рассылает сообщение всем администраторам.

    Args:
        document: опционально (bytes, filename) — отправить как документ вместо текста.
    """
    for admin_id in ADMIN_IDS:
        try:
            if document is not None:
                data, filename = document
                await bot.send_document(
                    chat_id=admin_id,
                    document=BufferedInputFile(data, filename=filename),
                    caption=text or None,
                    parse_mode=parse_mode,
                )
            else:
                await bot.send_message(
                    chat_id=admin_id, text=text,
                    reply_markup=reply_markup, parse_mode=parse_mode,
                )
        except Exception as e:
            logger.warning("Не удалось отправить уведомление админу %s: %s", admin_id, e)
        await asyncio.sleep(SEND_DELAY_SECONDS)


def render_template(
    key: str,
    default_text: str,
    placeholders: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Загружает редактируемый шаблон из settings и подставляет плейсхолдеры.

    Args:
        key: ключ настройки (например 'notification_text');
        default_text: текст по умолчанию, если шаблон не задан в БД;
        placeholders: {плейсхолдер: значение} — значения экранируются HTML.

    Returns:
        (text, photo_file_id) — готовый текст и file_id фото (или None).
    """
    from bot.utils.message_editor import get_message_data
    from bot.utils.text import escape_html

    data = get_message_data(key, default_text)
    text = data.get("text", default_text) or default_text
    photo_file_id = data.get("photo_file_id")

    if placeholders:
        for ph, value in placeholders.items():
            text = text.replace(ph, escape_html(str(value)))

    return text, photo_file_id
