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

async def start_new_key_config(message: Message, state: FSMContext, order_id: str, key_id: int=None):
    """
    Запускает процесс настройки нового ключа.
    Теперь сразу показывает subscription ссылку вместо выбора сервера.
    """
    from database.requests import find_order_by_order_id
    from bot.keyboards.admin import home_only_kb
    from bot.utils.key_sender import send_subscription_link
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    order = find_order_by_order_id(order_id)
    
    # Проверяем, это пробный период или обычная покупка
    is_trial = order and order.get('payment_type') == 'trial'
    
    if is_trial:
        # Для пробного периода это сообщение не должно вызываться
        # (обрабатывается в trial.py)
        return
    
    # Для обычной покупки показываем сообщение об успешной оплате
    success_message = (
        "🎉 <b>Оплата прошла успешно!</b>\n\n"
        "✅ Ваша подписка активирована\n\n"
        "📱 <b>Что дальше?</b>\n"
        "1. Нажмите кнопку ниже для просмотра вашей подписки\n"
        "2. Скопируйте ссылку или отсканируйте QR-код\n"
        "3. Импортируйте в VPN-клиент (Hiddify, v2rayNG)\n\n"
        "💡 <i>Подписка автоматически обновляется при продлении</i>"
    )
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📥 Показать подписку", callback_data="show_subscription"))
    builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
    builder.row(
        InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="start")
    )
    
    await safe_edit_or_send(
        message, 
        success_message,
        reply_markup=builder.as_markup(), 
        force_new=True
    )

@router.callback_query(F.data.startswith('new_key_server:'))
async def process_new_key_server_selection(callback: CallbackQuery, state: FSMContext):
    """Выбор сервера для нового ключа."""
    from database.requests import get_server_by_id
    from bot.services.vpn_api import get_client, VPNAPIError
    from bot.keyboards.user import new_key_inbound_list_kb
    from bot.states.user_states import NewKeyConfig
    server_id = int(callback.data.split(':')[1])
    server = get_server_by_id(server_id)
    if not server:
        await callback.answer('Сервер не найден', show_alert=True)
        return
    await state.update_data(new_key_server_id=server_id)
    try:
        client = await get_client(server_id)
        inbounds = await client.get_inbounds()
        if not inbounds:
            await callback.answer('❌ На сервере нет доступных протоколов', show_alert=True)
            return
        if len(inbounds) == 1:
            await process_new_key_final(callback, state, server_id, inbounds[0]['id'])
            return
        await state.set_state(NewKeyConfig.waiting_for_inbound)
        await safe_edit_or_send(callback.message, f"🖥️ <b>Сервер:</b> {escape_html(server['name'])}\n\nВыберите протокол:", reply_markup=new_key_inbound_list_kb(inbounds))
    except VPNAPIError as e:
        await callback.answer(f'❌ Ошибка подключения: {e}', show_alert=True)
    await callback.answer()

@router.callback_query(F.data.startswith('new_key_inbound:'))
async def process_new_key_inbound_selection(callback: CallbackQuery, state: FSMContext):
    """Выбор протокола (inbound) для нового ключа."""
    inbound_id = int(callback.data.split(':')[1])
    data = await state.get_data()
    server_id = data.get('new_key_server_id')
    await process_new_key_final(callback, state, server_id, inbound_id)

async def process_new_key_final(callback: CallbackQuery, state: FSMContext, server_id: int, inbound_id: int):
    """Финальный этап создания ключа."""
    from database.requests import get_server_by_id, update_vpn_key_config, update_payment_key_id, find_order_by_order_id, get_user_internal_id, get_key_details_for_user, create_initial_vpn_key
    from bot.services.vpn_api import get_client
    from bot.handlers.admin.users_keys import generate_unique_email
    from bot.utils.key_sender import send_key_with_qr
    from bot.keyboards.user import key_issued_kb
    data = await state.get_data()
    order_id = data.get('new_key_order_id')
    key_id = data.get('new_key_id')
    if not order_id:
        await safe_edit_or_send(callback.message, '❌ Ошибка: потерян номер заказа.')
        await state.clear()
        return
    order = find_order_by_order_id(order_id)
    if not order:
        await safe_edit_or_send(callback.message, '❌ Ошибка: заказ не найден.')
        await state.clear()
        return
    if not key_id:
        if order['vpn_key_id']:
            key_id = order['vpn_key_id']
        else:
            days = order.get('period_days') or order.get('duration_days') or 30
            from database.requests import get_tariff_by_id as _get_tariff
            _tariff = _get_tariff(order['tariff_id'])
            traffic_limit_bytes = (_tariff.get('traffic_limit_gb', 0) or 0) * 1024 ** 3 if _tariff else 0
            key_id = create_initial_vpn_key(order['user_id'], order['tariff_id'], days, traffic_limit=traffic_limit_bytes)
            update_payment_key_id(order_id, key_id)
    await safe_edit_or_send(callback.message, '⏳ Настраиваем ваш ключ...')
    try:
        user_id = order['user_id']
        telegram_id = callback.from_user.id
        username = callback.from_user.username
        user_fake_dict = {'telegram_id': telegram_id, 'username': username}
        panel_email = generate_unique_email(user_fake_dict)
        client = await get_client(server_id)
        days = order.get('period_days') or order.get('duration_days') or 30
        # Лимит трафика из тарифа (0 = безлимит на панели)
        from database.requests import get_tariff_by_id as _get_tariff_for_limit
        _tariff_data = _get_tariff_for_limit(order['tariff_id'])
        limit_gb = (_tariff_data.get('traffic_limit_gb', 0) or 0) if _tariff_data else 0
        flow = await client.get_inbound_flow(inbound_id)
        res = await client.add_client(inbound_id=inbound_id, email=panel_email, total_gb=limit_gb, expire_days=days, limit_ip=1, enable=True, tg_id=str(telegram_id), flow=flow)
        client_uuid = res['uuid']
        update_vpn_key_config(key_id=key_id, server_id=server_id, panel_inbound_id=inbound_id, panel_email=panel_email, client_uuid=client_uuid)
        update_payment_key_id(order_id, key_id)
        await state.clear()
        
        # Показываем subscription ссылку вместо отдельного ключа
        from bot.utils.key_sender import send_subscription_link
        from bot.keyboards.user import back_and_home_kb
        await send_subscription_link(callback, telegram_id, back_and_home_kb(back_callback="my_keys"))
    except Exception as e:
        logger.error(f'Ошибка настройки ключа (id={key_id}): {e}')
        await safe_edit_or_send(callback.message, f'❌ Ошибка настройки ключа: {escape_html(str(e))}\nОбратитесь в поддержку, указав Order ID: ' + str(order_id))

@router.callback_query(F.data == 'back_to_server_select')
async def back_to_server_select(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору сервера."""
    from database.requests import get_active_servers, find_order_by_order_id
    from bot.keyboards.user import new_key_server_list_kb
    from bot.states.user_states import NewKeyConfig
    from bot.utils.groups import get_servers_for_key
    data = await state.get_data()
    order_id = data.get('new_key_order_id')
    tariff_id = None
    if order_id:
        order = find_order_by_order_id(order_id)
        tariff_id = order.get('tariff_id') if order else None
    servers = get_servers_for_key(tariff_id) if tariff_id else get_active_servers()
    await state.set_state(NewKeyConfig.waiting_for_server)
    await safe_edit_or_send(callback.message, '🔑 Выберите сервер для вашего нового ключа.', reply_markup=new_key_server_list_kb(servers))