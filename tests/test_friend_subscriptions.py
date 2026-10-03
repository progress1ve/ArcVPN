import asyncio
import sqlite3
from contextlib import contextmanager
from unittest.mock import AsyncMock

import pytest
import subscription_api as api
from bot.services import friend_subscriptions as friends
from database.migrations import migration_71


@pytest.fixture
def guest_db(monkeypatch):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users(id INTEGER PRIMARY KEY,telegram_id INTEGER,identity_source TEXT,
            referral_code TEXT,device_limit INTEGER,lte_quota_gb INTEGER,used_trial INTEGER,enforce_device_tokens INTEGER,
            lte_cycle_started_at TEXT,lte_cycle_reset_at TEXT,lte_client_uuid TEXT,
            lte_panel_username TEXT,lte_remnawave_user_id TEXT);
        CREATE TABLE vpn_keys(id INTEGER PRIMARY KEY,user_id INTEGER,sub_id TEXT,expires_at TEXT,panel_disabled_at TEXT);
        CREATE TABLE user_devices(id INTEGER PRIMARY KEY,user_id INTEGER,is_active INTEGER,
            revoked_at TEXT,device_sub_id TEXT);
    """)
    migration_71(conn)
    @contextmanager
    def db():
        yield conn
        conn.commit()
    monkeypatch.setattr(friends, 'get_db', db)
    monkeypatch.setattr(api, 'get_db', db)
    return conn


def options(**changes):
    return dict(label='Friends',days=3,device_limit=1,lte_quota_gb=15,
                request_id='11111111-1111-4111-8111-111111111111', **changes)


def test_validation_and_idempotent_identity(guest_db):
    for name, value in [('days', 0), ('device_limit', True), ('lte_quota_gb', 501), ('days', 0.7)]:
        data = options(); data[name] = value
        with pytest.raises(ValueError): friends.validate_options(data)
    half = options(); half.update(days=0.5, lte_quota_gb=5)
    assert friends.validate_options(half)['days'] == 0.5
    half['lte_quota_gb'] = 10
    assert friends.validate_options(half)['lte_quota_gb'] == 10
    parsed = friends.validate_options(options())
    row, created = friends.reserve_guest(parsed, 'owner')
    same, again = friends.reserve_guest(parsed, 'owner')
    assert created and not again and row['id'] == same['id']
    assert guest_db.execute('SELECT count(*) FROM users').fetchone()[0] == 1
    assert row['device_limit'] == 1
    assert guest_db.execute('SELECT enforce_device_tokens FROM users').fetchone()[0] == 1
    assert not friends.list_guests()[0]['sub_id']


def test_expiry_blocks_before_panel_cleanup_and_cleanup_retries(guest_db, monkeypatch):
    row, _ = friends.reserve_guest(friends.validate_options(options()), 'owner')
    uid = row['user_id']
    guest_db.execute("UPDATE friend_subscriptions SET state='active',expires_at=datetime('now','-1 second')")
    guest_db.execute("INSERT INTO vpn_keys(id,user_id,sub_id,expires_at) VALUES(1,?,'guest-token',datetime('now','-1 second'))", (uid,))
    guest_db.execute("INSERT INTO user_devices VALUES(1,?,1,NULL,'alias')", (uid,))
    guest_db.commit()
    assert not friends.guest_access_allowed('guest-token')
    client = AsyncMock()
    client._assert_write_allowed = lambda value: None
    client.get_user.side_effect = [{'id':'main-panel'}, {'id':'lte-panel'}]
    client._request.side_effect = RuntimeError('provider offline')
    monkeypatch.setattr(friends, 'authority_server', lambda: {})
    import bot.services.panels.factory as vpn
    monkeypatch.setattr(vpn, 'create_panel_client', lambda server: client)
    with pytest.raises(RuntimeError): asyncio.run(friends.cleanup_guests())
    assert guest_db.execute('SELECT state FROM friend_subscriptions').fetchone()[0] == 'deleting'
    assert guest_db.execute('SELECT is_active FROM user_devices').fetchone()[0] == 0
    client.get_user.side_effect = [{'id':'main-panel'}, {'id':'lte-panel'}]
    client._request.side_effect = None
    asyncio.run(friends.cleanup_guests())
    assert guest_db.execute('SELECT state FROM friend_subscriptions').fetchone()[0] == 'deleted'
    assert guest_db.execute('SELECT sub_id FROM vpn_keys').fetchone()[0] is None
    assert client.get_user.call_args_list[-2].args == (f'arc_user_{uid}',)
    assert client.get_user.call_args_list[-1].args == (f'arc_lte_{uid}',)


def test_api_authorization_and_origin(guest_db, monkeypatch):
    client = api.app.test_client()
    monkeypatch.setattr(api, '_admin_authorized', lambda permission: False)
    assert client.get('/api/admin/friend-subscriptions').status_code == 403
    monkeypatch.setattr(api, '_admin_authorized', lambda permission: True)
    assert client.post('/api/admin/friend-subscriptions', json=options()).status_code == 403
    assert client.post('/api/admin/friend-subscriptions', json={'days': 1}, headers={'Origin':'https://arccnet.space'}).status_code == 400
    assert client.post('/api/admin/friend-subscriptions', json={'days': 1}, headers={'Origin':'https://panel.arccnet.space'}).status_code == 400
    assert client.post('/api/admin/friend-subscriptions', json=options(), headers={'Origin':'https://evil.example'}).status_code == 403
    result = client.get('/api/admin/friend-subscriptions')
    assert result.status_code == 200
    assert 'no-store' in result.headers['Cache-Control']


def test_partial_provision_failure_never_publishes_url(guest_db, monkeypatch):
    import database.requests as db
    import bot.services.panels.factory as vpn
    import bot.services.lte_identity as lte
    row, _ = friends.reserve_guest(friends.validate_options(options()), 'owner')
    client = AsyncMock()
    client.add_client.return_value = {'vlessUuid': 'test-uuid'}
    client.update_client_full.return_value = True
    monkeypatch.setattr(friends, 'authority_server', lambda: {'id': 1})
    monkeypatch.setattr(db, 'get_standard_trial_tariff', lambda: {'id': 1})
    monkeypatch.setattr(vpn, 'create_panel_client', lambda server: client)
    monkeypatch.setattr(lte, 'provision_lte_identity', AsyncMock(side_effect=RuntimeError('LTE failed')))
    with pytest.raises(RuntimeError): asyncio.run(friends.provision_guest(row))
    assert friends.list_guests()[0]['state'] == 'failed'
    assert not friends.list_guests()[0]['sub_id']
    client.close.assert_awaited_once()


def test_successful_provision_preserves_selected_limits_and_exact_expiry(guest_db, monkeypatch):
    import database.requests as db
    import bot.services.panels.factory as factory
    import bot.services.lte_identity as lte
    row, _ = friends.reserve_guest(friends.validate_options(options()), 'owner')
    client = AsyncMock()
    client.add_client.return_value = {'vlessUuid': 'test-uuid'}
    client.update_client_full.return_value = True
    monkeypatch.setattr(friends, 'authority_server', lambda: {'id': 1})
    monkeypatch.setattr(db, 'get_standard_trial_tariff', lambda: {'id': 1})
    monkeypatch.setattr(factory, 'create_panel_client', lambda server: client)
    provision_lte = AsyncMock()
    monkeypatch.setattr(lte, 'provision_lte_identity', provision_lte)
    def create(**kwargs):
        guest_db.execute("INSERT INTO vpn_keys(id,user_id,sub_id,expires_at) VALUES(1,?,'created-token',datetime('now','+1 day'))", (kwargs['user_id'],))
        guest_db.commit(); return 1
    monkeypatch.setattr(db, 'create_vpn_key_admin', create)
    asyncio.run(friends.provision_guest(row))
    assert client.add_client.call_args.kwargs['enable'] is False
    assert client.update_client_full.call_args.kwargs['limit_ip'] == 1
    assert provision_lte.call_args.kwargs['device_limit'] == 1
    assert provision_lte.call_args.kwargs['quota_gb'] == 15
    assert friends.list_guests()[0]['state'] == 'active'
    assert guest_db.execute('SELECT expires_at FROM vpn_keys').fetchone()[0] == row['expires_at']
    assert friends.guest_access_allowed('created-token')


def test_guest_presence_main_lte_and_stale(monkeypatch):
    from datetime import datetime, timezone, timedelta
    import bot.services.panels.factory as factory
    now = datetime.now(timezone.utc)
    client = AsyncMock()
    client._request.return_value = {'total': 3, 'users': [
        {'username': 'arc_user_1', 'userTraffic': {'onlineAt': (now-timedelta(minutes=5)).isoformat()}},
        {'username': 'arc_lte_1', 'userTraffic': {'onlineAt': now.isoformat()}},
        {'username': 'arc_user_2', 'userTraffic': {'onlineAt': (now-timedelta(minutes=5)).isoformat()}},
    ]}
    monkeypatch.setattr(friends, '_GUEST_PRESENCE_CACHE', (0, {}))
    monkeypatch.setattr(friends, 'authority_server', lambda: {})
    monkeypatch.setattr(factory, 'create_panel_client', lambda server: client)
    rows = [{'id': 1, 'user_id': 1}, {'id': 2, 'user_id': 2}]
    result = asyncio.run(friends.guest_presence(rows))
    assert result[1]['online'] and result[1]['last_activity'] == now.isoformat()
    assert not result[2]['online'] and result[2]['last_activity']
    asyncio.run(friends.guest_presence(rows))
    assert client._request.await_count == 1
    client.close.assert_awaited_once()


def test_created_id_is_new_guest_not_last_list_row(guest_db, monkeypatch):
    friends.reserve_guest(friends.validate_options(options()), 'owner')
    monkeypatch.setattr(api, '_admin_authorized', lambda permission: True)
    monkeypatch.setattr(api, '_admin_telegram_id', lambda: 1)
    monkeypatch.setattr(api, '_append_admin_audit_best_effort', lambda *a, **k: None)
    class Executor:
        def run(self, coroutine, **kwargs):
            coroutine.close()
            return {}
    monkeypatch.setattr(api, 'ASYNC_EXECUTOR', Executor())
    data = options(); data.update(request_id='22222222-2222-4222-8222-222222222222', days=0.5, lte_quota_gb=5)
    response = api.app.test_client().post('/api/admin/friend-subscriptions', json=data, headers={'Origin':'https://panel.arccnet.space'})
    assert response.status_code == 200
    assert response.json['created_id'] == response.json['subscriptions'][0]['id']
    assert response.json['created_id'] != response.json['subscriptions'][-1]['id']
