import logging
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_IDS
from database.requests import get_or_create_user, is_user_banned, get_all_servers, get_setting, is_referral_enabled, get_user_by_referral_code, set_user_referrer
from bot.keyboards.user import main_menu_kb
from bot.states.user_states import RenameKey, ReplaceKey
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)

router = Router()


async def _attribute_pending_advertising_start(user: Dict[str, Any], created: bool, state: FSMContext):
    """Restore an ad payload consumed by the mandatory channel middleware."""
    state_data = await state.get_data()
    payload = str(state_data.get("pending_start_args") or "")
    if not payload.startswith("ad_") or len(payload) <= 3:
        return False
    await state.update_data(pending_start_args=None)
    from database.db_campaigns import attribute_user_to_campaign
    attributed, _campaign = attribute_user_to_campaign(
        user["id"], payload[3:], is_new_user=created,
    )
    return attributed


def _format_bytes(value: int) -> str:
    value = max(0, int(value or 0))
    gb = value / (1024 ** 3)
    if gb >= 100:
        return f"{gb:.0f} ГБ"
    if gb >= 10:
        return f"{gb:.1f} ГБ".replace(".0 ", " ")
    if gb >= 1:
        return f"{gb:.1f} ГБ"
    return f"{value / (1024 ** 2):.0f} МБ"


def _plural_days(value: int) -> str:
    value = max(0, int(value))
    last_two = value % 100
    last = value % 10
    if 11 <= last_two <= 14:
        word = "дней"
    elif last == 1:
        word = "день"
    elif 2 <= last <= 4:
        word = "дня"
    else:
        word = "дней"
    return f"{value} {word}"


def _days_left(expires_at: Any) -> int:
    if not expires_at:
        return 0
    try:
        expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        seconds = (expires - datetime.now(timezone.utc)).total_seconds()
        return max(0, int((seconds + 86399) // 86400))
    except (TypeError, ValueError):
        return 0


def build_fallback_home_text(user: dict, primary_key: Optional[Dict[str, Any]]) -> str:
    """Компактный резервный кабинет без внутренних технических деталей."""
    first_name = escape_html(user.get("first_name") or "друг")
    if not primary_key:
        return (
            f"<b>ArcVPN</b>\n\n"
            f"{first_name}, подписка ещё не оформлена.\n"
            "Выберите тариф — после оплаты доступ появится автоматически.\n\n"
            "<blockquote>Основное управление доступно в приложении ArcVPN.</blockquote>"
        )

    active = bool(primary_key.get("is_active"))
    days = _days_left(primary_key.get("expires_at"))
    status = "Подписка активна" if active else "Подписка закончилась"
    status_icon = "●" if active else "○"
    lte_quota = max(0, int(primary_key.get("lte_quota_gb") or 0)) * 1024**3
    lte_used = max(0, int(primary_key.get("lte_used_bytes") or 0))
    traffic_line = "Основной трафик: <b>безлимит</b>"
    lte_line = (
        f"Обход глушилок: <b>{_format_bytes(max(0, lte_quota - lte_used))}</b> из "
        f"<b>{_format_bytes(lte_quota)}</b>"
        if lte_quota else "Обход глушилок: <b>не входит в тариф</b>"
    )

    if active:
        access_line = f"Осталось: <b>{_plural_days(days)}</b>"
        hint = "Откройте ArcVPN или выберите нужное действие ниже."
    else:
        access_line = "Доступ приостановлен"
        hint = "Продлите подписку — доступ восстановится автоматически."

    return (
        f"<b>ArcVPN</b>\n\n"
        f"{status_icon} <b>{status}</b>\n"
        f"{access_line}\n"
        f"{traffic_line}\n"
        f"{lte_line}\n\n"
        f"<blockquote>{hint}</blockquote>"
    )


def create_onboarding_kb() -> InlineKeyboardMarkup:
    """Минимальный вход: Mini App и резервный интерфейс в чате."""
    from aiogram.types import WebAppInfo
    import os, config
    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Подключиться",
        web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/app/"),
        style="primary",
    ))
    builder.row(InlineKeyboardButton(
        text="Продолжить в боте",
        callback_data="start",
    ))
    return builder.as_markup()


def trial_welcome_text(user: dict, trial_result: Optional[dict]) -> str:
    first_name = escape_html(user.get("first_name") or "друг")
    if trial_result:
        days = int(trial_result.get("trial_days") or 0)
        traffic = int(trial_result.get("trial_traffic_gb") or 0)
        traffic_line = f"\nТрафик: <b>{traffic} ГБ</b>" if traffic > 0 else ""
        return (
            f"👋 <b>{first_name}, добро пожаловать в ArcVPN!</b>\n\n"
            "Мы уже подготовили вашу пробную подписку — активировать её отдельно не нужно.\n\n"
            f"🎁 <b>{days} дней бесплатно</b>{traffic_line}\n"
            "⚡ Быстрые серверы для видео, мессенджеров и сайтов\n"
            "🔥 Российские сервисы продолжают работать с VPN\n\n"
            "Нажмите «Подключиться»: внутри подберём приложение и импортируем подписку."
        )
    return (
        f"<b>{first_name}, добро пожаловать в ArcVPN</b>\n\n"
        "Откройте приложение, чтобы проверить подписку и подключить VPN."
    )


def get_welcome_text(user: dict, is_admin: bool=False, show_trial_offer: bool=False, primary_key: Optional[Dict[str, Any]] = None) -> tuple:
    """Формирует приветственный текст с информацией о пользователе.
    
    Args:
        user: Словарь с данными пользователя
        is_admin: Является ли пользователь администратором
        show_trial_offer: Показывать ли предложение пробного периода
        primary_key: Основной ключ (для отображения трафика)
    
    Returns:
        Кортеж (text, photo_file_id) — текст и опциональное фото
    """
    from bot.utils.text import escape_html
    from bot.utils.message_editor import get_message_data
    
    # Получаем имя пользователя
    first_name = escape_html(user.get('first_name', 'Пользователь'))
    user_id = user.get('telegram_id', 0)

    # Формируем блок трафика
    traffic_line = ""
    if primary_key:
        used = int(primary_key.get('traffic_used') or 0)
        limit = int(primary_key.get('traffic_limit') or 0)
        if limit > 0:
            def _fmt_b(b):
                if b <= 0:
                    return "0 ГБ"
                gb = b / (1024**3)
                if gb >= 1024:
                    return f"{gb/1024:.1f} ТБ"
                if gb >= 10:
                    return f"{round(gb)} ГБ"
                if gb >= 1:
                    return f"{gb:.1f} ГБ"
                mb = b / (1024**2)
                return f"{max(1, round(mb))} МБ"
            traffic_line = f"\n— Трафик: {_fmt_b(used)} / {_fmt_b(limit)}"

    # Формируем блок с информацией пользователя (всегда добавляется в конец)
    user_info_block = (
        f"Привет, {first_name}!\n\n"
        f"<blockquote>— Ваш ID: {user_id}{traffic_line}</blockquote>\n\n"
        f"Новостной канал — @arcvpn1\n"
        f"Поддержка — @Turan11627"
    )
    
    # Загружаем кастомное сообщение из БД (если есть)
    welcome_data = get_message_data('main_page_text')
    custom_text = welcome_data.get('text', '').strip()
    photo_file_id = welcome_data.get('photo_file_id')
    
    # Формируем итоговый текст
    if custom_text:
        # Если есть кастомный текст, добавляем блок пользователя в конец
        welcome_text = custom_text + "\n\n" + user_info_block
    else:
        # Если кастомного текста нет, используем только блок пользователя
        welcome_text = user_info_block
    
    # Добавляем предложение пробного периода если нужно
    if show_trial_offer:
        from database.requests import get_trial_days
        days = get_trial_days()
        trial_text = f"\n\n<blockquote>👇 Получи {days} дней бесплатно</blockquote>"
        welcome_text = welcome_text + trial_text
    
    return (welcome_text, photo_file_id)

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
    
    # Пробный период теперь выдаётся АВТОМАТИЧЕСКИ при первом /start (см. ниже),
    # поэтому кнопки/оффера «получить триал» в меню больше нет.
    from database.requests import is_trial_enabled, has_used_trial, get_user_primary_key
    show_trial = False

    primary_key = get_user_primary_key(user_id)
    (text, welcome_photo) = get_welcome_text(user, is_admin, show_trial_offer=show_trial, primary_key=primary_key)
    args = command.args
    if args and args.startswith('ad_'):
        from database.db_campaigns import attribute_user_to_campaign
        campaign_code = args[3:]
        attributed, campaign = attribute_user_to_campaign(
            user['id'], campaign_code, is_new_user=is_new,
        )
        if attributed:
            logger.info(
                "User %s attributed to advertising campaign %s",
                user_id,
                campaign.get('id') if campaign else 'unknown',
            )
    # Глубокая ссылка из Mini App: ?start=buy_<tariff_id> — сразу открываем
    # оплату выбранного тарифа (или продление, если подписка уже есть).
    if args and args.startswith('buy_'):
        tariff_part = args[4:]
        if tariff_part.isdigit():
            tariff_id = int(tariff_part)
            from database.requests import get_tariff_by_id, get_user_primary_key
            if get_tariff_by_id(tariff_id):
                from bot.utils.payment_flow_ui import (
                    show_payment_method_selection_screen,
                )
                from bot.utils.message_editor import get_message_data
                primary = get_user_primary_key(user_id)
                if primary:
                    # Mini App уже получил явный выбор тарифа. Сохраняем его и
                    # сразу открываем оплату продления существующей подписки.
                    await show_payment_method_selection_screen(
                        message,
                        user_id,
                        tariff_id,
                        key_id=primary['id'],
                    )
                else:
                    intro = (get_message_data('payment_select_text', '').get('text', '') or '').strip() or None
                    await show_payment_method_selection_screen(message, user_id, tariff_id, intro_text=intro)
                return
        # Неизвестный/битый id — не падаем, просто показываем главное меню ниже.
        logger.warning(f"Mini App buy deeplink с неизвестным тарифом: {args!r}")

    if is_new and args and args.startswith('ref_'):
        ref_code = args[4:]
        referrer = get_user_by_referral_code(ref_code)
        if referrer and referrer['id'] != user['id']:
            if set_user_referrer(user['id'], referrer['id']):
                logger.info(f"User {user_id} привязан к рефереру {referrer['telegram_id']}")

    # Обязательный авто-триал: новый пользователь сразу получает пробную подписку
    # (без кнопки). Делаем ПОСЛЕ привязки реферера — чтобы начислить рефереру +N дней.
    # Пользователь мог быть создан middleware'ом/проверкой канала до первого
    # полноценного /start. Поэтому is_new здесь не подходит: выдаём триал
    # идемпотентно всем, кто ещё его не получал.
    trial_result = None
    try:
        if is_trial_enabled() and not has_used_trial(user_id):
            from bot.handlers.user.trial import provision_trial_for_user
            trial_result = await provision_trial_for_user(user)
            if trial_result:
                logger.info(f"Авто-триал выдан пользователю {user_id}")
            else:
                logger.warning(f"Авто-триал не создан для {user_id} (серверы недоступны?)")
    except Exception as e:
        logger.error(f"Ошибка авто-триала при /start для {user_id}: {e}")

    try:
        from bot.services.billing import process_campaign_bonus
        await process_campaign_bonus(user['id'], 'entry')
    except Exception:
        logger.exception("Advertising entry bonus failed for user %s", user_id)

    # Ключ мог появиться только что при авто-триале — собираем приветствие после
    # выдачи, чтобы пользователь сразу увидел актуальное состояние подписки.
    primary_key = get_user_primary_key(user_id)
    (text, welcome_photo) = get_welcome_text(user, is_admin, show_trial_offer=False, primary_key=primary_key)

    show_referral = is_referral_enabled()
    has_subscription, primary_key_id = _get_subscription_state(user_id)

    # Создаем клавиатуру с кнопкой пробного периода если нужно
    if is_new:
        text = trial_welcome_text(user, trial_result)
        kb = create_onboarding_kb()
        # Первое сообщение после согласия и подписки намеренно без картинки:
        # пользователь сразу видит выданный trial и два понятных действия.
        welcome_photo = None
    else:
        # Старые main_page_text/photo_file_id больше не управляют пользовательским UI.
        # /start и callback «На главную» обязаны показывать один новый кабинет.
        text = build_fallback_home_text(user, primary_key)
        kb = create_main_menu_kb(
            is_admin=is_admin, show_trial=show_trial, show_referral=show_referral,
            has_subscription=has_subscription, primary_key_id=primary_key_id,
        )
        cabinet_banner = Path(__file__).resolve().parents[2] / "assets" / "arc-cabinet-v6.png"
        welcome_photo = FSInputFile(cabinet_banner) if cabinet_banner.exists() else None

    try:
        await safe_edit_or_send(message, text, reply_markup=kb, photo=welcome_photo, force_new=True)
    except TelegramForbiddenError:
        logger.warning(f'User {user_id} blocked the bot during /start')
    except Exception as e:
        logger.error(f'Error sending start message to {user_id}: {e}')


def create_main_menu_kb(
    is_admin: bool = False,
    show_trial: bool = False,
    show_referral: bool = True,
    has_subscription: bool = False,
    primary_key_id: int = None,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню.

    Модель «одна подписка»: если у пользователя уже есть подписка (любой ключ,
    активный или истёкший) — показываем «Продлить подписку» вместо «Купить»,
    чтобы не плодить несколько подписок. «Купить» — только когда ключей нет.

    Args:
        is_admin: Показывать ли кнопку админ-панели
        show_trial: Показывать ли кнопку пробного периода
        show_referral: Показывать ли кнопку реферальной программы
        has_subscription: Есть ли у пользователя хотя бы один ключ
        primary_key_id: ID основной подписки (для кнопки продления)
    """
    # Акцентный цвет кнопок: Bot API 9.4 (фев 2026) добавил поле `style` у
    # InlineKeyboardButton с пресетом 'primary' — Telegram красит кнопку в
    # акцентный цвет темы пользователя. aiogram 3.13.1 поля не знает, но его
    # модели с extra='allow' прокидывают `style` в API как есть.
    builder = InlineKeyboardBuilder()

    # Пробный период выдаётся автоматически при первом /start — отдельной кнопки нет.

    # Ряд 1: Mini App — основная точка входа.
    # Кабинет живёт на apex-домене; subscription URL остаётся стабильным.
    from aiogram.types import WebAppInfo
    import os, config
    webapp_url = f"{os.getenv('WEBAPP_URL', config.SUBSCRIPTION_URL).rstrip('/')}/app"
    builder.row(InlineKeyboardButton(text="🚀 Открыть ArcVPN", web_app=WebAppInfo(url=webapp_url), style="primary"))

    # Самые частые резервные действия держим в первом ряду.
    builder.row(
        InlineKeyboardButton(text="📲 Подключить VPN", callback_data="bot_connect"),
        InlineKeyboardButton(text="🔐 Моя подписка", callback_data="my_keys"),
    )

    # Покупка/продление остаётся отдельной заметной кнопкой.
    # Если подписки ещё нет — продлевать нечего, показываем «Купить».
    if has_subscription and primary_key_id:
        builder.row(InlineKeyboardButton(text="⚡ Продлить подписку", callback_data=f"key_renew:{primary_key_id}", style="primary"))
    else:
        builder.row(InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="buy_key", style="primary"))

    secondary = []
    if show_referral:
        secondary.append(InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral_system"))
    secondary.append(InlineKeyboardButton(text="💬 Помощь", callback_data="bot_help"))
    builder.row(*secondary)
    builder.row(InlineKeyboardButton(text="⚙️ Настройки", callback_data="bot_settings"))

    # Админ-панель (если админ)
    if is_admin:
        builder.row(InlineKeyboardButton(
            text="📊 Business Console",
            web_app=WebAppInfo(url="https://panel.arccnet.space/"),
            style="primary",
        ))
        builder.row(InlineKeyboardButton(text="Состояние сервисов", callback_data="admin_panel"))

    return builder.as_markup()


def _get_subscription_state(telegram_id: int):
    """Возвращает (has_subscription, primary_key_id) для модели «одна подписка»."""
    from database.requests import get_user_primary_key
    primary = get_user_primary_key(telegram_id)
    if primary:
        return True, primary['id']
    return False, None

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
    
    # Триал автоматический — кнопки/оффера в меню нет.
    show_trial = False

    from database.requests import get_user_primary_key
    primary_key = get_user_primary_key(user_id)
    text = build_fallback_home_text(user, primary_key)
    cabinet_banner = Path(__file__).resolve().parents[2] / "assets" / "arc-cabinet-v6.png"
    welcome_photo = FSInputFile(cabinet_banner) if cabinet_banner.exists() else None

    show_referral = is_referral_enabled()
    has_subscription, primary_key_id = _get_subscription_state(user_id)
    kb = create_main_menu_kb(
        is_admin=is_admin, show_trial=show_trial, show_referral=show_referral,
        has_subscription=has_subscription, primary_key_id=primary_key_id,
    )
    await safe_edit_or_send(callback.message, text, reply_markup=kb, photo=welcome_photo)
    await callback.answer()


def _fallback_back_kb(*, primary_label: str, primary_callback: str) -> InlineKeyboardMarkup:
    from aiogram.types import WebAppInfo
    import os, config
    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Открыть ArcVPN",
        web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/app"),
        style="primary",
    ))
    builder.row(InlineKeyboardButton(text=primary_label, callback_data=primary_callback))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    return builder.as_markup()


def _bot_settings_keyboard(user_internal_id: int, *, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Compact bot fallback settings, matching the WebApp billing controls."""
    from database.db_recurring import get_active_recurring_method

    method = get_active_recurring_method(user_internal_id) if user_internal_id else None
    recurring_available = get_setting("yookassa_recurring_enabled", "0") == "1"
    builder = InlineKeyboardBuilder()
    if method:
        builder.row(InlineKeyboardButton(
            text="☑️ Банковская карта привязана",
            callback_data="noop",
        ))
        builder.row(InlineKeyboardButton(
            text="🗑 Удалить карту и отключить",
            callback_data="bot_recurring_disable",
        ))
    elif recurring_available:
        builder.row(InlineKeyboardButton(
            text="💳 Подключить при следующей оплате",
            callback_data="bot_recurring_setup",
            style="primary",
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="💳 Банковская карта не привязана",
            callback_data="bot_recurring_unavailable",
        ))
        if is_admin:
            builder.row(InlineKeyboardButton(
                text="👁 Предпросмотр отвязки карты",
                callback_data="bot_recurring_preview",
            ))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    return builder.as_markup()


@router.callback_query(F.data == "bot_settings")
async def bot_settings_menu_handler(callback: CallbackQuery):
    from aiogram.types import WebAppInfo
    import os, config
    webapp_url = os.getenv("WEBAPP_URL", config.SUBSCRIPTION_URL)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📱 Устройства",
        web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/app?screen=devices"),
    ))
    builder.row(InlineKeyboardButton(
        text="✉️ Добавить email",
        web_app=WebAppInfo(url=f"{webapp_url.rstrip('/')}/app?screen=email"),
    ))
    builder.row(InlineKeyboardButton(
        text="🔁 Автопродление",
        callback_data="bot_recurring_settings",
    ))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    await safe_edit_or_send(
        callback.message,
        "<b>ArcVPN</b>\n\n"
        "⚙️ <b>Настройки</b>\n\n"
        "Управляйте подключёнными устройствами, email и автопродлением подписки.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "bot_recurring_settings")
async def bot_settings_handler(callback: CallbackQuery, answer: bool = True):
    from database.db_recurring import get_active_recurring_method
    from database.requests import get_user_internal_id

    user_internal_id = get_user_internal_id(callback.from_user.id)
    method = get_active_recurring_method(user_internal_id) if user_internal_id else None
    recurring_available = get_setting("yookassa_recurring_enabled", "0") == "1"
    if method:
        status = "✅ <b>Включено</b>"
        detail = "Способ оплаты сохранён безопасно в ЮKassa. Отключить его можно самостоятельно ниже."
    elif recurring_available:
        status = "○ <b>Не подключено</b>"
        detail = "Выберите автопродление при следующей оплате — после подтверждения способ оплаты появится здесь."
    else:
        status = "⏳ <b>Ожидает подключения ЮKassa</b>"
        detail = "Интерфейс уже готов. Как только ЮKassa включит рекуррентные платежи, настройка станет доступна без обновления бота."
    await safe_edit_or_send(
        callback.message,
        "<b>ArcVPN</b>\n\n"
        "🔁 <b>Автопродление</b>\n\n"
        f"Статус: {status}\n\n"
        f"<blockquote>{detail}</blockquote>\n\n"
        "Вы всегда управляете автопродлением сами — обращение в поддержку не требуется.",
        reply_markup=_bot_settings_keyboard(
            user_internal_id or 0,
            is_admin=callback.from_user.id in ADMIN_IDS,
        ),
    )
    if answer:
        await callback.answer()


@router.callback_query(F.data == "bot_recurring_preview")
async def bot_recurring_preview_handler(callback: CallbackQuery):
    """Admin-only review screen for YooKassa recurring-payment approval."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недоступно", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="☑️ Банковская карта привязана",
        callback_data="noop",
    ))
    builder.row(InlineKeyboardButton(
        text="🗑 Удалить карту и отключить автопродление",
        callback_data="bot_recurring_preview_delete",
    ))
    builder.row(InlineKeyboardButton(
        text="← Назад",
        callback_data="bot_recurring_settings",
    ))
    await safe_edit_or_send(
        callback.message,
        "<b>ArcVPN</b>\n\n"
        "🔁 <b>Автопродление</b>\n\n"
        "Статус: ✅ <b>Включено</b>\n\n"
        "<blockquote>Банковская карта сохранена в ЮKassa. "
        "Вы можете в любой момент самостоятельно удалить её и отключить автопродление.</blockquote>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "bot_recurring_preview_delete")
async def bot_recurring_preview_delete_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недоступно", show_alert=True)
        return
    await callback.answer(
        "В рабочем сценарии эта кнопка сразу удаляет сохранённый способ оплаты в ArcVPN.",
        show_alert=True,
    )


@router.callback_query(F.data == "bot_recurring_disable")
async def bot_recurring_disable_handler(callback: CallbackQuery):
    from database.db_recurring import disable_recurring_methods
    from database.requests import get_user_internal_id

    user_internal_id = get_user_internal_id(callback.from_user.id)
    disabled = disable_recurring_methods(user_internal_id) if user_internal_id else 0
    await callback.answer("Автопродление отключено" if disabled else "Автопродление уже отключено", show_alert=True)
    await bot_settings_handler(callback, answer=False)


@router.callback_query(F.data == "bot_recurring_unavailable")
async def bot_recurring_unavailable_handler(callback: CallbackQuery):
    await callback.answer(
        "ЮKassa ещё согласовывает автоплатежи. Оплата без автопродления работает как обычно.",
        show_alert=True,
    )


@router.callback_query(F.data == "bot_recurring_setup")
async def bot_recurring_setup_handler(callback: CallbackQuery):
    from database.requests import get_user_primary_key
    from bot.utils.payment_flow_ui import show_tariff_selection_screen

    primary = get_user_primary_key(callback.from_user.id)
    await show_tariff_selection_screen(
        callback.message,
        callback.from_user.id,
        key_id=primary.get("id") if primary else None,
    )
    await callback.answer()


@router.callback_query(F.data == "bot_connect")
async def fallback_connect_handler(callback: CallbackQuery):
    from database.requests import get_user_primary_key

    primary = get_user_primary_key(callback.from_user.id)
    subscription_line = ""
    if primary and primary.get("sub_id"):
        from bot.handlers.user.keys import _subscription_urls
        subscription_url, _ = _subscription_urls(str(primary["sub_id"]))
        subscription_line = (
            f'\n\n🔗 <b>Ссылка на подписку</b>\n\n'
            f'<code>{escape_html(subscription_url)}</code>\n\n'
            '👆 Нажмите на ссылку, чтобы скопировать.'
        )
    text = (
        "📱 <b>Подключить VPN</b>\n\n"
        "1. Установите приложение Happ.\n"
        "2. Импортируйте подписку.\n"
        "3. Выберите сервер и включите VPN.\n\n"
        "<blockquote>Если приложение уже установлено, нажмите «Импортировать подписку».</blockquote>"
        + subscription_line
    )
    await safe_edit_or_send(
        callback.message,
        text,
        reply_markup=_fallback_back_kb(
            primary_label="📲 Импортировать подписку",
            primary_callback="show_subscription",
        ),
    )
    await callback.answer()


FAQ_ANSWERS = {
    "connect": (
        "🔌 <b>VPN не подключается</b>\n\n"
        "Откройте Happ и нажмите кнопку проверки задержки — обычно это значок "
        "пинга или спидометра над списком серверов. Happ проверит все подключения "
        "и покажет время в миллисекундах. Выберите сервер с наименьшим значением.\n\n"
        "Если у всех серверов ошибка, обновите подписку, выключите другие VPN "
        "и перезапустите Happ."
    ),
    "lte": (
        "<b>Обход блокировок</b>\n\n"
        "Для мобильного интернета выберите сервер с названием "
        "«Обход глушилок (LTE)». Он предназначен для сетей с белыми списками."
    ),
    "speed": (
        "⚡ <b>Низкая скорость</b>\n\n"
        "В Happ нажмите кнопку проверки задержки — значок пинга или спидометра "
        "над списком серверов. Дождитесь окончания проверки и выберите сервер "
        "с минимальным пингом в миллисекундах.\n\n"
        "Для видео попробуйте сервер со значком ⚡ и сравните скорость по Wi‑Fi "
        "и мобильной сети."
    ),
    "payment": (
        "<b>Оплата или подписка</b>\n\n"
        "После успешной оплаты подписка обновляется автоматически. "
        "Если статус не изменился, откройте ArcVPN заново через несколько секунд."
    ),
}


@router.callback_query(F.data == "bot_help")
async def fallback_help_handler(callback: CallbackQuery):
    from database.requests import get_setting as _get_setting
    support_link = _get_setting("support_channel_link", "https://t.me/ArcVPN_support")
    if not support_link or not support_link.startswith(("http://", "https://")):
        support_link = "https://t.me/ArcVPN_support"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔌 VPN не подключается", callback_data="bot_faq:connect"))
    builder.row(InlineKeyboardButton(text="📡 Как настроить обход", callback_data="bot_faq:lte"))
    builder.row(InlineKeyboardButton(text="⚡ Низкая скорость", callback_data="bot_faq:speed"))
    builder.row(InlineKeyboardButton(text="💳 Оплата и подписка", callback_data="bot_faq:payment"))
    builder.row(InlineKeyboardButton(text="💬 Написать в поддержку", url=support_link, style="primary"))
    builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
    await safe_edit_or_send(
        callback.message,
        "💬 <b>Помощь ArcVPN</b>\n\nВыберите тему — ответ откроется прямо здесь.",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_faq:"))
async def fallback_faq_handler(callback: CallbackQuery):
    topic = callback.data.partition(":")[2]
    answer = FAQ_ANSWERS.get(topic)
    if not answer:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    await safe_edit_or_send(
        callback.message,
        answer,
        reply_markup=_fallback_back_kb(primary_label="← Другие вопросы", primary_callback="bot_help"),
    )
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
    from database.requests import get_or_create_user, is_trial_enabled, has_used_trial, is_referral_enabled
    
    user_id = callback.from_user.id
    bot = callback.bot
    
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_ID, user_id=user_id)
        
        if member.status in ["left", "kicked"]:
            await callback.answer("❌ Вы еще не подписались на канал", show_alert=True)
            return
        
        # Middleware intercepts the first /start before the normal handler, so
        # the user may not exist yet when this callback arrives.
        user, created = get_or_create_user(
            telegram_id=user_id,
            username=callback.from_user.username
        )
        attributed = await _attribute_pending_advertising_start(user, created, state)

        from database.db_legal_consent import record_legal_consent
        from database.requests import get_setting
        consent_version = get_setting('legal_consent_version', '2026-08-26')
        if not record_legal_consent(user_id, consent_version, 'telegram_channel_gate'):
            logger.error("Не удалось сохранить согласие пользователя %s", user_id)
            await callback.answer("Не удалось сохранить согласие. Попробуйте ещё раз.", show_alert=True)
            return
        await callback.answer("✅ Спасибо за подписку!")
        
        # После проверки обязательного канала триал тоже выдаётся сам. Это
        # покрывает пользователя, которого middleware успел создать раньше
        # первого /start, и не оставляет в интерфейсе устаревший CTA.
        trial_result = None
        if is_trial_enabled() and not has_used_trial(user_id):
            from bot.handlers.user.trial import provision_trial_for_user
            try:
                trial_result = await provision_trial_for_user(user)
                if not trial_result:
                    logger.warning("Авто-триал после проверки канала не создан для %s", user_id)
            except Exception:
                logger.exception("Ошибка авто-триала после проверки канала для %s", user_id)
        if attributed:
            try:
                from bot.services.billing import process_campaign_bonus
                await process_campaign_bonus(user['id'], 'entry')
            except Exception:
                logger.exception("Advertising entry bonus failed for user %s", user_id)
        show_trial = False
        
        # Проверяем реферальную систему
        show_referral = is_referral_enabled()
        
        # Проверяем админа
        is_admin = user_id in ADMIN_IDS
        
        keyboard = create_onboarding_kb()
        
        # Получаем правильное приветственное сообщение
        text = trial_welcome_text(user, trial_result)
        
        # Удаляем старое сообщение
        try:
            await callback.message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
        
        # Отправляем главное меню
        await callback.message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}", exc_info=True)
        await callback.answer("❌ Ошибка проверки подписки", show_alert=True)
