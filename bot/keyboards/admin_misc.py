from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

def back_button(callback: str='back') -> InlineKeyboardButton:
    """Кнопка 'Назад'."""
    return InlineKeyboardButton(text='◁ Назад', callback_data=callback)

def home_button() -> InlineKeyboardButton:
    """Кнопка 'На главную'."""
    return InlineKeyboardButton(text='На главную', callback_data='start', icon_custom_emoji_id='5873147866364514353')

def cancel_button() -> InlineKeyboardButton:
    """Кнопка 'Отмена'."""
    return InlineKeyboardButton(text='Отмена', callback_data='admin_servers', icon_custom_emoji_id='5870657884844462243')

def cancel_kb(callback_data: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Отмена'."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Отмена', callback_data=callback_data, icon_custom_emoji_id='5870657884844462243'))
    return builder.as_markup()

def back_and_home_kb(back_callback: str='back') -> InlineKeyboardMarkup:
    """Клавиатура с кнопками 'Назад' и 'На главную'."""
    builder = InlineKeyboardBuilder()
    builder.row(back_button(back_callback), home_button())
    return builder.as_markup()

def home_only_kb() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой 'На главную'."""
    builder = InlineKeyboardBuilder()
    builder.row(home_button())
    return builder.as_markup()

def admin_main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='Сервера', callback_data='admin_servers', icon_custom_emoji_id='5870982283724328568'),
        InlineKeyboardButton(text='Оплаты', callback_data='admin_payments', icon_custom_emoji_id='5769126056262898415')
    )
    builder.row(
        InlineKeyboardButton(text='Пользователи', callback_data='admin_users', icon_custom_emoji_id='5870772616305839506'),
        InlineKeyboardButton(text='Рассылка', callback_data='admin_broadcast', icon_custom_emoji_id='6039422865189638057')
    )
    builder.row(
        InlineKeyboardButton(text='Настройки бота', callback_data='admin_bot_settings', icon_custom_emoji_id='5870982283724328568'),
        InlineKeyboardButton(text='Скачать логи', callback_data='admin_logs_menu', icon_custom_emoji_id='6039802767931871481')
    )
    builder.row(home_button())
    return builder.as_markup()

def admin_logs_menu_kb() -> InlineKeyboardMarkup:
    """Меню скачивания логов."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Полный лог', callback_data='admin_download_log_full', icon_custom_emoji_id='5870528606328852614'), InlineKeyboardButton(text='Ошибки', callback_data='admin_download_log_errors', icon_custom_emoji_id='6039486778597970865'))
    builder.row(InlineKeyboardButton(text='Очистить логи', callback_data='admin_clear_logs_confirm', icon_custom_emoji_id='5870875489362513438'))
    builder.row(back_button('admin_panel'), home_button())
    return builder.as_markup()

def stop_bot_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения остановки бота."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Точно остановить', callback_data='admin_stop_bot_confirm', icon_custom_emoji_id='5870633910337015697'))
    builder.row(InlineKeyboardButton(text='Отмена', callback_data='admin_bot_settings', icon_custom_emoji_id='5870657884844462243'))
    return builder.as_markup()

def force_overwrite_confirm_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения принудительной перезаписи."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Да, перезаписать', callback_data='admin_force_overwrite_confirm', icon_custom_emoji_id='5870633910337015697'))
    builder.row(InlineKeyboardButton(text='Нет, отмена', callback_data='admin_bot_settings', icon_custom_emoji_id='5870657884844462243'))
    return builder.as_markup()

def update_confirm_kb(has_updates: bool=True, has_blocking: bool=False, is_beta_only: bool=False) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения обновления бота.
    
    Args:
        has_updates: Есть ли доступные обновления
        has_blocking: Есть ли блокирующий коммит среди обновлений
        is_beta_only: Все ли доступные обновления являются бета-версиями
    """
    builder = InlineKeyboardBuilder()
    if has_updates:
        if has_blocking:
            button_text = '⚠️ Обновить до блокирующего коммита'
            callback = 'admin_update_bot_confirm'
            builder.row(InlineKeyboardButton(text=button_text, callback_data=callback))
        elif is_beta_only:
            button_text = '🧪 Накатить бета версию'
            callback = 'admin_update_bot_confirm'
            builder.row(InlineKeyboardButton(text=button_text, callback_data=callback))
        else:
            button_text = '✅ Обновить и перезапустить'
            callback = 'admin_update_bot_confirm'
            builder.row(InlineKeyboardButton(text=button_text, callback_data=callback))
    
    builder.row(InlineKeyboardButton(text='Принудительно перезаписать', callback_data='admin_force_overwrite_confirm', icon_custom_emoji_id='6039486778597970865'))
    
    if has_updates:
        builder.row(InlineKeyboardButton(text='Отмена', callback_data='admin_bot_settings', icon_custom_emoji_id='5870657884844462243'))
    else:
        builder.row(InlineKeyboardButton(text='◁ Назад', callback_data='admin_bot_settings'))
    return builder.as_markup()
