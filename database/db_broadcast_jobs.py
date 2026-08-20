"""Persistent jobs for restart-safe Telegram broadcasts."""
from database.connection import get_db


def create_broadcast_job(created_by, filter_type, message_text, photo_file_id, user_ids):
    recipients = sorted({int(user_id) for user_id in user_ids})
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO broadcast_jobs
               (created_by, filter_type, message_text, photo_file_id, total_count)
               VALUES (?, ?, ?, ?, ?)""",
            (int(created_by), filter_type, message_text, photo_file_id, len(recipients)),
        )
        job_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO broadcast_job_recipients(job_id, telegram_id) VALUES (?, ?)",
            ((job_id, user_id) for user_id in recipients),
        )
        return job_id


def recover_interrupted_broadcasts():
    with get_db() as conn:
        return conn.execute(
            """UPDATE broadcast_jobs SET status='queued', updated_at=CURRENT_TIMESTAMP,
               last_error='Bot restarted; delivery resumed' WHERE status='running'"""
        ).rowcount


def has_active_broadcast():
    with get_db() as conn:
        return conn.execute(
            "SELECT 1 FROM broadcast_jobs WHERE status IN ('queued','running') LIMIT 1"
        ).fetchone() is not None


def claim_next_broadcast():
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM broadcast_jobs WHERE status='queued' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            return None
        conn.execute(
            """UPDATE broadcast_jobs SET status='running',
               started_at=COALESCE(started_at, CURRENT_TIMESTAMP), updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='queued'""", (row['id'],)
        )
        return dict(conn.execute("SELECT * FROM broadcast_jobs WHERE id=?", (row['id'],)).fetchone())


def get_pending_recipient(job_id):
    with get_db() as conn:
        row = conn.execute(
            """SELECT telegram_id FROM broadcast_job_recipients
               WHERE job_id=? AND status='pending' ORDER BY telegram_id LIMIT 1""", (job_id,)
        ).fetchone()
        return int(row['telegram_id']) if row else None


def mark_broadcast_recipient(job_id, telegram_id, status, error=None):
    counter = {'sent': 'sent_count', 'blocked': 'blocked_count', 'failed': 'failed_count'}[status]
    with get_db() as conn:
        changed = conn.execute(
            """UPDATE broadcast_job_recipients SET status=?, attempts=attempts+1,
               last_error=?, sent_at=CASE WHEN ?='sent' THEN CURRENT_TIMESTAMP ELSE sent_at END
               WHERE job_id=? AND telegram_id=? AND status='pending'""",
            (status, error, status, job_id, telegram_id),
        ).rowcount
        if changed:
            conn.execute(
                f"UPDATE broadcast_jobs SET {counter}={counter}+1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (job_id,),
            )


def complete_broadcast(job_id):
    with get_db() as conn:
        conn.execute(
            """UPDATE broadcast_jobs SET status='completed', completed_at=CURRENT_TIMESTAMP,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""", (job_id,)
        )
        return dict(conn.execute("SELECT * FROM broadcast_jobs WHERE id=?", (job_id,)).fetchone())
