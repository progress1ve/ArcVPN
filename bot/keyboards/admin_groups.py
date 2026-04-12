from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional

from .admin_misc import back_button, home_button, cancel_button

def groups_list_kb(groups: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Клавиатура списка групп тарифов с кнопками ⬆️ для сортировки.
    
    Args:
        groups: Список групп из get_all_groups()
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='Добавить группу', callback_data='admin_group_add'))
    for group in groups:
        row_buttons = [InlineKeyboardButton(text=f"{group['name']}", callback_data=f"admin_group_view:{group['id']}")]
        if len(groups) > 1:
            row_buttons.append(InlineKeyboardButton(text='▲', callback_data=f"admin_group_up:{group['id']}"))
        builder.row(*row_buttons)
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()

def group_view_kb(group_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура просмотра группы тарифов.
    
    Args:
        group_id: ID группы
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='✏️ Переименовать', callback_data=f'admin_group_edit:{group_id}'))
    if group_id != 1:
        builder.row(InlineKeyboardButton(text='🗑️ Удалить группу', callback_data=f'admin_group_delete:{group_id}'))
    builder.row(back_button('admin_groups'), home_button())
    return builder.as_markup()

def group_delete_confirm_kb(group_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления группы.
    
    Args:
        group_id: ID группы
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='✅ Да, удалить', callback_data=f'admin_group_delete_confirm:{group_id}'))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data=f'admin_group_view:{group_id}'))
    return builder.as_markup()

def group_select_kb(groups: List[Dict[str, Any]], callback_prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора группы (используется при создании тарифа/сервера).
    
    Args:
        groups: Список групп
        callback_prefix: Префикс для callback_data (напр. "tariff_group_select")
        back_callback: Callback для кнопки «Назад»
    """
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.row(InlineKeyboardButton(text=f"📂 {group['name']}", callback_data=f"{callback_prefix}:{group['id']}"))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data=back_callback))
    return builder.as_markup()
