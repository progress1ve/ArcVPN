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
