"""
Обработчики раздела «Рассылка» в админ-панели.

Функционал:
- Рассылка сообщений всем пользователям с фильтрами
- Настройка автоуведомлений об истечении ключей
"""
import json
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from config import ADMIN_IDS
from database.requests import (
    get_setting, set_setting,
    get_users_for_broadcast, count_users_for_broadcast,
    get_all_promocodes
)
from bot.states.admin_states import AdminStates
from bot.utils.admin import is_admin
from bot.keyboards.admin import (
    broadcast_main_kb, broadcast_confirm_kb,
    broadcast_notifications_kb, broadcast_back_kb,
    broadcast_notify_back_kb, home_only_kb,
    BROADCAST_FILTERS, broadcast_templates_kb,
    broadcast_template_promocode_kb
)

logger = logging.getLogger(__name__)

from bot.utils.text import safe_edit_or_send

router = Router()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================




def get_broadcast_message() -> dict | None:
    """
    Получает сохранённое сообщение для рассылки.
    
    Returns:
        Словарь с ключами 'text' и 'photo_file_id' или None
    """
    msg_json = get_setting('broadcast_message')
    if msg_json:
        try:
            return json.loads(msg_json)
        except json.JSONDecodeError:
            return None
    return None


def save_broadcast_message(text: str, photo_file_id: str | None = None) -> None:
    """Сохраняет сообщение для рассылки."""
    data = {'text': text, 'photo_file_id': photo_file_id}
    set_setting('broadcast_message', json.dumps(data, ensure_ascii=False))


def is_broadcast_in_progress() -> bool:
    """Проверяет, идёт ли рассылка сейчас."""
    return get_setting('broadcast_in_progress', '0') == '1'


def set_broadcast_in_progress(value: bool) -> None:
    """Устанавливает флаг рассылки."""
    set_setting('broadcast_in_progress', '1' if value else '0')


# ============================================================================
# ГЛАВНЫЙ ЭКРАН РАССЫЛКИ
# ============================================================================

@router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает главный экран раздела рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.broadcast_menu)
    
    # Получаем данные для отображения
    msg_data = get_broadcast_message()
    has_message = msg_data is not None and msg_data.get('text')
    
    current_filter = get_setting('broadcast_filter', 'all')
    in_progress = is_broadcast_in_progress()
    user_count = count_users_for_broadcast(current_filter)
    
    text = (
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение всем пользователям бота.\n\n"
        "1️⃣ Отредактируйте сообщение\n"
        "2️⃣ Выберите фильтр получателей\n"
        "3️⃣ Нажмите «Начать рассылку»"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_main_kb(has_message, current_filter, in_progress, user_count)
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустой обработчик для разделителя."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await callback.answer()


# ============================================================================
# РЕДАКТИРОВАНИЕ СООБЩЕНИЯ
# ============================================================================

@router.callback_query(F.data == "broadcast_edit_message")
async def broadcast_edit_message(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование сообщения для рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.broadcast_waiting_message)
    
    text = (
        "✉️ <b>Редактирование сообщения</b>\n\n"
        "Отправьте мне сообщение, которое хотите разослать.\n\n"
        "Можно отправить:\n"
        "• Текст (с форматированием)\n"
        "• Фото с подписью\n\n"
        "💡 Сообщение будет отправлено пользователям в точности как вы его прислали."
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_back_kb()
    )
    await callback.answer()


@router.message(AdminStates.broadcast_waiting_message)
async def broadcast_save_message(message: Message, state: FSMContext):
    """Сохраняет сообщение для рассылки."""
    if not is_admin(message.from_user.id):
        return
    
    from bot.utils.text import get_message_text_for_storage, safe_edit_or_send
    
    text = None
    photo_file_id = None
    
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        text = get_message_text_for_storage(message, 'markdown')
    elif message.text:
        text = get_message_text_for_storage(message, 'markdown')
    else:
        await safe_edit_or_send(message,
            "❌ Поддерживаются только текст или фото с подписью.",
            reply_markup=broadcast_back_kb()
        )
        return
    
    save_broadcast_message(text, photo_file_id)
    
    await safe_edit_or_send(message,
        "✅ <b>Сообщение сохранено!</b>\n\n"
        "Теперь можете посмотреть превью или начать рассылку."
    )
    
    # Возвращаемся в меню рассылки
    await state.set_state(AdminStates.broadcast_menu)
    
    msg_data = get_broadcast_message()
    has_message = msg_data is not None
    current_filter = get_setting('broadcast_filter', 'all')
    in_progress = is_broadcast_in_progress()
    user_count = count_users_for_broadcast(current_filter)
    
    text = (
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение всем пользователям бота.\n\n"
        "1️⃣ Отредактируйте сообщение\n"
        "2️⃣ Выберите фильтр получателей\n"
        "3️⃣ Нажмите «Начать рассылку»"
    )
    
    await safe_edit_or_send(message,
        text,
        reply_markup=broadcast_main_kb(has_message, current_filter, in_progress, user_count),
        force_new=True
    )


# ============================================================================
# ПРЕВЬЮ СООБЩЕНИЯ
# ============================================================================

@router.callback_query(F.data == "broadcast_preview")
async def broadcast_preview(callback: CallbackQuery):
    """Показывает превью сообщения для рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    msg_data = get_broadcast_message()
    
    if not msg_data or not msg_data.get('text'):
        await callback.answer("❌ Сообщение не задано", show_alert=True)
        return
    
    await callback.answer("📤 Отправляю превью...")
    
    # Отправляем превью как отдельное сообщение
    if msg_data.get('photo_file_id'):
        await safe_edit_or_send(callback.message,
            photo=msg_data['photo_file_id'],
            text=msg_data.get('text', ''),
            force_new=True
        )
    else:
        await safe_edit_or_send(callback.message,
            text=msg_data['text'],
            force_new=True
        )


@router.callback_query(F.data == "broadcast_send_to_me")
async def broadcast_send_to_me(callback: CallbackQuery, bot: Bot):
    """Отправляет сообщение рассылки администратору для проверки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    msg_data = get_broadcast_message()
    
    if not msg_data or not msg_data.get('text'):
        await callback.answer("❌ Сообщение не задано", show_alert=True)
        return
    
    await callback.answer("📤 Отправляю вам сообщение...")
    
    try:
        # Отправляем сообщение администратору точно так же, как оно будет отправлено пользователям
        text = msg_data.get('text', '')
        photo_file_id = msg_data.get('photo_file_id')
        
        if photo_file_id:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photo_file_id,
                caption=text
            )
        else:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text
            )
        
        await callback.answer("✅ Сообщение отправлено вам в личку!", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка отправки тестового сообщения: {e}")
        await callback.answer("❌ Ошибка отправки сообщения", show_alert=True)


# ============================================================================
# ФИЛЬТРЫ
# ============================================================================

@router.callback_query(F.data.startswith("broadcast_filter:"))
async def broadcast_set_filter(callback: CallbackQuery):
    """Устанавливает фильтр получателей."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    filter_key = callback.data.split(":")[1]
    
    if filter_key not in BROADCAST_FILTERS:
        await callback.answer("❌ Неизвестный фильтр", show_alert=True)
        return
    
    set_setting('broadcast_filter', filter_key)
    
    # Обновляем экран
    msg_data = get_broadcast_message()
    has_message = msg_data is not None and msg_data.get('text')
    in_progress = is_broadcast_in_progress()
    user_count = count_users_for_broadcast(filter_key)
    
    text = (
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение всем пользователям бота.\n\n"
        "1️⃣ Отредактируйте сообщение\n"
        "2️⃣ Выберите фильтр получателей\n"
        "3️⃣ Нажмите «Начать рассылку»"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_main_kb(has_message, filter_key, in_progress, user_count)
    )
    await callback.answer(f"Фильтр: {BROADCAST_FILTERS[filter_key]}")


# ============================================================================
# ЗАПУСК РАССЫЛКИ
# ============================================================================

@router.callback_query(F.data == "broadcast_start")
async def broadcast_start(callback: CallbackQuery):
    """Показывает подтверждение рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Проверяем, не идёт ли уже рассылка
    if is_broadcast_in_progress():
        await callback.answer("⏳ Рассылка уже идёт!", show_alert=True)
        return
    
    # Проверяем наличие сообщения
    msg_data = get_broadcast_message()
    if not msg_data or not msg_data.get('text'):
        await callback.answer("❌ Сначала задайте сообщение!", show_alert=True)
        return
    
    current_filter = get_setting('broadcast_filter', 'all')
    user_count = count_users_for_broadcast(current_filter)
    
    if user_count == 0:
        await callback.answer("❌ Нет пользователей для рассылки!", show_alert=True)
        return
    
    filter_name = BROADCAST_FILTERS.get(current_filter, 'Все')
    
    text = (
        "🚀 <b>Подтверждение рассылки</b>\n\n"
        f"<b>Фильтр:</b> {filter_name}\n"
        f"<b>Получателей:</b> {user_count} чел.\n\n"
        "Начать рассылку?"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_confirm_kb(user_count)
    )
    await callback.answer()


@router.callback_query(F.data == "broadcast_in_progress")
async def broadcast_in_progress_callback(callback: CallbackQuery):
    """Уведомление о том, что рассылка уже идёт."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    await callback.answer("⏳ Рассылка уже идёт, дождитесь завершения", show_alert=True)


@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, bot: Bot):
    """Запускает рассылку."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Проверяем ещё раз
    if is_broadcast_in_progress():
        await callback.answer("⏳ Рассылка уже идёт!", show_alert=True)
        return
    
    msg_data = get_broadcast_message()
    if not msg_data:
        await callback.answer("❌ Сообщение не задано!", show_alert=True)
        return
    
    current_filter = get_setting('broadcast_filter', 'all')
    user_ids = get_users_for_broadcast(current_filter)
    
    if not user_ids:
        await callback.answer("❌ Нет получателей!", show_alert=True)
        return
    
    # Устанавливаем флаг
    set_broadcast_in_progress(True)
    
    total = len(user_ids)
    sent = 0
    blocked = 0
    
    # Начинаем рассылку
    await safe_edit_or_send(callback.message, 
        f"📤 <b>Рассылка запущена</b>\n\n"
        f"Отправлено: 0/{total}\n"
        f"🚫 Заблокировали бота: 0"
    )
    await callback.answer()
    
    text = msg_data.get('text', '')
    photo_file_id = msg_data.get('photo_file_id')
    
    for i, user_id in enumerate(user_ids):
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo_file_id,
                    caption=text
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=text
                )
            sent += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            blocked += 1
        except TelegramBadRequest as e:
            logger.warning(f"Ошибка отправки {user_id}: {e}")
            blocked += 1
        except Exception as e:
            logger.error(f"Неожиданная ошибка отправки {user_id}: {e}")
            blocked += 1
        
        # Обновляем прогресс каждые 10 сообщений
        if (i + 1) % 10 == 0 or (i + 1) == total:
            try:
                await safe_edit_or_send(callback.message, 
                    f"📤 <b>Рассылка в процессе...</b>\n\n"
                    f"Отправлено: {sent}/{total}\n"
                    f"🚫 Заблокировали бота: {blocked}"
                )
            except TelegramBadRequest:
                pass  # Сообщение не изменилось
        
        # Задержка между сообщениями
        await asyncio.sleep(0.5)
    
    # Сбрасываем флаг
    set_broadcast_in_progress(False)
    
    # Итоговый отчёт
    await safe_edit_or_send(callback.message, 
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"🚫 Заблокировали бота: {blocked}",
        reply_markup=home_only_kb()
    )


# ============================================================================
# ШАБЛОНЫ СООБЩЕНИЙ
# ============================================================================

@router.callback_query(F.data == "broadcast_templates")
async def broadcast_templates(callback: CallbackQuery):
    """Показывает список шаблонов сообщений."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    text = (
        "📋 <b>Шаблоны сообщений</b>\n\n"
        "Готовые шаблоны для разных категорий пользователей.\n"
        "Вы можете добавить промокод в сообщение.\n\n"
        "Выберите шаблон:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_templates_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("template_"))
async def broadcast_template_select(callback: CallbackQuery):
    """Обрабатывает выбор шаблона."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    template_type = callback.data.split("_", 1)[1]
    
    if template_type == "no_subscription" or template_type == "subscription":
        await show_template_promocode_selection(callback, "no_subscription")
    elif template_type.startswith("promo:"):
        # Формат: template_promo:template_type:promocode_id
        parts = callback.data.split(":")
        if len(parts) >= 3:
            tmpl_type = parts[1]
            promo_id = parts[2]
            await apply_template(callback, tmpl_type, promo_id)
    else:
        await callback.answer("❌ Неизвестный шаблон", show_alert=True)


async def show_template_promocode_selection(callback: CallbackQuery, template_type: str):
    """Показывает выбор промокода для шаблона."""
    from datetime import datetime
    
    # Получаем активные промокоды
    all_promos = get_all_promocodes()
    active_promos = []
    
    for promo in all_promos:
        expires_at = datetime.fromisoformat(promo['expires_at'])
        used_count = promo.get('used_count', 0)
        
        # Фильтруем только активные
        if datetime.now() <= expires_at and used_count < promo['max_uses']:
            active_promos.append(promo)
    
    text = (
        "<b>🎁 Шаблон для пользователей без подписки</b>\n\n"
        "Этот шаблон будет отправлен пользователям, которые:\n"
        "• Использовали пробную подписку, но она истекла\n"
        "• Никогда не имели подписок (даже пробной)\n\n"
        "Выберите промокод для добавления в сообщение:\n\n"
    )
    
    if active_promos:
        text += "Доступные промокоды:"
    else:
        text += "❌ Нет активных промокодов.\nВы можете создать их в разделе «Промокоды»."
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_template_promocode_kb(active_promos, template_type)
    )
    await callback.answer()


async def apply_template(callback: CallbackQuery, template_type: str, promo_id: str):
    """Применяет шаблон с промокодом."""
    from database.db_promocodes import get_promocode_by_code
    from database.requests import get_all_promocodes
    
    # Получаем промокод если указан
    promocode = None
    promo_code = None
    promo_discount = None
    
    if promo_id != "none":
        try:
            promo_id_int = int(promo_id)
            all_promos = get_all_promocodes()
            for p in all_promos:
                if p['id'] == promo_id_int:
                    promocode = p
                    promo_code = p['code']
                    promo_discount = p['discount_rub']
                    break
        except ValueError:
            pass
    
    # Генерируем текст шаблона для пользователей без подписки
    if template_type == "no_subscription":
        if promocode:
            text = (
                f"👋 <b>Привет!</b>\n\n"
                f"Мы заметили, что у вас нет активной подписки на наш VPN-сервис.\n\n"
                f"Специально для вас:\n"
                f"🎟️ Промокод <code>{promo_code}</code> на скидку <b>{promo_discount}₽</b>\n\n"
                f"🔐 Что вы получите:\n"
                f"• Быстрый и стабильный VPN\n"
                f"• Доступ к заблокированным сайтам\n"
                f"• Защиту ваших данных\n"
                f"• Несколько серверов на выбор\n"
                f"• Простую настройку за 2 минуты\n\n"
                f"💡 Как использовать промокод:\n"
                f"1. Нажмите «Купить ключ»\n"
                f"2. Выберите тариф\n"
                f"3. Введите промокод <code>{promo_code}</code>\n"
                f"4. Оплатите со скидкой!\n\n"
                f"⏰ Предложение ограничено!"
            )
        else:
            text = (
                f"👋 <b>Привет!</b>\n\n"
                f"Мы заметили, что у вас нет активной подписки на наш VPN-сервис.\n\n"
                f"🔐 Почему стоит попробовать:\n"
                f"• Быстрый и стабильный VPN\n"
                f"• Доступ к заблокированным сайтам\n"
                f"• Защита ваших данных\n"
                f"• Несколько серверов на выбор\n"
                f"• Простая настройка за 2 минуты\n\n"
                f"Нажмите «Купить ключ» чтобы начать!"
            )
    else:
        await callback.answer("❌ Неизвестный шаблон", show_alert=True)
        return
    
    # Сохраняем сообщение
    save_broadcast_message(text, None)
    
    # Устанавливаем фильтр "Без активных ключей" (inactive)
    # Этот фильтр включает и тех, у кого истекла пробная, и тех, кто никогда не покупал
    set_setting('broadcast_filter', 'inactive')
    
    await callback.answer("✅ Шаблон применён!")
    
    # Возвращаемся в главное меню рассылки
    msg_data = get_broadcast_message()
    has_message = msg_data is not None and msg_data.get('text')
    current_filter = get_setting('broadcast_filter', 'all')
    in_progress = is_broadcast_in_progress()
    user_count = count_users_for_broadcast(current_filter)
    
    text_menu = (
        "📢 <b>Рассылка</b>\n\n"
        "✅ Шаблон применён!\n\n"
        "Отправьте сообщение всем пользователям бота.\n\n"
        "1️⃣ Отредактируйте сообщение (если нужно)\n"
        "2️⃣ Выберите фильтр получателей\n"
        "3️⃣ Нажмите «Начать рассылку»"
    )
    
    await safe_edit_or_send(callback.message, 
        text_menu,
        reply_markup=broadcast_main_kb(has_message, current_filter, in_progress, user_count)
    )


# ============================================================================
# НАСТРОЙКИ АВТОУВЕДОМЛЕНИЙ
# ============================================================================

@router.callback_query(F.data == "broadcast_notifications")
async def broadcast_notifications(callback: CallbackQuery, state: FSMContext):
    """Показывает настройки автоуведомлений."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    days = int(get_setting('notification_days', '3'))
    
    text = (
        "⏰ <b>Автоуведомления</b>\n\n"
        "Бот автоматически напоминает пользователям об истечении VPN-ключей.\n\n"
        f"📅 Уведомлять за <b>{days}</b> дней до истечения\n"
        "📝 Текст уведомления настраивается отдельно"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_notifications_kb(days)
    )
    await callback.answer()


@router.callback_query(F.data == "broadcast_notify_days")
async def broadcast_notify_days(callback: CallbackQuery, state: FSMContext):
    """Начинает ввод количества дней."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.broadcast_waiting_notify_days)
    
    current_days = get_setting('notification_days', '3')
    
    text = (
        "📅 <b>За сколько дней уведомлять?</b>\n\n"
        f"Текущее значение: <b>{current_days}</b> дней\n\n"
        "Введите число от 1 до 30:"
    )
    
    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=broadcast_notify_back_kb()
    )
    await callback.answer()


@router.message(AdminStates.broadcast_waiting_notify_days)
async def broadcast_save_notify_days(message: Message, state: FSMContext):
    """Сохраняет количество дней для уведомления."""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text or not message.text.isdigit():
        await safe_edit_or_send(message,
            "❌ Введите число!",
            reply_markup=broadcast_notify_back_kb()
        )
        return
    
    days = int(message.text)
    if not 1 <= days <= 30:
        await safe_edit_or_send(message,
            "❌ Число должно быть от 1 до 30!",
            reply_markup=broadcast_notify_back_kb()
        )
        return
    
    set_setting('notification_days', str(days))
    
    await safe_edit_or_send(message,
        f"✅ Теперь уведомления будут отправляться за <b>{days}</b> дней до истечения."
    )
    
    # Возвращаемся в настройки уведомлений
    await state.set_state(AdminStates.broadcast_menu)
    
    text = (
        "⏰ <b>Автоуведомления</b>\n\n"
        "Бот автоматически напоминает пользователям об истечении VPN-ключей.\n\n"
        f"📅 Уведомлять за <b>{days}</b> дней до истечения\n"
        "📝 Текст уведомления настраивается отдельно"
    )
    
    await safe_edit_or_send(message,
        text,
        reply_markup=broadcast_notifications_kb(days),
        force_new=True
    )


@router.callback_query(F.data == "broadcast_notify_text")
async def broadcast_notify_text(callback: CallbackQuery, state: FSMContext):
    """Показывает/редактирует текст уведомления через универсальный редактор."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    from bot.handlers.admin.message_editor import show_message_editor
    
    await show_message_editor(
        callback.message, state,
        key='notification_text',
        back_callback='broadcast_notifications',
        help_text=(
            "📝 <b>Справка: Текст уведомления об истечении</b>\n\n"
            "Переменные:\n"
            "• <code>%дней%</code> — количество дней до истечения\n"
            "• <code>%имяподписки%</code> — название подписки"
        ),
        allowed_types=['text', 'photo'],
    )
    await callback.answer()

