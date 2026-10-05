import sqlite3
import pytest
from database.db_acquisition import acquisition_report

def test_exclusive_channels_and_moscow_month_boundary():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY,created_at TEXT,referred_by INTEGER);
    CREATE TABLE referral_stats(referral_id INTEGER,level INTEGER);
    CREATE TABLE user_campaign_attribution(user_id INTEGER);
    INSERT INTO users VALUES(1,'2026-09-30 21:01:00',NULL),(2,'2026-10-01 10:00:00',1),
    (3,'2026-10-02 10:00:00',NULL),(4,'2026-09-30 20:59:00',NULL),(5,'2026-10-03 10:00:00',NULL);
    INSERT INTO user_campaign_attribution VALUES(2),(3);
    INSERT INTO referral_stats VALUES(5,1),(5,1),(3,2);""")
    result=acquisition_report(conn,'2026-10-01','2026-10-31')
    assert (result['total'],result['direct'],result['referral'],result['campaign'])==(4,1,2,1)
    assert sum(sum(day[key] for key in ('direct','referral','campaign')) for day in result['series'])==4
    assert acquisition_report(conn)['total']==5
    with pytest.raises(ValueError):acquisition_report(conn,'2026-10-02','2026-10-01')
    with pytest.raises(ValueError):acquisition_report(conn,'bad','')

def test_acquisition_api_denies_guest_and_partner(monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api,'_admin_authorized',lambda *args:False)
    assert api.app.test_client().get('/api/admin/acquisition').status_code==403
