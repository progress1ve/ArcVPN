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
    """Обработчик демо-оплаты - создает платеж напрямую если тариф уже выбран."""
    from database.requests import get_user_internal_id, create_pending_order, update_order_tariff
    
    # Парсим callback_data
    parts = callback.data.split(':')
    
    # Если формат demo_pay_tariff:tariff_id:order_id - тариф уже выбран
    if len(parts) >= 2 and parts[0] == 'demo_pay_tariff':
        tariff_id = int(parts[1])
        order_id = parts[2] if len(parts) > 2 else None
        
        tariff = get_tariff_by_id(tariff_id)
        if not tariff:
            await callback.answer('❌ Тариф не найден', show_alert=True)
            return
        
        user_id = get_user_internal_id(callback.from_user.id)
        if not user_id:
            await callback.answer('❌ Ошибка пользователя', show_alert=True)
            return
        
        # Создаем или обновляем заказ
        if order_id:
            update_order_tariff(order_id, tariff_id, payment_type='demo')
        else:
            (_, order_id) = create_pending_order(
                user_id=user_id,
                tariff_id=tariff_id,
                payment_type='demo',
                vpn_key_id=None
            )
        
        price_rub = float(tariff.get('price_rub') or 0)
        
        text = (
            f"🏦 <b>Демо оплата (РФ карта)</b>\n\n"
            f"📦 Тариф: <b>{escape_html(tariff['name'])}</b>\n"
            f"💵 Сумма: <b>{price_rub} ₽</b>\n\n"
            f"⚠️ <i>Это демонстрационный режим оплаты.</i>\n\n"
            f"Нажмите кнопку ниже для имитации оплаты:"
        )
        
        from bot.keyboards.user import InlineKeyboardBuilder, InlineKeyboardButton
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text=f"💳 Оплатить {price_rub} ₽", callback_data=f"demo_confirm:{order_id}"))
        keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="buy_key"))
        
        await safe_edit_or_send(callback.message, text, reply_markup=keyboard.as_markup())
        await callback.answer()
    
    else:
        # Старая логика - показываем выбор тарифа
        order_id = parts[1] if len(parts) > 1 else None
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
