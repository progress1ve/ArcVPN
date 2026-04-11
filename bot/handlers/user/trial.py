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

@router.callback_query(F.data == 'trial_subscription')
async def show_trial_subscription(callback: CallbackQuery):
    """Показывает страницу пробной подписки."""
    from database.requests import is_trial_enabled, get_trial_tariff_id, has_used_trial, get_setting
    from bot.keyboards.user import trial_sub_kb
    from bot.keyboards.admin import home_only_kb
    user_id = callback.from_user.id
    if not is_trial_enabled():
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return
    if get_trial_tariff_id() is None:
        await callback.answer('❌ Тариф не настроен', show_alert=True)
        return
    if has_used_trial(user_id):
        await callback.answer('ℹ️ Вы уже использовали пробный период', show_alert=True)
        return
    from bot.utils.message_editor import send_editor_message
    await send_editor_message(
        callback.message,
        key='trial_page_text',
        default_text='🎁 <b>Пробная подписка</b>',
        reply_markup=trial_sub_kb(),
    )
    await callback.answer()

@router.callback_query(F.data == 'trial_activate')
async def activate_trial_subscription(callback: CallbackQuery, state: FSMContext):
    """Активирует пробную подписку: создаёт ключ через стандартный механизм."""
    from database.requests import is_trial_enabled, get_trial_tariff_id, has_used_trial, get_tariff_by_id, get_or_create_user, mark_trial_used, create_initial_vpn_key, create_pending_order, complete_order
    from bot.handlers.user.payments.keys_config import start_new_key_config
    from bot.keyboards.admin import home_only_kb
    user_id = callback.from_user.id
    if not is_trial_enabled():
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return
    tariff_id = get_trial_tariff_id()
    if tariff_id is None:
        await callback.answer('❌ Тариф не настроен', show_alert=True)
        return
    if has_used_trial(user_id):
        await callback.answer('ℹ️ Вы уже использовали пробный период', show_alert=True)
        return
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    (user, _) = get_or_create_user(user_id, callback.from_user.username)
    internal_user_id = user['id']
    mark_trial_used(internal_user_id)
    logger.info(f'Пользователь {user_id} активировал пробный период (тариф ID={tariff_id})')
    duration_days = tariff['duration_days']
    traffic_limit_bytes = (tariff.get('traffic_limit_gb', 0) or 0) * 1024 ** 3
    key_id = create_initial_vpn_key(internal_user_id, tariff_id, duration_days, traffic_limit=traffic_limit_bytes)
    (_, order_id) = create_pending_order(user_id=internal_user_id, tariff_id=tariff_id, payment_type='trial', vpn_key_id=key_id)
    complete_order(order_id)
    await state.update_data(new_key_order_id=order_id, new_key_id=key_id)
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await start_new_key_config(callback.message, state, order_id, key_id)