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
    """Показывает раздел реферальной системы."""
    telegram_id = callback.from_user.id
    
    if not is_referral_enabled():
        await callback.answer("❌ Реферальная система недоступна", show_alert=True)
        return
    
    user_internal_id = get_user_internal_id(telegram_id)
    if not user_internal_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    referral_code = ensure_user_referral_code(user_internal_id)
    bot_username = callback.bot.my_username if hasattr(callback.bot, 'my_username') else callback.bot.username
    referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
    
    reward_type = get_referral_reward_type()
    from bot.utils.message_editor import get_message_data
    conditions_data = get_message_data('referral_conditions_text', '')
    conditions_text = conditions_data.get('text', '')
    conditions_photo = conditions_data.get('photo_file_id')
    all_levels = get_referral_levels()
    active_levels = get_active_referral_levels()
    stats = get_referral_stats(user_internal_id)
    balance = get_user_balance(user_internal_id)
    
    # Весь текст в HTML
    text_lines = [
        "👥 <b>Реферальная система</b>",
        "",
        "📎 Ваша реферальная ссылка:",
        f"<code>{escape_html(referral_link)}</code>",
        "",
    ]
    
    text_lines.append("━━━━━━━━━━━━━━━")
    text_lines.append("📝 <b>Условия:</b>")
    if conditions_text:
        # Текст из редактора уже в HTML
        text_lines.append(conditions_text)
    elif reward_type == 'days':
        text_lines.append(DEFAULT_CONDITIONS_DAYS)
    else:
        text_lines.append(DEFAULT_CONDITIONS_BALANCE)
    text_lines.append("")
    
    stats_by_level = {s['level']: s for s in stats} if stats else {}
    
    text_lines.append("━━━━━━━━━━━━━━━")
    text_lines.append("📊 <b>Ваша статистика:</b>")
    text_lines.append("")
    
    for level_num, percent in active_levels:
        level_stat = stats_by_level.get(level_num)
        count = level_stat['count'] if level_stat else 0
        
        if reward_type == 'days':
            total_reward = level_stat['total_reward_days'] if level_stat else 0
            reward_display = escape_html(f"{total_reward} дн.")
        else:
            total_reward = level_stat['total_reward_cents'] if level_stat else 0
            reward_display = escape_html(format_price_compact(total_reward))
        
        # Динамические значения экранируются через escape_html
        text_lines.append(
            f"Уровень {escape_html(str(level_num))} "
            f"({escape_html(str(percent))}%): "
            f"{escape_html(str(count))} чел. — {reward_display}"
        )
    text_lines.append("")
    
    if reward_type == 'balance':
        text_lines.append("━━━━━━━━━━━━━━━")
        text_lines.append(f"💰 <b>Ваш баланс:</b> {escape_html(format_price_compact(balance))}")
        text_lines.append("")
    
    text = "\n".join(text_lines)
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=referral_menu_kb(),
        photo=conditions_photo,
    )
    await callback.answer()
