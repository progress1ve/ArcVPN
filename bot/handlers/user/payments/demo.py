import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.utils.text import escape_html, safe_edit_or_send
from database.requests import get_all_tariffs, get_tariff_by_id, get_key_details_for_user
from bot.keyboards.user import tariff_select_kb, renew_tariff_select_kb
from bot.keyboards.admin import home_only_kb

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data.startswith('demo_tariffs'))
async def demo_tariffs_handler(callback: CallbackQuery):
    """Обработчик демо-оплаты - показывает выбор тарифа."""
    # Формат demo_tariffs или demo_tariffs:order_id - показываем выбор тарифа
    parts = callback.data.split(':')
    order_id = parts[1] if len(parts) > 1 else None
    tariffs = get_all_tariffs(include_hidden=False)
    
    if not tariffs:
        await callback.answer('❌ Нет доступных тарифов', show_alert=True)
        return
    
    await safe_edit_or_send(
        callback.message,
        '🏦 <b>Демо оплата (РФ карта)</b>\n\nВыберите тариф:\n\n<i>Этот способ используется только для демонстрации интерфейса оплаты.</i>',
        reply_markup=tariff_select_kb(tariffs, order_id=order_id, is_demo=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo_pay_tariff:'))
async def demo_pay_tariff_handler(callback: CallbackQuery):
    """Обработчик выбора тарифа для демо-оплаты - показывает экран подтверждения."""
    from database.requests import get_user_internal_id, prepare_payment_order
    
    # Парсим callback_data
    parts = callback.data.split(':')
    
    # Формат demo_pay_tariff:tariff_id:order_id - тариф уже выбран (из tariff_select_kb)
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

    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='demo',
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    
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
    """Показ демонстрационного экрана оплаты с подтверждением (Продление)."""
    from database.requests import get_user_internal_id, prepare_payment_order
    
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return

    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='demo',
        vpn_key_id=key_id,
        order_id=order_id,
    )
    order_id = prepared_order['order_id']

    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        f"🏦 <b>Демо оплата (РФ карта)</b>\n\n"
        f"🔑 <b>Ключ:</b> {escape_html(key['display_name'])}\n"
        f"📦 <b>Продление на:</b> {escape_html(tariff['name'])}\n"
        f"📅 <b>Срок:</b> +{tariff['duration_days']} дн.\n"
        f"💵 <b>Сумма:</b> {price_rub} ₽\n\n"
        f"⚠️ <i>Это демонстрационный режим оплаты.</i>\n\n"
        f"Нажмите кнопку ниже для имитации оплаты:"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"💳 Оплатить {price_rub} ₽", callback_data=f"demo_confirm:{order_id}"))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data=f'key:{key_id}'))
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith('demo_confirm:'))
async def demo_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Подтверждение демо-оплаты через единый lifecycle заказа."""
    from database.requests import find_order_by_order_id, get_tariff_by_id, infer_order_operation_type
    from bot.services.billing import apply_paid_order, process_referral_reward
    from bot.handlers.user.payments.base import finalize_payment_ui

    order_id = callback.data.split(':')[1]
    
    order = find_order_by_order_id(order_id)
    if not order:
        await callback.answer('❌ Заказ не найден', show_alert=True)
        return
    
    tariff = get_tariff_by_id(order['tariff_id'])
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    already_applied = order.get('status') == 'paid' and order.get('fulfillment_status') == 'applied'
    operation_type = infer_order_operation_type(
        vpn_key_id=order.get('vpn_key_id'),
        payment_type=order.get('payment_type'),
        explicit_operation_type=order.get('operation_type'),
        tariff_id=order.get('tariff_id'),
    )

    try:
        success, _, updated_order = await apply_paid_order(order_id)
        if not success or not updated_order:
            await callback.answer('❌ Ошибка обработки демо-оплаты', show_alert=True)
            return

        days = updated_order.get('period_days') or updated_order.get('duration_days') or tariff['duration_days']
        amount_cents = updated_order.get('amount_cents') or int(float(tariff.get('price_rub') or 0) * 100)

        if not already_applied:
            logger.info(
                "Демо-оплата обработана через lifecycle: order_id=%s, operation=%s, user=%s",
                order_id,
                operation_type,
                callback.from_user.id,
            )
            await process_referral_reward(updated_order['user_id'], days, amount_cents, 'demo')

        if operation_type == 'renew':
            success_message = (
                "🎉 <b>Демо-оплата успешна!</b>\n\n"
                f"✅ Ключ продлён на {days} дней\n"
                f"📦 Тариф: {escape_html(tariff['name'])}\n\n"
                "👇 <b>Информация о ключе:</b>"
            )
        else:
            success_message = (
                "🎉 <b>Демо-оплата успешна!</b>\n\n"
                f"✅ Подписка активирована\n"
                f"📦 Тариф: {escape_html(tariff['name'])}\n"
                f"📅 Срок: {days} дней\n\n"
                "👇 <b>Ваша подписка готова!</b>"
            )

        await finalize_payment_ui(
            callback.message,
            state,
            success_message,
            updated_order,
            user_id=callback.from_user.id,
        )
        await callback.answer("✅ Оплата прошла успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при демо-оплате: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
