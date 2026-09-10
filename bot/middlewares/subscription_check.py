"""Versioned legal-consent gate for Telegram bot users."""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
logger = logging.getLogger(__name__)

REQUIRED_CHANNEL_LINK = "https://t.me/arcvpn1"


def advertising_start_payload(event: Message | CallbackQuery) -> str | None:
    """Return an ad deep-link payload before the channel gate consumes /start."""
    if not isinstance(event, Message):
        return None
    text = str(event.text or "").strip()
    command, separator, payload = text.partition(" ")
    if not separator or command.split("@", 1)[0].lower() != "/start":
        return None
    payload = payload.strip()
    return payload if payload.startswith("ad_") and len(payload) > 3 else None


class SubscriptionCheckMiddleware(BaseMiddleware):
    """Require the current agreement version, never channel membership."""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Show the agreement before the first protected interaction."""
        
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
            message = event
        else:  # CallbackQuery
            user_id = event.from_user.id
            message = event.message
        
        # Keep the old callback as an alias for already delivered keyboards.
        if isinstance(event, CallbackQuery) and event.data in {"accept_legal", "check_subscribe"}:
            return await handler(event, data)

        try:
            from database.db_legal_consent import get_legal_consent
            from database.requests import get_setting
            consent_version = get_setting('legal_consent_version', '2026-09-10')
            consent = get_legal_consent(user_id)
        except Exception:
            logger.exception("Ошибка проверки согласия пользователя %s", user_id)
            return await handler(event, data)

        if not consent or consent.get("version") != consent_version:
            payload = advertising_start_payload(event)
            state = data.get("state")
            if payload and state is not None:
                await state.update_data(pending_start_args=payload)
            await self.send_subscription_required(message)
            if isinstance(event, CallbackQuery):
                await event.answer("Сначала примите пользовательское соглашение", show_alert=True)
            return

        return await handler(event, data)
    
    async def send_subscription_required(self, message: Message):
        """Send the required agreement and an optional channel recommendation."""
        from config import SUBSCRIPTION_URL
        agreement_url = f"{SUBSCRIPTION_URL.rstrip('/')}/legal/user-agreement"
        text = (
            "👋 <b>Добро пожаловать в ArcVPN!</b>\n\n"
            "Чтобы продолжить, ознакомьтесь и примите "
            f'<a href="{agreement_url}">Пользовательское соглашение и Политику конфиденциальности</a>.\n\n'
            f'Подпишитесь на <a href="{REQUIRED_CHANNEL_LINK}">наш канал</a>, '
            "чтобы не пропускать важные новости, бонусы и статус сервиса. "
            "Подписка добровольная."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Принять и продолжить",
                callback_data="accept_legal"
            )]
        ])
        
        try:
            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о подписке: {e}")
