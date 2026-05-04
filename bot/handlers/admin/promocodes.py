"""
Роутер управления промокодами для админ-панели.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_promocodes import (
    create_promocode,
    get_all_promocodes,
    delete_promocode,
    get_promocode_usage_count,
)
from bot.utils.admin import is_admin
from bot.utils.text import safe_edit_or_send, escape_html, get_message_text_for_storage
from bot.keyboards.admin_misc import back_button, home_button
from bot.states.admin_states import AdminStates
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()


def promocodes_menu_kb():
    """Клавиатура меню промокодов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='➕ Создать промокод', callback_data='admin_promocode_create')
    )
    builder.row(
        InlineKeyboardButton(text='📋 Список промокодов', callback_data='admin_promocodes_list')
    )
    builder.row(back_button('admin_payments'), home_button())
    return builder.as_markup()


def promocodes_list_kb(promocodes):
    """Клавиатура списка промокодов."""
    builder = InlineKeyboardBuilder()
    
    for promo in promocodes:
        # Проверяем истек ли промокод
        expires_at = datetime.fromisoformat(promo['expires_at'])
        is_expired = datetime.now() > expires_at
        
        # Проверяем исчерпан ли
        used_count = promo.get('used_count', 0)
        is_exhausted = used_count >= promo['max_uses']
        
        if is_expired:
            status = "⏰"
        elif is_exhausted:
            status = "🚫"
        else:
            status = "✅"
        
        button_text = f"{status} {promo['code']} ({used_count}/{promo['max_uses']})"
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin_promocode_view:{promo['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text='➕ Создать промокод', callback_data='admin_promocode_create')
    )
    builder.row(back_button('admin_promocodes'), home_button())
    return builder.as_markup()


def promocode_view_kb(promocode_id: int):
    """Клавиатура просмотра промокода."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text='🗑️ Удалить промокод',
            callback_data=f'admin_promocode_delete:{promocode_id}'
        )
    )
    builder.row(back_button('admin_promocodes_list'), home_button())
    return builder.as_markup()


def promocode_delete_confirm_kb(promocode_id: int):
    """Клавиатура подтверждения удаления промокода."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text='✅ Да, удалить',
            callback_data=f'admin_promocode_delete_confirm:{promocode_id}'
        )
    )
    builder.row(
        InlineKeyboardButton(
            text='❌ Отмена',
            callback_data=f'admin_promocode_view:{promocode_id}'
        )
    )
    return builder.as_markup()


@router.callback_query(F.data == 'admin_promocodes')
async def show_promocodes_menu(callback: CallbackQuery):
    """Показывает меню промокодов."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    text = (
        "🎟️ <b>Управление промокодами</b>\n\n"
        "Создавайте промокоды для предоставления скидок пользователям.\n\n"
        "Промокод включает:\n"
        "• Код (название)\n"
        "• Скидку в рублях\n"
        "• Количество использований\n"
        "• Срок действия"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=promocodes_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == 'admin_promocodes_list')
async def show_promocodes_list(callback: CallbackQuery):
    """Показывает список промокодов."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    promocodes = get_all_promocodes()
    
    if not promocodes:
        text = (
            "📋 <b>Список промокодов</b>\n\n"
            "Промокодов пока нет.\n"
            "Создайте первый промокод!"
        )
    else:
        text = f"📋 <b>Список промокодов</b>\n\nВсего: {len(promocodes)}\n\n"
        text += "✅ - активный\n🚫 - исчерпан\n⏰ - истек"
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=promocodes_list_kb(promocodes)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('admin_promocode_view:'))
async def show_promocode_view(callback: CallbackQuery):
    """Показывает детали промокода."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    promocode_id = int(callback.data.split(':')[1])
    
    from database.db_promocodes import get_promocode_by_code, get_all_promocodes
    
    # Находим промокод
    promocodes = get_all_promocodes()
    promocode = next((p for p in promocodes if p['id'] == promocode_id), None)
    
    if not promocode:
        await callback.answer('Промокод не найден', show_alert=True)
        return
    
    # Форматируем дату истечения
    expires_at = datetime.fromisoformat(promocode['expires_at'])
    expires_str = expires_at.strftime('%d.%m.%Y %H:%M')
    
    # Проверяем статус
    is_expired = datetime.now() > expires_at
    used_count = promocode.get('used_count', 0)
    is_exhausted = used_count >= promocode['max_uses']
    
    if is_expired:
        status = "⏰ Истек"
    elif is_exhausted:
        status = "🚫 Исчерпан"
    else:
        status = "✅ Активен"
    
    text = (
        f"🎟️ <b>Промокод: {escape_html(promocode['code'])}</b>\n\n"
        f"💰 <b>Скидка:</b> {promocode['discount_rub']} ₽\n"
        f"👥 <b>Использований:</b> {used_count} / {promocode['max_uses']}\n"
        f"📅 <b>Действует до:</b> {expires_str}\n"
        f"📊 <b>Статус:</b> {status}"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=promocode_view_kb(promocode_id)
    )
    await callback.answer()


@router.callback_query(F.data == 'admin_promocode_create')
async def start_promocode_creation(callback: CallbackQuery, state: FSMContext):
    """Начинает создание промокода."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_promocode_code)
    
    text = (
        "➕ <b>Создание промокода</b>\n\n"
        "Шаг 1/4: Введите код промокода\n\n"
        "Например: <code>SUMMER2026</code> или <code>SALE50</code>\n\n"
        "Код будет автоматически переведен в верхний регистр."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data='admin_promocodes'))
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(AdminStates.waiting_promocode_code, F.text, ~F.text.startswith('/'))
async def process_promocode_code(message: Message, state: FSMContext):
    """Обрабатывает ввод кода промокода."""
    if not is_admin(message.from_user.id):
        return
    
    code = get_message_text_for_storage(message, 'plain').strip().upper()
    
    if len(code) < 3:
        await message.answer("❌ Код должен содержать минимум 3 символа")
        return
    
    if len(code) > 20:
        await message.answer("❌ Код должен содержать максимум 20 символов")
        return
    
    # Проверяем уникальность
    from database.db_promocodes import get_promocode_by_code
    if get_promocode_by_code(code):
        await message.answer(f"❌ Промокод <code>{escape_html(code)}</code> уже существует")
        return
    
    await state.update_data(promocode_code=code)
    await state.set_state(AdminStates.waiting_promocode_discount)
    
    text = (
        f"➕ <b>Создание промокода</b>\n\n"
        f"Код: <code>{escape_html(code)}</code>\n\n"
        f"Шаг 2/4: Введите размер скидки в рублях\n\n"
        f"Например: <code>100</code> или <code>500</code>"
    )
    
    await message.answer(text, parse_mode='HTML')
    try:
        await message.delete()
    except:
        pass


@router.message(AdminStates.waiting_promocode_discount, F.text, ~F.text.startswith('/'))
async def process_promocode_discount(message: Message, state: FSMContext):
    """Обрабатывает ввод скидки."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        discount = int(get_message_text_for_storage(message, 'plain').strip())
        if discount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return
    
    await state.update_data(promocode_discount=discount)
    await state.set_state(AdminStates.waiting_promocode_max_uses)
    
    data = await state.get_data()
    code = data.get('promocode_code')
    
    text = (
        f"➕ <b>Создание промокода</b>\n\n"
        f"Код: <code>{escape_html(code)}</code>\n"
        f"Скидка: {discount} ₽\n\n"
        f"Шаг 3/4: Введите максимальное количество использований\n\n"
        f"Например: <code>10</code> или <code>100</code>"
    )
    
    await message.answer(text, parse_mode='HTML')
    try:
        await message.delete()
    except:
        pass


@router.message(AdminStates.waiting_promocode_max_uses, F.text, ~F.text.startswith('/'))
async def process_promocode_max_uses(message: Message, state: FSMContext):
    """Обрабатывает ввод максимального количества использований."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        max_uses = int(get_message_text_for_storage(message, 'plain').strip())
        if max_uses <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return
    
    await state.update_data(promocode_max_uses=max_uses)
    await state.set_state(AdminStates.waiting_promocode_duration)
    
    data = await state.get_data()
    code = data.get('promocode_code')
    discount = data.get('promocode_discount')
    
    text = (
        f"➕ <b>Создание промокода</b>\n\n"
        f"Код: <code>{escape_html(code)}</code>\n"
        f"Скидка: {discount} ₽\n"
        f"Использований: {max_uses}\n\n"
        f"Шаг 4/4: Введите длительность действия в днях\n\n"
        f"Например: <code>7</code> (неделя) или <code>30</code> (месяц)"
    )
    
    await message.answer(text, parse_mode='HTML')
    try:
        await message.delete()
    except:
        pass


@router.message(AdminStates.waiting_promocode_duration, F.text, ~F.text.startswith('/'))
async def process_promocode_duration(message: Message, state: FSMContext):
    """Обрабатывает ввод длительности и создает промокод."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        duration_days = int(get_message_text_for_storage(message, 'plain').strip())
        if duration_days <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return
    
    data = await state.get_data()
    code = data.get('promocode_code')
    discount = data.get('promocode_discount')
    max_uses = data.get('promocode_max_uses')
    
    # Создаем промокод
    promocode_id = create_promocode(code, discount, max_uses, duration_days)
    
    if promocode_id:
        expires_at = datetime.now()
        from datetime import timedelta
        expires_at += timedelta(days=duration_days)
        expires_str = expires_at.strftime('%d.%m.%Y')
        
        text = (
            f"✅ <b>Промокод создан!</b>\n\n"
            f"🎟️ Код: <code>{escape_html(code)}</code>\n"
            f"💰 Скидка: {discount} ₽\n"
            f"👥 Использований: 0 / {max_uses}\n"
            f"📅 Действует до: {expires_str}"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text='📋 Список промокодов', callback_data='admin_promocodes_list'))
        builder.row(home_button())
        
        await message.answer(text, parse_mode='HTML', reply_markup=builder.as_markup())
    else:
        await message.answer("❌ Ошибка при создании промокода")
    
    await state.clear()
    try:
        await message.delete()
    except:
        pass


@router.callback_query(F.data.startswith('admin_promocode_delete:'))
async def confirm_promocode_deletion(callback: CallbackQuery):
    """Запрашивает подтверждение удаления промокода."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    promocode_id = int(callback.data.split(':')[1])
    
    text = (
        "⚠️ <b>Подтверждение удаления</b>\n\n"
        "Вы уверены, что хотите удалить этот промокод?\n\n"
        "Это действие нельзя отменить."
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=promocode_delete_confirm_kb(promocode_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('admin_promocode_delete_confirm:'))
async def delete_promocode_confirmed(callback: CallbackQuery):
    """Удаляет промокод после подтверждения."""
    if not is_admin(callback.from_user.id):
        await callback.answer('⛔ Доступ запрещён', show_alert=True)
        return
    
    promocode_id = int(callback.data.split(':')[1])
    
    if delete_promocode(promocode_id):
        await callback.answer('✅ Промокод удален', show_alert=True)
        
        # Возвращаемся к списку
        promocodes = get_all_promocodes()
        
        if not promocodes:
            text = (
                "📋 <b>Список промокодов</b>\n\n"
                "Промокодов пока нет.\n"
                "Создайте первый промокод!"
            )
        else:
            text = f"📋 <b>Список промокодов</b>\n\nВсего: {len(promocodes)}\n\n"
            text += "✅ - активный\n🚫 - исчерпан\n⏰ - истек"
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=promocodes_list_kb(promocodes)
        )
    else:
        await callback.answer('❌ Ошибка при удалении', show_alert=True)
