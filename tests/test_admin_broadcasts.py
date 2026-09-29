import asyncio
import sqlite3
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter
from aiogram.methods import SendMessage

from database import connection, db_admin_broadcasts as campaigns, db_promocodes
from database.migrations import run_migrations, migration_67
from bot.services.admin_broadcast_worker import process_recipient, send_test


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, 'DB_PATH', tmp_path / 'test.sqlite3')
    run_migrations()
    with connection.get_db() as conn:
        conn.executemany('INSERT INTO users(id,telegram_id,first_name,is_banned) VALUES(?,?,?,?)',
            [(1, 101, 'Active', 0), (2, 102, 'Expired', 0), (3, 103, 'No key', 0), (4, -10, 'Email', 0), (5, 105, 'Banned', 1)])
        conn.execute("INSERT INTO vpn_keys(id,user_id,tariff_id,expires_at,client_uuid,sub_id) VALUES(1,1,1,datetime('now','+10 days'),'uuid-active','stable-active')")
        conn.execute("INSERT INTO vpn_keys(id,user_id,tariff_id,expires_at,client_uuid,sub_id) VALUES(2,2,1,datetime('now','-5 days'),'uuid-expired','stable-expired')")
    return connection


def payload(kind='none', **offer):
    return {'title': 'Campaign', 'message_text': '<b>Спасибо</b> &amp; до встречи',
        'audience': {'segment': 'all'}, 'reward': {'kind': kind, **offer}, 'buttons': []}


def launch(data):
    campaign = campaigns.save(data, 'owner')
    campaigns.mark_tested(campaign['id'], campaign['revision'], 999)
    return campaigns.start(campaign['id'], campaign['revision'], campaign['total'])


@pytest.mark.parametrize('text', ['<div>bad</div>', '<b>bad</i>', '<b>open', 'x & y', '<a href="javascript:alert(1)">x</a>',
    '<b onclick="x">x</b>', '<br/>', '&nbsp;', '&#0;', '<script>x</script>', 'x < y', '<?xml version="1.0"?>x'])
def test_telegram_html_rejects_malformed_or_unsupported(text):
    with pytest.raises(ValueError):
        campaigns.validate_html(text)


def test_telegram_html_preserves_supported_format_and_checks_utf16():
    text = '<b>Привет</b>\n<a href="https://example.com/?a=1&amp;b=2">Ссылка</a> &lt;3'
    assert campaigns.validate_html(text) == text
    with pytest.raises(ValueError):
        campaigns.validate_html('😀' * 2049)


def test_audience_filters_and_fixed_selection(db):
    data = payload()
    assert campaigns.preview(data)['count'] == 3
    data['audience'] = {'segment': 'expired'}
    assert [r['telegram_id'] for r in campaigns.preview(data)['sample']] == [102]
    data['audience'] = {'segment': 'selected', 'selected': [101, 101, 102, 105], 'excluded': [101]}
    assert campaigns.preview(data)['count'] == 1
    campaign = campaigns.save(data, 'owner')
    with db.get_db() as conn:
        conn.execute("INSERT INTO users(id,telegram_id,is_banned) VALUES(6,106,0)")
    assert campaigns.detail(campaign['id'])['total'] == 1


def test_test_is_mandatory_edit_invalidates_and_start_is_once(db):
    campaign = campaigns.save(payload('days', days=3), 'owner')
    with pytest.raises(ValueError):
        campaigns.start(campaign['id'], campaign['revision'], campaign['total'])
    campaigns.mark_tested(campaign['id'], campaign['revision'], 999)
    edited = campaigns.save(payload('days', days=4), 'owner', campaign['id'])
    with pytest.raises(ValueError):
        campaigns.start(edited['id'], edited['revision'], edited['total'])
    campaigns.mark_tested(edited['id'], edited['revision'], 999)
    with pytest.raises(ValueError):
        campaigns.start(edited['id'], edited['revision'], 99)
    campaigns.start(edited['id'], edited['revision'], edited['total'])
    with pytest.raises(ValueError):
        campaigns.start(edited['id'], edited['revision'], edited['total'])


def test_test_sends_identical_payload_without_grants_and_variants(db):
    campaign = campaigns.save(payload('days', days=3), 'owner')
    bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=7)))
    with db.get_db() as conn:
        before = [tuple(r) for r in conn.execute('SELECT expires_at,client_uuid,sub_id FROM vpn_keys')]
    asyncio.run(send_test(bot, campaign['id'], 999))
    assert bot.send_message.await_count == 3  # Header + eligible + no-subscription variant.
    assert all(c.args[0] == 999 for c in bot.send_message.await_args_list)
    _, texts = campaigns.test_samples(campaign['id'])
    assert bot.send_message.await_args_list[1].args[1] == texts[0]
    with db.get_db() as conn:
        assert [tuple(r) for r in conn.execute('SELECT expires_at,client_uuid,sub_id FROM vpn_keys')] == before
    assert campaigns.detail(campaign['id'])['tested_revision'] == campaign['revision']


def test_gift_once_sync_retry_no_false_success_and_expired_from_now(db):
    c = launch(payload('days', days=3))
    recipient = campaigns.next_recipient()
    bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=1)))
    push = AsyncMock(return_value=False)
    with db.get_db() as conn:
        old = conn.execute('SELECT expires_at FROM vpn_keys WHERE id=1').fetchone()[0]
    asyncio.run(process_recipient(bot, recipient, push))
    bot.send_message.assert_not_awaited()
    with db.get_db() as conn:
        extended = conn.execute('SELECT expires_at FROM vpn_keys WHERE id=1').fetchone()[0]
        conn.execute('UPDATE admin_broadcast_recipients SET retry_at=NULL')
    assert (datetime.fromisoformat(extended) - datetime.fromisoformat(old)).days == 3
    campaigns.recover()
    push.return_value = True
    asyncio.run(process_recipient(bot, campaigns.next_recipient(), push))
    assert bot.send_message.await_count == 1
    with db.get_db() as conn:
        assert conn.execute('SELECT expires_at FROM vpn_keys WHERE id=1').fetchone()[0] == extended
        assert tuple(conn.execute('SELECT client_uuid,sub_id FROM vpn_keys WHERE id=1').fetchone()) == ('uuid-active', 'stable-active')
    asyncio.run(process_recipient(bot, campaigns.next_recipient(), push))
    with db.get_db() as conn:
        delta = conn.execute("SELECT julianday(expires_at)-julianday('now') FROM vpn_keys WHERE id=2").fetchone()[0]
    assert 2.99 < delta <= 3
    asyncio.run(process_recipient(bot, campaigns.next_recipient(), push))
    assert 'подписки пока нет' in bot.send_message.await_args.args[1]
    campaigns.finish_ready()
    assert campaigns.detail(c['id'])['status'] == 'completed'


def test_stop_finishes_existing_reward_sync_without_sending(db):
    c = launch(payload('days', days=3))
    row = campaigns.grant_once(campaigns.next_recipient())
    campaigns.stop(c['id'])
    bot = SimpleNamespace(send_message=AsyncMock())
    asyncio.run(process_recipient(bot, campaigns.next_recipient(), AsyncMock(return_value=True)))
    bot.send_message.assert_not_awaited()
    assert campaigns.detail(c['id'])['rewards']['applied'] == 1
    assert campaigns.next_recipient() is None


def test_banned_after_snapshot_gets_no_reward(db):
    c = launch(payload('days', days=3))
    with db.get_db() as conn:
        conn.execute('UPDATE users SET is_banned=1 WHERE id=1')
        before = conn.execute('SELECT expires_at FROM vpn_keys WHERE id=1').fetchone()[0]
    assert campaigns.grant_once(campaigns.next_recipient()) is None
    with db.get_db() as conn:
        assert conn.execute('SELECT expires_at FROM vpn_keys WHERE id=1').fetchone()[0] == before
    assert campaigns.detail(c['id'])['counts']['skipped'] == 1


def test_personal_discount_bound_atomic_order_reservation_and_test_inactive(db):
    c = campaigns.save(payload('personal_discount', discount_type='percent', discount_value=20, duration_days=7), 'owner')
    campaigns.test_samples(c['id'])
    with db.get_db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM promocodes').fetchone()[0] == 0
    campaigns.mark_tested(c['id'], c['revision'], 999)
    campaigns.start(c['id'], c['revision'], c['total'])
    row = campaigns.grant_once(campaigns.next_recipient())
    assert db_promocodes.is_promocode_valid(row['promo_code'], 1)[0]
    assert not db_promocodes.is_promocode_valid(row['promo_code'], 2)[0]
    def insert(conn, order):
        conn.execute("INSERT INTO payments(user_id,tariff_id,order_id,payment_type,period_days,status,promocode_id) VALUES(1,1,?,'yookassa',30,'pending',?)", (order, row['promo_id']))
    with db.get_db() as conn:
        insert(conn, 'one')
    assert not db_promocodes.is_promocode_valid(row['promo_code'], 1)[0]
    with pytest.raises(sqlite3.IntegrityError), db.get_db() as conn:
        insert(conn, 'two')
    campaigns.grant_once(row)
    with db.get_db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM promocodes').fetchone()[0] == 1


def test_photo_limit_includes_gift_line_before_launch(db):
    data = payload('days', days=3)
    data.update(photo_file_id='photo_id', message_text='x' * 1020)
    c = campaigns.save(data, 'owner')
    with pytest.raises(ValueError):
        campaigns.test_samples(c['id'])


def test_restart_does_not_repeat_ambiguous_send(db):
    launch(payload())
    row = campaigns.grant_once(campaigns.next_recipient())
    assert campaigns.reserve_send(row)
    campaigns.recover()
    with db.get_db() as conn:
        assert conn.execute('SELECT status FROM admin_broadcast_recipients WHERE user_id=1').fetchone()[0] == 'uncertain'
    assert campaigns.next_recipient()['user_id'] == 2


@pytest.mark.parametrize('exception,expected', [
    (TelegramForbiddenError(SendMessage(chat_id=101, text='x'), 'blocked'), 'blocked'),
    (TelegramNetworkError(SendMessage(chat_id=101, text='x'), 'timeout'), 'uncertain'),
    (TelegramRetryAfter(SendMessage(chat_id=101, text='x'), 'flood', 0), 'pending'),
])
def test_delivery_errors_are_classified(db, exception, expected):
    c = launch(payload())
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=exception))
    asyncio.run(process_recipient(bot, campaigns.next_recipient(), AsyncMock()))
    assert campaigns.detail(c['id'])['counts'][expected] >= 1


def test_migration_is_repeatable(db):
    with db.get_db() as conn:
        migration_67(conn)
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='admin_broadcasts'").fetchone()[0] == 1


def test_existing_promo_changes_require_retest(db):
    pid = db_promocodes.create_promocode('SAVE20', 0, 100, 7, discount_type='percent', discount_percent=20)
    c = campaigns.save(payload('existing_promo', promo_id=pid), 'owner')
    campaigns.mark_tested(c['id'], c['revision'], 999)
    with db.get_db() as conn:
        conn.execute('UPDATE promocodes SET discount_percent=50 WHERE id=?', (pid,))
    with pytest.raises(ValueError, match='изменён'):
        campaigns.start(c['id'], c['revision'], c['total'])


def test_shared_new_promo_is_created_only_on_start(db):
    c = campaigns.save(payload('new_promo', code='THANKS', discount_type='fixed', discount_value=50, duration_days=7, max_uses=10), 'owner')
    campaigns.test_samples(c['id'])
    assert db_promocodes.get_promocode_by_code('THANKS') is None
    campaigns.mark_tested(c['id'], c['revision'], 999)
    campaigns.start(c['id'], c['revision'], c['total'])
    assert db_promocodes.is_promocode_valid('THANKS', 1)[0]


def test_api_requires_owner_rejects_cross_origin_and_untested_start(db, monkeypatch):
    import subscription_api as api
    monkeypatch.setattr(api, '_admin_access_context', lambda: {'actor_id': 'support', 'role': 'support'})
    client = api.app.test_client()
    assert client.get('/api/admin/broadcasts').status_code == 403
    monkeypatch.setattr(api, '_admin_access_context', lambda: {'actor_id': 'owner', 'role': 'owner'})
    assert client.post('/api/admin/broadcasts', json=payload(), headers={'Origin': 'https://evil.test'}).status_code == 403
    r = client.post('/api/admin/broadcasts', json=payload())
    assert r.status_code == 200
    c = r.get_json()['campaign']
    assert client.post(f"/api/admin/broadcasts/{c['id']}/start", json={'revision': c['revision'], 'count': c['total']}).status_code == 409
    assert client.post(f"/api/admin/broadcasts/{c['id']}/test", json={'admin_id': 123456}).status_code == 400
