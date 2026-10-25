"""One-time backfill for pre-feature manager replies; no customer messages."""
import argparse
import json
import os
from pathlib import Path
from database.connection import get_db


def pause_existing_human_threads(conn):
    rows = conn.execute("""SELECT t.id,t.ai_handoff_reason,t.ai_context_start_id FROM support_threads t
        WHERE t.status!='closed' AND t.ai_handoff_reason IS NULL AND EXISTS(
          SELECT 1 FROM support_messages m WHERE m.thread_id=t.id AND m.sender='admin'
            AND COALESCE(m.sender_telegram_id,-1)!=0 AND m.id>=t.ai_context_start_id)""").fetchall()
    for row in rows:
        conn.execute("UPDATE support_threads SET ai_handoff_reason='human' WHERE id=? AND ai_handoff_reason IS NULL", (row['id'],))
    return [dict(row) for row in rows]


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', required=True)
    p.parse_args()
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        rows = pause_existing_human_threads(conn)
        target = Path('/root/ArcVPN/.secrets/support-human-backfill-20261025.json')
        if rows and not target.exists():
            with os.fdopen(os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as f:
                json.dump(rows, f)
    print(json.dumps({'legacy_human_threads_paused': len(rows)}))
