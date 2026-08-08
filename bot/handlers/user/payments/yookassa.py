import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from bot.utils.text import escape_html, safe_edit_or_send
from config import ADMIN_IDS
from bot.handlers.user.payments.base import finalize_payment_ui

logger = logging.getLogger(__name__)

router = Router()


def _can_save_payment_method(order: dict) -> bool:
    """Only request provider-side saving after YooKassa enables recurring payments."""
    from database.requests import get_setting
    setting = 'yookassa_sbp_recurring_enabled' if order.get('payment_type') == 'yookassa_qr' else 'yookassa_recurring_enabled'
    return bool(order.get('auto_renew_requested')) and get_setting(setting, '0') == '1'


@router.callback_query(F.data.startswith('sc:'))
async def sbp_recurring_confirmation(callback: CallbackQuery):
    """Ask for explicit recurring consent immediately before an SBP payment."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from config import SUBSCRIPTION_URL

    parts = callback.data.split(':')
    if len(parts) != 4:
        await callback.answer('Не удалось открыть подтверждение оплаты', show_alert=True)
        return
    _, key_id_raw, tariff_id_raw, order_id = parts
    key_id = int(key_id_raw)
    tariff_id = int(tariff_id_raw)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text='✅ Продолжить с автопродлением',
        callback_data=f'sr:1:{key_id}:{tariff_id}:{order_id}',
        style='primary',
    ))
    builder.row(InlineKeyboardButton(
        text='Отключить и оплатить один раз',
        callback_data=f'sr:0:{key_id}:{tariff_id}:{order_id}',
    ))
    builder.row(InlineKeyboardButton(
        text='📄 Пользовательское соглашение',
        url=f"{SUBSCRIPTION_URL.rstrip('/')}/legal/user-agreement",
    ))
    builder.row(InlineKeyboardButton(
        text='← Назад',
        callback_data=f'payment_return:{key_id}:{tariff_id}:{order_id}',
    ))
    await safe_edit_or_send(
        callback.message,
        '<b>ArcVPN</b>\n\n'
        '🔁 <b>Оставить автопродление?</b>\n\n'
        'С автопродлением доступ не прервётся: следующий платёж будет списан автоматически перед окончанием подписки. '
        'Отключить автопродление и удалить сохранённую карту можно самостоятельно в настройках ArcVPN.\n\n'
        '<blockquote>Нажимая «Продолжить с автопродлением», вы поручаете ArcVPN выполнять регулярные списания '
        'по выбранному тарифу и соглашаетесь с Пользовательским соглашением.</blockquote>',
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith('sr:'))
async def sbp_recurring_choice(callback: CallbackQuery):
    """Persist consent and continue to the existing QR creation flow."""
    from database.requests import get_setting, set_order_auto_renew

    parts = callback.data.split(':')
    if len(parts) != 5:
        await callback.answer('Не удалось продолжить оплату', show_alert=True)
        return
    _, enabled_raw, key_id_raw, tariff_id_raw, order_id = parts
    enabled = enabled_raw == '1'
    if enabled and get_setting('yookassa_sbp_recurring_enabled', '0') != '1':
        await callback.answer(
            'ЮKassa ещё согласовывает автоплатежи для ArcVPN. Пока выберите «Оплатить один раз».',
            show_alert=True,
        )
        return
    if not set_order_auto_renew(order_id, enabled):
        await callback.answer('Заказ уже завершён или не найден', show_alert=True)
        return

    key_id = int(key_id_raw)
    tariff_id = int(tariff_id_raw)
    next_data = (
        f'renew_pay_qr:{key_id}:{tariff_id}:{order_id}'
        if key_id else
        f'pay_qr_tariff:{tariff_id}:{order_id}'
    )
    forwarded = callback.model_copy(update={'data': next_data})
    if key_id:
        await renew_qr_create(forwarded)
    else:
        await pay_qr_handler(forwarded)

@router.callback_query(F.data.startswith('pay_cards'))
async def pay_cards_handler(callback: CallbackQuery):
    """Обработчик оплаты картой - создает инвойс напрямую если тариф уже выбран."""
    from aiogram.types import LabeledPrice
    from database.requests import (
        get_tariff_by_id, get_user_internal_id, get_setting, get_all_tariffs,
        prepare_payment_order
    )
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    from aiogram.exceptions import TelegramBadRequest
    
    # Парсим callback_data
    parts = callback.data.split(':')
    
    # Если формат pay_cards_tariff:tariff_id:order_id - тариф уже выбран
    if len(parts) >= 3 and parts[0] == 'pay_cards_tariff':
        tariff_id = int(parts[1])
        order_id = parts[2] if len(parts) > 2 else None
        
        tariff = get_tariff_by_id(tariff_id)
        if not tariff:
            await callback.answer('❌ Тариф не найден', show_alert=True)
            return
        
        user_id = get_user_internal_id(callback.from_user.id)
        provider_token = get_setting('cards_provider_token', '')
        
        if not provider_token:
            await callback.answer('❌ Провайдер платежей не настроен', show_alert=True)
            return
        
        days = tariff['duration_days']
        
        if not user_id:
            await callback.answer('❌ Ошибка пользователя', show_alert=True)
            return

        prepared_order = prepare_payment_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='cards',
            order_id=order_id,
        )
        order_id = prepared_order['order_id']
        price_rub = float(tariff.get('price_rub') or 0)
        discount_rub = prepared_order.get('discount_rub', 0) or 0
        if discount_rub > 0:
            price_rub = max(0, price_rub - discount_rub)
            logger.info(f"Применена скидка промокода: {discount_rub} руб, итоговая цена: {price_rub} руб")
        
        price_kopecks = int(round(price_rub * 100))
        
        if price_kopecks <= 0:
            await callback.answer('❌ Ошибка: цена тарифа в рублях не задана.', show_alert=True)
            return
        
        try:
            bot_info = await callback.bot.get_me()
            bot_name = bot_info.first_name
            
            await callback.message.answer_invoice(
                title=bot_name,
                description=f"Оплата тарифа «{tariff['name']}» ({days} дн.).",
                payload=f'vpn_key:{order_id}',
                provider_token=provider_token,
                currency='RUB',
                prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_kopecks)],
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text=f'💳 Оплатить {price_rub} ₽', pay=True)
                ).row(
                    InlineKeyboardButton(text='❌ Отмена', callback_data=f'pay_cards:{order_id}')
                ).as_markup()
            )
            
            await callback.message.delete()
            await callback.answer()
            
        except TelegramBadRequest as e:
            if 'CURRENCY_TOTAL_AMOUNT_INVALID' in str(e):
                logger.warning(f"Ошибка платежа (CARDS): сумма меньше лимита. Тариф ID {tariff['id']}, Цена {price_rub} руб.")
                await callback.answer('❌ Сумма тарифа меньше допустимого лимита эквайринга.', show_alert=True)
                return
            logger.exception('Ошибка при отправке инвойса картой.')
            raise e
    
    else:
        # Старая логика - показываем выбор тарифа (для обратной совместимости)
        order_id = parts[1] if len(parts) > 1 else None
        tariffs = get_all_tariffs(include_hidden=False)
        
        if not tariffs:
            await safe_edit_or_send(
                callback.message,
                '💳 <b>Оплата картой</b>\n\n😔 Нет доступных тарифов.\n\nПопробуйте позже.',
                reply_markup=home_only_kb()
            )
            await callback.answer()
            return
        
        await safe_edit_or_send(
            callback.message,
            '💳 <b>Оплата картой</b>\n\nВыберите тариф:',
            reply_markup=tariff_select_kb(tariffs, order_id=order_id, is_cards=True)
        )
        await callback.answer()

@router.callback_query(F.data.startswith('cards_pay:'))
async def pay_cards_invoice(callback: CallbackQuery):
    """Создание инвойса для оплаты Картой (Новый ключ)."""
    from aiogram.types import LabeledPrice
    from database.requests import get_tariff_by_id, get_user_internal_id, get_setting, prepare_payment_order
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    user_id = get_user_internal_id(callback.from_user.id)
    provider_token = get_setting('cards_provider_token', '')
    if not provider_token:
        await callback.answer('❌ Провайдер платежей не настроен', show_alert=True)
        return
    days = tariff['duration_days']
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='cards',
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    price_rub = float(tariff.get('price_rub') or 0)
    discount_rub = prepared_order.get('discount_rub', 0) or 0
    if discount_rub > 0:
        price_rub = max(0, price_rub - discount_rub)
    price_kopecks = int(round(price_rub * 100))
    if price_kopecks <= 0:
        await callback.answer('❌ Ошибка: цена тарифа в рублях не задана.', show_alert=True)
        return
    from aiogram.exceptions import TelegramBadRequest
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.first_name
        await callback.message.answer_invoice(title=bot_name, description=f"Оплата тарифа «{tariff['name']}» ({days} дн.).", payload=f'vpn_key:{order_id}', provider_token=provider_token, currency='RUB', prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_kopecks)], reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text=f'💳 Оплатить {price_rub} ₽', pay=True)).row(InlineKeyboardButton(text='❌ Отмена', callback_data=f'pay_cards:{order_id}')).as_markup())
    except TelegramBadRequest as e:
        if 'CURRENCY_TOTAL_AMOUNT_INVALID' in str(e):
            logger.warning(f"Ошибка платежа (CARDS): Неправильная сумма (меньше лимита ~$1). Тариф: ID {tariff['id']}, Цена {price_rub} руб. Подробности: {e}")
            await callback.answer('❌ Ошибка платежной системы. К сожалению, сумма тарифа меньше допустимого лимита эквайринга.', show_alert=True)
            return
        logger.exception('Ошибка при отправке инвойса картой (новый ключ).')
        raise e
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith('renew_cards_tariff:'))
async def renew_cards_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для продления (Картой)."""
    from database.requests import get_key_details_for_user, get_all_tariffs
    from bot.keyboards.user import renew_tariff_select_kb
    parts = callback.data.split(':')
    key_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    telegram_id = callback.from_user.id
    key = get_key_details_for_user(key_id, telegram_id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    from bot.utils.groups import get_tariffs_for_renewal
    tariffs = get_tariffs_for_renewal(key.get('tariff_id', 0))
    if not tariffs:
        await callback.answer('Нет доступных тарифов', show_alert=True)
        return
    await safe_edit_or_send(callback.message, f"💳 <b>Оплата картой</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:", reply_markup=renew_tariff_select_kb(tariffs, key_id, order_id=order_id, is_cards=True))
    await callback.answer()

@router.callback_query(F.data.startswith('renew_pay_cards:'))
async def renew_cards_invoice(callback: CallbackQuery):
    """Инвойс для продления (Картой)."""
    from aiogram.types import LabeledPrice
    from database.requests import get_tariff_by_id, get_user_internal_id, get_key_details_for_user, get_setting, prepare_payment_order
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('Ошибка тарифа или ключа', show_alert=True)
        return
    user_id = get_user_internal_id(callback.from_user.id)
    provider_token = get_setting('cards_provider_token', '')
    if not provider_token:
        await callback.answer('❌ Провайдер платежей не настроен', show_alert=True)
        return
    if not user_id:
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='cards',
        vpn_key_id=key_id,
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    price_rub = float(tariff.get('price_rub') or 0)
    discount_rub = prepared_order.get('discount_rub', 0) or 0
    if discount_rub > 0:
        price_rub = max(0, price_rub - discount_rub)
    price_kopecks = int(round(price_rub * 100))
    if price_kopecks <= 0:
        await callback.answer('❌ Ошибка: цена тарифа в рублях не задана.', show_alert=True)
        return
    from aiogram.exceptions import TelegramBadRequest
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.first_name
        await callback.message.answer_invoice(title=bot_name, description=f"Продление ключа «{key['display_name']}»: {tariff['name']}.", payload=f'renew:{order_id}', provider_token=provider_token, currency='RUB', prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_kopecks)], reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text=f"💳 Оплатить {price_rub} ₽", pay=True)).row(InlineKeyboardButton(text='❌ Отмена', callback_data=f'renew_invoice_cancel:{key_id}:{tariff_id}:{order_id}')).as_markup())
    except TelegramBadRequest as e:
        if 'CURRENCY_TOTAL_AMOUNT_INVALID' in str(e):
            logger.warning(f"Ошибка платежа (CARDS_RENEW): Неправильная сумма (меньше лимита ~$1). Тариф: ID {tariff['id']}, Цена {price_rub} руб. Подробности: {e}")
            await callback.answer('❌ Ошибка платежной системы. К сожалению, сумма тарифа меньше допустимого лимита эквайринга.', show_alert=True)
            return
        logger.exception('Ошибка при отправке инвойса картой (продление ключа).')
        raise e
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith('pay_qr'))
async def pay_qr_handler(callback: CallbackQuery):
    """Обработчик QR-оплаты - создает платеж напрямую если тариф уже выбран."""
    from database.requests import (
        get_tariff_by_id, get_user_internal_id, save_yookassa_payment_id,
        get_all_tariffs, prepare_payment_order
    )
    from bot.services.billing import create_yookassa_qr_payment
    from bot.keyboards.user import yookassa_qr_kb, tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    
    # Парсим callback_data
    parts = callback.data.split(':')
    existing_order_id = parts[1] if len(parts) > 1 else None
    
    # Если формат pay_qr_tariff:tariff_id:order_id - тариф уже выбран
    if len(parts) >= 3 and parts[0] == 'pay_qr_tariff':
        tariff_id = int(parts[1])
        order_id = parts[2] if len(parts) > 2 and parts[2] != 'None' else None
        
        tariff = get_tariff_by_id(tariff_id)
        if not tariff:
            await callback.answer('❌ Тариф не найден', show_alert=True)
            return
        
        price_rub = float(tariff.get('price_rub') or 0)
        if price_rub <= 0:
            await callback.answer('❌ Цена в рублях не задана для этого тарифа', show_alert=True)
            return
        
        user_id = get_user_internal_id(callback.from_user.id)
        if not user_id:
            await callback.answer('❌ Ошибка пользователя', show_alert=True)
            return
        
        prepared_order = prepare_payment_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='yookassa_qr',
            order_id=order_id,
        )
        order_id = prepared_order['order_id']
        discount_rub = prepared_order.get('discount_rub', 0) or 0
        if discount_rub > 0:
            price_rub = max(0, price_rub - discount_rub)
            logger.info(f"Применена скидка промокода: {discount_rub} руб, итоговая цена: {price_rub} руб")
        
        try:
            # Создаем платеж в ЮКассе
            bot_info = await callback.bot.get_me()
            bot_name = bot_info.username
            
            result = await create_yookassa_qr_payment(
                amount_rub=price_rub,
                order_id=order_id,
                description=f"Тариф {tariff['name']}",
                bot_name=bot_name,
                save_payment_method=_can_save_payment_method(prepared_order),
            )
            
            payment_id = result['yookassa_payment_id']
            qr_url = result.get('qr_url', '')
            qr_image_data = result.get('qr_image_data')
            
            save_yookassa_payment_id(order_id, payment_id)
            
            text = (
                f"📱 <b>QR-оплата (Карта/СБП)</b>\n\n"
                f"📦 Тариф: <b>{escape_html(tariff['name'])}</b>\n"
                f"💵 Сумма: <b>{price_rub} ₽</b>\n\n"
                f"Отсканируйте QR-код камерой телефона или нажмите кнопку «Оплатить».\n\n"
                f"После оплаты нажмите «Я оплатил»."
            )
            if discount_rub > 0:
                text = text.replace(
                    f"💵 Сумма: <b>{price_rub} ₽</b>",
                    f"💵 Цена: <s>{float(tariff.get('price_rub') or 0)} ₽</s> → <b>{price_rub} ₽</b>\n🎟️ Скидка по промокоду: <b>{discount_rub} ₽</b>"
                )
            
            from aiogram.types import BufferedInputFile
            photo = BufferedInputFile(qr_image_data, filename='qr.png')
            
            await safe_edit_or_send(
                callback.message,
                text,
                photo=photo,
                reply_markup=yookassa_qr_kb(
                    order_id,
                    back_callback=f'payment_return:0:{tariff_id}:{order_id}',
                    qr_url=qr_url,
                ),
                force_new=True
            )
            await callback.answer()
            
        except Exception as e:
            logger.exception(f'Ошибка создания QR ЮКасса: {e}')
            await callback.answer(f'❌ Ошибка создания платежа: {e}', show_alert=True)

    else:
        # Совместимость со старыми сообщениями: сразу открываем новый выбор тарифа.
        from bot.utils.payment_flow_ui import show_tariff_selection_screen
        await show_tariff_selection_screen(
            callback.message,
            callback.from_user.id,
            order_id=existing_order_id,
        )
        await callback.answer()

@router.callback_query(F.data.startswith('qr_pay:'))
async def qr_pay_create(callback: CallbackQuery):
    """Создаёт QR-платёж ЮКасса для нового ключа и отправляет QR-фото."""
    from database.requests import get_tariff_by_id, get_user_internal_id, save_yookassa_payment_id, prepare_payment_order
    from bot.services.billing import create_yookassa_qr_payment
    from bot.keyboards.user import yookassa_qr_kb
    from bot.keyboards.admin import home_only_kb
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub <= 0:
        await callback.answer('❌ Цена в рублях не задана для этого тарифа', show_alert=True)
        return
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Пользователь не найден', show_alert=True)
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='yookassa_qr',
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    discount_rub = prepared_order.get('discount_rub', 0) or 0
    if discount_rub > 0:
        price_rub = max(0, price_rub - discount_rub)
    await safe_edit_or_send(callback.message, '⏳ Создаём QR-код для оплаты...')
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.username
        description = f"Покупка «{tariff['name']}» — {tariff['duration_days']} дней"
        result = await create_yookassa_qr_payment(
            amount_rub=price_rub,
            order_id=order_id,
            description=description,
            bot_name=bot_name,
            save_payment_method=_can_save_payment_method(prepared_order),
        )
        save_yookassa_payment_id(order_id, result['yookassa_payment_id'])
        qr_image_data = result.get('qr_image_data')
        qr_url = result.get('qr_url', '')
        if not qr_image_data or not qr_url:
            await safe_edit_or_send(callback.message, '❌ ЮКасса не вернула данные для оплаты. Попробуйте позже.', reply_markup=home_only_kb())
            return
        text = f"📱 <b>QR-код для оплаты</b>\n\n💳 <b>Тариф:</b> {escape_html(tariff['name'])}\n💰 <b>Сумма:</b> {int(price_rub)} ₽\n⏳ <b>Срок:</b> {tariff['duration_days']} дней\n\nОтсканируйте QR-код банковским приложением (СБП) или перейдите по <a href=\"{qr_url}\">ссылке на оплату</a>.\n\n<i>После оплаты нажмите «✅ Я оплатил».</i>"
        if discount_rub > 0:
            text = text.replace(
                f"💰 <b>Сумма:</b> {int(price_rub)} ₽",
                f"💰 <b>Цена:</b> <s>{int(float(tariff.get('price_rub') or 0))} ₽</s> → {int(price_rub)} ₽\n🎟️ <b>Скидка по промокоду:</b> {discount_rub} ₽"
            )
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(qr_image_data, filename='qr.png')
        await safe_edit_or_send(
            callback.message,
            text,
            photo=photo,
            reply_markup=yookassa_qr_kb(
                order_id,
                back_callback=f'payment_return:0:{tariff_id}:{order_id}',
                qr_url=qr_url,
            ),
            force_new=True,
        )
    except Exception as e:
        logger.exception(f'Ошибка создания QR ЮКасса: {e}')
        await safe_edit_or_send(callback.message, f'❌ <b>Ошибка создания QR</b>\n\n<i>{escape_html(str(e))}</i>\n\nПопробуйте другой способ оплаты.', reply_markup=home_only_kb())
    await callback.answer()

@router.callback_query(F.data.startswith('check_yookassa_qr:'))
async def check_yookassa_payment(callback: CallbackQuery, state: FSMContext):
    """
    Проверяет статус QR-платежа ЮКасса по нажатию «✅ Я оплатил».
    При успехе — делегирует обработку в complete_payment_flow().
    """
    from database.requests import find_order_by_order_id, is_order_already_paid, update_payment_type
    from bot.services.billing import check_yookassa_payment_status
    from bot.keyboards.admin import home_only_kb
    order_id = callback.data.split(':', 1)[1]
    if is_order_already_paid(order_id):
        order = find_order_by_order_id(order_id)
        if order and order.get('fulfillment_status') == 'applied':
            await finalize_payment_ui(callback.message, state, '✅ Оплата уже была обработана ранее.', order, user_id=callback.from_user.id)
            await callback.answer()
            return
    order = find_order_by_order_id(order_id)
    if not order:
        await callback.answer('❌ Ордер не найден', show_alert=True)
        return
    yookassa_payment_id = order.get('yookassa_payment_id')
    if not yookassa_payment_id:
        await callback.answer('⚠️ Нет данных о платеже. Попробуйте чуть позже.', show_alert=True)
        return
    await callback.answer('🔍 Проверяем платёж...')
    try:
        status = await check_yookassa_payment_status(yookassa_payment_id)
    except Exception as e:
        logger.error(f'Ошибка проверки статуса ЮКасса {yookassa_payment_id}: {e}')
        await safe_edit_or_send(callback.message, '❌ Не удалось проверить статус платежа. Попробуйте позже.', reply_markup=home_only_kb(), force_new=True)
        return
    if status == 'succeeded':
        update_payment_type(order_id, 'yookassa_qr')
        # Определяем сумму для реферального вознаграждения
        state_data = await state.get_data()
        remaining_cents = state_data.get('remaining_cents', 0)
        if remaining_cents > 0:
            referral_amount = remaining_cents
        else:
            # Обычная QR-оплата без частичной — берём цену тарифа в копейках рублей
            from database.requests import get_tariff_by_id
            _tariff = get_tariff_by_id(order.get('tariff_id'))
            referral_amount = int((_tariff.get('price_rub', 0) or 0) * 100) if _tariff else 0
        logger.info(f"Yookassa QR referral: order={order_id}, referral_amount={referral_amount}")
        # Удаляем QR-фото перед показом результата
        try:
            await callback.message.delete()
        except Exception:
            pass
        from bot.services.billing import complete_payment_flow
        await complete_payment_flow(
            order_id=order_id,
            message=callback.message,
            state=state,
            telegram_id=callback.from_user.id,
            payment_type='yookassa_qr',
            referral_amount=referral_amount
        )
    elif status == 'canceled':
        await safe_edit_or_send(callback.message, '❌ <b>Платёж отменён</b>\n\nПохоже, платёж был отменён или истёк срок QR-кода.\nПопробуйте снова выбрать тариф.', reply_markup=home_only_kb(), force_new=True)
    else:
        await safe_edit_or_send(callback.message, '⏳ <b>Платёж ещё не поступил</b>\n\nОплатите QR-код и нажмите «✅ Я оплатил» снова.\n\n<i>Если только что оплатили — подождите пару секунд.</i>', force_new=True)

@router.callback_query(F.data.startswith('renew_qr_tariff:'))
async def renew_qr_select_tariff(callback: CallbackQuery):
    """Compatibility route: old QR buttons now open the modern payment screen."""
    from database.requests import find_order_by_order_id, get_key_details_for_user
    from bot.utils.payment_flow_ui import show_payment_method_selection_screen, show_tariff_selection_screen
    parts = callback.data.split(':')
    key_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not key:
        await callback.answer('❌ Ключ не найден', show_alert=True)
        return
    order = find_order_by_order_id(order_id) if order_id else None
    if order and order.get('tariff_id'):
        await show_payment_method_selection_screen(
            callback.message,
            callback.from_user.id,
            int(order['tariff_id']),
            key_id=key_id,
            order_id=order_id,
        )
    else:
        await show_tariff_selection_screen(callback.message, callback.from_user.id, key_id=key_id)
    await callback.answer()

@router.callback_query(F.data.startswith('renew_pay_qr:'))
async def renew_qr_create(callback: CallbackQuery):
    """Создаёт QR-платёж ЮКасса для продления ключа."""
    from database.requests import get_tariff_by_id, get_user_internal_id, save_yookassa_payment_id, get_key_details_for_user, prepare_payment_order
    from bot.services.billing import create_yookassa_qr_payment
    from bot.keyboards.user import yookassa_qr_kb
    from bot.keyboards.admin import home_only_kb
    parts = callback.data.split(':')
    key_id = int(parts[1])
    tariff_id = int(parts[2])
    order_id = parts[3] if len(parts) > 3 else None
    tariff = get_tariff_by_id(tariff_id)
    key = get_key_details_for_user(key_id, callback.from_user.id)
    if not tariff or not key:
        await callback.answer('❌ Ошибка тарифа или ключа', show_alert=True)
        return
    price_rub = float(tariff.get('price_rub') or 0)
    if price_rub <= 0:
        await callback.answer('❌ Цена в рублях не задана', show_alert=True)
        return
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Пользователь не найден', show_alert=True)
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='yookassa_qr',
        vpn_key_id=key_id,
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    discount_rub = prepared_order.get('discount_rub', 0) or 0
    if discount_rub > 0:
        price_rub = max(0, price_rub - discount_rub)
    await safe_edit_or_send(callback.message, '⏳ Создаём QR-код для оплаты...')
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.username
        description = f"Продление Ключа «{key['display_name']}»: «{tariff['name']}» ({tariff['duration_days']} дн.)"
        result = await create_yookassa_qr_payment(
            amount_rub=price_rub,
            order_id=order_id,
            description=description,
            bot_name=bot_name,
            save_payment_method=_can_save_payment_method(prepared_order),
        )
        save_yookassa_payment_id(order_id, result['yookassa_payment_id'])
        qr_image_data = result.get('qr_image_data')
        qr_url = result.get('qr_url', '')
        if not qr_image_data or not qr_url:
            await safe_edit_or_send(callback.message, '❌ ЮКасса не вернула данные для оплаты. Попробуйте позже.', reply_markup=home_only_kb())
            return
        text = f"📱 <b>QR-код для оплаты</b>\n\n🔑 <b>Ключ:</b> {escape_html(key['display_name'])}\n💳 <b>Тариф:</b> {escape_html(tariff['name'])}\n💰 <b>Сумма:</b> {int(price_rub)} ₽\n⏳ <b>Продление:</b> +{tariff['duration_days']} дней\n\nОтсканируйте QR-код банковским приложением (СБП) или перейдите по <a href=\"{qr_url}\">ссылке на оплату</a>.\n\n<i>После оплаты нажмите «✅ Я оплатил».</i>"
        if discount_rub > 0:
            text = text.replace(
                f"💰 <b>Сумма:</b> {int(price_rub)} ₽",
                f"💰 <b>Цена:</b> <s>{int(float(tariff.get('price_rub') or 0))} ₽</s> → {int(price_rub)} ₽\n🎟️ <b>Скидка по промокоду:</b> {discount_rub} ₽"
            )
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(qr_image_data, filename='qr.png')
        await safe_edit_or_send(
            callback.message,
            text,
            photo=photo,
            reply_markup=yookassa_qr_kb(
                order_id,
                back_callback=f'payment_return:{key_id}:{tariff_id}:{order_id}',
                qr_url=qr_url,
            ),
            force_new=True,
        )
    except Exception as e:
        logger.exception(f'Ошибка QR ЮКасса (продление): {e}')
        await safe_edit_or_send(callback.message, f'❌ <b>Ошибка создания QR</b>\n\n<i>{escape_html(str(e))}</i>', reply_markup=home_only_kb())
    await callback.answer()
