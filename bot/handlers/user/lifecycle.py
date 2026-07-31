"""Feedback and win-back callbacks for lifecycle messages."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.connection import get_db
from database.db_keys import extend_vpn_key
from bot.services.vpn_api import extend_key_on_server

router = Router()


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


@router.callback_query(F.data.startswith("lifecycle_rating:"))
async def lifecycle_rating(callback: CallbackQuery):
    rating = callback.data.rsplit(":", 1)[-1]
    saved, _ = _record_answer(callback.from_user.id, "day5_rating", rating)
    await callback.answer("Спасибо! Ответ сохранён 💙" if saved else "Вы уже оценили ArcVPN")
    if saved:
        await callback.message.edit_caption(
            caption="💙 <b>Спасибо за оценку!</b>\n\nОна поможет нам сделать ArcVPN удобнее.",
            reply_markup=None,
        )


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
    )
