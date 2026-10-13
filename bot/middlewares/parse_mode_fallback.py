"""
Кастомная сессия бота с автоматическим fallback при ошибках Markdown.

Перехватывает все вызовы методов Telegram API и при ошибке парсинга
автоматически повторяет запрос без parse_mode.
"""
import logging
from html.parser import HTMLParser
from typing import Optional

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import Default
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

        def handle_starttag(self, tag, attrs) -> None:
            if tag == 'br' or tag in {'p', 'div'}:
                self.parts.append('\n')

        def handle_endtag(self, tag) -> None:
            if tag in {'p', 'div'}:
                self.parts.append('\n')

    parser = TextOnly()
    parser.feed(markup)
    parser.close()
    return "".join(parser.parts)


def _unformatted(value, bot):
    """Build a retry payload, including captions inside media groups/edits."""
    update = {}
    mode = getattr(value, 'parse_mode', None)
    if isinstance(mode, Default):
        mode = bot.default.parse_mode
    has_entities = any(getattr(value, field, None) for field in ('entities', 'caption_entities'))
    if mode or has_entities:
        update['parse_mode'] = None
        for field in ('text', 'caption'):
            content = getattr(value, field, None)
            if isinstance(content, str) and str(mode).upper() == 'HTML':
                update[field] = _plain_text(content)
        for field in ('entities', 'caption_entities'):
            if hasattr(value, field):
                update[field] = None
    media = getattr(value, 'media', None)
    if isinstance(media, list):
        converted = [_unformatted(item, bot) for item in media]
        if any(new is not old for new, old in zip(converted, media)):
            update['media'] = converted
    elif hasattr(media, 'model_copy'):
        converted = _unformatted(media, bot)
        if converted is not media:
            update['media'] = converted
    return value.model_copy(update=update) if update else value


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
                method_copy = _unformatted(method, bot)
                if method_copy is not method:
                    logger.warning(
                        "Ошибка форматирования в %s, повторяю читаемым текстом",
                        method.__class__.__name__,
                    )
                    # Повторяем запрос без parse_mode
                    return await super().make_request(bot, method_copy, timeout)
            
            # Если это не ошибка парсинга или нет parse_mode — пробрасываем
            raise
