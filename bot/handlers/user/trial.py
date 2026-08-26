import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from config import DEFAULT_LIMIT_IP

logger = logging.getLogger(__name__)

router = Router()


async def provision_trial_for_user(user: dict) -> dict | None:
    """
    Ядро активации пробной подписки: создаёт одного пользователя в Remnawave.

    Переиспользуется и кнопкой «Активировать», и АВТО-активацией при первом
    /start (обязательный триал). Не зависит от callback/UI.

    Начисляет реферальный бонус рефереру (+N дней за запуск друга).

    Returns:
        dict с результатами {created_keys, failed_servers, first_key_id,
        order_id, trial_days, trial_traffic_gb} или None, если не удалось
        создать ни одного ключа.
    """
    from database.requests import (
        create_vpn_key_admin, get_trial_days,
        get_all_servers, get_standard_trial_tariff, acquire_trial_entitlement,
        activate_trial_entitlement, fail_trial_entitlement, get_trial_key_by_panel_email,
    )
    from bot.services.vpn_api import get_client_from_server_data
    from bot.services.panels.base import VPNAPIError

    internal_user_id = user['id']
    telegram_id = user['telegram_id']
    trial_days = get_trial_days()

    tariff = get_standard_trial_tariff()
    if not tariff:
        logger.error('provision_trial_for_user: активный тариф Standard не настроен')
        return None
    trial_traffic_gb = int(tariff.get('traffic_limit_gb') or 0)

    entitlement = acquire_trial_entitlement(internal_user_id, tariff['id'])
    if entitlement['status'] == 'active':
        key_id = entitlement.get('vpn_key_id')
        return {
            'created_keys': ([{'key_id': key_id, 'server_name': 'ArcVPN'}] if key_id else []),
            'failed_servers': [],
            'first_key_id': key_id,
            'order_id': None,
            'trial_days': trial_days,
            'trial_traffic_gb': trial_traffic_gb,
            'already_active': True,
        }
    if not entitlement.get('acquired'):
        logger.info('provision_trial_for_user: trial уже создаётся для user_id=%s', internal_user_id)
        return None

    remnawave_servers = sorted(
        (
            item for item in get_all_servers()
            if item.get('is_active') and str(item.get('panel_type') or '').lower() == 'remnawave'
        ),
        key=lambda item: int(item.get('id') or 0),
    )
    using_registered_server = bool(remnawave_servers)
    if using_registered_server:
        server = remnawave_servers[0]
    else:
        from bot.services.remnawave_stats import remnawave_authority_config
        authority = remnawave_authority_config()
        compatibility_servers = sorted(
            (item for item in get_all_servers() if item.get('is_active')),
            key=lambda item: int(item.get('id') or 0),
        )
        server = {**authority, 'id': compatibility_servers[0]['id']} if compatibility_servers else authority
    if not server.get('id') or (not using_registered_server and (
        not server.get('panel_api_url') or not server.get('panel_api_token')
    )):
        logger.warning('provision_trial_for_user: Remnawave control plane не настроен')
        fail_trial_entitlement(internal_user_id, 'remnawave authority unavailable')
        return None

    # Remnawave user-centric: один пользователь получает squad, а не отдельный
    # клиент на каждом legacy-сервере. Детерминированное имя делает retry
    # безопасным, даже если API успел создать пользователя до локального commit.
    panel_email = f"arc_user_{internal_user_id}"

    traffic_limit_bytes = trial_traffic_gb * (1024 ** 3) if trial_traffic_gb > 0 else 0

    client = None
    try:
        client = get_client_from_server_data(server)
        result = await client.get_user(panel_email)
        if result:
            client_uuid = str(result.get('vlessUuid') or '')
            if not client_uuid:
                raise VPNAPIError('Remnawave user has no vlessUuid')
            await client.update_client_full(
                inbound_id=0,
                client_uuid=client_uuid,
                email=panel_email,
                expiry_time_ms=int((datetime.now(timezone.utc) + timedelta(days=trial_days)).timestamp() * 1000),
                total_gb_bytes=traffic_limit_bytes,
                enable=True,
                limit_ip=int(tariff.get('device_limit') or DEFAULT_LIMIT_IP),
            )
        else:
            result = await client.add_client(
                inbound_id=0,
                email=panel_email,
                total_gb=trial_traffic_gb,
                expire_days=trial_days,
                limit_ip=int(tariff.get('device_limit') or DEFAULT_LIMIT_IP),
                enable=True,
                tg_id=str(telegram_id),
            )
            client_uuid = str(result.get('vlessUuid') or '')
            if not client_uuid:
                raise VPNAPIError('Remnawave create response has no vlessUuid')

        # If a previous attempt reached Remnawave and inserted the local key but
        # failed before activating the entitlement, reuse it instead of issuing
        # a second stable subscription URL.
        existing = get_trial_key_by_panel_email(internal_user_id, panel_email)
        if existing:
            key_id = int(existing['id'])
        else:
            key_id = create_vpn_key_admin(
                user_id=internal_user_id,
                server_id=server['id'],
                tariff_id=tariff['id'],
                panel_inbound_id=0,
                panel_email=panel_email,
                client_uuid=client_uuid,
                days=trial_days,
                traffic_limit=traffic_limit_bytes,
                custom_name=None,
            )
        logger.info("✅ Standard trial key %s provisioned through Remnawave", key_id)
    except Exception as exc:
        logger.error('Remnawave trial provisioning failed for user_id=%s: %s', internal_user_id, exc)
        fail_trial_entitlement(internal_user_id, str(exc))
        return None
    finally:
        if client is not None:
            await client.close()

    first_key_id = key_id
    # Trial — бесплатная выдача доступа, а не покупка или платёж на 0 ₽.
    order_id = None

    if not activate_trial_entitlement(internal_user_id, first_key_id):
        logger.error('Триал создан, но entitlement не активирован для user_id=%s', internal_user_id)
        return None

    # Реферальный бонус рефереру за запуск приглашённого друга (+N дн., раз на друга).
    try:
        from bot.services.billing import process_referral_trial_reward
        await process_referral_trial_reward(internal_user_id)
    except Exception as e:
        logger.error('Триал: ошибка начисления реф-бонуса: %s', e)

    return {
        'created_keys': [{'key_id': key_id, 'server_name': 'ArcVPN'}],
        'failed_servers': [],
        'first_key_id': first_key_id,
        'order_id': order_id,
        'trial_days': trial_days,
        'trial_traffic_gb': trial_traffic_gb,
    }


@router.callback_query(F.data == 'trial_subscription')
async def show_trial_subscription(callback: CallbackQuery):
    """Показывает страницу пробной подписки."""
    from database.requests import is_trial_enabled, get_standard_trial_tariff, has_used_trial, get_setting
    from bot.keyboards.user import trial_sub_kb
    from bot.keyboards.admin import home_only_kb
    user_id = callback.from_user.id

    logger.info(f'Пользователь {user_id} открывает страницу пробной подписки')

    if not is_trial_enabled():
        logger.warning(f'Пробная подписка отключена для пользователя {user_id}')
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return
    if get_standard_trial_tariff() is None:
        logger.warning(f'Тариф Standard не настроен для пробной подписки (пользователь {user_id})')
        await callback.answer('❌ Тариф Standard не настроен', show_alert=True)
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
