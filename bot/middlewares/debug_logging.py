"""
Middleware для отладки необработанных событий
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


class DebugLoggingMiddleware(BaseMiddleware):
    """Логирует все входящие callback_query для отладки"""
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, CallbackQuery):
            logger.info(f"📥 Получен callback: data='{event.data}', user={event.from_user.id}")
        
        try:
            result = await handler(event, data)
            if isinstance(event, CallbackQuery):
                logger.info(f"✅ Callback обработан: data='{event.data}'")
            return result
        except Exception as e:
            if isinstance(event, CallbackQuery):
                logger.error(f"❌ Ошибка обработки callback: data='{event.data}', error={e}")
            raise
