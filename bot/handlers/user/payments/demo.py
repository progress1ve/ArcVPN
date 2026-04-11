import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.utils.text import escape_html, safe_edit_or_send
from database.requests import get_all_tariffs, get_tariff_by_id, get_key_details_for_user
from bot.keyboards.user import tariff_select_kb, renew_tariff_select_kb
from bot.keyboards.admin import home_only_kb

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data.startswith('demo_tariffs'))
async def demo_tariffs_handler(callback: CallbackQuery):
    """Выбор тарифа для демонстрационной оплаты (Новый ключ)."""
    order_id = None
    if ':' in callback.data:
        order_id = callback.data.split(':')[1]
        
    tariffs = get_all_tariffs(include_hidden=False)
    
    await safe_edit_or_send(
        callback.message, 
        '🏦 <b>Демо оплата (РФ карта)</b>\n\nВыберите тариф:\n\n<i>Этот способ используется только для демонстрации интерфейса оплаты.</i>', 
        reply_markup=tariff_select_kb(tariffs, order_id=order_id, is_demo=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('renew_demo_tariffs:'))
async def renew_demo_tariffs_handler(callback: CallbackQuery):
    """Выбор тарифа для демонстрационной оплаты (Продление)."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
        
    from bot.utils.groups import get_tariffs_for_renewal
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    if not tariffs:
        await callback.answer('Нет доступных тарифов', show_alert=True)
        return
        
    await safe_edit_or_send(
        callback.message, 
        f"🏦 <b>Демо оплата (РФ карта)</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:", 
        reply_markup=renew_tariff_select_kb(tariffs, key_id, order_id=order_id, is_demo=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo_pay:'))
async def demo_pay_handler(callback: CallbackQuery):
    """Показ демонстрационного экрана оплаты (Новый ключ)."""
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return

    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        "🏦 <b>Демонстрационная оплата</b>\n\n"
        "Это демо-режим. Реального списания не происходит.\n\n"
        f"📦 <b>Тариф:</b> {escape_html(tariff['name'])}\n"
        f"📅 <b>Срок:</b> {tariff['duration_days']} дн.\n"
        f"💰 <b>Сумма:</b> {int(price_rub)} ₽\n\n"
        "<i>В рабочем режиме здесь появится форма оплаты российской картой.</i>"
    )
    
    # Можно добавить кнопку назад
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='⬅️ Назад к тарифами', callback_data='demo_tariffs'))
    builder.row(InlineKeyboardButton(text='🈴 На главную', callback_data='start'))
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith('renew_demo_pay:'))
async def renew_demo_pay_handler(callback: CallbackQuery):
    """Показ демонстрационного экрана оплаты (Продление)."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return

    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        "🏦 <b>Демонстрационная оплата</b>\n\n"
        "Это демо-режим. Реального списания не происходит.\n\n"
        f"🔑 <b>Ключ:</b> {escape_html(key['display_name'])}\n"
        f"📦 <b>Продление на:</b> {escape_html(tariff['name'])}\n"
        f"📅 <b>Срок:</b> +{tariff['duration_days']} дн.\n"
        f"💰 <b>Сумма:</b> {int(price_rub)} ₽\n\n"
        "<i>В рабочем режиме здесь появится форма оплаты российской картой.</i>"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='⬅️ Назад к тарифами', callback_data=f'renew_demo_tariffs:{key_id}'))
    builder.row(InlineKeyboardButton(text='🈴 На главную', callback_data='start'))
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()
