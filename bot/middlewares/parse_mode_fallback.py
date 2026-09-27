"""
Кастомная сессия бота с автоматическим fallback при ошибках Markdown.

Перехватывает все вызовы методов Telegram API и при ошибке парсинга
автоматически повторяет запрос без parse_mode.
"""
import logging
from html.parser import HTMLParser
from typing import Any, Optional

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType

logger = logging.getLogger(__name__)


def _plain_text(markup: str) -> str:
    """Avoid showing raw HTML tags if Telegram rejects formatted markup."""
    class TextOnly(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = TextOnly()
    parser.feed(markup)
    parser.close()
    return "".join(parser.parts)


class SafeParseSession(AiohttpSession):
    """
    Сессия с автоматическим fallback при ошибках Markdown/HTML парсинга.
    
    Если Telegram возвращает ошибку "can't parse entities", 
    автоматически повторяет запрос с parse_mode=None.
    """
    
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: Optional[float] = None
    ) -> TelegramType:
        try:
            return await super().make_request(bot, method, timeout)
        except TelegramBadRequest as e:
            error_msg = str(e).lower()
            
            # Проверяем, что это ошибка парсинга Markdown/HTML
            if "can't parse entities" in error_msg:
                # Проверяем, есть ли у метода атрибут parse_mode
                if hasattr(method, 'parse_mode') and method.parse_mode is not None:
                    logger.warning(
                        f"Ошибка Markdown парсинга в {method.__class__.__name__}, "
                        f"повторяю без форматирования: {e}"
                    )
                    
                    # If formatting is invalid, retry as readable plain text,
                    # not with visible <b>/<code> tags in the user's chat.
                    update = {'parse_mode': None}
                    for field in ('text', 'caption'):
                        value = getattr(method, field, None)
                        if isinstance(value, str):
                            update[field] = _plain_text(value)
                    method_copy = method.model_copy(update=update)
                    
                    # Повторяем запрос без parse_mode
                    return await super().make_request(bot, method_copy, timeout)
            
            # Если это не ошибка парсинга или нет parse_mode — пробрасываем
            raise
