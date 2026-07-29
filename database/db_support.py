"""Хранилище диалогов поддержки между WebApp и администраторами Telegram."""

from typing import Any, Dict, Optional

from .connection import get_db


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
            """SELECT id, sender, body, created_at, read_at FROM support_messages
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
        recent = conn.execute(
            """SELECT COUNT(*) count FROM support_messages WHERE thread_id = ?
               AND sender = 'user' AND created_at >= datetime('now', '-1 minute')""",
            (thread["id"],),
        ).fetchone()["count"]
        if int(recent) >= 6:
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
        return {"thread_id": thread["id"], "message": dict(row)}


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
        cur = conn.execute(
            "INSERT INTO support_messages(thread_id, sender, sender_telegram_id, body) VALUES (?, 'admin', ?, ?)",
            (thread_id, admin_telegram_id, body),
        )
        conn.execute("UPDATE support_threads SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
        row = conn.execute(
            "SELECT id, sender, body, created_at, read_at FROM support_messages WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return dict(row)
