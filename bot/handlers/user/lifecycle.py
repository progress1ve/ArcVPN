"""Feedback and win-back callbacks for lifecycle messages."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, ForceReply, Message, InlineKeyboardButton, InlineKeyboardMarkup

from database.connection import get_db
from database.db_keys import extend_vpn_key
from bot.services.vpn_api import extend_key_on_server

router = Router()

RATING_CAPTION = (
    "💙 <b>Поможете сделать ArcVPN лучше?</b>\n\n"
    "Пробная подписка работает уже день. Что нам важнее всего улучшить?\n\n"
    "Выберите один вариант — так мы быстрее поймём, что действительно мешает."
)
RATING_THANK_YOU = "💙 <b>Спасибо за ответ!</b>\n\nМы сохранили его и используем при следующих улучшениях ArcVPN."
RATING_CHOICES = {"great", "connection", "speed", "service", "setup", "other"}


def rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💙 Всё работает отлично", callback_data="lifecycle_rating:great")],
        [InlineKeyboardButton(text="🔌 Не подключается или нестабильно", callback_data="lifecycle_rating:connection")],
        [InlineKeyboardButton(text="🐢 Низкая скорость", callback_data="lifecycle_rating:speed")],
        [InlineKeyboardButton(text="📱 Не работает нужный сервис", callback_data="lifecycle_rating:service")],
        [InlineKeyboardButton(text="🧩 Сложно настроить", callback_data="lifecycle_rating:setup")],
        [InlineKeyboardButton(text="💬 Другое", callback_data="lifecycle_rating:other")],
    ])


def _rating_event(conn, telegram_id: int):
    return conn.execute("""
        SELECT le.id, le.answer FROM lifecycle_events le JOIN users u ON u.id=le.user_id
        WHERE u.telegram_id=? AND le.event_key IN ('trial_day1_rating','day5_rating')
        ORDER BY le.id DESC
        LIMIT 1
    """, (telegram_id,)).fetchone()


def _record_answer(telegram_id: int, event_key: str, answer: str) -> tuple[bool, int | None]:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not row:
            return False, None
        user_id = int(row["id"])
        event = conn.execute(
            "SELECT id, answer FROM lifecycle_events WHERE user_id = ? AND event_key = ?",
            (user_id, event_key),
        ).fetchone()
        if not event:
            return False, user_id
        if event["answer"]:
            return False, user_id
        conn.execute(
            "UPDATE lifecycle_events SET answer = ?, answered_at = CURRENT_TIMESTAMP WHERE id = ?",
            (answer, event["id"]),
        )
        return True, user_id


def _record_rating_answer(telegram_id: int, answer: str) -> tuple[bool, int | None]:
    """Save one current answer; legacy numeric buttons are no longer accepted."""
    if answer not in RATING_CHOICES:
        return False, None
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not row:
            return False, None
        user_id = int(row["id"])
        event = _rating_event(conn, telegram_id)
        if not event or event["answer"]:
            return False, user_id
        conn.execute(
            "UPDATE lifecycle_events SET answer = ?, answered_at = CURRENT_TIMESTAMP WHERE id = ?",
            (answer, event["id"]),
        )
        return True, user_id


def _reset_rating_answer(telegram_id: int) -> bool:
    """Let a user undo a provisional free-text choice and choose again."""
    with get_db() as conn:
        event = _rating_event(conn, telegram_id)
        if not event or str(event["answer"] or "").split(":", 1)[0] not in {"other", "service"}:
            return False
        conn.execute("UPDATE lifecycle_events SET answer=NULL, answered_at=NULL WHERE id=?", (event["id"],))
        return True


def _record_rating_detail(telegram_id: int, details: str) -> bool:
    details = details.strip()[:500]
    if not details:
        return False
    with get_db() as conn:
        event = _rating_event(conn, telegram_id)
        if not event or event["answer"] not in {"other", "service"}:
            return False
        conn.execute(
            "UPDATE lifecycle_events SET answer=?, answered_at=CURRENT_TIMESTAMP WHERE id=?",
            (f"{event['answer']}: {details}", event["id"]),
        )
        return True


@router.callback_query(F.data.startswith("lifecycle_rating:"))
async def lifecycle_rating(callback: CallbackQuery):
    answer = callback.data.rsplit(":", 1)[-1]
    if answer == "back":
        if _reset_rating_answer(callback.from_user.id):
            await callback.message.edit_caption(caption=RATING_CAPTION, reply_markup=rating_keyboard(), parse_mode="HTML")
            await callback.answer("Выберите другой вариант")
        else:
            await callback.answer("Ответ уже завершён")
        return
    if answer in {"1", "3", "5"}:
        await callback.message.edit_caption(caption=RATING_CAPTION, reply_markup=rating_keyboard(), parse_mode="HTML")
        await callback.answer("Опрос обновлён — выберите вариант ниже")
        return
    saved, _ = _record_rating_answer(callback.from_user.id, answer)
    await callback.answer("Выберите вариант или вернитесь назад" if saved and answer in {"other", "service"}
                          else "Спасибо! Ответ сохранён 💙" if saved else "Вы уже оценили ArcVPN")
    if saved:
        if answer in {"other", "service"}:
            await callback.message.edit_caption(
                caption="💙 <b>Расскажите подробнее</b>\n\nНапишите ответ на сообщение ниже или вернитесь к выбору.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="↩️ К выбору", callback_data="lifecycle_rating:back")],
                ]), parse_mode="HTML",
            )
            prompt = ("Напишите, пожалуйста, что именно стоит улучшить."
                      if answer == "other" else "Напишите, какой сайт или приложение не работает.")
            await callback.message.answer(
                prompt,
                reply_markup=ForceReply(input_field_placeholder="Коротко опишите проблему"),
            )
        else:
            await callback.message.edit_caption(caption=RATING_THANK_YOU, reply_markup=None, parse_mode="HTML")


@router.message(F.reply_to_message.text.contains("что именно стоит улучшить") | F.reply_to_message.text.contains("какой сайт или приложение"))
async def lifecycle_rating_details(message: Message):
    if _record_rating_detail(message.from_user.id, message.text or ""):
        await message.answer("Записали подробности, спасибо 💙")
    else:
        await message.answer("Этот ответ уже не ожидается. Выберите вариант в опросе.")


@router.callback_query(F.data.startswith("lifecycle_winback:"))
async def lifecycle_winback(callback: CallbackQuery):
    reason = callback.data.rsplit(":", 1)[-1]
    saved, user_id = _record_answer(callback.from_user.id, "expired_winback", reason)
    if not saved or user_id is None:
        await callback.answer("Бонус уже был начислен", show_alert=True)
        return
    with get_db() as conn:
        key = conn.execute(
            "SELECT id FROM vpn_keys WHERE user_id = ? ORDER BY expires_at DESC LIMIT 1", (user_id,)
        ).fetchone()
    if key:
        key_id = int(key["id"])
        extend_vpn_key(key_id, 3)
        await extend_key_on_server(key_id, 3)
    await callback.answer("Подарили 3 дня подписки 🎁", show_alert=True)
    await callback.message.edit_caption(
        caption=(
            "🎁 <b>3 дня уже добавлены</b>\n\n"
            "Проверьте ArcVPN ещё раз. Если решите остаться — выгоднее всего тарифы "
            "на 3–12 месяцев: от 80 ₽ в месяц."
        ),
        reply_markup=None,
        parse_mode="HTML",
    )
    if reason == "competitor":
        await callback.message.answer(
            "Спасибо за ответ — для нас это очень ценно ❤️\n\n"
            "Напишите, пожалуйста, название VPN, которым вы пользуетесь, и почему решили выбрать его.",
            reply_markup=ForceReply(input_field_placeholder="Название VPN и причина выбора"),
        )


@router.callback_query(F.data == "lifecycle_offer:reason")
async def lifecycle_offer_reason(callback: CallbackQuery):
    """Open the existing reason survey from a trial conversion offer."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Дорого", callback_data="lifecycle_winback:expensive")],
        [InlineKeyboardButton(text="📉 Плохо работало", callback_data="lifecycle_winback:quality")],
        [InlineKeyboardButton(text="🔄 Пользуюсь другим VPN", callback_data="lifecycle_winback:competitor")],
        [InlineKeyboardButton(text="💬 Другое", callback_data="lifecycle_winback:other")],
    ])
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.message(F.reply_to_message.text.contains("название VPN"))
async def lifecycle_competitor_details(message: Message):
    details = (message.text or "").strip()[:500]
    if not details:
        return
    with get_db() as conn:
        conn.execute("""
            UPDATE lifecycle_events SET answer = 'competitor: ' || ?
            WHERE user_id=(SELECT id FROM users WHERE telegram_id=?)
              AND event_key='expired_winback' AND answer='competitor'
        """, (details, message.from_user.id))
    await message.answer("Записали, спасибо! Это поможет нам стать лучше 💙")
