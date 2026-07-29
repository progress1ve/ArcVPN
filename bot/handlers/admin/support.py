"""Быстрые ответы администратора в диалоги поддержки WebApp."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

import config
from bot.states.admin_states import AdminStates
from bot.utils.admin import is_admin
from bot.utils.text import escape_html
from database.requests import add_admin_support_message, get_support_thread

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("support_reply:"))
async def begin_support_reply(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    try:
        thread_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Диалог не найден", show_alert=True)
        return
    thread = get_support_thread(thread_id)
    if not thread:
        await callback.answer("Диалог не найден", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_support_reply)
    await state.update_data(support_thread_id=thread_id)
    await callback.answer()
    await callback.message.answer(
        f"Ответ пользователю <code>{thread['telegram_id']}</code>\n\n"
        "Отправьте одно текстовое сообщение. /cancel — отмена.",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_support_reply, F.text)
async def finish_support_reply(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Ответ отменён.")
        return
    data = await state.get_data()
    thread_id = int(data.get("support_thread_id") or 0)
    body = (message.text or "").strip()[:2000]
    thread = get_support_thread(thread_id)
    if not thread or not body:
        await state.clear()
        await message.answer("Диалог не найден или ответ пустой.")
        return
    saved = add_admin_support_message(thread_id, message.from_user.id, body)
    if not saved:
        await state.clear()
        await message.answer("Не удалось сохранить ответ.")
        return

    webapp_url = getattr(config, "WEBAPP_URL", "") or f"{config.SUBSCRIPTION_URL.rstrip('/')}/app/?design=flow"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть диалог", web_app=WebAppInfo(url=webapp_url))
    ]])
    try:
        await message.bot.send_message(
            chat_id=int(thread["telegram_id"]),
            text=f"💬 <b>Поддержка ArcVPN ответила</b>\n\n{escape_html(body)}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        delivery = "Ответ сохранён и отправлен пользователю."
    except Exception as exc:
        logger.warning("Ответ support thread %s сохранён, но Telegram delivery failed: %s", thread_id, exc)
        delivery = "Ответ сохранён в WebApp, но Telegram-уведомление не доставлено."
    await state.clear()
    await message.answer(delivery)
