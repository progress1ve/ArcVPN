"""Deliver only device-import events queued after the feature was enabled."""
from datetime import datetime, timezone
from database.connection import get_db
from database.db_webapp import notification_allowed
from bot.services.notifications import send_to_user
from bot.utils.text import escape_html

async def deliver_device_notifications(bot) -> dict:
    with get_db() as conn:
        rows = [dict(row) for row in conn.execute("""SELECT n.*,u.telegram_id,u.is_banned
            FROM device_connection_notifications n JOIN users u ON u.id=n.user_id
            WHERE n.sent_at IS NULL AND n.attempt_count<5 AND datetime(n.next_attempt_at)<=datetime('now')
            ORDER BY n.id LIMIT 100""").fetchall()]
    result = {"sent":0,"skipped":0,"failed":0}
    for row in rows:
        allowed = int(row['telegram_id'])>0 and not row['is_banned'] and notification_allowed(row['telegram_id'], 'connection')
        delivered = False
        if allowed:
            try:
                delivered = await send_to_user(bot, row['telegram_id'],
                    "🔔 <b>Новое устройство в ArcVPN</b>\n\n"
                    + f"Устройство: <b>{escape_html(row['display_name'])}</b>\n"
                    + "Если это были не вы, откройте Настройки → Устройства и удалите неизвестное устройство.")
            except Exception:
                delivered = False
        with get_db() as conn:
            if delivered or not allowed:
                conn.execute("UPDATE device_connection_notifications SET sent_at=CURRENT_TIMESTAMP WHERE id=?", (row['id'],))
                result['sent' if delivered else 'skipped'] += 1
            else:
                conn.execute("UPDATE device_connection_notifications SET attempt_count=attempt_count+1,next_attempt_at=datetime('now','+5 minutes') WHERE id=?", (row['id'],))
                result['failed'] += 1
    return result
