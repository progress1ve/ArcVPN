import logging
import uuid
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from config import ADMIN_IDS, DEFAULT_LIMIT_IP
from database.requests import get_or_create_user, is_user_banned, get_all_servers, get_setting, is_referral_enabled, get_user_by_referral_code, set_user_referrer
from bot.keyboards.user import main_menu_kb
from bot.states.user_states import RenameKey, ReplaceKey
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)

router = Router()


async def provision_trial_for_user(user: dict, *, mark_used: bool = True) -> dict | None:
    """
    Ядро активации пробной подписки: создаёт ключи на всех активных серверах.

    Переиспользуется и кнопкой «Активировать», и АВТО-активацией при первом
    /start (обязательный триал). Не зависит от callback/UI.

    Начисляет реферальный бонус рефереру (+N дней за запуск друга).

    Returns:
        dict с результатами {created_keys, failed_servers, first_key_id,
        order_id, trial_days, trial_traffic_gb} или None, если не удалось
        создать ни одного ключа.
    """
    from database.requests import (
        mark_trial_used, create_vpn_key_admin,
        get_trial_days, get_trial_traffic_gb, get_active_servers,
    )
    from bot.services.vpn_api import get_client_from_server_data, VPNAPIError

    internal_user_id = user['id']
    telegram_id = user['telegram_id']
    trial_days = get_trial_days()
    trial_traffic_gb = get_trial_traffic_gb()

    servers = get_active_servers()
    if not servers:
        logger.warning('provision_trial_for_user: нет активных серверов')
        return None

    traffic_limit_bytes = trial_traffic_gb * (1024 ** 3) if trial_traffic_gb > 0 else 0

    def _gen_email(u: dict) -> str:
        base = f"user_{u['username']}" if u.get('username') else f"user_{u['telegram_id']}"
        return f'{base}_{uuid.uuid4().hex[:8]}'

    created_keys = []
    failed_servers = []
    for server in servers:
        try:
            email = _gen_email(user)
            client = get_client_from_server_data(server)
            result = await client.provision_client_all_inbounds(
                email=email,
                total_gb=trial_traffic_gb,
                expire_days=trial_days,
                limit_ip=DEFAULT_LIMIT_IP,
                tg_id=str(telegram_id),
            )
            key_id = create_vpn_key_admin(
                user_id=internal_user_id,
                server_id=server['id'],
                tariff_id=None,  # None = пробный ключ
                panel_inbound_id=result['primary_inbound_id'],
                panel_email=email,
                client_uuid=result['uuid'],
                days=trial_days,
                traffic_limit=traffic_limit_bytes,
                custom_name=None,
            )
            created_keys.append({'key_id': key_id, 'server_name': server['name']})
            logger.info("✅ Пробный ключ %s на сервере %s (%s дн., %s ГБ)", key_id, server['name'], trial_days, trial_traffic_gb)
        except VPNAPIError as e:
            logger.error('❌ Триал: ошибка на сервере %s: %s', server.get('name'), e)
            failed_servers.append(f"{server['name']} ({e})")
        except Exception as e:
            logger.error('❌ Триал: неожиданная ошибка на сервере %s: %s', server.get('name'), e)
            failed_servers.append(f"{server['name']} (ошибка)")

    if not created_keys:
        return None

    first_key_id = created_keys[0]['key_id']
    # Trial — бесплатная выдача доступа, а не покупка или платёж на 0 ₽.
    order_id = None

    if mark_used:
        mark_trial_used(internal_user_id)

    # Реферальный бонус рефереру за запуск приглашённого друга (+N дн., раз на друга).
    try:
        from bot.services.billing import process_referral_trial_reward
        await process_referral_trial_reward(internal_user_id)
    except Exception as e:
        logger.error('Триал: ошибка начисления реф-бонуса: %s', e)

    return {
        'created_keys': created_keys,
        'failed_servers': failed_servers,
        'first_key_id': first_key_id,
        'order_id': order_id,
        'trial_days': trial_days,
        'trial_traffic_gb': trial_traffic_gb,
    }


@router.callback_query(F.data == 'trial_subscription')
async def show_trial_subscription(callback: CallbackQuery):
    """Показывает страницу пробной подписки."""
    from database.requests import is_trial_enabled, get_trial_tariff_id, has_used_trial, get_setting
    from bot.keyboards.user import trial_sub_kb
    from bot.keyboards.admin import home_only_kb
    user_id = callback.from_user.id

    logger.info(f'Пользователь {user_id} открывает страницу пробной подписки')

    if not is_trial_enabled():
        logger.warning(f'Пробная подписка отключена для пользователя {user_id}')
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return
    if get_trial_tariff_id() is None:
        logger.warning(f'Тариф не настроен для пробной подписки (пользователь {user_id})')
        await callback.answer('❌ Тариф не настроен', show_alert=True)
        return

    trial_used = has_used_trial(user_id)
    logger.info(f'Пользователь {user_id}: has_used_trial={trial_used}')

    if trial_used:
        logger.info(f'Пользователь {user_id} уже использовал пробный период')
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
    """Активация пробной подписки по кнопке. Ядро — provision_trial_for_user."""
    from database.requests import is_trial_enabled, has_used_trial, get_or_create_user

    user_id = callback.from_user.id

    if not is_trial_enabled():
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return

    (user, _is_new) = get_or_create_user(user_id, callback.from_user.username)
    if has_used_trial(user_id):
        await callback.answer('ℹ️ Вы уже использовали пробный период', show_alert=True)
        return

    await callback.answer('⏳ Создание пробной подписки...')

    result = await provision_trial_for_user(user)
    if not result:
        await callback.message.answer(
            '❌ <b>Не удалось создать пробную подписку</b>\n\n'
            'Все серверы недоступны. Попробуйте позже.',
            parse_mode="HTML"
        )
        return

    first_key_id = result['first_key_id']
    await state.update_data(new_key_order_id=result.get('order_id'), new_key_id=first_key_id)

    try:
        await callback.message.delete()
    except Exception:
        pass

    from bot.utils.key_sender import send_subscription_link
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))

    servers_text = "\n".join([f"• {k['server_name']}" for k in result['created_keys']])
    trial_info = (
        f"🎉 <b>Пробный период активирован!</b>\n\n"
        f"✅ {result['trial_days']} дней бесплатного доступа\n"
        f"📊 Трафик: {result['trial_traffic_gb']} ГБ\n"
        f"🖥️ Серверов: {len(result['created_keys'])}\n\n"
        f"{servers_text}\n\n"
        f"👇 <b>Ваша подписка готова!</b>"
    )
    if result['failed_servers']:
        trial_info += "\n\n⚠️ Некоторые серверы недоступны:\n" + "\n".join([f"• {s}" for s in result['failed_servers']])

    await callback.message.answer(trial_info, parse_mode="HTML")
    await send_subscription_link(callback, first_key_id, builder.as_markup())
