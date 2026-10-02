from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sqlite3
from unittest.mock import AsyncMock

import subscription_api as api
from monitoring.cdn_connections import schema, ingest, identity_hash


def test_lte_presence_is_separate_from_normal_and_stale_activity(monkeypatch):
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE users(id INTEGER,telegram_id INTEGER); CREATE TABLE vpn_keys(user_id INTEGER,panel_email TEXT); INSERT INTO users VALUES(1,100),(2,200),(3,300); INSERT INTO vpn_keys VALUES(1,"arc_user_1"),(2,"arc_user_2"),(3,"arc_user_3");')
    @contextmanager
    def db(): yield conn
    monkeypatch.setattr(api, 'get_db', db)
    monkeypatch.setattr(api, '_load_remnawave_runtime_config', lambda: {'REMNAWAVE_PANEL_URL':'https://example.com','REMNAWAVE_API_TOKEN':'test'})
    now = datetime.now(timezone.utc)
    schema(conn)
    ingest(conn, '87.251.19.197', {'available': True, 'identities': [
        {'hash': identity_hash(101), 'probe_at': now.timestamp()},
        {'hash': identity_hash(102), 'user_at': now.timestamp()},
    ]}, now.timestamp())
    def item(username, tg, at):
        return {'username': username, 'telegramId': tg, 'id': 101 if username == 'arc_lte_1' else 102 if username == 'arc_user_2' else 103, 'userTraffic': {'onlineAt':at.isoformat(),'lastConnectedNodeUuid':'ee'}}
    panel = AsyncMock()
    panel._request.side_effect = [{'total':4,'users':[item('arc_lte_1',100,now),item('arc_user_1',100,now),item('arc_user_2',200,now),item('arc_lte_3',300,now-timedelta(minutes=5))]}, [{'uuid':'ee','name':'Estonia'}]]
    monkeypatch.setattr(api, 'RemnawaveClient', lambda server: panel)
    monkeypatch.setattr(api, '_ADMIN_PRESENCE_CACHE', (0,False,{}))
    authoritative, rows = api._admin_live_presence()
    assert authoritative and rows[1]['lte_online'] is True
    assert rows[2]['lte_online'] is False
    assert rows[1]['lte_usage'] == 'probe'
    assert rows[2]['lte_usage'] == 'user'
    assert 3 not in rows
