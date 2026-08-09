import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from bot.utils.text import escape_html, safe_edit_or_send
from config import ADMIN_IDS
from bot.handlers.user.payments.base import _format_price_compact, _is_cards_via_yookassa_direct

logger = logging.getLogger(__name__)

router = Router()

async def _show_balance_payment_screen(callback: CallbackQuery, state: FSMContext, tariff_id: int, user_internal_id: int, key_id: int=None, order_id: str=None):
    """
    Показать экран оплаты с учётом баланса по ТЗ.
    
    Вызывается по кнопке «💎 Использовать баланс».
    
    Расчёт:
        balance_to_deduct = min(balance, price)
        remaining_cents = price - balance_to_deduct
    
    Сохраняет в FSM state: balance_to_deduct, tariff_price_cents, tariff_id, key_id, order_id
    
    Args:
        order_id: ID заказа (если есть промокод)
    """
    from database.requests import get_tariff_by_id, get_user_balance, is_cards_enabled, is_yookassa_qr_configured, find_order_by_order_id
    from bot.keyboards.user import balance_payment_kb
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    # Базовая цена тарифа
    tariff_price_cents = int(tariff.get('price_rub', 0) * 100)
    
    # Проверяем, есть ли промокод в заказе
    discount_rub = 0
    if order_id:
        order = find_order_by_order_id(order_id)
        if order and order.get('discount_rub'):
            discount_rub = order['discount_rub']
            logger.info(f"Найдена скидка по промокоду: {discount_rub}₽ для order {order_id}")
    
    # Применяем скидку от промокода
    final_price_cents = max(0, tariff_price_cents - (discount_rub * 100))
    
    if tariff_price_cents <= 0 and final_price_cents <= 0:
        await callback.answer('❌ Ошибка: цена тарифа не задана', show_alert=True)
        return
    
    balance_cents = get_user_balance(user_internal_id)
    balance_to_deduct = min(balance_cents, final_price_cents)
    remaining_cents = max(0, final_price_cents - balance_to_deduct)
    
    await state.update_data(
        balance_to_deduct=balance_to_deduct, 
        tariff_price_cents=final_price_cents,  # Сохраняем цену С учетом промокода
        tariff_id=tariff_id, 
        key_id=key_id,
        order_id=order_id
    )
    
    price_str = _format_price_compact(tariff_price_cents)
    balance_str = _format_price_compact(balance_cents)
    deduct_str = _format_price_compact(balance_to_deduct)
    remaining_str = _format_price_compact(remaining_cents)
    
    text = f"💳 <b>Оплата тарифа «{escape_html(tariff['name'])}»</b>\n\n"
    
    if discount_rub > 0:
        text += f"💰 Цена: <s>{price_str}</s> → {_format_price_compact(final_price_cents)}\n"
        text += f"🎟️ Скидка по промокоду: {discount_rub} ₽\n"
    else:
        text += f"💰 Сумма: {price_str}\n"
    
    text += f"💎 Ваш баланс: {balance_str}\n\n"
    text += f"✅ С баланса будет списано: {deduct_str}\n"
    text += f"💳 К оплате: {remaining_str}"
    
    cards_enabled = is_cards_enabled()
    yookassa_qr_enabled = is_yookassa_qr_configured()
    cards_via_yookassa_direct = _is_cards_via_yookassa_direct()
    available_methods = []
    if yookassa_qr_enabled:
        available_methods.append('qr')
    if cards_enabled:
        if cards_via_yookassa_direct:
            available_methods.append('card')
        elif remaining_cents >= 10000:
            available_methods.append('card')
    if remaining_cents > 0 and (not available_methods):
        text += '\n\n💡 <b>Для доплаты этой суммы нет подходящего способа оплаты.</b>\nПоднакопите ещё немного на реферальном балансе\nили оплатите тариф без использования баланса.'
    
    await safe_edit_or_send(callback.message, text, reply_markup=balance_payment_kb(
        tariff_id=tariff_id, 
        key_id=key_id, 
        balance_cents=balance_cents, 
        tariff_price_cents=final_price_cents,  # Передаем цену С учетом промокода
        balance_to_deduct=balance_to_deduct, 
        remaining_cents=remaining_cents, 
        cards_enabled=cards_enabled, 
        yookassa_qr_enabled=yookassa_qr_enabled, 
        cards_via_yookassa_direct=cards_via_yookassa_direct,
        order_id=order_id
    ))
    await callback.answer()

@router.callback_query(F.data == 'pay_use_balance')
async def pay_use_balance_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифа для оплаты с баланса (новый ключ)."""
    logger.info(f"pay_use_balance_buy_handler вызван для user {callback.from_user.id}")
    from database.requests import get_all_tariffs, get_user_internal_id, is_referral_enabled, get_referral_reward_type, get_user_balance
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    telegram_id = callback.from_user.id
    user_id = get_user_internal_id(telegram_id)
    if not is_referral_enabled() or get_referral_reward_type() != 'balance':
        await callback.answer('❌ Оплата с баланса недоступна', show_alert=True)
        return
    balance_cents = get_user_balance(user_id) if user_id else 0
    if balance_cents <= 0:
        await callback.answer('❌ Недостаточно средств на балансе', show_alert=True)
        return
    tariffs = get_all_tariffs(include_hidden=False)
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] > 0]
    if not rub_tariffs:
        await safe_edit_or_send(callback.message, '💎 <b>Оплата с баланса</b>\n\n😔 Нет доступных тарифов с ценой в рублях.', reply_markup=home_only_kb())
        await callback.answer()
        return
    await safe_edit_or_send(callback.message, f'💎 <b>Оплата с баланса</b>\n\nВаш баланс: <b>{_format_price_compact(balance_cents)}</b>\n\nВыберите тариф:', reply_markup=tariff_select_kb(rub_tariffs, back_callback='buy_key', is_balance=True))
    await callback.answer()

@router.callback_query(F.data.startswith('pay_use_balance:'))
async def pay_use_balance_renew_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработка кнопки «Использовать баланс» для продления.
    Callback: pay_use_balance:{key_id}
    """
    from database.requests import get_user_internal_id, get_key_details_for_user, is_referral_enabled, get_referral_reward_type, get_user_balance, get_all_tariffs
    from bot.keyboards.user import renew_tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id
    user_id = get_user_internal_id(telegram_id)
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    if not is_referral_enabled() or get_referral_reward_type() != 'balance':
        await callback.answer('❌ Оплата с баланса недоступна', show_alert=True)
        return
    balance_cents = get_user_balance(user_id) if user_id else 0
    if balance_cents <= 0:
        await callback.answer('❌ Недостаточно средств на балансе', show_alert=True)
        return
    from bot.utils.groups import get_tariffs_for_renewal
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    rub_tariffs = [t for t in tariffs if t.get('price_rub') and t['price_rub'] > 0]
    if not rub_tariffs:
        await safe_edit_or_send(callback.message, '💎 <b>Оплата с баланса</b>\n\n😔 Нет доступных тарифов с ценой в рублях.', reply_markup=home_only_kb())
        await callback.answer()
        return
    await safe_edit_or_send(callback.message, f"💎 <b>Оплата с баланса</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\nВаш баланс: <b>{_format_price_compact(balance_cents)}</b>\n\nВыберите тариф:", reply_markup=renew_tariff_select_kb(rub_tariffs, key_id, is_balance=True))
    await callback.answer()

@router.callback_query(F.data.startswith('balance_pay:'))
async def balance_pay_handler(callback: CallbackQuery, state: FSMContext):
    """
    Показ экрана оплаты с балансом после выбора тарифа.
    Callback: balance_pay:{tariff_id} или balance_pay:{tariff_id}:{key_id} или balance_pay:{tariff_id}:{key_id}:{order_id}
    """
    logger.info(f"balance_pay_handler вызван: callback_data={callback.data}")
    from database.requests import get_user_internal_id, get_tariff_by_id
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    key_id = int(parts[2]) if len(parts) > 2 and parts[2] != '0' else None
    order_id = parts[3] if len(parts) > 3 else None
    user_id = get_user_internal_id(callback.from_user.id)
    logger.info(f"balance_pay_handler: tariff_id={tariff_id}, key_id={key_id}, order_id={order_id}, user_id={user_id}")
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    await _show_balance_payment_screen(callback, state, tariff_id, user_id, key_id=key_id, order_id=order_id)

@router.callback_query(F.data.startswith('pay_balance_tariff:'))
async def pay_balance_tariff_handler(callback: CallbackQuery, state: FSMContext):
    """
    Алиас для balance_pay_handler.
    Обрабатывает callback: pay_balance_tariff:{tariff_id}
    """
    logger.info(f"pay_balance_tariff_handler вызван: callback_data={callback.data}")
    from database.requests import get_user_internal_id, get_tariff_by_id
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    user_id = get_user_internal_id(callback.from_user.id)
    logger.info(f"pay_balance_tariff_handler: tariff_id={tariff_id}, user_id={user_id}")
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    await _show_balance_payment_screen(callback, state, tariff_id, user_id, key_id=None)

@router.callback_query(F.data.startswith('pay_with_balance:'))
async def pay_with_balance_handler(callback: CallbackQuery, state: FSMContext):
    """
    Полная оплата с баланса (когда remaining_cents == 0).
    Атомарная операция: списать + выдать ключ.
    
    При оплате балансом реферальные вознаграждения НЕ начисляются.
    Если был применен промокод, он отмечается как использованный.
    """
    from database.requests import (
        get_user_internal_id, get_user_balance, deduct_from_balance, 
        get_tariff_by_id, get_or_create_user, create_initial_vpn_key, 
        extend_vpn_key, find_order_by_order_id, complete_order, update_key_tariff,
        prepare_payment_order, update_payment_key_id
    )
    from database.db_promocodes import use_promocode
    from bot.services.user_locks import user_locks
    from bot.services.vpn_api import push_key_to_panel, restore_traffic_limit_in_db
    
    data = await state.get_data()
    balance_to_deduct = data.get('balance_to_deduct', 0)
    tariff_price_cents = data.get('tariff_price_cents', 0)
    tariff_id = data.get('tariff_id')
    key_id = data.get('key_id')
    order_id = data.get('order_id')
    
    parts = callback.data.split(':')
    if not tariff_id:
        tariff_id = int(parts[1]) if len(parts) > 1 else None
    if not key_id:
        key_id = int(parts[2]) if len(parts) > 2 and parts[2] else None
    if not tariff_id:
        await callback.answer('❌ Ошибка: тариф не определён', show_alert=True)
        return
    
    telegram_id = callback.from_user.id
    (user, _) = get_or_create_user(telegram_id, callback.from_user.username)
    user_internal_id = user['id']
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    days = tariff['duration_days']
    
    prepared_order = prepare_payment_order(
        user_id=user_internal_id,
        tariff_id=tariff_id,
        payment_type='balance',
        vpn_key_id=key_id,
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    promocode_id = prepared_order.get('promocode_id')
    if promocode_id:
        logger.info(f"Найден промокод {promocode_id} в заказе {order_id}")
    
    async with user_locks[user_internal_id]:
        current_balance = get_user_balance(user_internal_id)
        if current_balance < tariff_price_cents:
            await callback.answer('❌ Недостаточно средств на балансе', show_alert=True)
            return
        actual_deduct = min(current_balance, tariff_price_cents)
        deduct_from_balance(user_internal_id, actual_deduct)
        
        # Отмечаем использование промокода
        if promocode_id:
            use_promocode(promocode_id, user_internal_id)
            logger.info(f"Промокод {promocode_id} отмечен как использованный при оплате балансом")
        
        complete_order(order_id)
        logger.info(f"Заказ {order_id} закрыт после оплаты балансом")
        
        if key_id:
            extend_vpn_key(key_id, days)
            traffic_limit_bytes = (tariff.get('traffic_limit_gb', 0) or 0) * 1024 ** 3
            update_key_tariff(key_id, tariff_id, traffic_limit_bytes)
            # Восстанавливаем лимит трафика в БД
            restore_traffic_limit_in_db(key_id)
            # Пушим ВСЕ данные из БД на панель (сброс up/down + обновление)
            await push_key_to_panel(key_id, reset_traffic=True)
            logger.info(f'Ключ {key_id} продлён на {days} дней за баланс {actual_deduct} коп')
        else:
            traffic_limit_bytes = (tariff.get('traffic_limit_gb', 0) or 0) * 1024 ** 3
            new_key_id = create_initial_vpn_key(user_internal_id, tariff_id, days, traffic_limit=traffic_limit_bytes)
            logger.info(f'Создан черновик ключа {new_key_id} для user {user_internal_id} за баланс {actual_deduct} коп')
    
    await state.update_data(balance_to_deduct=0)

    def format_price_compact(cents: int) -> str:
        if cents >= 10000:
            return f'{cents // 100} ₽'
        else:
            return f'{cents / 100:.2f} ₽'.replace('.', ',')
    price_str = format_price_compact(actual_deduct)
    
    if key_id:
        # Продление — ключ уже на сервере, просто сообщаем
        await safe_edit_or_send(callback.message, f'✅ <b>Оплата успешно завершена!</b>\n\nС вашего баланса списано {price_str}\nКлюч продлён на {days} дн.', reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text='🈴 На главную', callback_data='start')).as_markup())
    else:
        # Новый ключ — нужно настроить (выбор сервера/inbound)
        from bot.handlers.user.payments.base import finalize_payment_ui
        update_payment_key_id(order_id, new_key_id)
        order = find_order_by_order_id(order_id) or {'order_id': order_id, 'vpn_key_id': new_key_id, 'tariff_id': tariff_id}
        order['vpn_key_id'] = new_key_id
        await finalize_payment_ui(callback.message, state, f'✅ <b>Оплата успешно завершена!</b>\n\nС вашего баланса списано {price_str}', order, user_id=telegram_id)
    await callback.answer()

@router.callback_query(F.data.startswith('pay_card_balance:'))
async def pay_card_balance_handler(callback: CallbackQuery, state: FSMContext):
    """
    Частичная оплата: баланс + карта.
    
    Берёт данные из FSM state: balance_to_deduct, remaining_cents, tariff_id, key_id, order_id
    Создаёт инвойс на remaining_cents (не на полную цену тарифа!)
    Учитывает промокод если он был применен.
    """
    from aiogram.types import LabeledPrice
    from database.requests import (
        get_tariff_by_id, get_user_internal_id, get_user_balance, 
        prepare_payment_order, get_setting, find_order_by_order_id
    )
    from aiogram.exceptions import TelegramBadRequest
    
    data = await state.get_data()
    balance_to_deduct = data.get('balance_to_deduct', 0)
    tariff_price_cents = data.get('tariff_price_cents', 0)
    tariff_id = data.get('tariff_id')
    key_id = data.get('key_id')
    existing_order_id = data.get('order_id')  # Заказ с промокодом из state
    
    parts = callback.data.split(':')
    if not tariff_id:
        tariff_id = int(parts[1]) if len(parts) > 1 else None
    if not key_id:
        key_id = int(parts[2]) if len(parts) > 2 and parts[2] != '0' else None
    
    if not tariff_id:
        await callback.answer('❌ Ошибка: тариф не определён', show_alert=True)
        return
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    provider_token = get_setting('cards_provider_token', '')
    if not provider_token:
        await callback.answer('❌ Провайдер платежей не настроен', show_alert=True)
        return
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    
    # Проверяем есть ли промокод в существующем заказе
    discount_rub = 0
    promocode_id = None
    if existing_order_id:
        order = find_order_by_order_id(existing_order_id)
        if order:
            discount_rub = order.get('discount_rub', 0) or 0
            promocode_id = order.get('promocode_id')
            logger.info(f"Найден заказ {existing_order_id} с промокодом {promocode_id}, скидка {discount_rub}₽")
    
    # Пересчитываем цену с учетом промокода
    if not tariff_price_cents:
        base_price_cents = int(tariff.get('price_rub', 0) * 100)
        tariff_price_cents = max(0, base_price_cents - (discount_rub * 100))
    
    if not balance_to_deduct:
        balance_cents = get_user_balance(user_id)
        balance_to_deduct = min(balance_cents, tariff_price_cents)
    
    remaining_cents = tariff_price_cents - balance_to_deduct
    
    await state.update_data(
        balance_to_deduct=balance_to_deduct,
        tariff_price_cents=tariff_price_cents,
        tariff_id=tariff_id,
        key_id=key_id,
        remaining_cents=remaining_cents,
        order_id=existing_order_id
    )
    
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='cards',
        vpn_key_id=key_id,
        order_id=existing_order_id,
    )
    order_id = prepared_order['order_id']
    if existing_order_id:
        logger.info(f"Используем существующий заказ {order_id} с промокодом")
    
    price_rub = remaining_cents / 100
    price_kopecks = remaining_cents
    
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.first_name
        back_cb = f'key_renew:{key_id}' if key_id else 'buy_key'
        
        await callback.message.answer_invoice(
            title=bot_name,
            description=f"Оплата тарифа «{tariff['name']}» ({tariff['duration_days']} дн.).",
            payload=f'vpn_key:{order_id}',
            provider_token=provider_token,
            currency='RUB',
            prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_kopecks)],
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text=f'💳 Оплатить {price_rub:.2f} ₽', pay=True)
            ).row(
                InlineKeyboardButton(text='❌ Отмена', callback_data=back_cb)
            ).as_markup()
        )
    except TelegramBadRequest as e:
        if 'CURRENCY_TOTAL_AMOUNT_INVALID' in str(e):
            logger.warning(f"Ошибка платежа (CARDS): Неправильная сумма. Тариф: ID {tariff['id']}")
            await callback.answer('❌ Ошибка платежной системы. Сумма тарифа меньше допустимого лимита.', show_alert=True)
            return
        logger.exception('Ошибка при отправке инвойса картой.')
        raise e
    
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith('pay_qr_balance:'))
async def pay_qr_balance_handler(callback: CallbackQuery, state: FSMContext):
    """
    Частичная оплата: баланс + QR (СБП).
    
    Берёт данные из FSM state: balance_to_deduct, remaining_cents, tariff_id, key_id
    Создаёт инвойс на remaining_cents / 100 рублей (ЮKassa принимает рубли)
    """
    from database.requests import (
        get_tariff_by_id, get_user_internal_id, get_user_balance, 
        prepare_payment_order, save_yookassa_payment_id, find_order_by_order_id
    )
    from bot.services.billing import create_yookassa_qr_payment
    from bot.keyboards.user import yookassa_qr_kb
    from bot.keyboards.admin import home_only_kb
    
    data = await state.get_data()
    balance_to_deduct = data.get('balance_to_deduct', 0)
    tariff_price_cents = data.get('tariff_price_cents', 0)
    tariff_id = data.get('tariff_id')
    key_id = data.get('key_id')
    
    parts = callback.data.split(':')
    if not tariff_id:
        tariff_id = int(parts[1]) if len(parts) > 1 else None
    if not key_id:
        key_id = int(parts[2]) if len(parts) > 2 and parts[2] != '0' else None
    
    # Получаем order_id если передан
    existing_order_id = data.get('order_id') or (parts[3] if len(parts) > 3 and parts[3] != '0' else None)
    
    if not tariff_id:
        await callback.answer('❌ Ошибка: тариф не определён', show_alert=True)
        return
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Пользователь не найден', show_alert=True)
        return
    
    if not tariff_price_cents:
        tariff_price_cents = int(tariff.get('price_rub', 0) * 100)
    
    if not balance_to_deduct:
        balance_cents = get_user_balance(user_id)
        balance_to_deduct = min(balance_cents, tariff_price_cents)
    
    # Проверяем есть ли промокод в существующем заказе
    discount_rub = 0
    promocode_id = None
    if existing_order_id:
        order = find_order_by_order_id(existing_order_id)
        if order:
            discount_rub = order.get('discount_rub', 0) or 0
            promocode_id = order.get('promocode_id')
            logger.info(f"Найден заказ {existing_order_id} с промокодом {promocode_id}, скидка {discount_rub}₽")
    
    # Применяем скидку от промокода
    final_price_cents = max(0, tariff_price_cents - (discount_rub * 100))
    remaining_cents = final_price_cents - balance_to_deduct
    remaining_rub = remaining_cents / 100
    
    await state.update_data(
        balance_to_deduct=balance_to_deduct,
        tariff_price_cents=tariff_price_cents,
        tariff_id=tariff_id,
        key_id=key_id,
        remaining_cents=remaining_cents
    )
    
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='yookassa_qr',
        vpn_key_id=key_id,
        order_id=existing_order_id,
    )
    order_id = prepared_order['order_id']
    if existing_order_id:
        logger.info(f"Используем существующий заказ {order_id} с промокодом")
    
    await safe_edit_or_send(callback.message, '⏳ Создаём оплату...')
    
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.username
        description = f"Покупка «{tariff['name']}» — {tariff['duration_days']} дней"
        
        result = await create_yookassa_qr_payment(
            amount_rub=remaining_rub,
            order_id=order_id,
            description=description,
            bot_name=bot_name
        )
        
        save_yookassa_payment_id(order_id, result['yookassa_payment_id'])
        
        qr_url = result.get('qr_url', '')
        
        if not qr_url:
            await safe_edit_or_send(
                callback.message,
                '❌ ЮКасса не вернула данные для оплаты. Попробуйте позже.',
                reply_markup=home_only_kb()
            )
            return
        
        text = (
            f"💳 <b>Оплата подписки</b>\n\n"
            f"<b>{escape_html(tariff['name'])}</b> · {remaining_rub:.2f} ₽\n"
            f"Срок: {tariff['duration_days']} дней\n\n"
            "Нажмите кнопку ниже и подтвердите оплату в приложении банка.\n\n"
            "<i>Подписка обновится автоматически сразу после оплаты.</i>"
        )
        
        if discount_rub > 0:
            text = text.replace(
                f"<b>{escape_html(tariff['name'])}</b> · {remaining_rub:.2f} ₽",
                f"💰 <b>Цена:</b> <s>{tariff['price_rub']:.2f} ₽</s> → {remaining_rub:.2f} ₽\n"
                f"🎟️ <b>Скидка по промокоду:</b> {discount_rub} ₽"
            )
        
        back_cb = f'key_renew:{key_id}' if key_id else 'buy_key'
        
        await safe_edit_or_send(
            callback.message,
            text,
            reply_markup=yookassa_qr_kb(
                order_id, back_callback=back_cb, qr_url=qr_url, amount_rub=remaining_rub
            ),
        )
        
    except Exception as e:
        logger.exception(f'Ошибка создания QR ЮКасса: {e}')
        await safe_edit_or_send(
            callback.message,
            f'❌ <b>Не удалось создать оплату</b>\n\n<i>{escape_html(str(e))}</i>\n\nПопробуйте ещё раз.',
            reply_markup=home_only_kb()
        )
    
    await callback.answer()
