"""
Главный роутер админ-панели.

Обрабатывает вход в админку и главное меню.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.requests import get_all_servers
from bot.states.admin_states import AdminStates
from bot.keyboards.admin import admin_main_menu_kb
from bot.utils.admin import is_admin
from bot.utils.text import safe_edit_or_send

logger = logging.getLogger(__name__)

router = Router()


# ============================================================================
# ПРОВЕРКА АДМИНИСТРАТОРА
# ============================================================================




# ============================================================================
# ГЛАВНОЕ МЕНЮ АДМИНКИ
# ============================================================================

async def get_admin_stats_text() -> str:
    """Small status surface; all mutations live in Web Admin."""
    servers = get_all_servers()
    active = sum(1 for item in servers if item.get('is_active'))
    remnawave = sum(
        1 for item in servers
        if item.get('is_active') and str(item.get('panel_type') or '').lower() == 'remnawave'
    )
    authority = "🟢 настроен" if remnawave else "🔴 не настроен"
    return (
        "⚙️ <b>ArcVPN · состояние</b>\n\n"
        f"Remnawave: <b>{authority}</b>\n"
        f"Активных узлов: <b>{active}</b>\n\n"
        "<blockquote>Операции, платежи, тарифы и поддержка перенесены в Web Admin.</blockquote>"
    )


from aiogram.exceptions import TelegramBadRequest

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Показывает главное меню админ-панели."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.admin_menu)
    
    text = await get_admin_stats_text()
    
    try:
        await safe_edit_or_send(callback.message, 
            text,
            reply_markup=admin_main_menu_kb()
        )
    except TelegramBadRequest as e:
        if "is not modified" not in str(e):
            logger.error(f"Ошибка при обновлении меню: {e}")


# ============================================================================
# ПЕРЕАДРЕСАЦИЯ НА ПОДРОУТЕРЫ
# ============================================================================

# Раздел «Пользователи» реализован в users.py
# Раздел «Настройки бота» реализован в system.py
