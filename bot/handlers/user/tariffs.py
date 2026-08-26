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
from bot.utils.text import safe_edit_or_send

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == 'buy_key')
async def buy_key_handler(callback: CallbackQuery):
    """Показывает список тарифов для покупки."""
    from database.requests import get_all_tariffs, get_user_primary_key
    from bot.utils.payment_flow_ui import tariff_product_keyboard, build_tariff_catalog_text
    from bot.keyboards.admin import home_only_kb
    from bot.utils.message_editor import get_message_data

    telegram_id = callback.from_user.id

    # Модель «одна подписка»: если у пользователя уже есть ключ — не покупаем
    # новый, а ведём на продление существующего.
    primary = get_user_primary_key(telegram_id)
    if primary:
        from bot.utils.payment_flow_ui import show_tariff_selection_screen
        await callback.answer('У вас уже есть подписка — оформляем продление.')
        await show_tariff_selection_screen(callback.message, telegram_id, key_id=primary['id'])
        return

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
    
    # Фото остаётся редактируемым, но состав и описания тарифов
    # строятся из каталога, чтобы старый custom text их не скрыл.
    tariff_select_data = get_message_data('tariff_select_text', '')
    photo_file_id = tariff_select_data.get('photo_file_id')
    text = build_tariff_catalog_text(tariffs)
    
    await safe_edit_or_send(
        callback.message,
        text,
        photo=photo_file_id,
        reply_markup=tariff_product_keyboard(tariffs)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('select_product:'))
async def select_product_handler(callback: CallbackQuery):
    """Step two: show periods only for the selected product family."""
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb

    _, product_code, target = callback.data.split(':', 2)
    tariffs = [item for item in get_all_tariffs(include_hidden=False) if item.get('product_code') == product_code]
    if not tariffs:
        await callback.answer('Тариф временно недоступен', show_alert=True)
        return
    key_id = int(target) if target.isdigit() else None
    selected = tariffs[0]
    traffic = 'основной трафик безлимитный'
    text = (
        f"<b>{selected.get('name', '').split('·')[0].strip()}</b>\n"
        f"{traffic} · LTE {selected.get('lte_quota_gb', 0)} ГБ · "
        f"{selected.get('device_limit', 2)} устройств\n\n"
        "Выберите период. Чем длиннее срок, тем ниже цена за месяц."
    )
    markup = tariff_select_kb(
        tariffs,
        back_callback='buy_key' if key_id is None else f'key_renew:{key_id}',
        is_select_only=True,
        select_callback_prefix='select_tariff' if key_id is None else 'key_renew_tariff',
        select_callback_suffix='' if key_id is None else f':{key_id}',
    )
    await safe_edit_or_send(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith('select_tariff:'))
async def select_tariff_handler(callback: CallbackQuery):
    """Показывает способы оплаты для выбранного тарифа (единый экран)."""
    from bot.utils.payment_flow_ui import show_payment_method_selection_screen, show_tariff_selection_screen
    from bot.utils.message_editor import get_message_data
    from database.requests import get_user_primary_key

    tariff_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id

    # Гард модели «одна подписка»: если ключ уже есть — это должно быть продление.
    primary = get_user_primary_key(telegram_id)
    if primary:
        await callback.answer('У вас уже есть подписка — оформляем продление.')
        await show_tariff_selection_screen(callback.message, telegram_id, key_id=primary['id'])
        return

    # Кастомный текст экрана оплаты грузим здесь и передаём как intro:
    # хелпер сам подтягивает только photo_file_id из payment_select_text.
    intro = (get_message_data('payment_select_text', '').get('text', '') or '').strip() or None

    await show_payment_method_selection_screen(
        callback.message,
        telegram_id,
        tariff_id,
        intro_text=intro,
    )
    await callback.answer()
