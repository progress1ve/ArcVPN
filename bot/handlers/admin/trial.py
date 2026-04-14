"""
Обработчики раздела «Пробная подписка» в админ-панели.

Управление функцией пробного периода:
- Включение/выключение
- Настройка количества дней
- Настройка лимита трафика
- Редактирование текста страницы
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.states.admin_states import AdminStates
from bot.utils.admin import is_admin
from bot.utils.text import escape_html, safe_edit_or_send

logger = logging.getLogger(__name__)

from bot.utils.text import safe_edit_or_send

router = Router()


# ============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: ОТОБРАЖЕНИЕ МЕНЮ
# ============================================================================

async def show_trial_menu(callback: CallbackQuery):
    """Показывает меню настроек пробной подписки."""
    from database.requests import (
        is_trial_enabled, get_trial_days, get_trial_traffic_gb
    )
    from bot.keyboards.admin import trial_settings_kb

    enabled = is_trial_enabled()
    days = get_trial_days()
    traffic_gb = get_trial_traffic_gb()

    status_text = "✅ Включена" if enabled else "❌ Выключена"
    traffic_text = f"{traffic_gb} ГБ" if traffic_gb > 0 else "Безлимит"

    text = (
        "🎁 <b>Пробная подписка</b>\n\n"
        "Управление функцией пробного доступа для новых пользователей.\n\n"
        f"📌 <b>Статус:</b> {escape_html(status_text)}\n"
        f"⏱ <b>Длительность:</b> {days} дней\n"
        f"📊 <b>Трафик:</b> {traffic_text}\n\n"
        "❓ <b>Как работает:</b>\n"
        "• Если включено — кнопка «🎁 Получить X дней бесплатно» появляется на главной у пользователей, которые ещё не использовали пробный период.\n"
        "• При активации — пользователю выдаётся ключ с указанными параметрами.\n"
        "• Каждый пользователь может активировать пробный период только один раз."
    )

    await safe_edit_or_send(callback.message, 
        text,
        reply_markup=trial_settings_kb(enabled)
    )
    await callback.answer()


# ============================================================================
# ГЛАВНЫЙ ЭКРАН ПРОБНОЙ ПОДПИСКИ
# ============================================================================

@router.callback_query(F.data == "admin_trial")
async def admin_trial_menu(callback: CallbackQuery):
    """Показывает меню управления пробной подпиской."""
    if not is_admin(callback.from_user.id):
        return
    await show_trial_menu(callback)


# ============================================================================
# ВКЛЮЧЕНИЕ / ВЫКЛЮЧЕНИЕ
# ============================================================================

@router.callback_query(F.data == "admin_trial_toggle")
async def admin_trial_toggle(callback: CallbackQuery):
    """Переключает статус пробной подписки."""
    if not is_admin(callback.from_user.id):
        return

    from database.requests import get_setting, set_setting, is_trial_enabled

    current = is_trial_enabled()
    new_value = '0' if current else '1'
    set_setting('trial_enabled', new_value)

    action = "включена" if new_value == '1' else "выключена"
    logger.info(f"Пробная подписка {action} (admin: {callback.from_user.id})")

    await show_trial_menu(callback)


# ============================================================================
# РЕДАКТИРОВАНИЕ ТЕКСТА
# ============================================================================

@router.callback_query(F.data == "admin_trial_edit_text")
async def admin_trial_edit_text_start(callback: CallbackQuery, state: FSMContext):
    """Начинает редактирование текста пробной подписки через универсальный редактор."""
    if not is_admin(callback.from_user.id):
        return

    from bot.handlers.admin.message_editor import show_message_editor

    await show_message_editor(
        callback.message, state,
        key='trial_page_text',
        back_callback='admin_trial',
        allowed_types=['text', 'photo'],
    )
    await callback.answer()


# ============================================================================
# НАСТРОЙКА КОЛИЧЕСТВА ДНЕЙ
# ============================================================================

@router.callback_query(F.data == "admin_trial_set_days")
async def admin_trial_set_days_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения количества дней."""
    if not is_admin(callback.from_user.id):
        return

    from database.requests import get_trial_days
    from bot.keyboards.admin import back_button, home_button
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    current_days = get_trial_days()

    builder = InlineKeyboardBuilder()
    builder.row(back_button("admin_trial"))
    builder.row(home_button())

    await safe_edit_or_send(callback.message,
        f"⏱ <b>Настройка длительности пробного периода</b>\n\n"
        f"Текущее значение: <b>{current_days} дней</b>\n\n"
        f"Отправьте новое количество дней (число от 1 до 365):",
        reply_markup=builder.as_markup()
    )

    await state.set_state(AdminStates.trial_set_days)
    await callback.answer()


@router.message(StateFilter(AdminStates.trial_set_days))
async def admin_trial_set_days_process(message: Message, state: FSMContext):
    """Обрабатывает ввод количества дней."""
    if not is_admin(message.from_user.id):
        return

    from database.requests import set_trial_days
    from bot.keyboards.admin import back_button, home_button
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    try:
        days = int(message.text.strip())
        if days < 1 or days > 365:
            raise ValueError("Число вне диапазона")

        set_trial_days(days)
        logger.info(f"Длительность пробного периода изменена на {days} дней (admin: {message.from_user.id})")

        builder = InlineKeyboardBuilder()
        builder.row(back_button("admin_trial"))

        await message.answer(
            f"✅ Длительность пробного периода установлена: <b>{days} дней</b>",
            reply_markup=builder.as_markup()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат. Отправьте число от 1 до 365:"
        )


# ============================================================================
# НАСТРОЙКА ЛИМИТА ТРАФИКА
# ============================================================================

@router.callback_query(F.data == "admin_trial_set_traffic")
async def admin_trial_set_traffic_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения лимита трафика."""
    if not is_admin(callback.from_user.id):
        return

    from database.requests import get_trial_traffic_gb
    from bot.keyboards.admin import back_button, home_button
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    current_traffic = get_trial_traffic_gb()
    traffic_text = f"{current_traffic} ГБ" if current_traffic > 0 else "Безлимит"

    builder = InlineKeyboardBuilder()
    builder.row(back_button("admin_trial"))
    builder.row(home_button())

    await safe_edit_or_send(callback.message,
        f"📊 <b>Настройка лимита трафика</b>\n\n"
        f"Текущее значение: <b>{traffic_text}</b>\n\n"
        f"Отправьте новое количество гигабайт (число от 0 до 1000):\n"
        f"• 0 = безлимит\n"
        f"• 1-1000 = лимит в ГБ",
        reply_markup=builder.as_markup()
    )

    await state.set_state(AdminStates.trial_set_traffic)
    await callback.answer()


@router.message(StateFilter(AdminStates.trial_set_traffic))
async def admin_trial_set_traffic_process(message: Message, state: FSMContext):
    """Обрабатывает ввод лимита трафика."""
    if not is_admin(message.from_user.id):
        return

    from database.requests import set_trial_traffic_gb
    from bot.keyboards.admin import back_button, home_button
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    try:
        traffic_gb = int(message.text.strip())
        if traffic_gb < 0 or traffic_gb > 1000:
            raise ValueError("Число вне диапазона")

        set_trial_traffic_gb(traffic_gb)
        traffic_text = f"{traffic_gb} ГБ" if traffic_gb > 0 else "Безлимит"
        logger.info(f"Лимит трафика пробного периода изменен на {traffic_text} (admin: {message.from_user.id})")

        builder = InlineKeyboardBuilder()
        builder.row(back_button("admin_trial"))

        await message.answer(
            f"✅ Лимит трафика установлен: <b>{traffic_text}</b>",
            reply_markup=builder.as_markup()
        )
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Неверный формат. Отправьте число от 0 до 1000:"
        )
