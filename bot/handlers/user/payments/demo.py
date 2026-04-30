import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.utils.text import escape_html, safe_edit_or_send
from database.requests import get_all_tariffs, get_tariff_by_id, get_key_details_for_user
from bot.keyboards.user import tariff_select_kb, renew_tariff_select_kb
from bot.keyboards.admin import home_only_kb

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data.startswith('demo_tariffs'))
async def demo_tariffs_handler(callback: CallbackQuery):
    """Обработчик демо-оплаты - показывает выбор тарифа."""
    # Формат demo_tariffs или demo_tariffs:order_id - показываем выбор тарифа
    parts = callback.data.split(':')
    order_id = parts[1] if len(parts) > 1 else None
    tariffs = get_all_tariffs(include_hidden=False)
    
    if not tariffs:
        await callback.answer('❌ Нет доступных тарифов', show_alert=True)
        return
    
    await safe_edit_or_send(
        callback.message,
        '🏦 <b>Демо оплата (РФ карта)</b>\n\nВыберите тариф:\n\n<i>Этот способ используется только для демонстрации интерфейса оплаты.</i>',
        reply_markup=tariff_select_kb(tariffs, order_id=order_id, is_demo=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo_pay_tariff:'))
async def demo_pay_tariff_handler(callback: CallbackQuery):
    """Обработчик выбора тарифа для демо-оплаты - показывает экран подтверждения."""
    from database.requests import get_user_internal_id, create_pending_order, update_order_tariff
    
    # Парсим callback_data
    parts = callback.data.split(':')
    
    # Формат demo_pay_tariff:tariff_id:order_id - тариф уже выбран (из tariff_select_kb)
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    
    # Создаем или обновляем заказ
    if order_id:
        update_order_tariff(order_id, tariff_id, payment_type='demo')
    else:
        (_, order_id) = create_pending_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='demo',
            vpn_key_id=None
        )
    
    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        f"🏦 <b>Демо оплата (РФ карта)</b>\n\n"
        f"📦 Тариф: <b>{escape_html(tariff['name'])}</b>\n"
        f"💵 Сумма: <b>{price_rub} ₽</b>\n\n"
        f"⚠️ <i>Это демонстрационный режим оплаты.</i>\n\n"
        f"Нажмите кнопку ниже для имитации оплаты:"
    )
    
    from bot.keyboards.user import InlineKeyboardBuilder, InlineKeyboardButton
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text=f"💳 Оплатить {price_rub} ₽", callback_data=f"demo_confirm:{order_id}"))
    keyboard.row(InlineKeyboardButton(text="❌ Отмена", callback_data="buy_key"))
    
    await safe_edit_or_send(callback.message, text, reply_markup=keyboard.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith('renew_demo_tariffs:'))
async def renew_demo_tariffs_handler(callback: CallbackQuery):
    """Выбор тарифа для демонстрационной оплаты (Продление)."""
    parts = callback.data.split(':')
    key_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
        
    from bot.utils.groups import get_tariffs_for_renewal
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    if not tariffs:
        await callback.answer('Нет доступных тарифов', show_alert=True)
        return
        
    await safe_edit_or_send(
        callback.message, 
        f"🏦 <b>Демо оплата (РФ карта)</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:", 
        reply_markup=renew_tariff_select_kb(tariffs, key_id, order_id=order_id, is_demo=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('demo_pay:'))
async def demo_pay_handler(callback: CallbackQuery):
    """Показ демонстрационного экрана оплаты (Новый ключ)."""
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return

    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        "🏦 <b>Демонстрационная оплата</b>\n\n"
        "Это демо-режим. Реального списания не происходит.\n\n"
        f"📦 <b>Тариф:</b> {escape_html(tariff['name'])}\n"
        f"📅 <b>Срок:</b> {tariff['duration_days']} дн.\n"
        f"💰 <b>Сумма:</b> {int(price_rub)} ₽\n\n"
        "<i>В рабочем режиме здесь появится форма оплаты российской картой.</i>"
    )
    
    # Можно добавить кнопку назад
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='⬅️ Назад к тарифами', callback_data='demo_tariffs'))
    builder.row(InlineKeyboardButton(text='🈴 На главную', callback_data='start'))
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith('renew_demo_pay:'))
async def renew_demo_pay_handler(callback: CallbackQuery):
    """Показ демонстрационного экрана оплаты с подтверждением (Продление)."""
    from database.requests import get_user_internal_id, create_pending_order, update_order_tariff
    
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    
    # Создаем или обновляем заказ
    if order_id:
        update_order_tariff(order_id, tariff_id, payment_type='demo')
    else:
        (_, order_id) = create_pending_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='demo',
            vpn_key_id=key_id
        )

    price_rub = float(tariff.get('price_rub') or 0)
    
    text = (
        f"🏦 <b>Демо оплата (РФ карта)</b>\n\n"
        f"🔑 <b>Ключ:</b> {escape_html(key['display_name'])}\n"
        f"📦 <b>Продление на:</b> {escape_html(tariff['name'])}\n"
        f"📅 <b>Срок:</b> +{tariff['duration_days']} дн.\n"
        f"💵 <b>Сумма:</b> {price_rub} ₽\n\n"
        f"⚠️ <i>Это демонстрационный режим оплаты.</i>\n\n"
        f"Нажмите кнопку ниже для имитации оплаты:"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"💳 Оплатить {price_rub} ₽", callback_data=f"demo_confirm:{order_id}"))
    builder.row(InlineKeyboardButton(text='❌ Отмена', callback_data=f'key:{key_id}'))
    
    await safe_edit_or_send(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith('demo_confirm:'))
async def demo_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Подтверждение демо-оплаты и выдача subscription или продление ключа."""
    from database.requests import (
        find_order_by_order_id, complete_order, get_tariff_by_id,
        create_initial_vpn_key, update_payment_key_id, extend_vpn_key,
        get_active_servers, update_vpn_key_config
    )
    from bot.utils.key_sender import send_subscription_link
    from bot.handlers.user.keys import show_key_details
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    from bot.services.vpn_api import get_client
    import uuid
    
    order_id = callback.data.split(':')[1]
    
    order = find_order_by_order_id(order_id)
    if not order:
        await callback.answer('❌ Заказ не найден', show_alert=True)
        return
    
    tariff = get_tariff_by_id(order['tariff_id'])
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    
    try:
        # Проверяем, это продление или новый ключ
        is_renewal = order.get('vpn_key_id') is not None
        
        if is_renewal:
            # Продление существующего ключа
            key_id = order['vpn_key_id']
            days = tariff['duration_days']
            
            if extend_vpn_key(key_id, days):
                complete_order(order_id)
                
                logger.info(f"Демо-оплата (продление) завершена: order_id={order_id}, key_id={key_id}, user={callback.from_user.id}")
                
                # Восстанавливаем лимит трафика
                from bot.services.vpn_api import push_key_to_panel, restore_traffic_limit_in_db
                restore_traffic_limit_in_db(key_id)
                await push_key_to_panel(key_id, reset_traffic=True)
                
                # Начисляем реферальное вознаграждение
                from bot.services.billing import process_referral_reward
                user_internal_id = order['user_id']
                price_rub = float(tariff.get('price_rub') or 0)
                amount_cents = int(price_rub * 100)  # Конвертируем рубли в копейки
                await process_referral_reward(user_internal_id, days, amount_cents, 'demo')
                
                # Удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                
                # Отправляем сообщение об успехе
                success_message = (
                    "🎉 <b>Демо-оплата успешна!</b>\n\n"
                    f"✅ Ключ продлён на {days} дней\n"
                    f"📦 Тариф: {escape_html(tariff['name'])}\n\n"
                    "👇 <b>Информация о ключе:</b>"
                )
                
                # Показываем детали ключа
                await show_key_details(
                    telegram_id=callback.from_user.id,
                    key_id=key_id,
                    message=callback.message,
                    is_callback=False,
                    prepend_text=success_message
                )
                
                await callback.answer("✅ Оплата прошла успешно!")
            else:
                logger.error(f"Не удалось продлить ключ {key_id} после демо-оплаты!")
                await callback.answer("❌ Ошибка продления ключа", show_alert=True)
        else:
            # Создание нового ключа
            traffic_limit_bytes = (tariff.get('traffic_limit_gb', 0) or 0) * 1024 ** 3
            key_id = create_initial_vpn_key(
                user_id=order['user_id'],
                tariff_id=order['tariff_id'],
                days=tariff['duration_days'],
                traffic_limit=traffic_limit_bytes
            )
            
            # Обновляем заказ
            update_payment_key_id(order_id, key_id)
            
            logger.info(f"Демо-оплата: создан черновик ключа key_id={key_id}, начинаем настройку на панели...")
            
            # АВТОМАТИЧЕСКАЯ НАСТРОЙКА КЛЮЧА НА ПАНЕЛИ
            try:
                # Получаем первый доступный сервер
                servers = get_active_servers()
                if not servers:
                    raise Exception("Нет доступных серверов")
                
                server = servers[0]  # Берем первый активный сервер
                server_id = server['id']
                
                logger.info(f"Выбран сервер: {server['name']} (ID: {server_id})")
                
                # Подключаемся к панели
                client = await get_client(server_id)
                inbounds = await client.get_inbounds()
                
                if not inbounds:
                    raise Exception(f"На сервере {server['name']} нет доступных протоколов")
                
                # Берем первый inbound
                inbound = inbounds[0]
                inbound_id = inbound['id']
                
                logger.info(f"Выбран inbound: {inbound.get('remark', 'N/A')} (ID: {inbound_id}, protocol: {inbound.get('protocol', 'N/A')})")
                
                # Генерируем уникальный email для панели
                telegram_id = callback.from_user.id
                username = callback.from_user.username
                base = f"user_{username}" if username else f"user_{telegram_id}"
                suffix = uuid.uuid4().hex[:5]
                panel_email = f'{base}_{suffix}'
                
                # Получаем flow для inbound
                flow = await client.get_inbound_flow(inbound_id)
                
                # Создаем клиента на панели
                limit_gb = (tariff.get('traffic_limit_gb', 0) or 0)
                days = tariff['duration_days']
                
                logger.info(f"Создаем клиента на панели: email={panel_email}, limit={limit_gb}GB, days={days}")
                
                res = await client.add_client(
                    inbound_id=inbound_id,
                    email=panel_email,
                    total_gb=limit_gb,
                    expire_days=days,
                    limit_ip=1,
                    enable=True,
                    tg_id=str(telegram_id),
                    flow=flow
                )
                
                client_uuid = res['uuid']
                
                logger.info(f"Клиент создан на панели: uuid={client_uuid}")
                
                # Обновляем ключ в БД с данными панели
                update_vpn_key_config(
                    key_id=key_id,
                    server_id=server_id,
                    panel_inbound_id=inbound_id,
                    panel_email=panel_email,
                    client_uuid=client_uuid
                )
                
                logger.info(f"Ключ {key_id} успешно настроен на панели")
                
            except Exception as e:
                logger.error(f"Ошибка настройки ключа на панели: {e}", exc_info=True)
                # Продолжаем выполнение - ключ создан, но не настроен
                # Пользователь сможет настроить его позже через интерфейс
            
            # Завершаем заказ
            complete_order(order_id)
            
            # Начисляем реферальное вознаграждение
            from bot.services.billing import process_referral_reward
            user_internal_id = order['user_id']
            days = tariff['duration_days']
            price_rub = float(tariff.get('price_rub') or 0)
            amount_cents = int(price_rub * 100)  # Конвертируем рубли в копейки
            await process_referral_reward(user_internal_id, days, amount_cents, 'demo')
            
            # Удаляем предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass
            
            # Отправляем сообщение об успехе
            success_message = (
                "🎉 <b>Демо-оплата успешна!</b>\n\n"
                f"✅ Подписка активирована\n"
                f"📦 Тариф: {escape_html(tariff['name'])}\n"
                f"📅 Срок: {tariff['duration_days']} дней\n\n"
                "👇 <b>Ваша подписка готова!</b>"
            )
            
            await callback.message.answer(success_message, parse_mode="HTML")
            
            # Создаем клавиатуру
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📄 Инструкция", callback_data="device_instructions"))
            builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
            
            # Сразу показываем subscription ссылку с QR-кодом
            await send_subscription_link(callback, key_id, builder.as_markup())
            
            await callback.answer("✅ Оплата прошла успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при демо-оплате: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
