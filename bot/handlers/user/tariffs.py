import logging
import uuid
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from config import ADMIN_IDS
from database.requests import get_or_create_user, is_user_banned, get_all_servers, get_setting, is_referral_enabled, get_user_by_referral_code, set_user_referrer
from bot.keyboards.user import main_menu_kb
from bot.states.user_states import RenameKey, ReplaceKey
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == 'buy_key')
async def buy_key_handler(callback: CallbackQuery):
    """Страница «Купить ключ» с условиями и способами оплаты."""
    from database.requests import is_crypto_configured, is_stars_enabled, is_cards_enabled, get_setting, get_user_internal_id, get_all_tariffs, create_pending_order, is_yookassa_qr_configured, get_crypto_integration_mode, is_referral_enabled, get_referral_reward_type, get_user_balance, is_demo_payment_enabled
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    from bot.keyboards.user import buy_key_kb
    from bot.keyboards.admin import home_only_kb
    telegram_id = callback.from_user.id
    crypto_configured = is_crypto_configured()
    crypto_mode = get_crypto_integration_mode()
    crypto_url = None
    existing_order_id = None
    user_id = get_user_internal_id(telegram_id)
    if crypto_configured and user_id:
        (_, order_id) = create_pending_order(user_id=user_id, tariff_id=None, payment_type=None, vpn_key_id=None)
        existing_order_id = order_id
        if crypto_mode == 'standard':
            crypto_item_url = get_setting('crypto_item_url')
            item_id = extract_item_id_from_url(crypto_item_url)
            if item_id:
                crypto_url = build_crypto_payment_url(item_id=item_id, invoice_id=order_id, tariff_external_id=None, price_cents=None)
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    yookassa_qr = is_yookassa_qr_configured()
    show_balance_button = False
    if is_referral_enabled() and get_referral_reward_type() == 'balance':
        if user_id:
            balance_cents = get_user_balance(user_id)
            if balance_cents > 0:
                show_balance_button = True
    demo_enabled = is_demo_payment_enabled()
    if not crypto_configured and (not stars_enabled) and (not cards_enabled) and (not yookassa_qr) and (not demo_enabled):
        await safe_edit_or_send(callback.message, '💳 <b>Купить ключ</b>\n\n😔 К сожалению, сейчас оплата недоступна.\n\nПопробуйте позже или обратитесь в поддержку.', reply_markup=home_only_kb())
        await callback.answer()
        return
    from bot.utils.message_editor import get_message_data, send_editor_message
    prepayment_data = get_message_data('prepayment_text', '')
    prepayment_text = prepayment_data.get('text', '') or ''
    # Добавляем приглашение выбрать способ оплаты (HTML)
    text_override = f'{prepayment_text}\n\nВыберите способ оплаты:' if prepayment_text else 'Выберите способ оплаты:'
    kb = buy_key_kb(crypto_url=crypto_url, crypto_mode=crypto_mode, crypto_configured=crypto_configured, stars_enabled=stars_enabled, cards_enabled=cards_enabled, yookassa_qr_enabled=yookassa_qr, order_id=existing_order_id, show_balance_button=show_balance_button, demo_enabled=demo_enabled)
    try:
        await send_editor_message(callback.message, data=prepayment_data, reply_markup=kb, text_override=text_override)
    except Exception:
        try:
            await callback.message.delete()
        except:
            pass
        # Фоллбэк: отправляем новое сообщение
        prepayment_photo = prepayment_data.get('photo_file_id')
        await safe_edit_or_send(callback.message, text_override, photo=prepayment_photo, reply_markup=kb, force_new=True)
    await callback.answer()