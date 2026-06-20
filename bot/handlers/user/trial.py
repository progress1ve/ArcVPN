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
    """Активирует пробную подписку: создаёт ключи на всех активных серверах."""
    from database.requests import (
        is_trial_enabled, has_used_trial, get_or_create_user, 
        mark_trial_used, create_vpn_key_admin, create_pending_order, 
        complete_order, get_trial_days, get_trial_traffic_gb, get_active_servers
    )
    from bot.services.vpn_api import get_client_from_server_data, VPNAPIError
    from bot.keyboards.admin import home_only_kb
    import uuid
    
    user_id = callback.from_user.id
    
    # Проверки
    if not is_trial_enabled():
        logger.warning(f'Пользователь {user_id} пытается активировать пробный период, но он отключен')
        await callback.answer('❌ Пробная подписка недоступна', show_alert=True)
        return
    
    # ВАЖНО: Сначала создаем пользователя, потом проверяем флаг
    (user, is_new) = get_or_create_user(user_id, callback.from_user.username)
    internal_user_id = user['id']
    
    logger.info(f'Пользователь {user_id} (internal_id={internal_user_id}, is_new={is_new}) пытается активировать пробный период. used_trial={user.get("used_trial", 0)}')
    
    if has_used_trial(user_id):
        logger.warning(f'Пользователь {user_id} уже использовал пробный период')
        await callback.answer('ℹ️ Вы уже использовали пробный период', show_alert=True)
        return
    
    # Получаем настройки пробного периода
    trial_days = get_trial_days()
    trial_traffic_gb = get_trial_traffic_gb()
    
    logger.info(f'Пользователь {user_id} активирует пробный период ({trial_days} дней, {trial_traffic_gb} ГБ)')
    
    # Получаем все активные серверы
    servers = get_active_servers()
    if not servers:
        await callback.answer('❌ Нет активных серверов', show_alert=True)
        return
    
    # Конвертируем трафик в байты (0 = безлимит)
    traffic_limit_bytes = trial_traffic_gb * (1024 ** 3) if trial_traffic_gb > 0 else 0
    
    await callback.answer('⏳ Создание пробной подписки...')
    
    # Генерируем уникальный email для панели
    def generate_unique_email(user: dict) -> str:
        base = f"user_{user['username']}" if user.get('username') else f"user_{user['telegram_id']}"
        suffix = uuid.uuid4().hex[:8]  # 8 символов для большей уникальности
        return f'{base}_{suffix}'
    
    created_keys = []
    failed_servers = []
    
    # Создаем ключи на всех серверах
    for server in servers:
        try:
            server_id = server['id']
            email = generate_unique_email(user)
            
            client = get_client_from_server_data(server)
            
            # Получаем первый доступный inbound
            inbounds = await client.get_inbounds()
            if not inbounds:
                logger.warning(f"Нет inbound на сервере {server['name']}")
                failed_servers.append(f"{server['name']} (нет inbound)")
                continue
            
            # Используем первый inbound
            inbound = inbounds[0]
            inbound_id = inbound.get('id')
            
            flow = await client.get_inbound_flow(inbound_id)
            
            # Создаём клиента на панели
            result = await client.add_client(
                inbound_id=inbound_id,
                email=email,
                total_gb=trial_traffic_gb,
                expire_days=trial_days,
                limit_ip=DEFAULT_LIMIT_IP,
                tg_id=str(user_id),
                flow=flow
            )
            
            client_uuid = result['uuid']
            
            # Создаем ключ в БД с привязкой к серверу
            key_id = create_vpn_key_admin(
                user_id=internal_user_id,
                server_id=server_id,
                tariff_id=None,  # None для пробного периода
                panel_inbound_id=inbound_id,
                panel_email=email,
                client_uuid=client_uuid,
                days=trial_days,
                traffic_limit=traffic_limit_bytes,
                custom_name=None  # Будет отображаться как "Пробная подписка"
            )
            
            created_keys.append({
                'key_id': key_id,
                'server_name': server['name']
            })
            
            logger.info(f"✅ Создан пробный ключ ID {key_id} на сервере {server['name']} ({trial_days} дней, {trial_traffic_gb} ГБ)")
            
        except VPNAPIError as e:
            logger.error(f'❌ Ошибка создания пробного ключа на сервере {server["name"]}: {e}')
            failed_servers.append(f"{server['name']} ({str(e)})")
        except Exception as e:
            logger.error(f'❌ Неожиданная ошибка на сервере {server["name"]}: {e}')
            failed_servers.append(f"{server['name']} (ошибка)")
    
    if not created_keys:
        await callback.message.answer(
            '❌ <b>Не удалось создать пробную подписку</b>\n\n'
            'Все серверы недоступны. Попробуйте позже.',
            parse_mode="HTML"
        )
        return
    
    # Создаем ордер для истории (используем первый созданный ключ)
    first_key_id = created_keys[0]['key_id']
    try:
        (_, order_id) = create_pending_order(
            user_id=internal_user_id, 
            tariff_id=None,  # None для пробного периода
            payment_type='trial', 
            vpn_key_id=first_key_id
        )
        complete_order(order_id)
        logger.info(f'Создан и завершен ордер {order_id} для пользователя {user_id}')
    except Exception as e:
        logger.error(f'Ошибка создания ордера для пробного периода: {e}')
    
    # Помечаем что пробный период использован ТОЛЬКО после успешного создания ключей
    mark_trial_used(internal_user_id)
    logger.info(f'Пользователь {user_id} (internal_id={internal_user_id}) успешно активировал пробный период. Флаг used_trial установлен.')
    
    await state.update_data(new_key_order_id=order_id if 'order_id' in locals() else None, new_key_id=first_key_id)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Для пробного периода сразу показываем subscription ссылку с QR-кодом
    from bot.utils.key_sender import send_subscription_link
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    # Создаем клавиатуру для пробного периода
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    
    # Отправляем сообщение с информацией о пробном периоде
    servers_text = "\n".join([f"• {k['server_name']}" for k in created_keys])
    trial_info = (
        f"🎉 <b>Пробный период активирован!</b>\n\n"
        f"✅ {trial_days} дней бесплатного доступа\n"
        f"📊 Трафик: {trial_traffic_gb} ГБ\n"
        f"🖥️ Серверов: {len(created_keys)}\n\n"
        f"{servers_text}\n\n"
        f"👇 <b>Ваша подписка готова!</b>"
    )
    
    if failed_servers:
        trial_info += f"\n\n⚠️ Некоторые серверы недоступны:\n" + "\n".join([f"• {s}" for s in failed_servers])
    
    await callback.message.answer(trial_info, parse_mode="HTML")
    
    # Сразу показываем subscription ссылку с QR-кодом
    await send_subscription_link(callback, first_key_id, builder.as_markup())