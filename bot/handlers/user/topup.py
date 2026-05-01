"""
Обработчики пополнения баланса
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database.requests import (
    get_user_internal_id,
    get_user_balance,
    is_stars_enabled,
    is_cards_enabled,
    is_yookassa_qr_configured,
    is_crypto_configured,
)
from bot.utils.text import safe_edit_or_send, escape_html

logger = logging.getLogger(__name__)

router = Router()


def format_price_compact(cents: int) -> str:
    """Форматирует копейки в компактную строку рублей."""
    if cents >= 10000:
        return f"{cents // 100} ₽"
    else:
        return f"{cents / 100:.2f} ₽".replace(".", ",")


# Предустановленные суммы для пополнения (в копейках)
TOPUP_AMOUNTS = [
    10000,   # 100₽
    30000,   # 300₽
    50000,   # 500₽
    100000,  # 1000₽
]


@router.callback_query(F.data == "topup_balance")
async def show_topup_amounts(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор суммы для пополнения баланса"""
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    balance = get_user_balance(user_id)
    
    text = (
        "💰 <b>Пополнение баланса</b>\n\n"
        f"💎 <b>Текущий баланс:</b> {format_price_compact(balance)}\n\n"
        "Выберите сумму пополнения:"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки с суммами
    for amount_cents in TOPUP_AMOUNTS:
        amount_rub = amount_cents // 100
        builder.row(
            InlineKeyboardButton(
                text=f"💵 {amount_rub} ₽",
                callback_data=f"topup_amount:{amount_cents}"
            )
        )
    
    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="referral_system")
    )
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("topup_amount:"))
async def show_topup_payment_methods(callback: CallbackQuery, state: FSMContext):
    """Показывает способы оплаты для пополнения баланса"""
    parts = callback.data.split(":")
    amount_cents = int(parts[1])
    amount_rub = amount_cents // 100
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    # Сохраняем сумму в state
    await state.update_data(topup_amount_cents=amount_cents)
    
    # Проверяем доступные способы оплаты
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    yookassa_qr_enabled = is_yookassa_qr_configured()
    crypto_enabled = is_crypto_configured()
    
    text = (
        "💰 <b>Пополнение баланса</b>\n\n"
        f"💵 <b>Сумма:</b> {amount_rub} ₽\n\n"
        "Выберите способ оплаты:"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки способов оплаты
    if stars_enabled:
        builder.row(
            InlineKeyboardButton(
                text="⭐ Telegram Stars",
                callback_data=f"topup_stars:{amount_cents}"
            )
        )
    
    if cards_enabled:
        builder.row(
            InlineKeyboardButton(
                text="💳 Банковская карта",
                callback_data=f"topup_cards:{amount_cents}"
            )
        )
    
    if yookassa_qr_enabled:
        builder.row(
            InlineKeyboardButton(
                text="📱 СБП / QR-код",
                callback_data=f"topup_qr:{amount_cents}"
            )
        )
    
    if crypto_enabled:
        builder.row(
            InlineKeyboardButton(
                text="🪙 Криптовалюта (USDT)",
                callback_data=f"topup_crypto:{amount_cents}"
            )
        )
    
    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="topup_balance")
    )
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


# TODO: Добавить обработчики для каждого способа оплаты
# topup_stars, topup_cards, topup_qr, topup_crypto


@router.callback_query(F.data.startswith("topup_stars:"))
async def topup_stars_handler(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса через Telegram Stars"""
    from aiogram.types import LabeledPrice
    from database.requests import create_pending_order, get_user_internal_id
    
    parts = callback.data.split(":")
    amount_cents = int(parts[1])
    amount_rub = amount_cents // 100
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    # Конвертируем рубли в Stars (примерно 1 Star = 1.3 рубля)
    # Используем курс из billing.py: 1 Star = 0.013 USD, USD/RUB ≈ 100
    # Итого: 1 Star ≈ 1.3 рубля
    stars_amount = int(amount_rub / 1.3)
    
    # Создаем pending order для пополнения (tariff_id=None означает пополнение баланса)
    success, order_id = create_pending_order(
        user_id=user_id,
        tariff_id=None,  # None означает пополнение баланса
        payment_type='stars',
        vpn_key_id=None,
        amount_cents=amount_cents,
        amount_stars=stars_amount
    )
    
    if not success:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return
    
    # Сохраняем в state что это пополнение баланса
    await state.update_data(is_topup=True, topup_amount_cents=amount_cents)
    
    logger.info(f"Sending stars invoice for topup: order_id={order_id}, amount={amount_cents}, stars={stars_amount}")
    
    # Отправляем invoice
    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Пополнение баланса на {amount_rub} ₽",
            description=f"Пополнение баланса на {amount_rub} рублей",
            payload=order_id,
            provider_token="",  # Пустой для Stars
            currency="XTR",
            prices=[LabeledPrice(label=f"Пополнение {amount_rub} ₽", amount=stars_amount)]
        )
        logger.info(f"Stars invoice sent successfully for order {order_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки invoice для Stars: {e}")
        await callback.answer("❌ Ошибка отправки счёта", show_alert=True)
        return
    
    await callback.answer()


@router.callback_query(F.data.startswith("topup_cards:"))
async def topup_cards_handler(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса через банковскую карту"""
    from aiogram.types import LabeledPrice
    from database.requests import create_pending_order, get_user_internal_id, get_payment_token
    
    parts = callback.data.split(":")
    amount_cents = int(parts[1])
    amount_rub = amount_cents // 100
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    # Проверяем минимальную сумму для карт (обычно 100₽)
    if amount_cents < 10000:
        await callback.answer("❌ Минимальная сумма для оплаты картой: 100 ₽", show_alert=True)
        return
    
    # Создаем pending order
    success, order_id = create_pending_order(
        user_id=user_id,
        tariff_id=None,
        payment_type='cards',
        vpn_key_id=None,
        amount_cents=amount_cents
    )
    
    if not success:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return
    
    await state.update_data(is_topup=True, topup_amount_cents=amount_cents)
    
    # Получаем токен провайдера
    payment_token = get_payment_token()
    if not payment_token:
        logger.warning(f"Payment token not configured for cards topup")
        await callback.answer("❌ Оплата картами временно недоступна", show_alert=True)
        return
    
    logger.info(f"Sending cards invoice for topup: order_id={order_id}, amount={amount_cents}")
    
    # Отправляем invoice
    try:
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Пополнение баланса на {amount_rub} ₽",
            description=f"Пополнение баланса на {amount_rub} рублей",
            payload=order_id,
            provider_token=payment_token,
            currency="RUB",
            prices=[LabeledPrice(label=f"Пополнение {amount_rub} ₽", amount=amount_cents)]
        )
        logger.info(f"Cards invoice sent successfully for order {order_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки invoice для карт: {e}")
        await callback.answer("❌ Ошибка отправки счёта", show_alert=True)
        return
    
    await callback.answer()


@router.callback_query(F.data.startswith("topup_qr:"))
async def topup_qr_handler(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса через QR-код (ЮКасса)"""
    from database.requests import create_pending_order, get_user_internal_id
    from bot.services.billing import create_yookassa_qr_payment
    from aiogram.types import BufferedInputFile
    
    parts = callback.data.split(":")
    amount_cents = int(parts[1])
    amount_rub = amount_cents / 100
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    # Создаем pending order
    success, order_id = create_pending_order(
        user_id=user_id,
        tariff_id=None,
        payment_type='yookassa_qr',
        vpn_key_id=None,
        amount_cents=amount_cents
    )
    
    if not success:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return
    
    await state.update_data(is_topup=True, topup_amount_cents=amount_cents)
    
    try:
        # Создаем QR-платеж
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
        payment_data = await create_yookassa_qr_payment(
            amount_rub=amount_rub,
            order_id=order_id,
            description=f"Пополнение баланса на {amount_rub:.0f} ₽",
            bot_name=bot_username
        )
        
        # Сохраняем yookassa_payment_id в БД
        from database.requests import update_payment_yookassa_id
        update_payment_yookassa_id(order_id, payment_data['yookassa_payment_id'])
        
        # Отправляем QR-код
        qr_image = BufferedInputFile(payment_data['qr_image_data'], filename="qr.png")
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_topup_qr:{order_id}")
        )
        builder.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="topup_balance")
        )
        
        await callback.message.answer_photo(
            photo=qr_image,
            caption=(
                f"📱 <b>Пополнение баланса на {amount_rub:.0f} ₽</b>\n\n"
                f"Отсканируйте QR-код приложением вашего банка\n"
                f"или перейдите по ссылке для оплаты.\n\n"
                f"После оплаты нажмите кнопку «✅ Я оплатил»"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка создания QR-платежа: {e}")
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)


@router.callback_query(F.data.startswith("topup_crypto:"))
async def topup_crypto_handler(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса через криптовалюту"""
    from database.requests import create_pending_order, get_user_internal_id, get_setting
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    
    parts = callback.data.split(":")
    amount_cents = int(parts[1])
    amount_rub = amount_cents // 100
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer("❌ Ошибка пользователя", show_alert=True)
        return
    
    # Создаем pending order
    success, order_id = create_pending_order(
        user_id=user_id,
        tariff_id=None,
        payment_type='crypto',
        vpn_key_id=None,
        amount_cents=amount_cents
    )
    
    if not success:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return
    
    await state.update_data(is_topup=True, topup_amount_cents=amount_cents)
    
    # Получаем настройки крипто-оплаты
    crypto_item_url = get_setting('crypto_item_url')
    item_id = extract_item_id_from_url(crypto_item_url)
    
    if not item_id:
        await callback.answer("❌ Крипто-оплата не настроена", show_alert=True)
        return
    
    # Генерируем ссылку на оплату
    crypto_url = build_crypto_payment_url(
        item_id=item_id,
        invoice_id=order_id,
        tariff_external_id=None,
        price_cents=amount_cents
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"💰 Оплатить ${amount_cents/100:.2f}", url=crypto_url)
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="topup_balance")
    )
    
    await safe_edit_or_send(
        callback.message,
        f"🪙 <b>Пополнение баланса на {amount_rub} ₽</b>\n\n"
        f"💵 <b>Сумма:</b> ${amount_cents/100:.2f} USDT\n\n"
        f"Нажмите кнопку ниже для оплаты через криптопроцессинг:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("check_topup_qr:"))
async def check_topup_qr_payment(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса QR-платежа для пополнения баланса"""
    from database.requests import find_order_by_order_id, is_order_already_paid, get_user_internal_id, add_to_balance, complete_order
    from bot.services.billing import check_yookassa_payment_status
    
    parts = callback.data.split(":")
    order_id = parts[1]
    
    # Проверяем что заказ еще не оплачен
    if is_order_already_paid(order_id):
        await callback.answer("✅ Платеж уже обработан!", show_alert=True)
        return
    
    order = find_order_by_order_id(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    yookassa_payment_id = order.get('yookassa_payment_id')
    if not yookassa_payment_id:
        await callback.answer("❌ ID платежа не найден", show_alert=True)
        return
    
    try:
        # Проверяем статус в ЮКасса
        status = await check_yookassa_payment_status(yookassa_payment_id)
        
        if status == 'succeeded':
            # Платеж успешен - пополняем баланс
            user_id = order['user_id']
            amount_cents = order.get('amount_cents', 0)
            
            # Пополняем баланс
            from bot.services.user_locks import user_locks
            async with user_locks[user_id]:
                add_to_balance(user_id, amount_cents)
            
            # Закрываем заказ
            complete_order(order_id)
            
            logger.info(f"Баланс пополнен на {amount_cents} коп для user {user_id} (order {order_id})")
            
            # Показываем успех
            from database.requests import get_user_balance
            new_balance = get_user_balance(user_id)
            
            await callback.message.edit_caption(
                caption=(
                    f"✅ <b>Баланс успешно пополнен!</b>\n\n"
                    f"💰 <b>Зачислено:</b> {format_price_compact(amount_cents)}\n"
                    f"💎 <b>Ваш баланс:</b> {format_price_compact(new_balance)}"
                ),
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🏠 На главную", callback_data="start")
                ).as_markup(),
                parse_mode="HTML"
            )
            await callback.answer("✅ Баланс пополнен!")
            
        elif status in ['pending', 'waiting_for_capture']:
            await callback.answer("⏳ Платеж еще обрабатывается. Попробуйте через несколько секунд.", show_alert=True)
        else:
            await callback.answer("❌ Платеж не найден или отменен", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка проверки статуса платежа: {e}")
        await callback.answer("❌ Ошибка проверки платежа", show_alert=True)

