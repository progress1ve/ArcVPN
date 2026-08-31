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


def _subscription_urls(sub_id: str) -> tuple[str, str]:
    """Return the raw subscription URL and the HTTPS Happ import bridge."""
    import os, config
    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL)

    base = config.SUBSCRIPTION_URL.rstrip("/")
    subscription_url = f"{base}/sub/{sub_id}"
    return subscription_url, f"{base}/import/{sub_id}"

@router.message(Command('mykeys'))
async def cmd_mykeys(message: Message, state: FSMContext):
    """Обработчик команды /mykeys - вызывает логику кнопки 'Мои подписки'."""
    if is_user_banned(message.from_user.id):
        await safe_edit_or_send(message, '⛔ <b>Доступ заблокирован</b>\n\nВаш аккаунт заблокирован. Обратитесь в поддержку.', force_new=True)
        return
    await state.clear()
    await show_my_keys(message.from_user.id, message)

async def show_my_keys(
    telegram_id: int,
    message,
    is_callback: bool = True,
    prepend_text: str = "",
):
    """Показывает единственную подписку сразу, без устаревшего выбора ключа."""
    from aiogram.types import InlineKeyboardButton, WebAppInfo
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    import os
    import config
    from database.requests import (
        get_user_devices,
        get_user_entitlements,
        get_user_primary_key,
        is_traffic_exhausted,
    )
    from bot.handlers.user.start import _days_left, _format_bytes, _plural_days

    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL)

    primary = get_user_primary_key(telegram_id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Открыть ArcVPN",
        web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/app"),
        style="primary",
    ))

    if not primary:
        builder.row(InlineKeyboardButton(
            text="💳 Выбрать тариф",
            callback_data="buy_key",
            style="primary",
        ))
        builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
        text = (
            "🔐 <b>Моя подписка</b>\n\n"
            "Подписка ещё не оформлена.\n"
            "Выберите тариф — доступ появится автоматически после оплаты."
        )
        if prepend_text:
            text = f"{prepend_text}\n\n{text}"
        await safe_edit_or_send(
            message,
            text,
            reply_markup=builder.as_markup(),
            force_new=not is_callback,
        )
        return

    traffic_used = int(primary.get("traffic_used") or 0)
    traffic_limit = int(primary.get("traffic_limit") or 0)
    exhausted = is_traffic_exhausted(primary)
    active = bool(primary.get("is_active")) and not exhausted
    days = _days_left(primary.get("expires_at"))
    if traffic_limit > 0:
        traffic = f"{_format_bytes(max(0, traffic_limit - traffic_used))} осталось"
    else:
        traffic = "без ограничений"

    entitlements = get_user_entitlements(telegram_id)
    devices = get_user_devices(telegram_id)
    device_limit = int(entitlements.get("device_limit") or 2)
    device_count = len(devices)

    if active:
        status = "● <b>Активна</b>"
        access = f"Осталось: <b>{_plural_days(days)}</b>"
    elif exhausted:
        status = "○ <b>Трафик закончился</b>"
        access = "Продлите подписку, чтобы восстановить доступ"
    else:
        status = "○ <b>Срок закончился</b>"
        access = "Продлите подписку, чтобы восстановить доступ"

    text = (
        "🔐 <b>Моя подписка</b>\n\n"
        f"{status}\n"
        f"{access}\n\n"
        f"<blockquote>Трафик: <b>{traffic}</b>\n"
        f"Устройства: <b>{device_count} из {device_limit}</b></blockquote>"
    )
    sub_id = str(primary.get("sub_id") or "")
    if sub_id:
        subscription_url, _ = _subscription_urls(sub_id)
        text += (
            f'\n\n🔗 <b>Ссылка на подписку</b>\n\n'
            f'<code>{escape_html(subscription_url)}</code>\n\n'
            '👆 Нажмите на ссылку, чтобы скопировать.'
        )
    if prepend_text:
        text = f"{prepend_text}\n\n{text}"

    if active:
        builder.row(InlineKeyboardButton(
            text="📲 Импортировать подписку",
            callback_data="show_subscription",
        ))
    builder.row(InlineKeyboardButton(
        text="⚡ Продлить подписку",
        callback_data=f"key_renew:{primary['id']}",
        style="primary",
    ))
    builder.row(
        InlineKeyboardButton(text="📖 Инструкция", callback_data="device_instructions"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="start"),
    )

    await safe_edit_or_send(
        message,
        text,
        reply_markup=builder.as_markup(),
        force_new=not is_callback,
    )

@router.callback_query(F.data == 'my_keys')
async def my_keys_handler(callback: CallbackQuery):
    """Список VPN-подписок пользователя."""
    telegram_id = callback.from_user.id
    await show_my_keys(telegram_id, callback.message)
    await callback.answer()

async def show_key_details(telegram_id: int, key_id: int, message, is_callback: bool = True, prepend_text: str=''):
    """Совместимость с платёжными сценариями старого интерфейса."""
    await show_my_keys(
        telegram_id,
        message,
        is_callback=is_callback,
        prepend_text=prepend_text,
    )

@router.callback_query(F.data.startswith('key_delete:'))
async def key_delete_handler(callback: CallbackQuery):
    """Удаление истекшей подписки пользователем."""
    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.fromuser.id if hasattr(callback, 'fromuser') else callback.from_user.id
    from database.requests import get_key_details_for_user, delete_vpn_key
    from bot.services.vpn_api import get_client
    import logging
    logger = logging.getLogger(__name__)
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Подписка не найдена или вы не являетесь её владельцем.', show_alert=True)
        return
    if key['is_active']:
        await callback.answer('❌ Активные подписки нельзя удалить.', show_alert=True)
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
        await callback.answer(f"✅ Подписка {key['display_name']} успешно удалена.", show_alert=True)
        await show_my_keys(telegram_id, callback.message)
    else:
        await callback.answer('❌ Ошибка при удалении подписки из БД.', show_alert=True)

@router.callback_query(F.data.startswith('key:'))
async def key_details_handler(callback: CallbackQuery):
    """Совместимость со старыми сообщениями: сразу открывает новую подписку."""
    await show_my_keys(callback.from_user.id, callback.message)
    await callback.answer()

@router.callback_query(F.data.startswith('key_show:'))
async def key_show_handler(callback: CallbackQuery):
    """Показать subscription ссылку (заменяет показ отдельной подписки)."""
    from bot.utils.key_sender import send_subscription_link
    from bot.keyboards.user import back_and_home_kb
    from database.requests import get_user_primary_key
    
    telegram_id = callback.from_user.id
    primary = get_user_primary_key(telegram_id)
    if not primary:
        await callback.answer("Подписка не найдена", show_alert=True)
        return
    await send_subscription_link(callback, primary["id"], back_and_home_kb(back_callback="my_keys"))
    await callback.answer()

@router.callback_query(F.data == 'device_instructions')
async def device_instructions_handler(callback: CallbackQuery):
    """Показывает меню выбора устройства для инструкции."""
    logger.info(f"device_instructions_handler вызван для пользователя {callback.from_user.id}")
    
    from bot.keyboards.user import device_instructions_kb
    
    text = (
        "📱 <b>Подключить VPN</b>\n\n"
        "Выберите устройство. Покажем только нужные шаги для установки Happ "
        "и импорта вашей подписки."
    )
    
    try:
        await safe_edit_or_send(callback.message, text, reply_markup=device_instructions_kb())
        await callback.answer()
        logger.info("device_instructions_handler успешно выполнен")
    except Exception as e:
        logger.error(f"Ошибка в device_instructions_handler: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

# Конфигурация инструкций по устройствам: текст + ссылка на загрузку Happ.
# Единый обработчик ниже устраняет дублирование трёх почти одинаковых хендлеров.
_HAPP_FOOTER = (
    "<blockquote>Подписка обновляется автоматически каждый час.\n"
    "Российские сервисы продолжают работать с включённым VPN.</blockquote>"
)
INSTRUCTION_DEVICES = {
    "instruction_apple": {
        "download_url": "https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973",
        "text": (
            "<b>Apple · iPhone, iPad, Mac</b>\n\n"
            "<b>1.</b> Установите Happ.\n"
            "<b>2.</b> Нажмите «Импортировать подписку».\n"
            "<b>3.</b> Разрешите добавление и включите VPN в Happ.\n\n"
            + _HAPP_FOOTER
        ),
    },
    "instruction_android": {
        "download_url": "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru",
        "text": (
            "<b>Android</b>\n\n"
            "<b>1.</b> Установите Happ.\n"
            "<b>2.</b> Нажмите «Импортировать подписку».\n"
            "<b>3.</b> Разрешите добавление и включите VPN в Happ.\n\n"
            + _HAPP_FOOTER
        ),
    },
    "instruction_windows": {
        "download_url": "https://github.com/Happ-proxy/happ-desktop/releases/tag/2.9.1",
        "text": (
            "<b>Windows</b>\n\n"
            "<b>1.</b> Установите Happ.\n"
            "<b>2.</b> Нажмите «Импортировать подписку».\n"
            "<b>3.</b> Разрешите добавление и включите VPN в Happ."
        ),
    },
}

@router.callback_query(F.data.in_(INSTRUCTION_DEVICES.keys()))
async def instruction_device_handler(callback: CallbackQuery):
    """Инструкция по подключению для выбранного устройства (Apple/Android/Windows)."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from config import SUBSCRIPTION_URL
    from database.requests import get_user_keys_for_display, get_vpn_key_by_id

    device = callback.data
    cfg = INSTRUCTION_DEVICES[device]
    telegram_id = callback.from_user.id

    # Получаем первый активный ключ пользователя для subscription URL
    keys = get_user_keys_for_display(telegram_id)
    if not keys:
        await callback.answer("❌ У вас нет активных ключей. Сначала купите подписку!", show_alert=True)
        return

    key_data = get_vpn_key_by_id(keys[0]['id'])
    if not key_data or not key_data.get('sub_id'):
        await callback.answer("❌ Ошибка получения subscription ссылки", show_alert=True)
        return

    try:
        import_url = f"{SUBSCRIPTION_URL}/import/{key_data['sub_id']}"

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📥 Скачать Happ", url=cfg["download_url"]))
        builder.row(InlineKeyboardButton(text="📲 Импортировать подписку", url=import_url, style="primary"))
        builder.row(
            InlineKeyboardButton(text="← Назад", callback_data="device_instructions"),
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        )

        await safe_edit_or_send(callback.message, cfg["text"], reply_markup=builder.as_markup())
        await callback.answer()
        masked_sub_id = f"{key_data['sub_id'][:4]}...{key_data['sub_id'][-4:]}"
        logger.info(f"{device} успешно выполнен (sub_id={masked_sub_id})")
    except Exception as e:
        logger.error(f"Ошибка в {device}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == 'show_subscription')
async def show_subscription_handler(callback: CallbackQuery):
    """Show the modern direct subscription/import message without legacy QR UI."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from database.requests import get_user_primary_key
    
    telegram_id = callback.from_user.id
    primary = get_user_primary_key(telegram_id)
    if not primary or not primary.get("sub_id"):
        await callback.answer("Подписка не найдена", show_alert=True)
        return

    subscription_url, import_url = _subscription_urls(str(primary["sub_id"]))
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📲 Импортировать в Happ",
        url=import_url,
        style="primary",
    ))
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="my_keys"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="start"),
    )
    text = (
        "📲 <b>Подключить VPN</b>\n\n"
        "Нажмите кнопку ниже — Happ откроется и добавит подписку.\n\n"
        f'🔗 <b>Ссылка на подписку</b>\n\n'
        f'<code>{escape_html(subscription_url)}</code>\n\n'
        '👆 Нажмите на ссылку, чтобы скопировать.\n\n'
        "<blockquote>Подписка обновляется автоматически каждый час.</blockquote>"
    )
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith('key_renew:'))
async def key_renew_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для продления подписки (единый UI с покупкой)."""
    from bot.utils.payment_flow_ui import show_tariff_selection_screen

    key_id = int(callback.data.split(':')[1])
    telegram_id = callback.from_user.id

    ok = await show_tariff_selection_screen(callback.message, telegram_id, key_id=key_id)
    if not ok:
        await callback.answer('❌ Подписка не найдена или нет доступных тарифов.', show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith('key_renew_tariff:'))
async def key_renew_select_payment(callback: CallbackQuery):
    """Выбор способа оплаты после выбора тарифа (единый экран)."""
    from bot.utils.payment_flow_ui import show_payment_method_selection_screen

    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    telegram_id = callback.from_user.id

    await show_payment_method_selection_screen(
        callback.message,
        telegram_id,
        tariff_id,
        key_id=key_id,
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
        res = await new_client.add_client(inbound_id=new_inbound_id, email=new_email, total_gb=limit_gb, expire_days=days_left, limit_ip=DEFAULT_LIMIT_IP, enable=True, tg_id=str(telegram_id), flow=flow)
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
