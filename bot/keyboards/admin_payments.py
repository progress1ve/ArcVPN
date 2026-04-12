from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from .admin_misc import back_button, home_button, cancel_button

def payments_menu_kb(stars_enabled: bool, crypto_enabled: bool, cards_enabled: bool, qr_enabled: bool=False, monthly_reset_enabled: bool=False, demo_enabled: bool=False) -> InlineKeyboardMarkup:
    """
    Главное меню раздела оплат.

    Args:
        stars_enabled: Включены ли Telegram Stars
        crypto_enabled: Включены ли крипто-платежи
        cards_enabled: Включена ли оплата картами (ЮКасса Telegram Payments)
        qr_enabled: Включена ли прямая QR-оплата ЮКасса
        monthly_reset_enabled: Включён ли ежемесячный автосброс трафика
        demo_enabled: Включена ли демо-оплата
    """
    builder = InlineKeyboardBuilder()
    stars_status = '✅' if stars_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'⭐ Telegram Stars: {stars_status}', callback_data='admin_payments_toggle_stars'))
    crypto_status = '✅' if crypto_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💰 Крипто-платежи: {crypto_status}', callback_data='admin_payments_toggle_crypto'))
    cards_status = '✅' if cards_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💳 Оплата картами (ЮКасса): {cards_status}', callback_data='admin_payments_cards'))
    qr_status = '✅' if qr_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'📱 QR-оплата (ЮКасса/СБП): {qr_status}', callback_data='admin_payments_qr'))
    demo_status = '✅' if demo_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'💳 Демо оплата (РФ): {demo_status}', callback_data='admin_payments_toggle_demo'))
    reset_status = '✅' if monthly_reset_enabled else '❌'
    builder.row(InlineKeyboardButton(text=f'🔄 Автосброс трафика 1-го числа: {reset_status}', callback_data='admin_toggle_monthly_reset'))
    builder.row(InlineKeyboardButton(text='Группы тарифов', icon_custom_emoji_id='5884479287171485878', callback_data='admin_groups'))
    builder.row(InlineKeyboardButton(text='Тарифы', icon_custom_emoji_id='5870528606328852614', callback_data='admin_tariffs'))
    builder.row(InlineKeyboardButton(text='Пробная подписка', icon_custom_emoji_id='6032644646587338669', callback_data='admin_trial'))
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()

def crypto_setup_kb(step: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для шага настройки крипто-платежей.
    
    Args:
        step: Текущий шаг (1 = ссылка, 2 = ключ)
    """
    builder = InlineKeyboardBuilder()
    buttons = []
    if step > 1:
        buttons.append(InlineKeyboardButton(text='◁ Назад', callback_data='admin_crypto_setup_back'))
    buttons.append(InlineKeyboardButton(text='Отмена', icon_custom_emoji_id='5870657884844462243', callback_data='admin_payments'))
    builder.row(*buttons)
    return builder.as_markup()

def crypto_setup_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения настроек крипто."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Сохранить и включить', icon_custom_emoji_id='5870633910337015697', callback_data='admin_crypto_setup_save'))
    builder.row(InlineKeyboardButton(text='◁ Назад', callback_data='admin_crypto_setup_back'), InlineKeyboardButton(text='Отмена', icon_custom_emoji_id='5870657884844462243', callback_data='admin_payments'))
    return builder.as_markup()

def cards_management_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления оплатой картами."""
    builder = InlineKeyboardBuilder()
    toggle_text = 'Выключить 🔴' if is_enabled else 'Включить 🟢'
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data='admin_cards_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='Изменить Provider Token', icon_custom_emoji_id='5769289093221454192', callback_data='admin_cards_mgmt_edit_token'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()
    'Клавиатура подтверждения настройки крипто.'
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Сохранить и включить', icon_custom_emoji_id='5870633910337015697', callback_data='admin_crypto_setup_save'))
    builder.row(InlineKeyboardButton(text='◁ Назад', callback_data='admin_crypto_setup_back'), InlineKeyboardButton(text='Отмена', icon_custom_emoji_id='5870657884844462243', callback_data='admin_payments'))
    return builder.as_markup()

def edit_crypto_kb(current_param: int, total_params: int) -> InlineKeyboardMarkup:
    """
    Клавиатура редактирования крипто-настроек с навигацией.
    
    Args:
        current_param: Индекс текущего параметра
        total_params: Общее количество параметров
    """
    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if current_param > 0:
        nav_buttons.append(InlineKeyboardButton(text='◁ Пред.', callback_data='admin_crypto_edit_prev'))
    else:
        nav_buttons.append(InlineKeyboardButton(text='—', callback_data='noop'))
    if current_param < total_params - 1:
        nav_buttons.append(InlineKeyboardButton(text='▶ След.', callback_data='admin_crypto_edit_next'))
    else:
        nav_buttons.append(InlineKeyboardButton(text='—', callback_data='noop'))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text='Готово', icon_custom_emoji_id='5870633910337015697', callback_data='admin_crypto_edit_done'))
    return builder.as_markup()

def crypto_management_kb(is_enabled: bool, integration_mode: str) -> InlineKeyboardMarkup:
    """
    Меню управления крипто-платежами.
    
    Args:
        is_enabled: Включены ли крипто-платежи сейчас
        integration_mode: Текущий режим интеграции ('simple' или 'standard')
    """
    builder = InlineKeyboardBuilder()
    mode_text = '🔄 Режим: Простой (Счет)' if integration_mode == 'simple' else '🔄 Режим: Стандартный (Товар)'
    builder.row(InlineKeyboardButton(text=mode_text, callback_data='admin_crypto_mgmt_toggle_mode'))
    status_text = '🟢 Выключить' if is_enabled else '⚪ Включить'
    builder.row(InlineKeyboardButton(text=status_text, callback_data='admin_crypto_mgmt_toggle'))
    builder.row(InlineKeyboardButton(text='Изменить ссылку на товар', icon_custom_emoji_id='5769289093221454192', callback_data='admin_crypto_mgmt_edit_url'))
    builder.row(InlineKeyboardButton(text='Изменить секретный ключ', icon_custom_emoji_id='6037249452824072506', callback_data='admin_crypto_mgmt_edit_secret'))
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()
