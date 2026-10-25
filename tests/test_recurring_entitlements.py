from database import connection
from database.db_recurring import snapshot_recurring_entitlements
from database.db_webapp import apply_payment_entitlements
import json


def test_negotiated_renewal_keeps_base_and_price_then_plan_change_replaces_it(tmp_path,monkeypatch):
    monkeypatch.setattr(connection,'DB_PATH',tmp_path/'renew.sqlite')
    with connection.get_db() as c:
        c.executescript('''
          CREATE TABLE users(id INTEGER PRIMARY KEY,device_limit INTEGER,lte_quota_gb INTEGER,lte_cycle_bonus_gb INTEGER,
            traffic_monthly_limit_gb INTEGER,lte_used_bytes INTEGER,lte_cycle_started_at TEXT,lte_cycle_reset_at TEXT,entitlements_updated_at TEXT);
          CREATE TABLE tariffs(id INTEGER PRIMARY KEY,device_limit INTEGER,lte_quota_gb INTEGER,price_rub INTEGER,traffic_limit_gb INTEGER);
          CREATE TABLE payments(order_id TEXT PRIMARY KEY,user_id INTEGER,tariff_id INTEGER,status TEXT,amount_cents INTEGER,
            requested_device_limit INTEGER,requested_lte_quota_gb INTEGER,is_custom_tariff INTEGER DEFAULT 0,addons_applied_at TEXT);
          INSERT INTO users VALUES(178,3,20,30,1024,123456,'2026-10-11','2026-11-11',NULL);
          INSERT INTO tariffs VALUES(12,3,45,145,1024);
          INSERT INTO tariffs VALUES(13,8,115,299,1024);
          INSERT INTO payments VALUES('renew',178,12,'pending',11200,NULL,NULL,0,NULL);
        ''')
    assert not snapshot_recurring_entitlements('renew',999)
    assert snapshot_recurring_entitlements('renew',178)
    with connection.get_db() as c:
        r=c.execute("SELECT * FROM payments WHERE order_id='renew'").fetchone()
        assert (r['requested_device_limit'],r['requested_lte_quota_gb'],r['amount_cents'],r['is_custom_tariff'])==(3,20,11200,1)
        c.execute("UPDATE payments SET status='paid' WHERE order_id='renew'")
    assert not snapshot_recurring_entitlements('renew',178)
    assert apply_payment_entitlements('renew')['lte_quota_gb']==20
    assert apply_payment_entitlements('renew')['lte_quota_gb']==20
    with connection.get_db() as c:
        assert tuple(c.execute('SELECT lte_cycle_bonus_gb,lte_used_bytes FROM users').fetchone())==(30,123456)
        c.execute("INSERT INTO payments VALUES('change',178,13,'paid',29900,NULL,NULL,0,NULL)")
    assert apply_payment_entitlements('change')['lte_quota_gb']==115
    with connection.get_db() as c:
        assert c.execute('SELECT lte_quota_gb FROM users').fetchone()[0]==115


def test_personal_next_renewal_is_deferred_and_revoked_after_manual_plan_change(tmp_path,monkeypatch):
    monkeypatch.setattr(connection,'DB_PATH',tmp_path/'personal.sqlite')
    with connection.get_db() as c:
        c.executescript('''
          CREATE TABLE users(id INTEGER PRIMARY KEY,device_limit INTEGER,lte_quota_gb INTEGER,lte_cycle_bonus_gb INTEGER);
          CREATE TABLE tariffs(id INTEGER PRIMARY KEY,device_limit INTEGER,lte_quota_gb INTEGER,price_rub INTEGER);
          CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE payments(id INTEGER PRIMARY KEY,order_id TEXT,user_id INTEGER,tariff_id INTEGER,vpn_key_id INTEGER,
            status TEXT,amount_cents INTEGER,period_days INTEGER,operation_type TEXT,payment_type TEXT,
            requested_device_limit INTEGER,requested_lte_quota_gb INTEGER,is_custom_tariff INTEGER,addons_applied_at TEXT);
          INSERT INTO users VALUES(178,3,0,30);
          INSERT INTO tariffs VALUES(12,3,45,145);
          INSERT INTO payments VALUES(402,'source',178,12,223,'paid',11200,30,'renew','yookassa_card',3,0,1,'2026-10-25');
          INSERT INTO payments VALUES(403,'addon',178,NULL,223,'paid',6000,NULL,'addon_combined','yookassa_card',NULL,NULL,0,'2026-10-25');
          INSERT INTO payments VALUES(404,'next',178,12,223,'pending',11200,30,'renew','yookassa_recurring',NULL,NULL,0,NULL);
        ''')
        policy={'active':True,'source_payment_id':402,'tariff_id':12,'vpn_key_id':223,'amount_cents':11200,'period_days':30,'lte_quota_gb':20}
        c.execute('INSERT INTO settings VALUES(?,?)',('personal_recurring_plan:178',json.dumps(policy)))
    assert snapshot_recurring_entitlements('next',178)
    with connection.get_db() as c:
        assert tuple(c.execute('SELECT lte_quota_gb,lte_cycle_bonus_gb FROM users').fetchone())==(0,30)
        assert tuple(c.execute("SELECT requested_device_limit,requested_lte_quota_gb,amount_cents FROM payments WHERE order_id='next'").fetchone())==(3,20,11200)
        c.execute("UPDATE payments SET status='paid' WHERE order_id='next'")
        c.execute('UPDATE users SET lte_quota_gb=20')
        c.execute("INSERT INTO payments VALUES(405,'later',178,12,223,'pending',11200,30,'renew','yookassa_recurring',NULL,NULL,0,NULL)")
    assert snapshot_recurring_entitlements('later',178)
    with connection.get_db() as c:
        c.execute("INSERT INTO payments VALUES(406,'change',178,12,223,'paid',14500,30,'renew','yookassa_card',3,45,0,'2026-12-01')")
        c.execute('UPDATE users SET lte_quota_gb=45')
    assert snapshot_recurring_entitlements('later',178)
    with connection.get_db() as c:
        assert c.execute("SELECT requested_lte_quota_gb FROM payments WHERE order_id='later'").fetchone()[0]==45
        assert not json.loads(c.execute('SELECT value FROM settings').fetchone()[0])['active']
