"""Connection-start classification, never inferred from byte counts or onlineAt."""
import hashlib
import re
import sqlite3
import time

PROBE_URL = 'http://sub.arccnet.space:18080/generate_204'
HTTPS_PROBE_URL = 'https://sub.arccnet.space:18443/generate_204'
PROBE_TARGETS = {'tcp:sub.arccnet.space:18080', 'tcp:217.60.33.38:18080',
                 'tcp:sub.arccnet.space:18443', 'tcp:217.60.33.38:18443'}
LEGACY_TARGETS = {'tcp:www.gstatic.com:80', 'tcp:www.gstatic.com:443',
                  'tcp:www.google.com:80', 'tcp:www.google.com:443'}
WINDOW = 180
CDN_INBOUND_TAGS = frozenset(
    f'{country}_{variant}'
    for country in ('EE', 'SE', 'LT', 'NL')
    for variant in ('CDN_TEST_4096', 'CDN_TEST_24000', 'CDN_BODY_65536', 'CDN_HEADER_32768')
) | {'NL_CDN_RESERVE_XHTTP'}


def identity_hash(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def classify(line):
    # Xray access format: from ... accepted destination [inbound -> outbound] email: identity
    match = re.search(r' accepted (\S+) \[([^\]]+)\].*? email: (\S+)\s*$', line[:8192])
    if not match:
        return None
    destination, detour, email = match.groups()
    inbound = re.split(r'\s*(?:->|>>)\s*', detour)[0]
    if inbound not in CDN_INBOUND_TAGS:
        return None
    kind = 'probe' if destination in PROBE_TARGETS else 'legacy' if destination in LEGACY_TARGETS else 'user'
    return identity_hash(email), kind


def schema(conn):
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS cdn_connection_reports(host TEXT PRIMARY KEY, received_at REAL NOT NULL, available INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS cdn_connection_activity(host TEXT NOT NULL, identity_hash TEXT NOT NULL,
        user_at REAL NOT NULL DEFAULT 0, probe_at REAL NOT NULL DEFAULT 0, legacy_at REAL NOT NULL DEFAULT 0,
        PRIMARY KEY(host,identity_hash));
    ''')


def ingest(conn, host, payload, now=None):
    now = time.time() if now is None else now
    available = payload.get('available')
    rows = payload.get('identities')
    if type(available) is not bool or not isinstance(rows, list) or len(rows) > 2000:
        raise ValueError('invalid_cdn_report')
    parsed = []
    for row in rows:
        if not isinstance(row, dict) or not re.fullmatch(r'[0-9a-f]{64}', str(row.get('hash', ''))):
            raise ValueError('invalid_cdn_report')
        values = []
        for key in ('user_at', 'probe_at', 'legacy_at'):
            value = row.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= now + 10:
                raise ValueError('invalid_cdn_report')
            values.append(value if value >= now - WINDOW else 0)
        parsed.append((host, row['hash'], *values))
    conn.execute('INSERT OR REPLACE INTO cdn_connection_reports VALUES(?,?,?)', (host, now, int(available)))
    for row in parsed:
        conn.execute('''INSERT INTO cdn_connection_activity VALUES(?,?,?,?,?) ON CONFLICT(host,identity_hash)
          DO UPDATE SET user_at=max(user_at,excluded.user_at),probe_at=max(probe_at,excluded.probe_at),legacy_at=max(legacy_at,excluded.legacy_at)''', row)
    conn.execute('DELETE FROM cdn_connection_activity WHERE max(user_at,probe_at,legacy_at)<?', (now - WINDOW,))


def observations(conn, identities, origin, now=None):
    now = time.time() if now is None else now
    try:
        report = conn.execute("SELECT * FROM cdn_connection_reports WHERE host=?", (origin,)).fetchone()
        rows = conn.execute("SELECT * FROM cdn_connection_activity WHERE host=?", (origin,)).fetchall()
    except sqlite3.OperationalError:
        return {}
    byhash = {r['identity_hash']: r for r in rows}
    fresh = report and report['received_at'] >= now - 30 and bool(report['available'])
    result = {}
    for uid, values in identities.items():
        hashes = {identity_hash(value) for value in values if value}
        activity = [byhash[key] for key in hashes if key in byhash]
        user_at = max((row['user_at'] for row in activity), default=0)
        if user_at >= now - WINDOW:
            result[uid] = ('user', user_at)
        elif not fresh or any(row['legacy_at'] >= now - WINDOW for row in activity):
            result[uid] = ('unknown', None)
        elif any(row['probe_at'] >= now - WINDOW for row in activity):
            result[uid] = ('probe', None)
        else:
            result[uid] = ('none', None)
    return result
