import sqlite3
from database.paid_subscriber_stats import paid_subscriber_stats


def db():
    c=sqlite3.connect(':memory:')
    c.executescript('''CREATE TABLE vpn_keys(id INTEGER,user_id INTEGER,expires_at TEXT);
        CREATE TABLE trial_entitlements(vpn_key_id INTEGER,status TEXT);
        CREATE TABLE payments(user_id INTEGER,status TEXT,operation_type TEXT,
          payment_type TEXT,offer_code TEXT,amount_cents INTEGER,amount_stars INTEGER,paid_at TEXT);''')
    return c


def payment(c,user,at,operation='renew',kind='cards',status='paid',offer=None,amount=100):
    c.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?)',(user,status,operation,kind,offer,amount,amount,at))


def test_unique_active_users_excludes_unpaid_trials_and_expired():
    c=db()
    c.executemany('INSERT INTO vpn_keys VALUES(?,?,?)',[(1,1,'2026-12-01'),(2,1,'2026-12-02'),(3,2,'2026-12-01'),(4,3,'2026-11-01'),(5,4,'2026-12-01'),(6,5,'2026-12-01')])
    c.execute("INSERT INTO trial_entitlements VALUES(6,'active')")
    for u in (1,3,5):
        payment(c,u,'2026-11-01');payment(c,u,'2026-11-02')
    payment(c,4,'2026-11-01',kind='demo')
    assert paid_subscriber_stats(c,'2026-11-08')=={'paid':1,'first_paid_today':0}


def test_first_payment_counts_renew_after_trial_but_not_repeat_or_addons():
    c=db();c.execute("INSERT INTO vpn_keys VALUES(1,1,'2026-12-01')")
    payment(c,1,'2026-11-07T20:59:59Z')
    payment(c,1,'2026-11-08T01:00:00Z')
    payment(c,2,'2026-11-07T21:00:00Z')
    payment(c,2,'2026-11-08T03:00:00Z')
    for u,kwargs in [(3,{'operation':'addon_lte'}),(4,{'operation':'topup'}),(5,{'kind':'demo'}),(6,{'kind':'trial'}),(7,{'status':'pending'}),(8,{'offer':'email_paid_trial'}),(9,{'amount':0}),(10,{'status':'canceled'})]:
        payment(c,u,'2026-11-08T03:00:00Z',**kwargs)
    assert paid_subscriber_stats(c,'2026-11-08T20:59:59Z')=={'paid':1,'first_paid_today':1}
    assert paid_subscriber_stats(c,'2026-11-08T21:00:00Z')['first_paid_today']==0
    assert paid_subscriber_stats(c,'2026-11-07T20:59:59Z')['first_paid_today']==1
