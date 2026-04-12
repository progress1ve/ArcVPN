"""
Middleware для проверки обязательной подписки на канал.
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# ID канала для обязательной подписки (укажите свой)
REQUIRED_CHANNEL_ID = "@arcvpn1"  # Можно указать @username или -100123456789
REQUIRED_CHANNEL_LINK = "https://t.me/arcvpn1"


class SubscriptionCheckMiddleware(BaseMiddleware):
    """Проверяет подписку пользователя на обязательный канал."""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Проверяет подписку перед выполнением хендлера."""
        
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
            message = event
        else:  # CallbackQuery
            user_id = event.from_user.id
            message = event.message
        
        # Админы пропускаются без проверки
        if user_id in ADMIN_IDS:
            return await handler(event, data)
        
        # Пропускаем callback "check_subscribe"
        if isinstance(event, CallbackQuery) and event.data == "check_subscribe":
            return await handler(event, data)
        
        # Проверяем подписку
        bot = data.get("bot")
        if not bot:
            return await handler(event, data)
        
        try:
            member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
            
            # Если пользователь не подписан
            if member.status in ["left", "kicked"]:
                await self.send_subscription_required(message)
                
                # Если это callback, отвечаем на него
                if isinstance(event, CallbackQuery):
                    await event.answer("❌ Необходимо подписаться на канал", show_alert=True)
                
                return  # Прерываем выполнение хендлера
                
        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
            # В случае ошибки пропускаем пользователя
            return await handler(event, data)
        
        # Пользователь подписан, продолжаем
        return await handler(event, data)
    
    async def send_subscription_required(self, message: Message):
        """Отправляет сообщение о необходимости подписки."""
        text = (
            "👋 <b>Добро пожаловать в ArcVPN!</b>\n\n"
            "<blockquote>Для использования бота необходимо подписаться на наш канал 👇</blockquote>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Подписаться на канал",
                url=REQUIRED_CHANNEL_LINK
            )],
            [InlineKeyboardButton(
                text="✅ Я подписался",
                callback_data="check_subscribe"
            )]
        ])
        
        try:
            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о подписке: {e}")
