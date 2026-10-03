"""Admin-only temporary access with durable provisioning and cleanup."""
import asyncio
import secrets
import math
import time
from datetime import datetime, timedelta, timezone

from database.connection import get_db


def validate_options(payload):
    import uuid
    if not isinstance(payload, dict):
        raise ValueError('invalid_options')
    label = str(payload.get('label') or '').strip()
    if not label or len(label) > 80:
        raise ValueError('invalid_label')
    values = {}
    days = payload.get('days')
    if isinstance(days, bool) or not isinstance(days, (int, float)) or not math.isfinite(days) or not 0.5 <= days <= 90 or days * 2 != int(days * 2):
        raise ValueError('invalid_days')
    values['days'] = days
    for field, maximum in [('device_limit', 15), ('lte_quota_gb', 500)]:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError('invalid_' + field)
        values[field] = value
    values['request_id'] = str(uuid.UUID(str(payload.get('request_id') or '')))
    return dict(values, label=label)


def reserve_guest(options, actor):
    """One transaction reserves a synthetic identity and idempotency token."""
    with get_db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT * FROM friend_subscriptions WHERE request_id=?',
                                (options['request_id'],)).fetchone()
        if existing:
            return dict(existing), False
        synthetic = -(2_000_000_000_000 + secrets.randbelow(899_999_999_999))
        user = conn.execute("""INSERT INTO users(telegram_id,identity_source,referral_code,
            device_limit,lte_quota_gb,used_trial,enforce_device_tokens) VALUES(?,'guest',?,?,?,1,1)""",
            (synthetic, secrets.token_urlsafe(8), options['device_limit'], options['lte_quota_gb']))
        expiry = (datetime.now(timezone.utc) + timedelta(days=options['days'])).strftime('%Y-%m-%d %H:%M:%S')
        row = conn.execute("""INSERT INTO friend_subscriptions(request_id,user_id,label,
            device_limit,lte_quota_gb,created_by,expires_at) VALUES(?,?,?,?,?,?,?)""",
            (options['request_id'], user.lastrowid, options['label'], options['device_limit'],
             options['lte_quota_gb'], actor, expiry))
        return dict(conn.execute('SELECT * FROM friend_subscriptions WHERE id=?', (row.lastrowid,)).fetchone()), True


def authority_server():
    from database.requests import get_all_servers
    from bot.services.remnawave_stats import remnawave_authority_config
    servers = sorted([s for s in get_all_servers() if s.get('is_active')], key=lambda s: s['id'])
    native = next((s for s in servers if s.get('panel_type') == 'remnawave'), None)
    if native:
        return native
    if not servers:
        raise RuntimeError('authority_unavailable')
    return dict(remnawave_authority_config(), id=servers[0]['id'])


async def provision_guest(row):
    from database.requests import get_standard_trial_tariff, create_vpn_key_admin
    from bot.services.panels.factory import create_panel_client
    from bot.services.lte_identity import provision_lte_identity
    server = authority_server()
    tariff = get_standard_trial_tariff()
    if not tariff:
        raise RuntimeError('standard_unavailable')
    with get_db() as conn:
        user = dict(conn.execute('SELECT * FROM users WHERE id=?', (row['user_id'],)).fetchone())
    expiry = datetime.fromisoformat(row['expires_at']).replace(tzinfo=timezone.utc)
    username = f"arc_user_{row['user_id']}"
    client = create_panel_client(server)
    try:
        result = await client.add_client(0, username, expire_days=1,
                                         limit_ip=row['device_limit'], enable=False)
        client_uuid = str(result.get('vlessUuid') or '')
        if not client_uuid:
            raise RuntimeError('missing_identity')
        synced = await client.update_client_full(inbound_id=0, client_uuid=client_uuid, email=username,
            expiry_time_ms=int(expiry.timestamp()*1000), total_gb_bytes=0, enable=True,
            limit_ip=row['device_limit'])
        if not synced:
            raise RuntimeError('primary_sync_failed')
        await provision_lte_identity(client, user=user, expires_at=expiry,
            quota_gb=row['lte_quota_gb'], device_limit=row['device_limit'])
        key_id = create_vpn_key_admin(user_id=user['id'], server_id=server['id'], tariff_id=tariff['id'],
            panel_inbound_id=0, panel_email=username, client_uuid=client_uuid, days=1,
            traffic_limit=0, custom_name=row['label'])
        with get_db() as conn:
            conn.execute('UPDATE vpn_keys SET expires_at=? WHERE id=?', (row['expires_at'], key_id))
            conn.execute("""UPDATE users SET lte_cycle_started_at=CURRENT_TIMESTAMP,
                lte_cycle_reset_at=? WHERE id=?""", (row['expires_at'], user['id']))
            conn.execute("UPDATE friend_subscriptions SET state='active' WHERE id=? AND state='pending'", (row['id'],))
    except Exception:
        with get_db() as conn:
            conn.execute("UPDATE friend_subscriptions SET state='failed' WHERE id=?", (row['id'],))
        raise
    finally:
        await client.close()


def list_guests():
    with get_db() as conn:
        rows = conn.execute("""SELECT f.*,k.sub_id,
            (SELECT COUNT(*) FROM user_devices d WHERE d.user_id=f.user_id AND COALESCE(d.is_active,1)=1) devices_used
            FROM friend_subscriptions f LEFT JOIN vpn_keys k ON k.user_id=f.user_id
            WHERE f.state!='deleted' ORDER BY f.id DESC LIMIT 100""").fetchall()
        return [dict(r) for r in rows]


def guest_access_allowed(sub_id):
    import sqlite3
    with get_db() as conn:
        try:
            row = conn.execute("""SELECT f.state,f.expires_at FROM friend_subscriptions f
                JOIN vpn_keys k ON k.user_id=f.user_id WHERE k.sub_id=?""", (sub_id,)).fetchone()
        except sqlite3.OperationalError as exc:
            # Compatibility while migration is applied; no guest can predate this table.
            if 'no such table' in str(exc):
                return True
            raise
        return not row or (row['state'] == 'active' and row['expires_at'] > datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))


async def cleanup_guests():
    from bot.services.panels.factory import create_panel_client
    with get_db() as conn:
        rows = conn.execute("""SELECT * FROM friend_subscriptions
            WHERE state IN ('deleting','failed') OR (state='active' AND expires_at<=datetime('now'))
            OR (state='pending' AND created_at<=datetime('now','-5 minutes')) LIMIT 100""").fetchall()
        for row in rows:
            conn.execute("UPDATE friend_subscriptions SET state='deleting' WHERE id=?", (row['id'],))
            conn.execute("UPDATE vpn_keys SET expires_at=datetime('now') WHERE user_id=?", (row['user_id'],))
            conn.execute("UPDATE user_devices SET is_active=0,revoked_at=CURRENT_TIMESTAMP WHERE user_id=?", (row['user_id'],))
    if not rows:
        return
    client = create_panel_client(authority_server())
    try:
        for row in rows:
            uid = int(row['user_id'])
            # Delete exactly the two generated identities; never enumerate/remove fleet users.
            for username in (f'arc_user_{uid}', f'arc_lte_{uid}'):
                client._assert_write_allowed(username)
                panel = await client.get_user(username)
                if panel:
                    await client._request('DELETE', f"/api/users/{panel['id']}")
            with get_db() as conn:
                conn.execute('UPDATE vpn_keys SET sub_id=NULL,panel_disabled_at=CURRENT_TIMESTAMP WHERE user_id=?', (uid,))
                conn.execute('UPDATE user_devices SET device_sub_id=NULL WHERE user_id=?', (uid,))
                conn.execute('UPDATE users SET lte_client_uuid=NULL,lte_panel_username=NULL,lte_remnawave_user_id=NULL WHERE id=?', (uid,))
                conn.execute("UPDATE friend_subscriptions SET state='deleted',deleted_at=CURRENT_TIMESTAMP WHERE id=?", (row['id'],))
    finally:
        await client.close()


async def run_friend_cleanup():
    import logging
    while True:
        try:
            await cleanup_guests()
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger(__name__).warning('Temporary access cleanup will retry')
        await asyncio.sleep(60)


_GUEST_PRESENCE_CACHE = (0, {})

async def guest_presence(rows):
    """Panel connection recency, not proof of continuous payload consumption."""
    global _GUEST_PRESENCE_CACHE
    from bot.services.panels.factory import create_panel_client
    now = time.time()
    if now - _GUEST_PRESENCE_CACHE[0] < 20:
        observed = _GUEST_PRESENCE_CACHE[1]
    else:
        client = create_panel_client(authority_server())
        observed = {}
        try:
            start = 0
            while start < 10000:
                result = await client._request('GET', '/api/users', params={'start': start, 'size': 500})
                users = result.get('users', [])
                for user in users:
                    name = str(user.get('username') or '')
                    if name.startswith(('arc_user_', 'arc_lte_')):
                        observed[name] = (user.get('userTraffic') or {}).get('onlineAt')
                start += len(users)
                if not users or start >= int(result.get('total', start)):
                    break
            _GUEST_PRESENCE_CACHE = (now, observed)
        finally:
            await client.close()
    response = {}
    for row in rows:
        dates = []
        for name in (f"arc_user_{row['user_id']}", f"arc_lte_{row['user_id']}"):
            raw = observed.get(name)
            if raw:
                try:
                    at = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
                    if at.tzinfo is None:
                        at = at.replace(tzinfo=timezone.utc)
                    dates.append(at)
                except ValueError:
                    pass
        latest = max(dates) if dates else None
        response[row['id']] = {'online': bool(latest and latest.timestamp() >= now - 180),
                               'last_activity': latest.isoformat() if latest else None}
    return response
