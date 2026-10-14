import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from database import connection
from database.db_lte_addons import active_lte_addons, reconcile_lte_addons
from database.db_traffic_cycles import start_or_preserve_traffic_cycle
from database.db_webapp import apply_payment_addon, get_lte_identity_by_id
from database.migrations import migration_57
from bot.services.lte_identity import lte_quota_patch

GIB = 1024**3
NOW = '2026-10-14 12:00:00'


@pytest.fixture(autouse=True)
def isolated_authority(monkeypatch):
    from bot.services import remnawave_stats
    monkeypatch.setattr(remnawave_stats, 'remnawave_authority_config', lambda: {})


@pytest.fixture
def addon_db(tmp_path, monkeypatch):
    path = tmp_path / 'addons.sqlite'
    monkeypatch.setattr(connection, 'DB_PATH', path)
    with connection.get_db() as conn:
        conn.executescript('''
          CREATE TABLE users (
            id INTEGER PRIMARY KEY,telegram_id INTEGER,device_limit INTEGER,
            lte_quota_gb INTEGER,lte_cycle_bonus_gb INTEGER DEFAULT 0,
            normal_used_bytes INTEGER DEFAULT 123,lte_used_bytes INTEGER DEFAULT 456,
            lte_notified_pct INTEGER DEFAULT 100,entitlements_updated_at TEXT,
            lte_client_uuid TEXT,lte_panel_username TEXT,lte_remnawave_user_id TEXT,
            is_banned INTEGER DEFAULT 0,traffic_cycle_started_at TEXT,
            traffic_cycle_reset_at TEXT,lte_cycle_started_at TEXT,lte_cycle_reset_at TEXT
          );
          CREATE TABLE payments (
            order_id TEXT PRIMARY KEY,user_id INTEGER,status TEXT,addon_kind TEXT,
            addon_units INTEGER,addon_lte_gb INTEGER DEFAULT 0,
            addon_device_units INTEGER DEFAULT 0,addons_applied_at TEXT
          );
          CREATE TABLE vpn_keys (
            id INTEGER PRIMARY KEY,user_id INTEGER,created_at TEXT,expires_at TEXT,
            panel_email TEXT,traffic_used INTEGER DEFAULT 789,
            traffic_notified_pct INTEGER DEFAULT 100,traffic_updated_at TEXT,
            last_online_at TEXT
          );
          CREATE TABLE settings (key TEXT PRIMARY KEY,value TEXT);
          INSERT INTO users(id,telegram_id,device_limit,lte_quota_gb,
            lte_client_uuid,lte_panel_username,lte_remnawave_user_id)
            VALUES(1,1001,3,5,'stable-lte','arc_lte_1','panel-lte');
          INSERT INTO vpn_keys(id,user_id,created_at,expires_at,panel_email)
            VALUES(11,1,'2026-09-11 13:51:26','2099-01-01','stable-main');
          INSERT INTO payments VALUES('boost',1,'paid','combined',45,45,0,'2026-09-22 20:07:11');
        ''')
        migration_57(conn)
    return path


def test_receipt_restores_missing_bonus_and_excludes_unpaid_or_unapplied(addon_db):
    with connection.get_db() as conn:
        conn.executescript('''
          INSERT INTO payments VALUES('pending',1,'pending','lte',30,30,0,'2026-10-01');
          INSERT INTO payments VALUES('unapplied',1,'paid','lte',20,20,0,NULL);
          INSERT INTO payments VALUES('canceled',1,'canceled','lte',10,10,0,'2026-10-01');
          INSERT INTO payments VALUES('device',1,'paid','device',1,0,1,'2026-10-01');
        ''')
        assert reconcile_lte_addons(conn, now=NOW) == {'checked': 1, 'changed': 1}
        assert reconcile_lte_addons(conn, now=NOW)['changed'] == 0
        row = conn.execute('SELECT * FROM users').fetchone()
        assert (row['lte_quota_gb'],row['lte_cycle_bonus_gb'],row['device_limit']) == (5,45,3)
        assert (row['normal_used_bytes'],row['lte_used_bytes']) == (123,456)
        assert (row['lte_client_uuid'],row['lte_panel_username']) == ('stable-lte','arc_lte_1')
        assert active_lte_addons(conn, 1, now=NOW)['next_expiry_at'] == '2026-10-22 20:07:11'


def test_each_boost_expires_independently_and_month_end_is_clamped(addon_db):
    with connection.get_db() as conn:
        conn.execute("INSERT INTO payments VALUES('second',1,'paid','lte',15,0,0,'2026-09-30 21:00:00')")
        assert active_lte_addons(conn, 1, now='2026-10-22 20:07:10')['bonus_gb'] == 60
        assert active_lte_addons(conn, 1, now='2026-10-22 20:07:11')['bonus_gb'] == 15
        assert active_lte_addons(conn, 1, now='2026-10-30 21:00:00')['bonus_gb'] == 0
        conn.execute("INSERT INTO payments VALUES('leap',1,'paid','lte',7,7,0,'2024-01-31 12:00:00')")
        assert active_lte_addons(conn, 1, now='2024-02-29 11:59:59')['bonus_gb'] == 7
        assert active_lte_addons(conn, 1, now='2024-02-29 12:00:00')['bonus_gb'] == 0
        conn.execute('UPDATE users SET lte_cycle_bonus_gb=60')
        assert reconcile_lte_addons(conn, now='2026-11-01')['changed'] == 1
        assert conn.execute('SELECT lte_cycle_bonus_gb FROM users').fetchone()[0] == 0


def test_bad_receipt_and_legacy_schema_preserve_allowance(addon_db):
    with connection.get_db() as conn:
        conn.execute('UPDATE users SET lte_cycle_bonus_gb=45')
        conn.execute("UPDATE payments SET addons_applied_at='bad-date'")
        assert reconcile_lte_addons(conn, now=NOW) == {'checked': 0, 'changed': 0}
        assert conn.execute('SELECT lte_cycle_bonus_gb FROM users').fetchone()[0] == 45
        conn.execute('DROP TABLE payments')
        assert reconcile_lte_addons(conn, user_id=1, now=NOW)['changed'] == 0


def test_duplicate_concurrent_callbacks_grant_devices_only_once(addon_db):
    with connection.get_db() as conn:
        conn.execute("INSERT INTO payments VALUES('new',1,'paid','combined',17,15,2,NULL)")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(apply_payment_addon, ['new']*4))
    assert all(item['device_limit'] == 5 for item in results)
    with connection.get_db() as conn:
        assert conn.execute('SELECT device_limit,lte_quota_gb FROM users').fetchone()[:] == (5,5)
        grant = active_lte_addons(conn, 1)
        assert grant['bonus_gb'] >= 15
        assert conn.execute("SELECT addons_applied_at FROM payments WHERE order_id='new'").fetchone()[0]


class Panel:
    def __init__(self, *, reject=False):
        self.reject = reject
        self.resets = 0
        self.patches = []
        self.user = {'id':'panel-lte','vlessUuid':'stable-lte','expireAt':'2099-01-01T00:00:00Z',
                     'status':'LIMITED','trafficLimitBytes':5*GIB,'userTraffic':{'usedTrafficBytes':6*GIB}}

    async def get_user(self, _name):
        return {**self.user, 'userTraffic':dict(self.user['userTraffic'])}

    async def reset_client_traffic(self, *_args):
        self.resets += 1
        self.user['userTraffic']['usedTrafficBytes'] = 0
        return True

    async def _request(self, *_args, json):
        self.patches.append(json)
        if not self.reject:
            self.user.update(json)
        return self.user

    async def close(self):
        pass


@pytest.mark.parametrize('reject', [False, True])
def test_calendar_reset_keeps_paid_boost_and_requires_panel_readback(addon_db, monkeypatch, reject):
    from bot.services import scheduler
    start_or_preserve_traffic_cycle(1, activated_at='2026-09-11 13:51:26', preserve_existing=False)
    with connection.get_db() as conn:
        conn.execute('UPDATE users SET lte_used_bytes=456')
    panel = Panel(reject=reject)
    monkeypatch.setattr(scheduler, 'get_client_from_server_data', lambda _: panel)
    async def accepted(_id):
        return True
    result = asyncio.run(scheduler.process_due_traffic_cycle_resets(resetter=accepted, now=NOW))
    assert result['failed' if reject else 'applied'] == 1
    assert panel.patches == [{'id':'panel-lte','trafficLimitBytes':50*GIB,'status':'ACTIVE'}]
    identity = get_lte_identity_by_id(1, now=NOW)
    assert identity['lte_quota_gb'] == 50
    with connection.get_db() as conn:
        row = conn.execute('SELECT * FROM users').fetchone()
        assert row['lte_quota_gb'] == 5 and row['lte_cycle_bonus_gb'] == 45
        assert row['lte_used_bytes'] == (456 if reject else 0)
        assert row['traffic_cycle_reset_at'] == ('2026-10-11 13:51:26' if reject else '2026-11-11 13:51:26')
    if not reject:
        assert asyncio.run(scheduler.process_due_traffic_cycle_resets(resetter=accepted, now=NOW))['applied'] == 0
        assert panel.resets == 1


@pytest.mark.parametrize('status,quota,used,banned,expiry,expected', [
    ('LIMITED',50,6,False,'2099-01-01',{'trafficLimitBytes':50*GIB,'status':'ACTIVE'}),
    ('ACTIVE',5,6,False,'2099-01-01',{'status':'LIMITED'}),
    ('DISABLED',50,0,False,'2099-01-01',{'trafficLimitBytes':50*GIB}),
    ('ACTIVE',0,0,False,'2099-01-01',{'trafficLimitBytes':0,'status':'DISABLED'}),
    ('EXPIRED',50,0,True,'2099-01-01',{}),
    ('EXPIRED',50,0,False,'2026-10-01',{}),
])
def test_quota_sync_preserves_revocations_identity_expiry_and_usage(status,quota,used,banned,expiry,expected):
    identity = {'lte_quota_gb':quota,'is_banned':banned,'subscription_expires_at':expiry}
    panel = Panel().user
    panel['status'] = status
    panel['userTraffic']['usedTrafficBytes'] = used*GIB
    patch = lte_quota_patch(identity, panel, NOW)
    assert patch == ({'id':'panel-lte',**expected} if expected else {})
    assert panel['userTraffic']['usedTrafficBytes'] == used*GIB
    assert 'expireAt' not in patch and 'vlessUuid' not in patch


@pytest.mark.parametrize('reject', [False, True])
def test_periodic_sync_repairs_quota_without_reset_and_retries_rejection(monkeypatch, reject):
    from bot.services import scheduler
    from database import db_webapp
    panel = Panel(reject=reject)
    identity = {'user_id':1,'telegram_id':1001,'lte_panel_username':'arc_lte_1',
                'lte_client_uuid':'stable-lte','lte_quota_gb':50,'subscription_expires_at':'2099-01-01'}
    monkeypatch.setattr(scheduler, 'get_client_from_server_data', lambda _: panel)
    monkeypatch.setattr(db_webapp, 'list_lte_identities', lambda: [identity])
    mirrored = []
    def save(_tg, used):
        mirrored.append(used)
        return {'lte_quota_gb':50}
    monkeypatch.setattr(db_webapp, 'set_lte_usage', save)
    result = asyncio.run(scheduler.reconcile_lte_usage())
    assert result == {'updated':0 if reject else 1,'failed':1 if reject else 0}
    assert mirrored == ([] if reject else [6*GIB])
    assert panel.resets == 0
    panel.reject = False
    assert asyncio.run(scheduler.reconcile_lte_usage())['updated'] == 1
    assert panel.user['trafficLimitBytes'] == 50*GIB
    assert panel.user['userTraffic']['usedTrafficBytes'] == 6*GIB


def test_renewal_does_not_store_boost_in_base_allowance(addon_db, monkeypatch):
    from bot.services import billing, lte_identity, vpn_api
    from bot.services.panels import remnawave
    with connection.get_db() as conn:
        conn.execute("UPDATE payments SET addons_applied_at=CURRENT_TIMESTAMP")
    monkeypatch.setattr(billing, 'get_vpn_key_by_id', lambda _: {'expires_at':'2099-01-01'})
    monkeypatch.setattr(billing, 'extend_vpn_key', lambda *_: True)
    monkeypatch.setattr(billing, 'get_user_by_id', lambda _: {'id':1,'telegram_id':1001})
    monkeypatch.setattr(billing, 'update_order_fulfillment', lambda *_: None)
    monkeypatch.setattr(billing, '_reload_order', lambda _: {})
    monkeypatch.setattr(billing, 'start_or_preserve_traffic_cycle', lambda *_args, **_kwargs: {})
    monkeypatch.setattr(vpn_api, 'restore_traffic_limit_in_db', lambda _: None)
    async def pushed(*_args, **_kwargs):
        return True
    monkeypatch.setattr(vpn_api, 'push_key_to_panel', pushed)
    monkeypatch.setattr(remnawave, 'RemnawaveClient', lambda _: Panel())
    provisioned = []
    async def provision(_client, **kwargs):
        provisioned.append(kwargs)
        if kwargs.get('persist_base_quota', True):
            with connection.get_db() as conn:
                conn.execute('UPDATE users SET lte_quota_gb=?', (kwargs['quota_gb'],))
    monkeypatch.setattr(lte_identity, 'provision_lte_identity', provision)
    result = asyncio.run(billing._apply_renew_order('renew', {'user_id':1,'vpn_key_id':11,'period_days':30}))
    assert result[0]
    assert provisioned[0]['quota_gb'] == 50
    assert provisioned[0]['persist_base_quota'] is False
    with connection.get_db() as conn:
        assert conn.execute('SELECT lte_quota_gb,lte_cycle_bonus_gb FROM users').fetchone()[:] == (5,45)
