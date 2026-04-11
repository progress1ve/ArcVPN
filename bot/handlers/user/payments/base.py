import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from bot.utils.text import escape_html, safe_edit_or_send
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
router = Router()

def _format_price_compact(cents: int) -> str:
    """Форматирование цены в компактном виде."""
    if cents >= 10000:
        return f'{cents // 100} ₽'
    else:
        return f'{cents / 100:.2f} ₽'.replace('.', ',')

def _is_cards_via_yookassa_direct() -> bool:
    """
    Проверяет, используется ли оплата картами через ЮKassa напрямую (webhook).
    
    Returns:
        True если карты через ЮKassa напрямую (минимум 1₽),
        False если через Telegram Payments API (минимум ~100₽)
    """
    from database.requests import get_setting
    return get_setting('cards_via_yookassa_direct', '0') == '1'

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery):
    """Подтверждение pre-checkout для Telegram Stars."""
    await pre_checkout.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, state: FSMContext):
    """
    Обработка успешной оплаты Stars или Cards.
    
    Делегирует общую post-payment логику в complete_payment_flow().
    """
    from bot.services.billing import complete_payment_flow
    payment = message.successful_payment
    payload = payment.invoice_payload
    currency = payment.currency
    payment_type = 'stars' if currency == 'XTR' else 'cards'
    logger.info(f'Успешная оплата {payment_type}: {payload}, charge_id={payment.telegram_payment_charge_id}')
    
    if payload.startswith('renew:'):
        order_id = payload.split(':')[1]
    elif payload.startswith('vpn_key:'):
        order_id = payload.split(':')[1]
    else:
        order_id = payload
    
    await complete_payment_flow(
        order_id=order_id,
        message=message,
        state=state,
        telegram_id=message.from_user.id,
        payment_type=payment_type,
        referral_amount=payment.total_amount
    )

async def finalize_payment_ui(message: Message, state: FSMContext, text: str, order: dict, user_id: int):
    """
    Завершает UI после успешной оплаты.
    Показывает сообщение и либо перекидывает на настройку (draft), либо на главную.
    """
    from bot.keyboards.admin import home_only_kb
    from database.requests import get_key_details_for_user
    import logging
    logger = logging.getLogger(__name__)
    from bot.handlers.user.payments.keys_config import start_new_key_config
    key_id = order.get('vpn_key_id')
    logger.info(f"finalize_payment_ui: Order={order.get('order_id')}, Key={key_id}, User={user_id}")
    is_draft = False
    if key_id:
        key = get_key_details_for_user(key_id, user_id)
        if key:
            logger.info(f"Key details found: ID={key['id']}, ServerID={key.get('server_id')}")
            if not key.get('server_id'):
                is_draft = True
        else:
            logger.warning(f'Key {key_id} not found for user {user_id} via details check!')
    else:
        logger.info('No key_id in order object.')
    logger.info(f'Result: is_draft={is_draft}')
    if is_draft:
        await safe_edit_or_send(message, text, force_new=True)
        await start_new_key_config(message, state, order['order_id'], key_id)
    else:
        from bot.handlers.user.keys import show_key_details
        await show_key_details(telegram_id=user_id, key_id=key_id, message=message, is_callback=False, prepend_text=text)

@router.callback_query(F.data.startswith('renew_invoice_cancel:'))
async def renew_invoice_cancel_handler(callback: CallbackQuery):
    """Отмена инвойса и возврат к выбору способа оплаты."""
    from bot.keyboards.user import renew_payment_method_kb
    from database.requests import get_key_details_for_user, get_all_tariffs, is_crypto_configured, is_stars_enabled, is_cards_enabled, get_user_internal_id, create_pending_order, get_setting, is_yookassa_qr_configured, get_crypto_integration_mode, is_referral_enabled, get_referral_reward_type, get_user_balance, is_demo_payment_enabled
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    parts = callback.data.split(':')
    key_id = int(parts[1])
    telegram_id = callback.from_user.id

    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
        
    crypto_configured = is_crypto_configured()
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    yookassa_qr_enabled = is_yookassa_qr_configured()
    demo_enabled = is_demo_payment_enabled()
    
    if not crypto_configured and (not stars_enabled) and (not cards_enabled) and (not yookassa_qr_enabled) and (not demo_enabled):
        await safe_edit_or_send(callback.message, '😔 Способы оплаты временно недоступны.', force_new=True)
        return

    crypto_url = None
    crypto_mode = get_crypto_integration_mode()
    user_id = get_user_internal_id(telegram_id)
    
    if crypto_configured and user_id:
        tariffs = get_all_tariffs(include_hidden=False)
        if tariffs:
            (_, order_id) = create_pending_order(user_id=user_id, tariff_id=tariffs[0]['id'], payment_type='crypto', vpn_key_id=key_id)
            if crypto_mode == 'standard':
                item_url = get_setting('crypto_item_url')
                item_id = extract_item_id_from_url(item_url)
                if item_id:
                    crypto_url = build_crypto_payment_url(item_id=item_id, invoice_id=order_id, tariff_external_id=None, price_cents=None)
                    
    show_balance_button = False
    if is_referral_enabled() and get_referral_reward_type() == 'balance':
        if user_id:
            balance_cents = get_user_balance(user_id)
            if balance_cents > 0:
                show_balance_button = True

    await safe_edit_or_send(
        callback.message,
        f"💳 <b>Продление ключа</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите способ оплаты:",
        reply_markup=renew_payment_method_kb(
            key_id=key_id,
            crypto_url=crypto_url,
            crypto_mode=crypto_mode,
            crypto_configured=crypto_configured,
            stars_enabled=stars_enabled,
            cards_enabled=cards_enabled,
            yookassa_qr_enabled=yookassa_qr_enabled,
            show_balance_button=show_balance_button,
            demo_enabled=demo_enabled
        ),
        force_new=True
    )
    await callback.answer()