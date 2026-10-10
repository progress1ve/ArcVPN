import asyncio
import sqlite3
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
import subscription_api as api
from bot.services import email_trials as policy
from database import db_trials
from database.migrations import migration_76


@pytest.fixture
def policy_db(monkeypatch):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''CREATE TABLE payments(user_id INTEGER,status TEXT,offer_code TEXT,payment_type TEXT);
    CREATE TABLE vpn_keys(user_id INTEGER); CREATE TABLE trial_entitlements(user_id INTEGER,status TEXT);
    CREATE TABLE tariffs(id INTEGER,name TEXT,is_active INTEGER,duration_days INTEGER,display_order INTEGER,price_rub INTEGER);''')
    @contextmanager
    def get_db():
        yield conn
    monkeypatch.setattr(policy,'get_db',get_db)
    monkeypatch.setattr(db_trials,'get_db',get_db)
    monkeypatch.setattr(policy,'email_paid_trial_state',lambda _: 'available')
    return conn


def test_free_day_cannot_be_reissued_or_given_to_commercial_account(policy_db):
    account={'id':1,'identity_source':'email','email_verified_at':'now','used_trial':0}
    assert policy.free_trial_available(account)
    assert not policy.free_trial_available({**account,'used_trial':1})
    assert not policy.free_trial_available({**account,'email_verified_at':None})
    assert not policy.free_trial_available({**account,'identity_source':'telegram'})
    policy_db.execute("INSERT INTO payments(user_id,status) VALUES(1,'paid')")
    assert not policy.free_trial_available(account)


def test_failed_free_provisioning_can_retry_but_active_cannot(policy_db):
    account={'id':1,'identity_source':'email','email_verified_at':'now','used_trial':0}
    policy_db.execute("INSERT INTO trial_entitlements VALUES(1,'failed')")
    policy_db.execute("INSERT INTO vpn_keys VALUES(1)")
    assert policy.free_trial_available(account)
    policy_db.execute("UPDATE trial_entitlements SET status='active'")
    assert not policy.free_trial_available(account)


def test_paid_trial_is_for_new_accounts_and_free_trial_users(policy_db):
    account={'id':1,'identity_source':'email','email_verified_at':'now'}
    assert policy.paid_trial_eligible(account)
    policy_db.execute('INSERT INTO vpn_keys VALUES(1)')
    assert not policy.paid_trial_eligible(account)
    policy_db.execute("INSERT INTO trial_entitlements VALUES(1,'active')")
    assert policy.paid_trial_eligible(account)
    policy_db.execute("INSERT INTO payments(user_id,status) VALUES(1,'paid')")
    assert not policy.paid_trial_eligible(account)


def test_monthly_standard_is_resolved_from_current_tariff(policy_db):
    policy_db.executemany('INSERT INTO tariffs VALUES(?,?,?,?,?,?)',[(1,'Стандарт',1,90,1,399),(2,'Стандарт',1,30,2,145),(3,'Эконом',1,30,0,99)])
    assert policy.offer_details()['renewal_amount_rub']==145


def test_trial_renewal_uses_agreed_monthly_snapshot_and_old_consent_fails_closed():
    order={'offer_code':'email_paid_trial','amount_cents':1000,'period_days':7,'renewal_amount_cents':14500,'renewal_period_days':30}
    assert policy.recurring_terms(order)=={'amount_cents':14500,'period_days':30}
    assert policy.recurring_terms({k:v for k,v in order.items() if not k.startswith('renewal_')}) is None
    assert policy.recurring_terms({'amount_cents':39900,'period_days':90})=={'amount_cents':39900,'period_days':90}


def test_renewal_snapshot_migration_preserves_old_payments():
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE payments(id INTEGER,amount_cents INTEGER)')
    conn.execute('INSERT INTO payments VALUES(1,1000)')
    migration_76(conn)
    assert conn.execute('SELECT amount_cents,renewal_amount_cents,renewal_period_days FROM payments').fetchone()==(1000,None,None)


def test_free_endpoint_auth_and_exact_one_day(monkeypatch):
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:None)
    assert api.app.test_client().post('/api/trials/email-free').status_code==401
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:-1001)
    monkeypatch.setattr(api,'get_webapp_account',lambda _: {'id':9,'identity_source':'email','email_verified_at':'now'})
    monkeypatch.setattr(api,'get_trial_entitlement',lambda _:None)
    monkeypatch.setattr(api,'free_trial_available',lambda _:True)
    async def provision(user,**kwargs):
        assert kwargs=={'trial_days_override':1,'grant_referral_reward':False}
        return {'first_key_id':1}
    monkeypatch.setattr('bot.handlers.user.trial.provision_trial_for_user',provision)
    monkeypatch.setattr(api.ASYNC_EXECUTOR,'run',lambda coro,timeout:asyncio.run(coro))
    assert api.app.test_client().post('/api/trials/email-free').json['trial_days']==1
    monkeypatch.setattr(api,'get_trial_entitlement',lambda _: {'status':'active','vpn_key_id':1})
    assert api.app.test_client().post('/api/trials/email-free').json['already_active']


def test_changed_renewal_price_blocks_checkout_before_charge(monkeypatch):
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:-1001)
    monkeypatch.setattr(api,'get_webapp_account',lambda _: {'id':9,'identity_source':'email'})
    monkeypatch.setattr(api,'paid_trial_eligible',lambda _:True)
    monkeypatch.setattr(api,'email_paid_trial_state',lambda _:'available')
    monkeypatch.setattr(api,'get_setting',lambda *_:'1')
    monkeypatch.setattr(api,'get_standard_monthly_tariff',lambda:{'id':7,'price_rub':150})
    provider=Mock();monkeypatch.setattr(api,'create_yookassa_qr_payment',provider)
    assert api.app.test_client().post('/api/payments/email-trial',json={'method':'sbp','renewal_amount_rub':145}).json['error']=='trial_terms_changed'
    provider.assert_not_called()


def test_pending_trial_resumes_existing_order_without_second_charge(monkeypatch):
    monkeypatch.setattr(api,'_webapp_telegram_id',lambda:-1001)
    monkeypatch.setattr(api,'get_webapp_account',lambda _: {'id':9,'identity_source':'email'})
    monkeypatch.setattr(api,'paid_trial_eligible',lambda _:True)
    monkeypatch.setattr(api,'email_paid_trial_state',lambda _:'pending')
    conn=Mock();conn.execute.return_value.fetchone.return_value={'order_id':'existing','yookassa_payment_id':'provider'}
    @contextmanager
    def get_db(): yield conn
    monkeypatch.setattr(api,'get_db',get_db)
    async def details(_): return {'status':'pending','confirmation':{'confirmation_url':'https://pay.example/existing'}}
    monkeypatch.setattr(api,'get_yookassa_payment_details',details)
    monkeypatch.setattr(api.ASYNC_EXECUTOR,'run',lambda coro,timeout:asyncio.run(coro))
    provider=Mock();monkeypatch.setattr(api,'create_yookassa_qr_payment',provider)
    result=api.app.test_client().post('/api/payments/email-trial',json={'method':'sbp'})
    assert result.json['resumed'] and result.json['order_id']=='existing'
    provider.assert_not_called()


def test_paid_week_extends_free_key_once_without_replacing_subscription(monkeypatch):
    from bot.services import billing
    order={'order_id':'week','user_id':9,'operation_type':'trial_start','offer_code':'email_paid_trial','amount_cents':1000,'period_days':7,'status':'paid','fulfillment_status':'pending'}
    monkeypatch.setattr(billing,'find_order_by_order_id',lambda _:order)
    monkeypatch.setattr(billing,'_reload_order',lambda _:order)
    monkeypatch.setattr('database.db_partners.needs_verified_amount',lambda _:False)
    monkeypatch.setattr(policy,'paid_trial_eligible',lambda _:True)
    monkeypatch.setattr(billing,'get_user_by_id',lambda _: {'id':9})
    monkeypatch.setattr(billing,'is_order_already_paid',lambda _:True)
    monkeypatch.setattr(billing,'apply_payment_entitlements',lambda _:{'device_limit':3,'lte_quota_gb':5})
    monkeypatch.setattr(billing,'update_order_fulfillment',Mock(return_value=True))
    monkeypatch.setattr(billing,'validate_email_paid_trial_claim',lambda *_:True)
    monkeypatch.setattr(db_trials,'get_trial_entitlement',lambda _:{'status':'active','vpn_key_id':33})
    applied=[]
    async def renew(_, selected):
        applied.append((selected['vpn_key_id'],selected['period_days']))
        order['fulfillment_status']='applied'
        return True,'ready',order
    monkeypatch.setattr(billing,'_apply_renew_order',renew)
    claim=Mock();monkeypatch.setattr(billing,'update_email_paid_trial_claim',claim)
    assert asyncio.run(billing.apply_paid_order('week'))[0]
    assert applied==[(33,7)]
    claim.assert_called_once_with('week','applied')
    assert asyncio.run(billing.apply_paid_order('week'))[0]
    assert applied==[(33,7)]


def test_normal_purchase_winning_trial_race_preserves_access(monkeypatch):
    from bot.services import billing
    order={'order_id':'week','user_id':9,'operation_type':'trial_start','offer_code':'email_paid_trial','status':'paid','fulfillment_status':'pending'}
    monkeypatch.setattr(billing,'find_order_by_order_id',lambda _:order)
    monkeypatch.setattr(billing,'_reload_order',lambda _:order)
    monkeypatch.setattr('database.db_partners.needs_verified_amount',lambda _:False)
    monkeypatch.setattr(billing,'is_order_already_paid',lambda _:True)
    monkeypatch.setattr(billing,'get_user_by_id',lambda _: {'id':9})
    monkeypatch.setattr(policy,'paid_trial_eligible',lambda _:False)
    changed=Mock();monkeypatch.setattr(billing,'apply_payment_entitlements',changed)
    fulfillment=Mock();monkeypatch.setattr(billing,'update_order_fulfillment',fulfillment)
    monkeypatch.setattr(billing,'update_email_paid_trial_claim',Mock())
    assert asyncio.run(billing.apply_paid_order('week'))[0]
    changed.assert_not_called()
    assert fulfillment.call_args.args[1]=='manual_review'
