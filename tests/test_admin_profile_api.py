import subscription_api as api
from test_admin_user_detail_api import client, detail_db  # noqa: F401


def add_support_schema(conn):
    conn.executescript('''CREATE TABLE support_threads(id INTEGER PRIMARY KEY,user_id INTEGER,status TEXT,created_at TEXT,updated_at TEXT,ai_handoff_reason TEXT);
        CREATE TABLE support_messages(id INTEGER PRIMARY KEY,thread_id INTEGER,sender TEXT,sender_telegram_id INTEGER,body TEXT,created_at TEXT,read_at TEXT);''')


def test_profile_totals_full_history_currencies_status_and_plan(client, detail_db, monkeypatch):
    add_support_schema(detail_db)
    detail_db.execute('ALTER TABLE payments ADD COLUMN vpn_key_id INTEGER')
    detail_db.execute("UPDATE payments SET vpn_key_id=10,is_custom_tariff=1,requested_device_limit=4,requested_lte_quota_gb=40,operation_type='new' WHERE id=1")
    for i in range(5, 110):
        detail_db.execute("INSERT INTO payments(id,user_id,order_id,payment_type,status,paid_at,amount_cents,operation_type) VALUES(?,1,?,'balance','paid','2026-08-09',1,'addon_lte')",(i,f'p-{i}'))
    detail_db.execute("INSERT INTO payments(id,user_id,order_id,payment_type,status,paid_at,amount_cents,operation_type) VALUES(200,1,'failed','cards','canceled','2026-08-12',10000,'new'),(201,1,'deposit','cards','paid','2026-08-12',1000,'topup'),(202,1,'crypto','crypto','paid','2026-08-13',250,'addon_lte')")
    detail_db.execute("INSERT INTO payments(id,user_id,order_id,payment_type,status,paid_at,amount_stars,operation_type) VALUES(203,1,'stars','stars','succeeded','2026-08-13',25,'addon_lte')")
    monkeypatch.setattr(api,'_ADMIN_ACTIVITY_CACHE',{1:{'online_at':'2026-08-10','online_node':'Actual Sweden'}})
    data=client.get('/api/admin/users/700001/profile').get_json()
    assert len(data['payments'])==100
    assert data['summary']['purchase_totals']=={'rub':404.0,'usd':2.5,'stars':25,'count':108}
    assert data['summary']['first_subscription_at']=='2026-08-01'
    assert data['subscriptions'][0]['plan_kind']=='custom'
    assert data['subscriptions'][0]['plan_purchase']['requested_device_limit']==4
    assert data['presence']['last_node']=='Actual Sweden'
    assert data['presence']['online'] is False
    assert data['support']==[]
    assert data['payments_page']['next_cursor']==100
    older=client.get('/api/admin/users/700001/profile?payment_cursor=100').get_json()
    assert older['payments_page']['next_cursor'] is None
    assert len(older['payments'])==10
    assert older['summary']==data['summary']


def test_profile_never_invents_node_or_online_on_outage(client, detail_db, monkeypatch):
    add_support_schema(detail_db)
    monkeypatch.setattr(api,'_admin_live_presence',lambda:(False,{}))
    monkeypatch.setattr(api,'_ADMIN_ACTIVITY_CACHE',{1:{'online_at':'2099','online_node':'Stale'}})
    detail_db.execute("UPDATE vpn_keys SET panel_disabled_at='2026-08-11' WHERE id=10")
    data=client.get('/api/admin/users/700001/profile').get_json()
    assert data['presence']['last_node'] is None
    assert data['presence']['online'] is None
    assert data['presence']['last_online_at']=='2026-08-10'
    assert data['subscriptions'][0]['active']==0
    assert data['subscriptions'][0]['plan_name']=='Стандарт'
    trial=client.get('/api/admin/users/700002/profile').get_json()
    assert trial['subscriptions'][0]['plan_kind']=='trial'
    assert trial['summary']['purchase_totals']['rub']==10


def test_legacy_unlinked_custom_purchase_uses_snapshot_and_fulfilled_date(client, detail_db):
    add_support_schema(detail_db)
    detail_db.execute('ALTER TABLE payments ADD COLUMN vpn_key_id INTEGER')
    detail_db.execute("UPDATE tariffs SET device_limit=2,lte_quota_gb=5")
    detail_db.execute("UPDATE payments SET paid_at=NULL,fulfilled_at='2026-08-06',operation_type='new',requested_device_limit=4,requested_lte_quota_gb=40 WHERE id=1")
    data=client.get('/api/admin/users/700001/profile').get_json()
    assert data['subscriptions'][0]['plan_kind']=='custom'
    assert data['payments'][0]['paid_at']=='2026-08-06'


def test_profile_support_permissions_and_customer_isolation(client, detail_db, monkeypatch):
    add_support_schema(detail_db)
    detail_db.executescript("INSERT INTO support_threads VALUES(1,1,'open','2026-08-01','2026-08-09','spam'),(2,2,'closed','2026-08-01','2026-08-09',NULL); INSERT INTO support_messages VALUES(1,1,'user',700001,'Help','2026-08-09',NULL);")
    data=client.get('/api/admin/users/700001/profile').get_json()
    assert [row['id'] for row in data['support']]==[1]
    assert data['support'][0]['user_messages']==1
    monkeypatch.setattr(api,'_admin_authorized',lambda permission=None:permission=='overview.read')
    assert client.get('/api/admin/users/700001/profile').get_json()['support'] is None
    monkeypatch.setattr(api,'_admin_authorized',lambda permission=None:False)
    assert client.get('/api/admin/users/700001/profile').status_code==403


def test_feedback_problem_search_and_unanswered(client, detail_db):
    assert client.get('/api/admin/feedback?answer=problems&q=YouTube').get_json()['total']==1
    assert client.get('/api/admin/feedback?answer=unanswered').get_json()['total']==1
    assert client.get('/api/admin/feedback?q=friend_one').get_json()['total']==1
    assert client.get('/api/admin/feedback?q=%25').get_json()['total']==0
    assert client.get('/api/admin/feedback?answer=bad').status_code==400
    detail_db.execute("UPDATE users SET first_name='Айгуль' WHERE id=1")
    assert client.get('/api/admin/feedback?q=айгуль').get_json()['total']==2


def test_site_customer_with_negative_identity_can_open_profile(client, detail_db):
    add_support_schema(detail_db)
    detail_db.execute("INSERT INTO users(id,telegram_id,identity_source,device_limit) VALUES(4,-400,'email',3)")
    data=client.get('/api/admin/users/-400/profile').get_json()
    assert data['user']['id']==4
    assert data['subscriptions']==[]
    assert data['summary']['first_subscription_at'] is None


def test_support_filter_paging_sender_and_actual_counts(client, detail_db):
    add_support_schema(detail_db)
    detail_db.executescript("INSERT INTO support_threads VALUES(1,1,'open','2026-08-01','2026-08-09','spam'),(2,2,'closed','2026-08-01','2026-08-09',NULL); INSERT INTO support_messages VALUES(1,1,'user',700001,'Help','2026-08-09',NULL),(2,1,'admin',0,'AI','2026-08-09',NULL);")
    result=client.get('/api/admin/support/threads?status=handoff&limit=1').get_json()
    assert result['total']==1
    assert result['threads'][0]['messages_count']==2
    assert result['threads'][0]['unread']==1
    assert result['threads'][0]['last_is_ai']==1
    assert result['threads'][0]['created_at']=='2026-08-01'
    page=client.get('/api/admin/support/threads?limit=1').get_json()
    assert page['next_cursor']==1
    assert client.get('/api/admin/support/threads?cursor=1&limit=1').get_json()['threads'][0]['id']==2
    assert client.get('/api/admin/support/threads?status=closed&q=friend_one').get_json()['total']==1
    assert client.get('/api/admin/support/threads?status=invalid').status_code==400
    detail_db.execute("UPDATE users SET first_name='Айгуль' WHERE id=1")
    assert client.get('/api/admin/support/threads?q=айгуль').get_json()['total']==1
