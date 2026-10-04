import asyncio
from unittest.mock import AsyncMock
import pytest
from database import connection
from database.migrations import run_migrations
from database.db_webapp import register_import_device
from bot.services import device_notifications as notices

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, 'DB_PATH', tmp_path / 'db.sqlite')
    run_migrations()
    with connection.get_db() as c:
        c.execute("INSERT INTO users(id,telegram_id,first_name) VALUES(1,123,'Owner')")
        c.execute("INSERT INTO vpn_keys(id,user_id,tariff_id,sub_id,client_uuid,expires_at) VALUES(1,1,1,'test-sub','test-uuid',datetime('now','+5 days'))")
    return connection

def test_new_device_once_and_reactivation_queues_next_notice(db):
    assert register_import_device('test-sub', 'stable-token', 'android', '', 'Phone')
    register_import_device('test-sub', 'stable-token', 'android', '', 'Phone')
    with db.get_db() as c:
        assert c.execute('SELECT COUNT(*) FROM device_connection_notifications').fetchone()[0] == 1
        c.execute('UPDATE device_connection_notifications SET sent_at=CURRENT_TIMESTAMP')
        c.execute('UPDATE user_devices SET is_active=0')
    register_import_device('test-sub', 'stable-token', 'android', '', 'Phone')
    with db.get_db() as c:
        assert c.execute('SELECT COUNT(*) FROM device_connection_notifications').fetchone()[0] == 2

def test_migration_does_not_backfill_old_devices(db):
    with db.get_db() as c:
        c.execute("INSERT INTO user_devices(user_id,vpn_key_id,device_token_hash,display_name) VALUES(1,1,'old','Old')")
        assert c.execute('SELECT COUNT(*) FROM device_connection_notifications').fetchone()[0] == 0

@pytest.mark.parametrize('allowed,delivered,expected', [(True,True,'sent'), (False,True,'skipped'), (True,False,'failed')])
def test_delivery_preferences_dedup_and_retry(db, monkeypatch, allowed, delivered, expected):
    register_import_device('test-sub', 'new-token', 'android', '', 'Phone <test>')
    sender = AsyncMock(return_value=delivered)
    monkeypatch.setattr(notices, 'send_to_user', sender)
    monkeypatch.setattr(notices, 'notification_allowed', lambda *_: allowed)
    result = asyncio.run(notices.deliver_device_notifications(object()))
    assert result[expected] == 1
    assert (sender.call_count == 1) == allowed
    if allowed:
        assert 'Phone &lt;test&gt;' in sender.call_args.args[2]
    again = asyncio.run(notices.deliver_device_notifications(object()))
    assert again == {'sent':0, 'skipped':0, 'failed':0}
