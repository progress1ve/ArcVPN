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

def get_welcome_text(user: dict, is_admin: bool=False) -> tuple:
    """Формирует приветственный текст с информацией о пользователе и тарифами.
    
    Args:
        user: Словарь с данными пользователя
        is_admin: Является ли пользователь администратором
    
    Returns:
        Кортеж (text, photo_file_id) — текст и опциональное фото
    """
    from database.requests import get_all_tariffs, get_setting, is_crypto_configured, is_stars_enabled, is_cards_enabled, is_yookassa_qr_configured, is_demo_payment_enabled
    from bot.utils.text import escape_html
    from bot.utils.message_editor import get_message_data
    
    # Получаем имя пользователя
    first_name = escape_html(user.get('first_name', 'Пользователь'))
    user_id = user.get('telegram_id', 0)
    balance = user.get('personal_balance', 0) / 100  # Конвертируем копейки в рубли
    
    # Формируем приветствие
    greeting = (
        f"Привет, {first_name}!\n\n"
        f"<blockquote>— Ваш ID: {user_id}\n"
        f"— Ваш баланс: {balance:.2f} ₽</blockquote>\n\n"
        f"Новостной канал — @arcvpn1\n"
        f"Техническая поддержка — @progressive_dev"
    )
    
    welcome_data = get_message_data('main_page_text', greeting)
    welcome_text = welcome_data.get('text', greeting)
    photo_file_id = welcome_data.get('photo_file_id')
    
    crypto_enabled = is_crypto_configured()
    stars_enabled = is_stars_enabled()
    cards_enabled = is_cards_enabled()
    yookassa_qr_enabled = is_yookassa_qr_configured()
    demo_enabled = is_demo_payment_enabled()
    tariffs = get_all_tariffs()
    tariff_lines = []
    
    if tariffs:
        tariff_lines.append('\n\n📋 <b>Тарифы:</b>')
        for tariff in tariffs:
            prices = []
            if crypto_enabled:
                price_usd = tariff['price_cents'] / 100
                price_str = f'{price_usd:g}'.replace('.', ',')
                prices.append(f'${escape_html(price_str)}')
            if stars_enabled:
                prices.append(f"{tariff['price_stars']} ⭐")
            if (cards_enabled or yookassa_qr_enabled or demo_enabled) and tariff.get('price_rub', 0) > 0:
                prices.append(f"{int(tariff['price_rub'])} ₽")
            price_display = ' / '.join(prices) if prices else 'Цена не установлена'
            tariff_lines.append(f"• {escape_html(tariff['name'])} — {price_display}")
    
    tariff_text = '\n'.join(tariff_lines)
    
    if '%без_тарифов%' in welcome_text:
        return (welcome_text.replace('%без_тарифов%', ''), photo_file_id)
    if '%тарифы%' not in welcome_text:
        welcome_text = f'{welcome_text}\n\n%тарифы%'
    
    return (welcome_text.replace('%тарифы%', tariff_text), photo_file_id)

@router.message(Command('start'), StateFilter('*'))
async def cmd_start(message: Message, state: FSMContext, command: CommandObject):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f'CMD_START: User {user_id} started bot')
    await state.clear()
    
    # Удаляем Reply-клавиатуру, если она "застряла" от предыдущих стейтов
    from aiogram.types import ReplyKeyboardRemove
    try:
        temp_msg = await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())
        await temp_msg.delete()
    except Exception:
        pass

    (user, is_new) = get_or_create_user(user_id, username)
    if user.get('is_banned'):
        await safe_edit_or_send(message, '⛔ <b>Доступ заблокирован</b>\n\nВаш аккаунт заблокирован. Обратитесь в поддержку.', force_new=True)
        return
    
    # Сохраняем имя пользователя
    if message.from_user.first_name:
        from database.requests import update_user_name
        update_user_name(user_id, message.from_user.first_name)
        user['first_name'] = message.from_user.first_name
    
    is_admin = user_id in ADMIN_IDS
    (text, welcome_photo) = get_welcome_text(user, is_admin)
    args = command.args
    if args and args.startswith('bill'):
        from bot.services.billing import process_crypto_payment
        from bot.handlers.user.payments.base import finalize_payment_ui
        try:
            (success, text, order) = await process_crypto_payment(args, user_id=user['id'])
            if success and order:
                await finalize_payment_ui(message, state, text, order, user_id=message.from_user.id)
            else:
                await safe_edit_or_send(message, text, force_new=True)
        except Exception as e:
            from bot.errors import TariffNotFoundError
            if isinstance(e, TariffNotFoundError):
                from database.requests import get_setting
                from bot.keyboards.user import support_kb
                support_link = get_setting('support_channel_link', 'https://t.me/ArcVPN_support')
                await safe_edit_or_send(message, str(e), reply_markup=support_kb(support_link), force_new=True)
            else:
                logger.exception(f'Ошибка обработки платежа: {e}')
                await safe_edit_or_send(message, '❌ Произошла ошибка при обработке платежа.', force_new=True)
        return
    if is_new and args and args.startswith('ref_'):
        ref_code = args[4:]
        referrer = get_user_by_referral_code(ref_code)
        if referrer and referrer['id'] != user['id']:
            if set_user_referrer(user['id'], referrer['id']):
                logger.info(f"User {user_id} привязан к рефереру {referrer['telegram_id']}")
    from database.requests import is_trial_enabled, get_trial_tariff_id, has_used_trial
    show_trial = is_trial_enabled() and get_trial_tariff_id() is not None and (not has_used_trial(user_id))
    show_referral = is_referral_enabled()
    kb = main_menu_kb(is_admin=is_admin, show_trial=show_trial, show_referral=show_referral)
    try:
        await safe_edit_or_send(message, text, reply_markup=kb, photo=welcome_photo, force_new=True)
    except TelegramForbiddenError:
        logger.warning(f'User {user_id} blocked the bot during /start')
    except Exception as e:
        logger.error(f'Error sending start message to {user_id}: {e}')

@router.callback_query(F.data == 'start')
async def callback_start(callback: CallbackQuery, state: FSMContext):
    """Возврат на главный экран по кнопке."""
    user_id = callback.from_user.id
    if is_user_banned(user_id):
        await callback.answer('⛔ Доступ заблокирован', show_alert=True)
        return
    await state.clear()
    
    # Получаем данные пользователя
    from database.requests import get_user
    user = get_user(user_id)
    if not user:
        await callback.answer('❌ Ошибка получения данных', show_alert=True)
        return
    
    is_admin = user_id in ADMIN_IDS
    (text, welcome_photo) = get_welcome_text(user, is_admin)
    from database.requests import is_trial_enabled, get_trial_tariff_id, has_used_trial
    show_trial = is_trial_enabled() and get_trial_tariff_id() is not None and (not has_used_trial(user_id))
    show_referral = is_referral_enabled()
    kb = main_menu_kb(is_admin=is_admin, show_trial=show_trial, show_referral=show_referral)
    await safe_edit_or_send(callback.message, text, reply_markup=kb, photo=welcome_photo)
    await callback.answer()

@router.message(Command('help'))
async def cmd_help(message: Message, state: FSMContext):
    """Обработчик команды /help - вызывает логику кнопки 'Справка'."""
    if is_user_banned(message.from_user.id):
        await safe_edit_or_send(message, '⛔ <b>Доступ заблокирован</b>\n\nВаш аккаунт заблокирован. Обратитесь в поддержку.', force_new=True)
        return
    await state.clear()
    await show_help(message, is_callback=False)

async def show_help(message: 'Message', is_callback: bool = False):
    """Общая логика для показа справки.
    
    Использует send_editor_message() для единого HTML-контракта.
    
    Args:
        message: Сообщение (Message) для отправки/редактирования
        is_callback: True если вызвано из callback (редактируем), False если из команды (отправляем новое)
    """
    from bot.keyboards.admin import home_only_kb
    from bot.keyboards.user import help_kb
    from database.requests import get_setting
    from bot.utils.message_editor import get_message_data, send_editor_message
    help_data = get_message_data('help_page_text', '❓ <b>Справка</b>')
    help_photo = help_data.get('photo_file_id')
    default_news = 'https://t.me/ArcVPN'
    default_support = 'https://t.me/ArcVPN_support'
    news_link = get_setting('news_channel_link', default_news)
    support_link = get_setting('support_channel_link', default_support)
    if not news_link or not news_link.startswith(('http://', 'https://')):
        news_link = default_news
    if not support_link or not support_link.startswith(('http://', 'https://')):
        support_link = default_support
    news_hidden = get_setting('news_hidden', '0') == '1'
    support_hidden = get_setting('support_hidden', '0') == '1'
    news_name = get_setting('news_button_name', 'Новости')
    support_name = get_setting('support_button_name', 'Поддержка')
    kb = help_kb(news_link, support_link, news_hidden=news_hidden, support_hidden=support_hidden, news_name=news_name, support_name=support_name)
    if is_callback:
        await send_editor_message(message, data=help_data, default_text='❓ <b>Справка</b>', reply_markup=kb)
    else:
        await send_editor_message(message, data=help_data, default_text='❓ <b>Справка</b>', reply_markup=kb)

@router.callback_query(F.data == 'help')
async def help_handler(callback: CallbackQuery):
    """Показывает справку по кнопке."""
    await show_help(callback.message, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == 'noop')
async def noop_handler(callback: CallbackQuery):
    """Заглушка: нажатие на заголовок группы ничего не делает."""
    await callback.answer()

@router.callback_query(F.data == 'check_subscribe')
async def check_subscribe_handler(callback: CallbackQuery, state: FSMContext):
    """Проверяет подписку пользователя на канал."""
    from bot.middlewares.subscription_check import REQUIRED_CHANNEL_ID
    
    user_id = callback.from_user.id
    bot = callback.bot
    
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        
        if member.status in ["left", "kicked"]:
            await callback.answer("❌ Вы еще не подписались на канал", show_alert=True)
            return
        
        # Пользователь подписан
        await callback.answer("✅ Спасибо за подписку!")
        
        # Проверяем, новый ли пользователь и доступен ли пробный период
        from database.requests import get_user, is_trial_enabled, get_trial_tariff_id, has_used_trial
        user = get_user(user_id)
        
        if user and is_trial_enabled() and get_trial_tariff_id() and not has_used_trial(user_id):
            # Показываем предложение пробного периода
            await show_trial_offer(callback.message, state)
        else:
            # Перенаправляем на главное меню
            await cmd_start(callback.message, state, CommandObject(command="start", args=None))
        
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки подписки", show_alert=True)


async def show_trial_offer(message: Message, state: FSMContext):
    """Показывает предложение пробного периода новому пользователю."""
    from database.requests import get_trial_tariff_id, get_tariff_by_id
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    trial_tariff_id = get_trial_tariff_id()
    if not trial_tariff_id:
        # Если пробный период не настроен, показываем главное меню
        await cmd_start(message, state, CommandObject(command="start", args=None))
        return
    
    trial_tariff = get_tariff_by_id(trial_tariff_id)
    if not trial_tariff:
        await cmd_start(message, state, CommandObject(command="start", args=None))
        return
    
    days = trial_tariff.get('duration_days', 7)
    
    text = (
        f"🎉 <b>Попробуйте ArcVPN бесплатно на {days} дней!</b>\n\n"
        f"💳 <b>Привязка карты не требуется</b>\n"
        f"Начните пробный период и наслаждайтесь безопасным интернетом без ограничений\n\n"
        f"📌 <b>После пробного периода:</b>\n"
        f"• Ежемесячная подписка: 80₽/месяц\n"
        f"• Подписка на 3 месяца: 200₽\n\n"
        f"Продолжая, вы принимаете <a href='https://telegra.ph/Usloviya-ispolzovaniya-ArcVPN-01-01'>Условия использования</a> и\n"
        f"<a href='https://telegra.ph/Politika-konfidencialnosti-ArcVPN-01-01'>Политику конфиденциальности</a>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎁 Подключить VPN",
            callback_data="trial"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="start"
        )]
    ])
    
    await safe_edit_or_send(message, text, reply_markup=keyboard)
