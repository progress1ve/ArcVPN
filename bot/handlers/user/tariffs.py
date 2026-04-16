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
    """Показывает список тарифов для покупки."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    
    telegram_id = callback.from_user.id
    
    # Получаем список активных тарифов
    tariffs = get_all_tariffs(include_hidden=False)
    
    if not tariffs:
        await safe_edit_or_send(
            callback.message,
            '💳 <b>Купить подписку</b>\n\n'
            '😔 К сожалению, сейчас нет доступных тарифов.\n\n'
            'Попробуйте позже или обратитесь в поддержку.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    
    # Показываем список тарифов
    text = (
        '💳 <b>Купить подписку</b>\n\n'
        'Выберите тариф:'
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=tariff_select_kb(tariffs, back_callback='start', is_select_only=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('select_tariff:'))
async def select_tariff_handler(callback: CallbackQuery):
    """Показывает способы оплаты для выбранного тарифа."""
    from database.requests import (
        is_crypto_configured, is_stars_enabled, is_cards_enabled, 
        get_setting, get_user_internal_id, get_tariff_by_id,
        create_pending_order, is_yookassa_qr_configured, 
        get_crypto_integration_mode, is_referral_enabled, 
        get_referral_reward_type, get_user_balance, is_demo_payment_enabled
    )
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    from bot.keyboards.user import payment_method_kb
    from bot.keyboards.admin import home_only_kb
    
    # Получаем ID тарифа из callback_data
    tariff_id = int(callback.data.split(':')[1])
    tariff = get_tariff_by_id(tariff_id)
    
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    telegram_id = callback.from_user.id
    user_id = get_user_internal_id(telegram_id)
    
    # Проверяем доступные способы оплаты
    crypto_configured = is_crypto_configured()
    crypto_mode = get_crypto_integration_mode()
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    yookassa_qr = is_yookassa_qr_configured()
    demo_enabled = is_demo_payment_enabled()
    
    if not crypto_configured and not stars_enabled and not cards_enabled and not yookassa_qr and not demo_enabled:
        await safe_edit_or_send(
            callback.message,
            '💳 <b>Оплата</b>\n\n'
            '😔 К сожалению, сейчас оплата недоступна.\n\n'
            'Попробуйте позже или обратитесь в поддержку.',
            reply_markup=home_only_kb()
        )
        await callback.answer()
        return
    
    # Создаем ордер
    crypto_url = None
    existing_order_id = None
    
    if user_id:
        (_, order_id) = create_pending_order(
            user_id=user_id, 
            tariff_id=tariff_id, 
            payment_type=None, 
            vpn_key_id=None
        )
        existing_order_id = order_id
        
        if crypto_configured and crypto_mode == 'standard':
            crypto_item_url = get_setting('crypto_item_url')
            item_id = extract_item_id_from_url(crypto_item_url)
            if item_id:
                crypto_url = build_crypto_payment_url(
                    item_id=item_id, 
                    invoice_id=order_id, 
                    tariff_external_id=tariff.get('external_id'),
                    price_cents=tariff['price_cents']
                )
    
    # Проверяем баланс для оплаты
    show_balance_button = False
    if is_referral_enabled() and get_referral_reward_type() == 'balance':
        if user_id:
            balance_cents = get_user_balance(user_id)
            if balance_cents > 0:
                show_balance_button = True
    
    # Формируем текст с информацией о тарифе
    price_usd = tariff['price_cents'] / 100
    price_str = f"{price_usd:g}".replace('.', ',')
    
    traffic_gb = tariff.get('traffic_limit_gb', 0)
    traffic_text = f"{traffic_gb} ГБ" if traffic_gb > 0 else "Безлимит"
    
    text = (
        f"💳 <b>Оплата подписки</b>\n\n"
        f"📋 <b>Тариф:</b> {escape_html(tariff['name'])}\n"
        f"💰 <b>Цена:</b> ${price_str} / ⭐ {tariff['price_stars']} / ₽ {tariff.get('price_rub', 0)}\n"
        f"📅 <b>Срок:</b> {tariff['duration_days']} дней\n"
        f"📦 <b>Трафик:</b> {traffic_text}\n\n"
        f"Выберите способ оплаты:"
    )
    
    kb = payment_method_kb(
        tariff_id=tariff_id,
        crypto_url=crypto_url,
        crypto_mode=crypto_mode,
        crypto_configured=crypto_configured,
        stars_enabled=stars_enabled,
        cards_enabled=cards_enabled,
        yookassa_qr_enabled=yookassa_qr,
        order_id=existing_order_id,
        show_balance_button=show_balance_button,
        demo_enabled=demo_enabled
    )
    
    await safe_edit_or_send(callback.message, text, reply_markup=kb)
    await callback.answer()