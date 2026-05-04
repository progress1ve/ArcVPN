"""
Роутер использования промокодов пользователями.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_promocodes import is_promocode_valid, use_promocode
from database.requests import get_user_internal_id, get_tariff_by_id
from bot.utils.text import safe_edit_or_send, escape_html, get_message_text_for_storage
from bot.states.user_states import UserStates

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith('use_promocode:'))
async def start_promocode_input(callback: CallbackQuery, state: FSMContext):
    """Начинает ввод промокода для покупки."""
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    
    # Сохраняем данные в state
    await state.update_data(
        promocode_tariff_id=tariff_id,
        promocode_order_id=order_id,
        promocode_action='buy'
    )
    await state.set_state(UserStates.waiting_for_promocode)
    
    text = (
        "🎟️ <b>Использование промокода</b>\n\n"
        "Введите код промокода для получения скидки.\n\n"
        "Например: <code>SUMMER2026</code>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="buy_key")
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith('use_promocode_renew:'))
async def start_promocode_input_renew(callback: CallbackQuery, state: FSMContext):
    """Начинает ввод промокода для продления."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    
    # Сохраняем данные в state
    await state.update_data(
        promocode_key_id=key_id,
        promocode_tariff_id=tariff_id,
        promocode_action='renew'
    )
    await state.set_state(UserStates.waiting_for_promocode)
    
    text = (
        "🎟️ <b>Использование промокода</b>\n\n"
        "Введите код промокода для получения скидки.\n\n"
        "Например: <code>SUMMER2026</code>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"key_renew:{key_id}")
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(UserStates.waiting_for_promocode, F.text, ~F.text.startswith('/'))
async def process_promocode_input(message: Message, state: FSMContext):
    """Обрабатывает ввод промокода."""
    code = get_message_text_for_storage(message, 'plain').strip().upper()
    
    # Получаем ID пользователя
    user_internal_id = get_user_internal_id(message.from_user.id)
    if not user_internal_id:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return
    
    # Проверяем валидность промокода
    is_valid, error_message, promocode = is_promocode_valid(code, user_internal_id)
    
    if not is_valid:
        await message.answer(error_message)
        return
    
    # Получаем данные из state
    data = await state.get_data()
    tariff_id = data.get('promocode_tariff_id')
    action = data.get('promocode_action')
    old_order_id = data.get('promocode_order_id')
    
    # Получаем тариф
    from database.requests import get_tariff_by_id, create_pending_order, get_setting
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await message.answer("❌ Ошибка: тариф не найден")
        await state.clear()
        return
    
    # Вычисляем цену со скидкой
    original_price = tariff['price_rub']
    discount = promocode['discount_rub']
    final_price = max(0, original_price - discount)
    
    # Отмечаем использование промокода
    use_promocode(promocode['id'], user_internal_id)
    
    # Создаем НОВЫЙ заказ с промокодом
    key_id = data.get('promocode_key_id') if action == 'renew' else None
    (_, new_order_id) = create_pending_order(
        user_id=user_internal_id,
        tariff_id=tariff_id,
        payment_type=None,
        vpn_key_id=key_id,
        promocode_id=promocode['id'],
        discount_rub=discount
    )
    
    # Формируем сообщение об успехе
    text = (
        f"✅ <b>Промокод применен!</b>\n\n"
        f"🎟️ Промокод: <code>{escape_html(code)}</code>\n"
        f"💰 Скидка: {discount} ₽\n\n"
        f"Цена без скидки: <s>{original_price} ₽</s>\n"
        f"<b>Цена со скидкой: {final_price} ₽</b>\n\n"
    )
    
    if final_price == 0:
        text += "🎉 Подписка бесплатна! Нажмите кнопку ниже для активации."
        builder = InlineKeyboardBuilder()
        
        if action == 'renew':
            key_id = data.get('promocode_key_id')
            builder.row(
                InlineKeyboardButton(
                    text="✅ Активировать продление",
                    callback_data=f"activate_free_renew:{key_id}:{tariff_id}:{promocode['id']}"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="✅ Активировать подписку",
                    callback_data=f"activate_free_sub:{tariff_id}:{new_order_id}:{promocode['id']}"
                )
            )
        
        builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    else:
        text += "Выберите способ оплаты со скидкой:"
        
        # Возвращаемся к выбору способа оплаты с новым order_id
        from bot.keyboards.user import payment_method_kb, renew_payment_method_kb
        from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
        from database.requests import (
            is_crypto_configured, is_stars_enabled, is_cards_enabled,
            is_yookassa_qr_configured, is_demo_payment_enabled,
            get_crypto_integration_mode, is_referral_enabled,
            get_referral_reward_type, get_user_balance
        )
        
        # Получаем настройки оплаты
        crypto_configured = is_crypto_configured()
        crypto_mode = get_crypto_integration_mode()
        stars_enabled = is_stars_enabled()
        cards_enabled = is_cards_enabled()
        yookassa_qr_enabled = is_yookassa_qr_configured()
        demo_enabled = is_demo_payment_enabled()
        
        # Проверяем баланс
        show_balance_button = False
        if is_referral_enabled() and get_referral_reward_type() == 'balance':
            balance_cents = get_user_balance(user_internal_id)
            if balance_cents > 0:
                show_balance_button = True
        
        # Генерируем crypto URL если нужно
        crypto_url = None
        if crypto_configured and crypto_mode == 'standard':
            crypto_item_url = get_setting('crypto_item_url')
            item_id = extract_item_id_from_url(crypto_item_url)
            if item_id:
                crypto_url = build_crypto_payment_url(
                    item_id=item_id,
                    invoice_id=new_order_id,
                    tariff_external_id=tariff.get('external_id'),
                    price_cents=tariff['price_cents']
                )
        
        if action == 'renew':
            key_id = data.get('promocode_key_id')
            builder = renew_payment_method_kb(
                key_id=key_id,
                tariff_id=tariff_id,
                crypto_url=crypto_url,
                crypto_mode=crypto_mode,
                crypto_configured=crypto_configured,
                stars_enabled=stars_enabled,
                cards_enabled=cards_enabled,
                yookassa_qr_enabled=yookassa_qr_enabled,
                demo_enabled=demo_enabled,
                show_balance_button=show_balance_button
            )
        else:
            builder = payment_method_kb(
                tariff_id=tariff_id,
                crypto_url=crypto_url,
                crypto_mode=crypto_mode,
                crypto_configured=crypto_configured,
                stars_enabled=stars_enabled,
                cards_enabled=cards_enabled,
                yookassa_qr_enabled=yookassa_qr_enabled,
                order_id=new_order_id,
                demo_enabled=demo_enabled,
                show_balance_button=show_balance_button
            )
    
    await message.answer(text, parse_mode='HTML', reply_markup=builder)
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    await state.clear()


@router.callback_query(F.data.startswith('activate_free_sub:'))
async def activate_free_subscription(callback: CallbackQuery):
    """Активирует бесплатную подписку (100% скидка по промокоду)."""
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2]
    promocode_id = int(parts[3])
    
    # Здесь нужно создать ключ без оплаты
    # Это будет обрабатываться в billing.py
    
    await callback.answer("🎉 Подписка активирована!", show_alert=True)
    
    # TODO: Реализовать создание ключа
    text = "✅ <b>Подписка активирована!</b>\n\nВаш ключ создается..."
    
    await safe_edit_or_send(callback.message, text)


@router.callback_query(F.data.startswith('activate_free_renew:'))
async def activate_free_renewal(callback: CallbackQuery):
    """Активирует бесплатное продление (100% скидка по промокоду)."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    promocode_id = int(parts[3])
    
    # Здесь нужно продлить ключ без оплаты
    # Это будет обрабатываться в billing.py
    
    await callback.answer("🎉 Продление активировано!", show_alert=True)
    
    # TODO: Реализовать продление ключа
    text = "✅ <b>Продление активировано!</b>\n\nВаш ключ продлевается..."
    
    await safe_edit_or_send(callback.message, text)
