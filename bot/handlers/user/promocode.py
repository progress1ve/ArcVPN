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
PROMOCODE_INPUT_TEXT = (
    "🎟️ <b>Использование промокода</b>\n\n"
    "Введите код промокода для получения скидки.\n\n"
    "Например: <code>SUMMER2026</code>"
)


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
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="buy_key")
    )
    
    await safe_edit_or_send(
        callback.message,
        PROMOCODE_INPUT_TEXT,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith('use_promocode_renew:'))
async def start_promocode_input_renew(callback: CallbackQuery, state: FSMContext):
    """Начинает ввод промокода для продления."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    
    # Сохраняем данные в state
    await state.update_data(
        promocode_key_id=key_id,
        promocode_tariff_id=tariff_id,
        promocode_order_id=order_id,
        promocode_action='renew'
    )
    await state.set_state(UserStates.waiting_for_promocode)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"key_renew:{key_id}")
    )
    
    await safe_edit_or_send(
        callback.message,
        PROMOCODE_INPUT_TEXT,
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
    from database.requests import get_tariff_by_id, prepare_payment_order, get_setting
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await message.answer("❌ Ошибка: тариф не найден")
        await state.clear()
        return
    
    # Вычисляем цену со скидкой
    original_price = tariff['price_rub']
    discount = promocode['discount_rub']
    final_price = max(0, original_price - discount)
    
    # НЕ отмечаем использование сразу - это будет сделано при успешной оплате
    # use_promocode(promocode['id'], user_internal_id)  # УБРАЛИ
    
    key_id = data.get('promocode_key_id') if action == 'renew' else None
    prepared_order = prepare_payment_order(
        user_id=user_internal_id,
        tariff_id=tariff_id,
        payment_type=None,
        vpn_key_id=key_id,
        order_id=old_order_id,
        promocode_id=promocode['id'],
        discount_rub=discount
    )
    new_order_id = prepared_order['order_id']
    
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

        await message.answer(text, parse_mode='HTML', reply_markup=builder)

        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass

        await state.clear()
        return

    # final_price > 0: возвращаемся к единому экрану способов оплаты со скидкой.
    # Полный прайс-блок (strike-through + строка скидки) рисует общий хелпер,
    # сюда передаём только краткое подтверждение применения промокода.
    from bot.utils.payment_flow_ui import show_payment_method_selection_screen

    helper_key_id = data.get('promocode_key_id') if action == 'renew' else None
    intro = (
        f"✅ <b>Промокод применён!</b>\n\n"
        f"🎟️ <code>{escape_html(code)}</code> — скидка {discount} ₽"
    )
    await show_payment_method_selection_screen(
        message,
        message.from_user.id,
        tariff_id,
        key_id=helper_key_id,
        order_id=new_order_id,
        intro_text=intro,
        has_promocode=True,
    )

    # Удаляем введённый пользователем код
    try:
        await message.delete()
    except Exception:
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
