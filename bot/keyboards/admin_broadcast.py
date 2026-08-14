from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from .admin_misc import back_button, home_button, cancel_button

BROADCAST_FILTERS = {'all': '👤 Все пользователи', 'active': '✅ С активными ключами', 'inactive': '❌ Без активных ключей', 'never_paid': '🆕 Никогда не покупали', 'expired': '🚫 Ключ истёк', 'selected': '🎯 Выбранные активные'}

def broadcast_main_kb(has_message: bool, current_filter: str, broadcast_in_progress: bool, user_count: int) -> InlineKeyboardMarkup:
    """
    Главное меню рассылки.
    
    Args:
        has_message: Есть ли сохранённое сообщение
        current_filter: Текущий выбранный фильтр
        broadcast_in_progress: Идёт ли рассылка сейчас
        user_count: Количество пользователей по текущему фильтру
    """
    builder = InlineKeyboardBuilder()
    msg_status = '✅' if has_message else '❌'
    builder.row(InlineKeyboardButton(text=f'✉️ Сообщение: {msg_status}', callback_data='broadcast_edit_message'))
    builder.row(
        InlineKeyboardButton(text='👁️ Превью', callback_data='broadcast_preview'),
        InlineKeyboardButton(text='📤 Отправить себе', callback_data='broadcast_send_to_me')
    )
    builder.row(InlineKeyboardButton(text='📋 Шаблоны сообщений', callback_data='broadcast_templates'))
    for (filter_key, filter_name) in BROADCAST_FILTERS.items():
        if filter_key == 'selected':
            continue
        radio = '🔘' if filter_key == current_filter else '⚪'
        builder.row(InlineKeyboardButton(text=f'{radio} {filter_name}', callback_data=f'broadcast_filter:{filter_key}'))
    selected_radio = '🔘' if current_filter == 'selected' else '⚪'
    builder.row(InlineKeyboardButton(
        text=f'{selected_radio} 🎯 Выбрать конкретных активных',
        callback_data='broadcast_select_users:0',
    ))
    if broadcast_in_progress:
        builder.row(InlineKeyboardButton(text='⏳ Рассылка в процессе...', callback_data='broadcast_in_progress'))
    else:
        builder.row(InlineKeyboardButton(text=f'🚀 Начать рассылку ({user_count} чел.)', callback_data='broadcast_start'))
    builder.row(InlineKeyboardButton(text='🎁 Подарить дни по фильтру', callback_data='broadcast_gift_days'))
    builder.row(InlineKeyboardButton(text='─────────────────', callback_data='noop'))
    builder.row(InlineKeyboardButton(text='⏰ Настройки автоуведомлений', callback_data='broadcast_notifications'))
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()


def broadcast_user_selection_kb(
    users: List[Dict[str, Any]], selected_ids: set[int], page: int, pages: int
) -> InlineKeyboardMarkup:
    """Paginated multi-select keyboard for active broadcast recipients."""
    builder = InlineKeyboardBuilder()
    for user in users:
        telegram_id = int(user['telegram_id'])
        marker = '✅' if telegram_id in selected_ids else '⚪'
        username = user.get('username')
        first_name = user.get('first_name')
        label = f'@{username}' if username else (first_name or f'ID {telegram_id}')
        builder.row(InlineKeyboardButton(
            text=f'{marker} {label}'[:60],
            callback_data=f'broadcast_user_toggle:{telegram_id}:{page}',
        ))
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text='◀️', callback_data=f'broadcast_select_users:{page - 1}'))
    navigation.append(InlineKeyboardButton(text=f'{page + 1}/{max(pages, 1)}', callback_data='noop'))
    if page + 1 < pages:
        navigation.append(InlineKeyboardButton(text='▶️', callback_data=f'broadcast_select_users:{page + 1}'))
    builder.row(*navigation)
    builder.row(
        InlineKeyboardButton(text='🧹 Очистить', callback_data=f'broadcast_users_clear:{page}'),
        InlineKeyboardButton(text=f'✅ Готово ({len(selected_ids)})', callback_data='broadcast_users_done'),
    )
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_broadcast'))
    return builder.as_markup()

def broadcast_templates_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора шаблона сообщения."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='🛠 Извинения после тех. работ', callback_data='template_maintenance'))
    builder.row(InlineKeyboardButton(text='🎁 Для пользователей без подписки', callback_data='template_no_subscription'))
    builder.row(back_button('admin_broadcast'), home_button())
    return builder.as_markup()


def broadcast_gift_confirm_kb(user_count: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения подарка дней."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f'✅ Да, начислить ({user_count} чел.)', callback_data='broadcast_gift_confirm'))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_broadcast'))
    return builder.as_markup()


def broadcast_gift_back_kb() -> InlineKeyboardMarkup:
    """Клавиатура отмены ввода дней подарка."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_broadcast'))
    return builder.as_markup()

def broadcast_template_promocode_kb(promocodes: List[Dict[str, Any]], template_type: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора промокода для шаблона.
    
    Args:
        promocodes: Список активных промокодов
        template_type: Тип шаблона (trial_expired, never_paid)
    """
    builder = InlineKeyboardBuilder()
    
    if promocodes:
        from database.db_promocodes import format_promocode_discount
        for promo in promocodes:
            code = promo['code']
            discount = format_promocode_discount(promo)
            used = promo.get('used_count', 0)
            max_uses = promo['max_uses']

            button_text = f"🎟️ {code} (-{discount}) [{used}/{max_uses}]"
            builder.row(InlineKeyboardButton(
                text=button_text, 
                callback_data=f'template_promo:{template_type}:{promo["id"]}'
            ))
    
    builder.row(InlineKeyboardButton(text='❌ Без промокода', callback_data=f'template_promo:{template_type}:none'))
    builder.row(back_button('broadcast_templates'))
    return builder.as_markup()

def broadcast_confirm_kb(user_count: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f'✅ Да, разослать ({user_count} чел.)', callback_data='broadcast_confirm'))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_broadcast'))
    return builder.as_markup()

def broadcast_notifications_kb(days: int) -> InlineKeyboardMarkup:
    """Клавиатура настройки автоуведомлений."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f'📅 За сколько дней: {days}', callback_data='broadcast_notify_days'))
    builder.row(InlineKeyboardButton(text='📝 Текст уведомления', callback_data='broadcast_notify_text'))
    builder.row(back_button('admin_broadcast'), home_button())
    return builder.as_markup()

def broadcast_back_kb() -> InlineKeyboardMarkup:
    """Клавиатура возврата к рассылке."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_broadcast'))
    return builder.as_markup()

def broadcast_notify_back_kb() -> InlineKeyboardMarkup:
    """Клавиатура возврата к настройкам уведомлений."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='broadcast_notifications'))
    return builder.as_markup()
