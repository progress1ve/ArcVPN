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
    get_referral_earned_days,
    get_user_internal_id,
    ensure_user_referral_code,
    get_active_referral_levels,
    get_setting,
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
    earned_days = get_referral_earned_days(user_internal_id)

    # Подсчитываем общее количество приглашенных
    total_invited = sum(s['count'] for s in stats) if stats else 0

    # Размеры бонусов (настройки)
    try:
        trial_bonus = int(get_setting('referral_trial_bonus_days', '3'))
    except (TypeError, ValueError):
        trial_bonus = 3
    try:
        purchase_bonus = int(get_setting('referral_purchase_bonus_days', '5'))
    except (TypeError, ValueError):
        purchase_bonus = 5

    # Весь текст в HTML с blockquote
    text_lines = [
        "🤝 <b>Партнёрская программа</b>",
        "",
        "<b>Приглашай друзей — получай дни подписки!</b>",
        "<blockquote>"
        f"🎁 <b>+{trial_bonus} дня</b> — когда друг запустит бота по твоей ссылке\n"
        f"🚀 <b>+{purchase_bonus} дней</b> тебе И <b>+{purchase_bonus} дней</b> другу — за его первую покупку"
        "</blockquote>",
        "",
        "📊 <b>Ваша статистика:</b>",
        f"<blockquote>Приглашено: {escape_html(str(total_invited))}",
        f"Заработано дней: {escape_html(str(earned_days))}</blockquote>",
        "",
        "🔗 <b>Ваша ссылка:</b>",
        f"<code>{escape_html(referral_link)}</code>",
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
