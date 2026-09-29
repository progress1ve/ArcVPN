"""Export owner-only repaired links to a private artifact, never stdout."""
import asyncio
import sqlite3
import sys
import urllib.parse
from pathlib import Path

ROOT = Path('/root/ArcVPN')
sys.path.insert(0, str(ROOT))
import subscription_api as api
from database.connection import DB_PATH

async def run():
    with sqlite3.connect(str(DB_PATH)) as db:
        row = db.execute("SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id WHERE lower(u.username)='progressive_dev' AND k.expires_at>datetime('now') ORDER BY k.expires_at DESC LIMIT 1").fetchone()
    if not row:
        raise RuntimeError('Owner active key not found')
    key = api.get_active_key_by_subscription_id(row[0])
    links = await api._native_remnawave_links(key)
    parts = ['# ArcVPN — CDN GET/header\n\nОбновлено 29.09.2026. Только для владельца.\n']
    for path, name in [('/api-test', 'Эстония'), ('/api-fin', 'Финляндия')]:
        link = next((v for v in links if urllib.parse.urlsplit(v).hostname == 'cdn-de.arccnet.space'
                     and urllib.parse.parse_qs(urllib.parse.urlsplit(v).query).get('path') == [path]), None)
        if not link:
            raise RuntimeError('Missing managed CDN path: ' + path)
        link = api._normalize_native_share_link(link).rsplit('#', 1)[0] + '#' + urllib.parse.quote('ArcVPN CDN → Москва → ' + name)
        parts.append('\n## ' + name + '\n\n```text\n' + link + '\n```\n')
    target = Path('/opt/arcvpn/staging/owner-cdn-links.md')
    with target.open('w', encoding='utf-8') as f:
        target.chmod(0o600)
        f.write(''.join(parts))
    print('Exported two repaired owner links; credentials omitted')

if __name__ == '__main__':
    asyncio.run(run())
