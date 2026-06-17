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

@router.callback_query(F.data.startswith('renew_stars_tariff:'))
async def renew_stars_select_tariff(callback: CallbackQuery):
    """Выбор тарифа для продления (Stars)."""
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
    await safe_edit_or_send(callback.message, f"⭐ <b>Оплата звёздами</b>\n\n🔑 Ключ: <b>{escape_html(key['display_name'])}</b>\n\nВыберите тариф для продления:", reply_markup=renew_tariff_select_kb(tariffs, key_id, order_id=order_id))
    await callback.answer()

@router.callback_query(F.data.startswith('renew_pay_stars:'))
async def renew_stars_invoice(callback: CallbackQuery):
    """Инвойс для продления (Stars)."""
    from aiogram.types import LabeledPrice
    from database.requests import get_tariff_by_id, get_user_internal_id, get_key_details_for_user, prepare_payment_order
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
    if not user_id:
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='stars',
        vpn_key_id=key_id,
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    bot_info = await callback.bot.get_me()
    bot_name = bot_info.first_name
    await callback.message.answer_invoice(title=bot_name, description=f"Продление ключа «{key['display_name']}»: {tariff['name']}.", payload=f'renew:{order_id}', currency='XTR', prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=tariff['price_stars'])], reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text=f"⭐️ Оплатить {tariff['price_stars']} XTR", pay=True)).row(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'renew_invoice_cancel:{key_id}:{tariff_id}')).as_markup())
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith('pay_stars'))
async def pay_stars_handler(callback: CallbackQuery):
    """Обработчик оплаты Stars - создает инвойс напрямую если тариф уже выбран."""
    from aiogram.types import LabeledPrice
    from database.requests import (
        get_tariff_by_id, get_user_internal_id, get_all_tariffs, prepare_payment_order
    )
    from bot.keyboards.user import tariff_select_kb
    from bot.keyboards.admin import home_only_kb
    
    # Парсим callback_data
    parts = callback.data.split(':')
    
    # Если формат pay_stars_tariff:tariff_id:order_id - тариф уже выбран
    if len(parts) >= 3 and parts[0] == 'pay_stars_tariff':
        tariff_id = int(parts[1])
        order_id = parts[2] if len(parts) > 2 and parts[2] != 'None' else None
        
        tariff = get_tariff_by_id(tariff_id)
        if not tariff:
            await callback.answer('❌ Тариф не найден', show_alert=True)
            return
        
        days = tariff['duration_days']
        
        user_id = get_user_internal_id(callback.from_user.id)
        if not user_id:
            await callback.answer('❌ Ошибка пользователя', show_alert=True)
            return
        
        prepared_order = prepare_payment_order(
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='stars',
            order_id=order_id,
        )
        order_id = prepared_order['order_id']
        
        # Получаем финальную цену с учетом промокода
        base_price_stars = tariff.get('price_stars', 0)
        
        if not base_price_stars or base_price_stars <= 0:
            await callback.answer('❌ Цена в Stars не задана для этого тарифа', show_alert=True)
            return
        
        # Применяем скидку от промокода если есть
        if prepared_order:
            discount_rub = prepared_order.get('discount_rub', 0) or 0
            if discount_rub > 0:
                # Конвертируем скидку в Stars (примерно 1 Star ≈ 1.3 RUB)
                discount_stars = int(discount_rub / 1.3)
                price_stars = max(1, base_price_stars - discount_stars)
                logger.info(f"Применена скидка промокода: {discount_rub} руб = {discount_stars} Stars, итого: {price_stars} Stars")
            else:
                price_stars = base_price_stars
        else:
            price_stars = base_price_stars
        
        try:
            bot_info = await callback.bot.get_me()
            bot_name = bot_info.first_name
            
            await callback.message.answer_invoice(
                title=bot_name,
                description=f"Оплата тарифа «{tariff['name']}» ({days} дн.).",
                payload=f'vpn_key:{order_id}',
                provider_token='',
                currency='XTR',
                prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_stars)],
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text=f'⭐ Оплатить {price_stars} звёзд', pay=True)
                ).row(
                    InlineKeyboardButton(text='❌ Отмена', callback_data='buy_key')
                ).as_markup()
            )
            
            await callback.message.delete()
            await callback.answer()
            
        except Exception as e:
            logger.exception('Ошибка при отправке инвойса Stars.')
            await callback.answer('❌ Ошибка создания инвойса', show_alert=True)
    
    else:
        # Старая логика - показываем выбор тарифа
        order_id = parts[1] if len(parts) > 1 else None
        tariffs = get_all_tariffs(include_hidden=False)
        
        if not tariffs:
            await safe_edit_or_send(
                callback.message,
                '⭐ <b>Оплата звёздами</b>\n\n😔 Нет доступных тарифов.\n\nПопробуйте позже.',
                reply_markup=home_only_kb()
            )
            await callback.answer()
            return
        
        await safe_edit_or_send(
            callback.message,
            '⭐ <b>Оплата звёздами</b>\n\nВыберите тариф:',
            reply_markup=tariff_select_kb(tariffs, order_id=order_id)
        )
        await callback.answer()

@router.callback_query(F.data.startswith('stars_pay:'))
async def pay_stars_invoice(callback: CallbackQuery):
    """Создание инвойса для оплаты Stars."""
    from aiogram.types import LabeledPrice
    from database.requests import get_tariff_by_id, get_user_internal_id, prepare_payment_order
    parts = callback.data.split(':')
    tariff_id = int(parts[1])
    order_id = parts[2] if len(parts) > 2 else None
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer('❌ Тариф не найден', show_alert=True)
        return
    days = tariff['duration_days']
    user_id = get_user_internal_id(callback.from_user.id)
    if not user_id:
        await callback.answer('❌ Ошибка пользователя', show_alert=True)
        return
    prepared_order = prepare_payment_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type='stars',
        order_id=order_id,
    )
    order_id = prepared_order['order_id']
    try:
        bot_info = await callback.bot.get_me()
        bot_name = bot_info.first_name
        price_stars = tariff['price_stars']
        await callback.message.answer_invoice(title=bot_name, description=f"Оплата тарифа «{tariff['name']}» ({days} дн.).", payload=order_id, currency='XTR', prices=[LabeledPrice(label=f"Тариф {tariff['name']}", amount=price_stars)], reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text=f'⭐️ Оплатить {price_stars} XTR', pay=True)).row(InlineKeyboardButton(text='❌ Отмена', callback_data='buy_key')).as_markup())
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Ошибка при выставлении счета Stars: {e}')
        await callback.answer('❌ Произошла ошибка при создании счета', show_alert=True)
        return
    await callback.message.delete()
    await callback.answer()
