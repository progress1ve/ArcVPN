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

@router.message(Command('mykeys'))
async def cmd_mykeys(message: Message, state: FSMContext):
    """Обработчик команды /mykeys - вызывает логику кнопки 'Мои ключи'."""
    if is_user_banned(message.from_user.id):
        await safe_edit_or_send(message, '⛔ <b>Доступ заблокирован</b>\n\nВаш аккаунт заблокирован. Обратитесь в поддержку.', force_new=True)
        return
    await state.clear()
    await show_my_keys(message.from_user.id, message)

async def show_my_keys(telegram_id: int, message, is_callback: bool = True):
    """
    Общая логика для показа списка ключей.
    
    Args:
        telegram_id: ID пользователя в Telegram
        message: Сообщение (Message) для отправки/редактирования
        is_callback: True если вызвано из callback (редактируем), False если из команды (отправляем новое)
    """
    from database.requests import get_user_keys_for_display, is_traffic_exhausted
    from bot.keyboards.user import my_keys_list_kb
    from bot.keyboards.admin import home_only_kb
    from bot.services.vpn_api import get_client, format_traffic
    keys = get_user_keys_for_display(telegram_id)
    if not keys:
        if is_callback:
            await safe_edit_or_send(message, '🔑 <b>Мои подписки</b>\n\nУ вас пока нет VPN-подписок.\n\nНажмите «Купить подписку» на главной, чтобы приобрести доступ! 🚀', reply_markup=home_only_kb())
        else:
            await safe_edit_or_send(message, '🔑 <b>Мои подписки</b>\n\nУ вас пока нет VPN-подписок.\n\nНажмите «Купить подписку» на главной, чтобы приобрести доступ! 🚀', reply_markup=home_only_kb(), force_new=True)
        return
    lines = ['🔑 <b>Мои подписки</b>\n']
    for key in keys:
        if key['is_active'] and (not is_traffic_exhausted(key)):
            status_emoji = '🟢'
        else:
            status_emoji = '🔴'
        traffic_used = key.get('traffic_used', 0) or 0
        traffic_limit = key.get('traffic_limit', 0) or 0
        used_str = format_traffic(traffic_used)
        limit_str = format_traffic(traffic_limit) if traffic_limit > 0 else '∞'
        traffic_text = f'{used_str} / {limit_str}'
        protocol = 'VLESS'
        inbound_name = 'VPN'
        if key.get('server_id') and key.get('panel_email'):
            try:
                client = await get_client(key['server_id'])
                stats = await client.get_client_stats(key['panel_email'])
                if stats:
                    protocol = stats['protocol'].upper()
                    inbound_name = stats.get('remark', 'VPN') or 'VPN'
            except Exception as e:
                logger.warning(f"Не удалось получить протокол для ключа {key['id']}: {e}")
        # Форматируем дату в формате ДД-ММ-ГГГГ
        if key['expires_at']:
            from datetime import datetime
            expires_dt = datetime.fromisoformat(key['expires_at'])
            expires = expires_dt.strftime('%d-%m-%Y')
        else:
            expires = '—'
        server = key.get('server_name') or 'Не выбран'
        lines.append(f"{status_emoji}<b>{escape_html(key['display_name'])}</b> - {traffic_text} - до {expires}")
        lines.append(f'     📍{escape_html(server)} - {escape_html(inbound_name)} ({escape_html(protocol)})')
        lines.append('')
    lines.append('Выберите подписку для управления:')
    text = '\n'.join(lines)
    if is_callback:
        await safe_edit_or_send(message, text, reply_markup=my_keys_list_kb(keys))
    else:
        await safe_edit_or_send(message, text, reply_markup=my_keys_list_kb(keys), force_new=True)

@router.callback_query(F.data == 'my_keys')
async def my_keys_handler(callback: CallbackQuery):
    """Список VPN-ключей пользователя."""
    telegram_id = callback.from_user.id
    await show_my_keys(telegram_id, callback.message)
    await callback.answer()

async def show_key_details(telegram_id: int, key_id: int, message, is_callback: bool = True, prepend_text: str=''):
    """Общая логика для показа деталей ключа."""
    from database.requests import get_key_details_for_user, get_key_payments_history, is_key_active, is_traffic_exhausted
    from bot.keyboards.user import key_manage_kb
    from bot.services.vpn_api import format_traffic
    import logging
    logger = logging.getLogger(__name__)
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        if is_callback:
            await safe_edit_or_send(message, '❌ Ключ не найден или вы не являетесь его владельцем.')
        else:
            await safe_edit_or_send(message, '❌ Ключ не найден или вы не являетесь его владельцем.', force_new=True)
        return
    traffic_exhausted = is_traffic_exhausted(key)
    key_active = is_key_active(key)
    if traffic_exhausted:
        status = '🔴 Трафик исчерпан'
    elif key_active:
        status = '🟢 Активен'
    else:
        status = '🔴 Истёк'
    inbound_name = '—'
    protocol = '—'
    is_unconfigured = not key.get('server_id')
    traffic_used = key.get('traffic_used', 0) or 0
    traffic_limit = key.get('traffic_limit', 0) or 0
    if is_unconfigured:
        traffic_info = '⚠️ Требует настройки'
    elif traffic_limit > 0:
        used_str = format_traffic(traffic_used)
        limit_str = format_traffic(traffic_limit)
        percent = traffic_used / traffic_limit * 100 if traffic_limit > 0 else 0
        traffic_info = f'{used_str} из {limit_str} ({percent:.1f}%)'
    elif traffic_used > 0:
        traffic_info = f'{format_traffic(traffic_used)} (безлимит)'
    else:
        traffic_info = 'Безлимит'
    if key.get('server_active') and key.get('panel_email'):
        try:
            from bot.services.vpn_api import get_client
            client = await get_client(key['server_id'])
            stats = await client.get_client_stats(key['panel_email'])
            if stats:
                protocol = stats.get('protocol', 'vless').upper()
                inbound_name = stats.get('remark', 'VPN') or 'VPN'
        except Exception as e:
            logger.warning(f'Ошибка получения протокола: {e}')
    # Форматируем дату в формате ДД-ММ-ГГГГ
    if key['expires_at']:
        expires_dt = datetime.fromisoformat(key['expires_at'])
        expires = expires_dt.strftime('%d-%m-%Y')
    else:
        expires = '—'
    server = key.get('server_name') or 'Не выбран'
    lines = []
    if prepend_text:
        lines.append(prepend_text)
        lines.append('')
    lines.extend([f"🔑 <b>{escape_html(key['display_name'])}</b>\n", f'<b>Статус:</b> {status}', f'<b>Сервер:</b> {escape_html(server)}', f'<b>Протокол:</b> {escape_html(inbound_name)} ({escape_html(protocol)})', f'<b>Трафик:</b> {traffic_info}', f'<b>Действует до:</b> {expires}', ''])
    payments = get_key_payments_history(key_id)
    if payments:
        lines.append('📜 <b>История операций:</b>')
        for p in payments:
            # Форматируем дату в формате ДД-ММ-ГГГГ
            if p['paid_at']:
                paid_dt = datetime.fromisoformat(p['paid_at'])
                date = paid_dt.strftime('%d-%m-%Y')
            else:
                date = '—'
            tariff = escape_html(p.get('tariff_name') or 'Тариф')
            
            # Показываем цену в рублях если есть, иначе в долларах
            if p['payment_type'] == 'stars':
                amount = f"{p['amount_stars']} ⭐"
            elif p.get('amount_rub') and p['amount_rub'] > 0:
                amount = f"{p['amount_rub']} ₽"
            else:
                amount_val = p['amount_cents'] / 100
                amount_str = f'{amount_val:g}'.replace('.', ',')
                amount = f'${amount_str}'
            
            lines.append(f'   • {date}: {tariff} ({amount})')
    msg_text = '\n'.join(lines)
    kb = key_manage_kb(key_id, is_unconfigured=is_unconfigured, is_active=key_active, is_traffic_exhausted=traffic_exhausted)
    if is_callback:
        await safe_edit_or_send(message, msg_text, reply_markup=kb)
    else:
        await safe_edit_or_send(message, msg_text, reply_markup=kb, force_new=True)

@router.callback_query(F.data.startswith('key_delete:'))
async def key_delete_handler(callback: CallbackQuery):
    """Удаление истекшего ключа пользователем."""
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.fromuser.id if hasattr(callback, 'fromuser') else callback.from_user.id
    from database.requests import get_key_details_for_user, delete_vpn_key
    from bot.services.vpn_api import get_client
    import logging
    logger = logging.getLogger(__name__)
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден или вы не являетесь его владельцем.', show_alert=True)
        return
    if key['is_active']:
        await callback.answer('❌ Активные ключи нельзя удалить.', show_alert=True)
        return
    if key.get('server_id') and key.get('panel_inbound_id') and key.get('client_uuid'):
        try:
            client = await get_client(key['server_id'])
            await client.delete_client(key['panel_inbound_id'], key['client_uuid'])
            logger.info(f"Клиент {key.get('panel_email', 'unknown')} удален с сервера 3X-UI")
        except Exception as e:
            logger.warning(f"Не удалось удалить клиента {key.get('panel_email', 'unknown')} с сервера 3X-UI: {e}")
    success = delete_vpn_key(key_id)
    if success:
        await callback.answer(f"✅ Ключ {key['display_name']} успешно удален.", show_alert=True)
        await show_my_keys(telegram_id, callback.message)
    else:
        await callback.answer('❌ Ошибка при удалении ключа из БД.', show_alert=True)

@router.callback_query(F.data.startswith('key:'))
async def key_details_handler(callback: CallbackQuery):
    """Показывает ключ с QR-кодом и краткой информацией."""
    from database.requests import get_key_details_for_user, is_key_active, is_traffic_exhausted
    from bot.services.vpn_api import format_traffic
    from bot.utils.key_sender import send_key_with_qr
    from bot.keyboards.user import InlineKeyboardBuilder, InlineKeyboardButton
    
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id
    
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    
    # Проверяем статус
    traffic_exhausted = is_traffic_exhausted(key)
    key_active = is_key_active(key)
    
    # Для активных ключей показываем subscription ссылку с QR
    if key_active and not traffic_exhausted:
        # Показываем subscription ссылку с QR-кодом
        from bot.utils.key_sender import send_subscription_link
        from bot.keyboards.user import InlineKeyboardBuilder, InlineKeyboardButton
        
        # Создаем клавиатуру с нужными кнопками
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
        builder.row(InlineKeyboardButton(text="📈 Продлить", callback_data=f"key_renew:{key_id}"))
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="my_keys"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        )
        
        await send_subscription_link(callback, key_id, builder.as_markup())
    else:
        # Для неактивных ключей показываем краткую информацию
        lines = [f"🔑 <b>{escape_html(key['display_name'])}</b>\n"]
        
        # Статус
        if traffic_exhausted:
            lines.append('🔴 <b>Трафик исчерпан</b>')
        elif key_active:
            lines.append('🟢 <b>Активен</b>')
        else:
            lines.append('🔴 <b>Срок истёк</b>')
        
        # Трафик
        traffic_used = key.get('traffic_used', 0) or 0
        traffic_limit = key.get('traffic_limit', 0) or 0
        if traffic_limit > 0:
            used_str = format_traffic(traffic_used)
            limit_str = format_traffic(traffic_limit)
            percent = traffic_used / traffic_limit * 100 if traffic_limit > 0 else 0
            lines.append(f'📊 <b>Трафик:</b> {used_str} из {limit_str} ({percent:.1f}%)')
        else:
            lines.append(f'📊 <b>Трафик:</b> Безлимит')
        
        # Срок действия
        if key['expires_at']:
            expires_dt = datetime.fromisoformat(key['expires_at'])
            expires = expires_dt.strftime('%d-%m-%Y')
        else:
            expires = '—'
        lines.append(f'📅 <b>Действует до:</b> {expires}')
        lines.append('\n⚠️ <i>Продлите подписку, чтобы получить доступ</i>')
        
        text = '\n'.join(lines)
        
        # Клавиатура
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="� Продлить", callback_data=f"key_renew:{key_id}"))
        builder.row(
            InlineKeyboardButton(text="� Мои ключи", callback_data="my_keys"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        )
        
        await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    
    await callback.answer()

@router.callback_query(F.data.startswith('key_show:'))
async def key_show_handler(callback: CallbackQuery):
    """Показать subscription ссылку (заменяет показ отдельного ключа)."""
    from bot.utils.key_sender import send_subscription_link
    from bot.keyboards.user import back_and_home_kb
    
    telegram_id = callback.from_user.id
    
    # Показываем subscription ссылку вместо отдельного ключа
    await send_subscription_link(callback, telegram_id, back_and_home_kb(back_callback="my_keys"))
    await callback.answer()

@router.callback_query(F.data == 'device_instructions')
async def device_instructions_handler(callback: CallbackQuery):
    """Показывает меню выбора устройства для инструкции."""
    logger.info(f"device_instructions_handler вызван для пользователя {callback.from_user.id}")
    
    from bot.keyboards.user import device_instructions_kb
    
    text = (
        "📱 <b>Выберите ваше устройство</b>\n\n"
        "Мы используем самый скрытный и надежный протокол VLESS Reality.\n\n"
        "Для подключения нужно скачать приложение Happ и импортировать подписку."
    )
    
    try:
        await safe_edit_or_send(callback.message, text, reply_markup=device_instructions_kb())
        await callback.answer()
        logger.info("device_instructions_handler успешно выполнен")
    except Exception as e:
        logger.error(f"Ошибка в device_instructions_handler: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == 'instruction_apple')
async def instruction_apple_handler(callback: CallbackQuery):
    """Инструкция для Apple устройств."""
    logger.info(f"instruction_apple_handler вызван для пользователя {callback.from_user.id}")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from config import SUBSCRIPTION_URL
    from database.requests import get_user_keys_for_display
    import urllib.parse
    
    telegram_id = callback.from_user.id
    
    # Получаем первый активный ключ пользователя для subscription URL
    keys = get_user_keys_for_display(telegram_id)
    if not keys:
        await callback.answer("❌ У вас нет активных ключей. Сначала купите подписку!", show_alert=True)
        return
    
    # Берем первый ключ и получаем его sub_id
    first_key = keys[0]
    from database.requests import get_vpn_key_by_id
    key_data = get_vpn_key_by_id(first_key['id'])
    
    if not key_data or not key_data.get('sub_id'):
        await callback.answer("❌ Ошибка получения subscription ссылки", show_alert=True)
        return
    
    # Формируем subscription URL с использованием sub_id
    subscription_url = f"{SUBSCRIPTION_URL}/sub/{key_data['sub_id']}"
    
    # Создаем ссылку через braconnect для автоматического импорта в Happ
    encoded_url = urllib.parse.quote(subscription_url, safe='')
    import_link = f"https://braconnect.app/link?url_ha={encoded_url}"
    
    text = (
        "🍎 <b>Инструкция для Apple (iOS/macOS)</b>\n\n"
        "<b>Шаг 1:</b> Скачайте приложение Happ\n"
        "Нажмите кнопку «📥 Скачать Happ» ниже\n\n"
        "<b>Шаг 2:</b> Импортируйте подписку\n"
        "Нажмите кнопку «🔗 Импортировать в Happ» - приложение откроется автоматически!\n\n"
        "<b>Шаг 3:</b> Подключитесь\n"
        "В приложении Happ нажмите кнопку подключения ▶️\n\n"
        "💡 <i>Подписка обновляется автоматически, вам не нужно добавлять ключи вручную</i>"
    )
    
    try:
        # Создаём клавиатуру с кнопками
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📥 Скачать Happ", url="https://apps.apple.com/app/happ-vpn-fast-secure/id6738501697"))
        builder.row(InlineKeyboardButton(text="🔗 Импортировать в Happ", url=import_link))
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="device_instructions"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        )
        
        await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
        await callback.answer()
        logger.info(f"instruction_apple_handler успешно выполнен (sub_id={key_data['sub_id']})")
    except Exception as e:
        logger.error(f"Ошибка в instruction_apple_handler: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == 'instruction_android')
async def instruction_android_handler(callback: CallbackQuery):
    """Инструкция для Android устройств."""
    logger.info(f"instruction_android_handler вызван для пользователя {callback.from_user.id}")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from config import SUBSCRIPTION_URL
    from database.requests import get_user_keys_for_display
    import urllib.parse
    
    telegram_id = callback.from_user.id
    
    # Получаем первый активный ключ пользователя для subscription URL
    keys = get_user_keys_for_display(telegram_id)
    if not keys:
        await callback.answer("❌ У вас нет активных ключей. Сначала купите подписку!", show_alert=True)
        return
    
    # Берем первый ключ и получаем его sub_id
    first_key = keys[0]
    from database.requests import get_vpn_key_by_id
    key_data = get_vpn_key_by_id(first_key['id'])
    
    if not key_data or not key_data.get('sub_id'):
        await callback.answer("❌ Ошибка получения subscription ссылки", show_alert=True)
        return
    
    # Формируем subscription URL с использованием sub_id
    subscription_url = f"{SUBSCRIPTION_URL}/sub/{key_data['sub_id']}"
    
    # Создаем ссылку через braconnect для автоматического импорта в Happ
    encoded_url = urllib.parse.quote(subscription_url, safe='')
    import_link = f"https://braconnect.app/link?url_ha={encoded_url}"
    
    text = (
        "🤖 <b>Инструкция для Android</b>\n\n"
        "<b>Шаг 1:</b> Скачайте приложение Happ\n"
        "Нажмите кнопку «📥 Скачать Happ» ниже\n\n"
        "<b>Шаг 2:</b> Импортируйте подписку\n"
        "Нажмите кнопку «🔗 Импортировать в Happ» - приложение откроется автоматически!\n\n"
        "<b>Шаг 3:</b> Подключитесь\n"
        "В приложении Happ нажмите кнопку подключения ▶️\n\n"
        "💡 <i>Подписка обновляется автоматически, вам не нужно добавлять ключи вручную</i>"
    )
    
    try:
        # Создаём клавиатуру с кнопками
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📥 Скачать Happ", url="https://play.google.com/store/apps/details?id=io.happ.app"))
        builder.row(InlineKeyboardButton(text="🔗 Импортировать в Happ", url=import_link))
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="device_instructions"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        )
        
        await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
        await callback.answer()
        logger.info(f"instruction_android_handler успешно выполнен (sub_id={key_data['sub_id']})")
    except Exception as e:
        logger.error(f"Ошибка в instruction_android_handler: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == 'instruction_windows')
async def instruction_windows_handler(callback: CallbackQuery):
    """Инструкция для Windows."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    text = (
        "🪟 <b>Инструкция для Windows</b>\n\n"
        "<b>Шаг 1:</b> Скачайте приложение Happ\n"
        "Нажмите кнопку ниже и скачайте версию для Windows\n\n"
        "<b>Шаг 2:</b> Скопируйте subscription ссылку\n"
        "Вернитесь назад и нажмите «Показать ключ»\n\n"
        "<b>Шаг 3:</b> Добавьте в приложение\n"
        "• Откройте Happ\n"
        "• Нажмите «+» → «Добавить подписку»\n"
        "• Вставьте скопированную ссылку\n\n"
        "<b>Шаг 4:</b> Подключитесь\n"
        "Нажмите кнопку подключения в приложении"
    )
    
    # Создаём клавиатуру с кнопкой скачивания
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📥 Скачать Happ", url="https://github.com/hamedap/Happ/releases/latest"))
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="device_instructions"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="start")
    )
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == 'show_subscription')
async def show_subscription_handler(callback: CallbackQuery):
    """Показать subscription ссылку пользователю."""
    from bot.utils.key_sender import send_subscription_link
    from bot.keyboards.user import back_and_home_kb
    
    telegram_id = callback.from_user.id
    await send_subscription_link(callback, telegram_id, back_and_home_kb(back_callback="my_keys"))
    await callback.answer()

@router.callback_query(F.data.startswith('key_renew:'))
async def key_renew_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для продления подписки."""
    from database.requests import get_all_tariffs, get_key_details_for_user
    from bot.keyboards.user import key_renew_tariff_list_kb, back_and_home_kb
    
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id
    
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден или вы не являетесь его владельцем.', show_alert=True)
        return
    
    # Получаем все доступные тарифы
    tariffs = get_all_tariffs(include_hidden=False)
    if not tariffs:
        await safe_edit_or_send(
            callback.message,
            '💳 <b>Продление подписки</b>\n\n😔 Нет доступных тарифов.\nПопробуйте позже.',
            reply_markup=back_and_home_kb(back_callback=f'key:{key_id}')
        )
        await callback.answer()
        return
    
    # Показываем информацию о текущей подписке и список тарифов
    if key['expires_at']:
        expires_dt = datetime.fromisoformat(key['expires_at'])
        expires = expires_dt.strftime('%d-%m-%Y')
        days_left = (expires_dt - datetime.now()).days
        if days_left < 0:
            days_left = 0
    else:
        expires = '—'
        days_left = 0
    
    text = (
        f"💳 <b>Продление подписки</b>\n\n"
        f"🔑 <b>Подписка:</b> {escape_html(key['display_name'])}\n"
        f"📅 <b>Действует до:</b> {expires}\n"
        f"⏳ <b>Осталось дней:</b> {days_left}\n\n"
        f"Выберите тариф для продления:"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=key_renew_tariff_list_kb(tariffs, key_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('key_renew_tariff:'))
async def key_renew_select_payment(callback: CallbackQuery):
    """Выбор способа оплаты после выбора тарифа."""
    from database.requests import get_tariff_by_id, get_key_details_for_user, get_user_internal_id, is_crypto_configured, is_stars_enabled, is_cards_enabled, get_setting, create_pending_order, get_crypto_integration_mode, is_referral_enabled, get_referral_reward_type, get_user_balance, is_demo_payment_enabled
    from bot.services.billing import build_crypto_payment_url, extract_item_id_from_url
    from bot.keyboards.user import renew_payment_method_kb, back_and_home_kb
    
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    telegram_id = callback.from_user.id
    
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден или вы не являетесь его владельцем.', show_alert=True)
        return
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    # Проверяем доступные способы оплаты
    crypto_configured = is_crypto_configured()
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    demo_enabled = is_demo_payment_enabled()
    from database.requests import is_yookassa_qr_configured
    yookassa_qr = is_yookassa_qr_configured()
    
    if not crypto_configured and not stars_enabled and not cards_enabled and not yookassa_qr and not demo_enabled:
        await safe_edit_or_send(
            callback.message,
            '💳 <b>Продление подписки</b>\n\n😔 Способы оплаты временно недоступны.\nПопробуйте позже.',
            reply_markup=back_and_home_kb(back_callback=f'key_renew:{key_id}')
        )
        await callback.answer()
        return
    
    # Создаем placeholder order для крипты если нужно
    crypto_url = None
    crypto_mode = get_crypto_integration_mode()
    user_id = get_user_internal_id(telegram_id)
    
    if crypto_configured and user_id:
        (_, order_id) = create_pending_order(user_id=user_id, tariff_id=tariff_id, payment_type='crypto', vpn_key_id=key_id)
        if crypto_mode == 'standard':
            item_url = get_setting('crypto_item_url')
            item_id = extract_item_id_from_url(item_url)
            if item_id:
                crypto_url = build_crypto_payment_url(item_id=item_id, invoice_id=order_id, tariff_external_id=None, price_cents=None)
    
    # Проверяем баланс для кнопки оплаты с баланса
    show_balance_button = False
    if is_referral_enabled() and get_referral_reward_type() == 'balance':
        if user_id:
            balance_cents = get_user_balance(user_id)
            if balance_cents > 0:
                show_balance_button = True
    
    # Показываем цену
    if tariff.get('price_rub') and tariff['price_rub'] > 0:
        price_display = f"{tariff['price_rub']} ₽"
    else:
        price_usd = tariff['price_cents'] / 100
        price_str = f"{price_usd:g}".replace('.', ',')
        price_display = f"${price_str}"
    
    text = (
        f"💳 <b>Продление подписки</b>\n\n"
        f"🔑 <b>Подписка:</b> {escape_html(key['display_name'])}\n"
        f"📦 <b>Тариф:</b> {escape_html(tariff['name'])}\n"
        f"⏰ <b>Продление на:</b> {tariff['duration_days']} дней\n"
        f"💰 <b>Стоимость:</b> {price_display}\n\n"
        f"Выберите способ оплаты:"
    )
    
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=renew_payment_method_kb(
            key_id=key_id,
            tariff_id=tariff_id,
            crypto_url=crypto_url,
            crypto_mode=crypto_mode,
            crypto_configured=crypto_configured,
            stars_enabled=stars_enabled,
            cards_enabled=cards_enabled,
            yookassa_qr_enabled=yookassa_qr,
            show_balance_button=show_balance_button,
            demo_enabled=demo_enabled
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith('key_replace:'))
async def key_replace_start_handler(callback: CallbackQuery, state: FSMContext):
    """Начало процедуры замены ключа."""
    from database.requests import get_key_details_for_user, get_active_servers
    from bot.services.vpn_api import get_client
    from bot.keyboards.user import replace_server_list_kb
    from bot.utils.groups import get_servers_for_key
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден или вы не являетесь его владельцем.', show_alert=True)
        return
    if not key['is_active']:
        await callback.answer('⏳ Срок действия ключа истёк.\nПродлите его перед заменой.', show_alert=True)
        return
    if key.get('server_active') and key.get('panel_email'):
        try:
            client = await get_client(key['server_id'])
            stats = await client.get_client_stats(key['panel_email'])
            if stats and stats['total'] > 0:
                used = stats['up'] + stats['down']
                percent = used / stats['total']
                if percent > 0.2:
                    await callback.answer(f'⛔ Замена невозможна.\nИспользовано {percent * 100:.1f}% трафика (макс. 20%).', show_alert=True)
                    return
            elif stats and stats['total'] == 0:
                pass
        except Exception as e:
            logger.warning(f'Ошибка проверки трафика для замены: {e}')
            pass
    tariff_id = key.get('tariff_id')
    servers = get_servers_for_key(tariff_id) if tariff_id else get_active_servers()
    if not servers:
        await callback.answer('❌ Нет доступных серверов', show_alert=True)
        return
    await state.set_state(ReplaceKey.users_server)
    await state.update_data(replace_key_id=key_id)
    await safe_edit_or_send(callback.message, '🔄 <b>Замена ключа</b>\n\nВы можете пересоздать ключ на другом или том же сервере.\nСтарый ключ будет удалён, но срок действия сохранится.\n\nВыберите сервер:', reply_markup=replace_server_list_kb(servers, key_id))
    await callback.answer()

@router.callback_query(ReplaceKey.users_server, F.data.startswith('replace_server:'))
async def key_replace_server_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор сервера для замены."""
    from database.requests import get_server_by_id
    from bot.services.vpn_api import get_client, VPNAPIError
    from bot.keyboards.user import replace_inbound_list_kb
    server_id = int(callback.data.split(':')[1])
    server = get_server_by_id(server_id)
    if not server:
        await callback.answer('Сервер не найден', show_alert=True)
        return
    await state.update_data(replace_server_id=server_id)
    try:
        client = await get_client(server_id)
        inbounds = await client.get_inbounds()
        if not inbounds:
            await callback.answer('❌ На сервере нет доступных протоколов', show_alert=True)
            return
        data = await state.get_data()
        key_id = data.get('replace_key_id')
        await state.set_state(ReplaceKey.users_inbound)
        await safe_edit_or_send(callback.message, f"🖥️ <b>Сервер:</b> {escape_html(server['name'])}\n\nВыберите протокол:", reply_markup=replace_inbound_list_kb(inbounds, key_id))
    except VPNAPIError as e:
        await callback.answer(f'❌ Ошибка подключения: {e}', show_alert=True)
    await callback.answer()

@router.callback_query(ReplaceKey.users_inbound, F.data.startswith('replace_inbound:'))
async def key_replace_inbound_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор inbound и подтверждение."""
    from database.requests import get_server_by_id, get_key_details_for_user
    from bot.keyboards.user import replace_confirm_kb
    inbound_id = int(callback.data.split(':')[1])
    await state.update_data(replace_inbound_id=inbound_id)
    data = await state.get_data()
    key_id = data.get('replace_key_id')
    server_id = data.get('replace_server_id')
    key = get_key_details_for_user(key_id, callback.from_user.id)
    server = get_server_by_id(server_id)
    await state.set_state(ReplaceKey.confirm)
    await safe_edit_or_send(callback.message, f"⚠️ <b>Подтверждение замены</b>\n\nКлюч: <b>{escape_html(key['display_name'])}</b>\nНовый сервер: <b>{escape_html(server['name'])}</b>\n\nСтарый ключ будет удалён и перестанет работать.\nВам нужно будет обновить настройки в приложении.\n\nВы уверены?", reply_markup=replace_confirm_kb(key_id))
    await callback.answer()

@router.callback_query(ReplaceKey.confirm, F.data == 'replace_confirm')
async def key_replace_execute(callback: CallbackQuery, state: FSMContext):
    """Выполнение замены ключа."""
    from database.requests import get_key_details_for_user, get_server_by_id, update_vpn_key_connection
    from bot.services.vpn_api import get_client, VPNAPIError
    from bot.handlers.admin.users_keys import generate_unique_email
    from bot.utils.key_sender import send_key_with_qr
    from bot.keyboards.user import key_issued_kb
    data = await state.get_data()
    key_id = data.get('replace_key_id')
    new_server_id = data.get('replace_server_id')
    new_inbound_id = data.get('replace_inbound_id')
    telegram_id = callback.from_user.id
    current_key = get_key_details_for_user(key_id, telegram_id)
    new_server_data = get_server_by_id(new_server_id)
    if not current_key or not new_server_data:
        await callback.answer('❌ Ошибка данных', show_alert=True)
        return
    await safe_edit_or_send(callback.message, '⏳ Выполняется замена ключа...')
    try:
        is_same_server = current_key['server_id'] == new_server_id
        if current_key.get('server_id') and current_key.get('server_active') and current_key.get('panel_email'):
            try:
                old_client = await get_client(current_key['server_id'])
                await old_client.delete_client(current_key['panel_inbound_id'], current_key['client_uuid'])
                logger.info(f"Старый ключ {key_id} успешно удалён (uuid: {current_key['client_uuid']})")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f'Ошибка удаления старого ключа {key_id}: {error_msg}')
                if is_same_server:
                    if 'not found' in error_msg.lower() or 'не найден' in error_msg.lower() or 'no client remained' in error_msg.lower():
                        logger.info('Ключ не найден на сервере, считаем удаленным.')
                    else:
                        raise VPNAPIError(f'Не удалось удалить старый ключ: {error_msg}. Замена отменена во избежание дублей.')
                else:
                    pass
        new_client = await get_client(new_server_id)
        user_fake_dict = {'telegram_id': telegram_id, 'username': current_key.get('username')}
        new_email = generate_unique_email(user_fake_dict)
        traffic_limit = current_key.get('traffic_limit', 0) or 0
        traffic_used = current_key.get('traffic_used', 0) or 0
        traffic_notified_pct = current_key.get('traffic_notified_pct', 100) or 100
        if traffic_limit > 0:
            remaining_bytes = max(0, traffic_limit - traffic_used)
            limit_gb = max(1, int(remaining_bytes / 1024 ** 3))
        else:
            remaining_bytes = 0
            limit_gb = 0
        expires_at = datetime.fromisoformat(current_key['expires_at'])
        now = datetime.now()
        delta = expires_at - now
        days_left = delta.days
        if delta.seconds > 0:
            days_left += 1
        if days_left < 1:
            days_left = 1
        flow = await new_client.get_inbound_flow(new_inbound_id)
        res = await new_client.add_client(inbound_id=new_inbound_id, email=new_email, total_gb=limit_gb, expire_days=days_left, limit_ip=1, enable=True, tg_id=str(telegram_id), flow=flow)
        new_uuid = res['uuid']
        update_vpn_key_connection(key_id=key_id, server_id=new_server_id, panel_inbound_id=new_inbound_id, panel_email=new_email, client_uuid=new_uuid)
        if traffic_limit > 0:
            from database.requests import bulk_update_traffic, update_key_notified_pct
            bulk_update_traffic([(traffic_used, key_id)])
            logger.info(f'Перенос трафика ключа {key_id}: остаток {remaining_bytes / 1024 ** 3:.1f} ГБ (totalGB на сервере), полный тариф {traffic_limit / 1024 ** 3:.1f} ГБ, использовано {traffic_used / 1024 ** 3:.1f} ГБ')
        await state.clear()
        
        # Показываем subscription ссылку вместо отдельного ключа
        from bot.utils.key_sender import send_subscription_link
        from bot.keyboards.user import back_and_home_kb
        await send_subscription_link(callback, telegram_id, back_and_home_kb(back_callback="my_keys"))
    except Exception as e:
        logger.error(f'Ошибка при замене ключа (user={callback.from_user.id}, key={key_id}): {e}')
        await safe_edit_or_send(callback.message, '❌ Произошла ошибка при замене ключа.\n\nПопробуйте позже или обратитесь в поддержку.')

@router.callback_query(F.data.startswith('key_rename:'))
async def key_rename_start_handler(callback: CallbackQuery, state: FSMContext):
    """Начало переименования ключа."""
    from database.requests import get_key_details_for_user
    from bot.keyboards.user import cancel_kb
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден или вы не являетесь его владельцем.', show_alert=True)
        return
    await state.set_state(RenameKey.waiting_for_name)
    await state.update_data(key_id=key_id)
    await safe_edit_or_send(callback.message, f"✏️ <b>Переименование ключа</b>\n\nТекущее имя: <b>{escape_html(key['display_name'])}</b>\n\nВведите новое название для ключа (макс. 30 символов):\n<i>(Отправьте любой текст)</i>", reply_markup=cancel_kb(cancel_callback=f'key:{key_id}'))
    await callback.answer()

@router.message(RenameKey.waiting_for_name)
async def key_rename_submit_handler(message: Message, state: FSMContext):
    """Обработка ввода нового имени ключа."""
    from database.requests import update_key_custom_name
    from bot.utils.text import get_message_text_for_storage
    data = await state.get_data()
    key_id = data.get('key_id')
    new_name = get_message_text_for_storage(message, 'plain')
    if not key_id:
        await state.clear()
        await safe_edit_or_send(message, '❌ Ошибка состояния. Попробуйте снова.')
        return
    if len(new_name) > 30:
        await safe_edit_or_send(message, '⚠️ Имя слишком длинное (макс. 30 символов). Попробуйте короче.')
        return
    success = update_key_custom_name(key_id, message.from_user.id, new_name)
    if success:
        prepend = f'✅ Ключ переименован в <b>{escape_html(new_name)}</b>'
    else:
        prepend = '❌ Не удалось переименовать ключ.'
    await state.clear()
    await show_key_details(message.from_user.id, key_id, message, is_callback=False, prepend_text=prepend)