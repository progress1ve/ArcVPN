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

@router.callback_query(F.data.startswith('renew_crypto_tariff:'))
async def renew_crypto_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для продления (Crypto)."""
    from database.requests import get_key_details_for_user, get_all_tariffs
    from bot.keyboards.user import renew_tariff_select_kb
    parts = callback.data.split(':')
    key_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    telegram_id = callback.from_user.id
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    from bot.utils.groups import get_tariffs_for_renewal
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    if not tariffs:
        await callback.answer('Нет доступных тарифов', show_alert=True)
        return
    await safe_edit_or_send(callback.message, f"💰 <b>Оплата криптовалютой</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:", reply_markup=renew_tariff_select_kb(tariffs, key_id, order_id=order_id, is_crypto=True))
    await callback.answer()

@router.callback_query(F.data.startswith('renew_pay_crypto:'))
async def renew_crypto_invoice(callback: CallbackQuery):
    """Инвойс для оплаты Crypto (за продление ключа)."""
    from database.requests import get_tariff_by_id, get_user_internal_id, create_pending_order, get_key_details_for_user, update_order_tariff, update_payment_type, get_setting
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('Ошибка тарифа или ключа', show_alert=True)
        return
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        return
    if order_id:
        update_order_tariff(order_id, tariff_id)
        update_payment_type(order_id, 'crypto')
    else:
        (_, order_id) = create_pending_order(user_id=user_id, tariff_id=tariff_id, payment_type='crypto', vpn_key_id=key_id)
    crypto_item_url = get_setting('crypto_item_url')
    item_id = extract_item_id_from_url(crypto_item_url)
    if not item_id:
        await callback.answer('❌ Ошибка настройки крипто-платежей', show_alert=True)
        return
    crypto_url = build_crypto_payment_url(item_id=item_id, invoice_id=order_id, tariff_external_id=None, price_cents=tariff['price_cents'])
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='💰 Перейти к оплате', url=crypto_url))
    cb_data = f'renew_crypto_tariff:{key_id}:{order_id}' if order_id else f'renew_crypto_tariff:{key_id}'
    builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data=cb_data))
    price_usd = tariff['price_cents'] / 100
    price_str = f'${price_usd:g}'.replace('.', ',')
    await safe_edit_or_send(callback.message, f"💰 <b>Продление ключа</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\nТариф: <b>{escape_html(tariff['name'])}</b>\nСумма к оплате: <b>{price_str}</b>\n\nНажмите кнопку ниже, чтобы перейти к генерации счета в @Ya_SellerBot.", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith('pay_crypto'))
async def pay_crypto_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для оплаты Crypto."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    order_id = None
    if ':' in callback.data:
        order_id = callback.data.split(':')[1]
    tariffs = get_all_tariffs(include_hidden=False)
    if not tariffs:
        await safe_edit_or_send(callback.message, '💰 <b>Оплата криптовалютой</b>\n\n😔 Нет доступных тарифов.\n\nПопробуйте позже или обратитесь в поддержку.', reply_markup=home_only_kb())
        await callback.answer()
        return
    await safe_edit_or_send(callback.message, '💰 <b>Оплата криптовалютой</b>\n\nВыберите тариф:', reply_markup=tariff_select_kb(tariffs, order_id=order_id, is_crypto=True))
    await callback.answer()

@router.callback_query(F.data.startswith('crypto_pay:'))
async def pay_crypto_invoice(callback: CallbackQuery):
    """Создание ссылки на оплату Crypto (Простой режим)."""
    from database.requests import get_tariff_by_id, update_order_tariff, get_setting, get_user_internal_id, create_pending_order
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    if order_id:
        update_order_tariff(order_id, tariff_id, payment_type='crypto')
    else:
        user_id = get_user_internal_id(callback.from_user.id)
        if not user_id:
            await callback.answer('❌ Ошибка пользователя', show_alert=True)
            return
        (_, order_id) = create_pending_order(user_id=user_id, tariff_id=tariff_id, payment_type='crypto', vpn_key_id=None)
    crypto_item_url = get_setting('crypto_item_url')
    item_id = extract_item_id_from_url(crypto_item_url)
    if not item_id:
        await callback.answer('❌ Ошибка настройки крипто-платежей', show_alert=True)
        return
    crypto_url = build_crypto_payment_url(item_id=item_id, invoice_id=order_id, tariff_external_id=None, price_cents=tariff['price_cents'])
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='💰 Перейти к оплате', url=crypto_url))
    builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'pay_crypto:{order_id}'))
    price_usd = tariff['price_cents'] / 100
    price_str = f'${price_usd:g}'.replace('.', ',')
    await safe_edit_or_send(callback.message, f"💰 <b>Оплата криптовалютой</b>\n\nТариф: <b>{escape_html(tariff['name'])}</b>\nСумма к оплате: <b>{price_str}</b>\n\nНажмите кнопку ниже, чтобы перейти к генерации счета в @Ya_SellerBot.", reply_markup=builder.as_markup())
    await callback.answer()