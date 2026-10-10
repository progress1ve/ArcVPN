"""Хранилище диалогов поддержки между WebApp и администраторами Telegram."""

from typing import Any, Dict, Optional

from .connection import get_db

SPAM_HANDOFF = "Вы отправили много сообщений подряд. Зовём на помощь менеджера — он ответит в этом чате. ИИ пока приостановлен."

def _thread_for_telegram_id(telegram_id: int, create: bool = False) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if not user:
            return None
        if create:
            conn.execute("INSERT OR IGNORE INTO support_threads(user_id) VALUES (?)", (user["id"],))
        row = conn.execute("SELECT * FROM support_threads WHERE user_id = ?", (user["id"],)).fetchone()
        return dict(row) if row else None


def get_support_messages(telegram_id: int, after_id: int = 0, limit: int = 100) -> Dict[str, Any]:
    thread = _thread_for_telegram_id(telegram_id)
    if not thread:
        return {"thread_id": None, "messages": []}
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, sender, body, created_at, read_at,
                      (sender = 'admin' AND sender_telegram_id = 0) AS is_ai FROM support_messages
               WHERE thread_id = ? AND id > ? ORDER BY id ASC LIMIT ?""",
            (thread["id"], max(0, after_id), min(max(1, limit), 200)),
        ).fetchall()
        conn.execute(
            "UPDATE support_messages SET read_at = CURRENT_TIMESTAMP "
            "WHERE thread_id = ? AND sender = 'admin' AND read_at IS NULL",
            (thread["id"],),
        )
        return {"thread_id": thread["id"], "messages": [dict(row) for row in rows]}


def add_user_support_message(telegram_id: int, body: str) -> Optional[Dict[str, Any]]:
    thread = _thread_for_telegram_id(telegram_id, create=True)
    if not thread:
        return None
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        state = conn.execute("SELECT * FROM support_threads WHERE id=?", (thread['id'],)).fetchone()
        if state['status'] == 'closed':
            start_id = conn.execute("SELECT COALESCE(MAX(id),0)+1 FROM support_messages WHERE thread_id=?", (thread['id'],)).fetchone()[0]
            conn.execute("UPDATE support_threads SET ai_handoff_reason=NULL,ai_context_start_id=? WHERE id=?", (start_id,thread['id']))
            conn.execute("DELETE FROM support_ai_attempts WHERE thread_id=?", (thread['id'],))
        handoff = state['ai_handoff_reason'] if state['status'] != 'closed' else None
        handoff_started = False
        if not handoff:
            conn.execute("DELETE FROM support_ai_attempts WHERE thread_id=? AND created_at<datetime('now','-5 minutes')", (thread['id'],))
            conn.execute("INSERT INTO support_ai_attempts(thread_id) VALUES (?)", (thread['id'],))
            attempts = conn.execute("SELECT COUNT(*) FROM support_ai_attempts WHERE thread_id=?", (thread['id'],)).fetchone()[0]
            if attempts >= 10:
                handoff = 'spam'
                handoff_started = True
                conn.execute("UPDATE support_threads SET ai_handoff_reason='spam' WHERE id=?", (thread['id'],))
        recent = conn.execute(
            """SELECT COUNT(*) count FROM support_messages WHERE thread_id = ?
               AND sender = 'user' AND created_at >= datetime('now', '-1 minute')""",
            (thread["id"],),
        ).fetchone()["count"]
        if int(recent) >= 6 and not handoff_started:
            return {"rate_limited": True, "thread_id": thread["id"]}
        cur = conn.execute(
            "INSERT INTO support_messages(thread_id, sender, sender_telegram_id, body) VALUES (?, 'user', ?, ?)",
            (thread["id"], telegram_id, body),
        )
        conn.execute("UPDATE support_threads SET status = 'open', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread["id"],))
        row = conn.execute(
            "SELECT id, sender, body, created_at, read_at FROM support_messages WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        result = {"thread_id": thread["id"], "message": dict(row), "ai_handoff": bool(handoff), "handoff_started": handoff_started}
        if handoff_started:
            notice = conn.execute("INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES (?,'admin',0,?)", (thread['id'], SPAM_HANDOFF))
            result['assistant_message'] = dict(conn.execute("SELECT id,sender,body,created_at,read_at,1 AS is_ai FROM support_messages WHERE id=?", (notice.lastrowid,)).fetchone())
        return result


def get_support_thread(thread_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT t.id, t.status, u.telegram_id, u.username, u.first_name
               FROM support_threads t JOIN users u ON u.id = t.user_id WHERE t.id = ?""",
            (thread_id,),
        ).fetchone()
        return dict(row) if row else None


def add_admin_support_message(thread_id: int, admin_telegram_id: int, body: str) -> Optional[Dict[str, Any]]:
    if not get_support_thread(thread_id):
        return None
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO support_messages(thread_id, sender, sender_telegram_id, body) VALUES (?, 'admin', ?, ?)",
            (thread_id, admin_telegram_id, body),
        )
        conn.execute("UPDATE support_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
        conn.execute("UPDATE support_threads SET ai_handoff_reason=NULL WHERE id=?", (thread_id,))
        conn.execute("DELETE FROM support_ai_attempts WHERE thread_id=?", (thread_id,))
        row = conn.execute(
            "SELECT id, sender, body, created_at, read_at FROM support_messages WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return dict(row)


def get_assistant_context(thread_id: int, message_id: int):
    """Return only conversation text when the requested turn is still latest."""
    with get_db() as conn:
        latest = conn.execute("SELECT id,sender FROM support_messages WHERE thread_id=? ORDER BY id DESC LIMIT 1", (thread_id,)).fetchone()
        if not latest or latest["id"] != message_id or latest["sender"] != "user":
            return []
        thread = conn.execute("SELECT status,ai_handoff_reason,ai_context_start_id FROM support_threads WHERE id=?", (thread_id,)).fetchone()
        if not thread or thread['status'] != 'open' or thread['ai_handoff_reason']:
            return []
        rows = conn.execute("SELECT sender,body FROM support_messages WHERE thread_id=? AND id>=? ORDER BY id DESC LIMIT 16", (thread_id,thread['ai_context_start_id'])).fetchall()
        return [dict(row) for row in reversed(rows)]


def add_assistant_support_message(thread_id: int, message_id: int, body: str):
    """Zero sender ID identifies AI; existing sender CHECK and human IDs stay intact."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        latest = conn.execute("SELECT id,sender FROM support_messages WHERE thread_id=? ORDER BY id DESC LIMIT 1", (thread_id,)).fetchone()
        thread = conn.execute("SELECT status,ai_handoff_reason FROM support_threads WHERE id=?", (thread_id,)).fetchone()
        if not thread or thread["status"] != "open" or thread['ai_handoff_reason'] or not latest or latest["id"] != message_id or latest["sender"] != "user":
            return False
        conn.execute("INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES (?,'admin',0,?)", (thread_id, body[:2000]))
        conn.execute("UPDATE support_threads SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (thread_id,))
        return True


def assistant_handoff_reason(thread_id):
    if not thread_id:
        return None
    with get_db() as conn:
        row = conn.execute('SELECT ai_handoff_reason FROM support_threads WHERE id=?', (thread_id,)).fetchone()
        return row['ai_handoff_reason'] if row else None


def handoff_to_manager(thread_id, message_id, body, reason):
    """Latch once and discard any stale AI work racing a human or a newer turn."""
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        latest = conn.execute('SELECT id,sender FROM support_messages WHERE thread_id=? ORDER BY id DESC LIMIT 1', (thread_id,)).fetchone()
        thread = conn.execute('SELECT status,ai_handoff_reason FROM support_threads WHERE id=?', (thread_id,)).fetchone()
        if not thread or thread['status'] != 'open' or thread['ai_handoff_reason'] or not latest or latest['id'] != message_id or latest['sender'] != 'user':
            return False
        conn.execute('UPDATE support_threads SET ai_handoff_reason=?,updated_at=CURRENT_TIMESTAMP WHERE id=?', (reason,thread_id))
        conn.execute("INSERT INTO support_messages(thread_id,sender,sender_telegram_id,body) VALUES (?,'admin',0,?)", (thread_id,body[:2000]))
        return True
