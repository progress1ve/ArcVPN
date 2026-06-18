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
    from database.requests import get_all_tariffs
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    from bot.utils.message_editor import get_message_data
    
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
    
    # Загружаем редактируемый текст из БД
    tariff_select_data = get_message_data('tariff_select_text', '')
    custom_text = tariff_select_data.get('text', '').strip()
    photo_file_id = tariff_select_data.get('photo_file_id')
    
    # Формируем текст
    if custom_text:
        text = custom_text
    else:
        text = '💳 <b>Купить подписку</b>\n\nВыберите тариф:'
    
    await safe_edit_or_send(
        callback.message,
        text,
        photo=photo_file_id,
        reply_markup=tariff_select_kb(tariffs, back_callback='start', is_select_only=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('select_tariff:'))
async def select_tariff_handler(callback: CallbackQuery):
    """Показывает способы оплаты для выбранного тарифа (единый экран)."""
    from bot.utils.payment_flow_ui import show_payment_method_selection_screen
    from bot.utils.message_editor import get_message_data

    tariff_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id

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
