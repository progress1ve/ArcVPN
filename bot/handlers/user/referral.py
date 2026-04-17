"""
Роутер раздела «Реферальная система» для пользователей.

Отображение реферальной ссылки и статистики по уровням.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.requests import (
    is_referral_enabled,
    get_referral_reward_type,
    get_referral_conditions_text,
    get_referral_levels,
    get_referral_stats,
    get_user_internal_id,
    get_user_balance,
    ensure_user_referral_code,
    get_active_referral_levels,
)
from bot.keyboards.user import referral_menu_kb
from bot.utils.text import safe_edit_or_send, escape_html

logger = logging.getLogger(__name__)

router = Router()


def format_price_compact(cents: int) -> str:
    """Форматирует копейки в компактную строку рублей."""
    if cents >= 10000:
        return f"{cents // 100} ₽"
    else:
        return f"{cents / 100:.2f} ₽".replace(".", ",")


# Дефолтные условия в HTML
DEFAULT_CONDITIONS_DAYS = (
    "Приглашённые пользователи регистрируются по вашей ссылке. "
    "Когда они оплачивают подписку, вы получаете процент от купленных дней. "
    "Дни автоматически добавляются к вашему первому активному ключу."
)

DEFAULT_CONDITIONS_BALANCE = (
    "Приглашённые пользователи регистрируются по вашей ссылке. "
    "Когда они оплачивают подписку, вы получаете процент от суммы оплаты на свой баланс. "
    "Накопленными средствами можно оплачивать новые ключи или продлевать существующие."
)


@router.callback_query(F.data == "referral_system")
async def show_referral_system(callback: CallbackQuery):
    """Показывает раздел партнерской программы."""
    telegram_id = callback.from_user.id
    
    if not is_referral_enabled():
        await callback.answer("❌ Партнерская программа недоступна", show_alert=True)
        return
    
    user_internal_id = get_user_internal_id(telegram_id)
    if not user_internal_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    referral_code = ensure_user_referral_code(user_internal_id)
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else callback.bot.username
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    stats = get_referral_stats(user_internal_id)
    balance = get_user_balance(user_internal_id)
    
    # Подсчитываем общее количество приглашенных
    total_invited = sum(s['count'] for s in stats) if stats else 0
    
    # Весь текст в HTML с blockquote
    text_lines = [
        "🤝 <b>Партнёрская программа</b>",
        "",
        "<b>Зарабатывай вместе с нами!</b>",
        "<blockquote>Приглашай друзей по своей уникальной ссылке и получай 50₽ с каждого пополнения.</blockquote>",
        "",
        "🔗 <b>Ваша ссылка:</b>",
        f"<code>{escape_html(referral_link)}</code>",
        "",
        "📊 <b>Ваша статистика:</b>",
        f"<blockquote>Приглашено: {escape_html(str(total_invited))}",
        f"Баланс: {escape_html(format_price_compact(balance))}",
    ]
    
    text = "\n".join(text_lines)
    
    # Создаем клавиатуру с кнопками
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Пригласить друзей" с share
    builder.row(
        InlineKeyboardButton(
            text="👥 Пригласить друзей",
            url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к ArcVPN!"
        )
    )
    
    # Кнопка "Личный кабинет" (возврат на главную)
    builder.row(
        InlineKeyboardButton(text="🏠На главную", callback_data="start")
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()
