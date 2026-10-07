"""Paired panel readings, collected independently of admin page visits."""
import math
from datetime import datetime

HOSTS = {'87.251.19.197', '136.148.220.228'}

def schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS node_demand_samples(
        host TEXT NOT NULL,sampled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        users INTEGER NOT NULL,tx_bps REAL NOT NULL,cpu_pct REAL,mem_pct REAL,
        PRIMARY KEY(host,sampled_at))''')
    columns={r[1] for r in conn.execute('PRAGMA table_info(node_demand_samples)')}
    for field in ('cpu_pct','mem_pct'):
        if field not in columns:
            conn.execute(f'ALTER TABLE node_demand_samples ADD COLUMN {field} REAL')

def record(conn, nodes):
    schema(conn)
    for node in nodes:
        host = node.get('address')
        stats = (node.get('system') or {}).get('stats') or {}
        tx = (stats.get('interface') or {}).get('txBytesPerSec')
        users = node.get('usersOnline')
        if host not in HOSTS or not node.get('isConnected') or node.get('isDisabled'):
            continue
        try:
            if conn.execute("SELECT 1 FROM node_benchmark_jobs WHERE host=? AND status IN ('running','cancelling')",(host,)).fetchone():
                continue
        except Exception as exc:
            import sqlite3
            if not isinstance(exc,sqlite3.OperationalError):
                raise
        if isinstance(users, bool) or not isinstance(users, (int,float)) or users < 0 or not isinstance(tx,(int,float)) or not math.isfinite(tx) or tx < 0:
            continue
        # Remnawave reports bytes/s; stored field uses bits/s, like agent telemetry.
        try:
            point=conn.execute("SELECT cpu_pct,mem_pct FROM server_health_samples WHERE host=? AND source='agent' AND sampled_at>=datetime('now','-2 minutes') ORDER BY sampled_at DESC LIMIT 1",(host,)).fetchone()
        except Exception as exc:
            import sqlite3
            if not isinstance(exc,sqlite3.OperationalError):
                raise
            point=None
        conn.execute('INSERT OR IGNORE INTO node_demand_samples(host,users,tx_bps,cpu_pct,mem_pct) VALUES(?,?,?,?,?)',(host,int(users),tx*8,point[0] if point else None,point[1] if point else None))
    conn.execute("DELETE FROM node_demand_samples WHERE sampled_at<datetime('now','-30 days')")

def estimate(rows, benchmark, summary):
    active = [r for r in rows if r['users'] > 0 and r['tx_bps'] > 0]
    if len(active) < 12 or not benchmark or len(benchmark) != 5 or any(not r.get('valid') or not math.isfinite(r['receiver_mbps']) or r['receiver_mbps']<=0 for r in benchmark):
        return None
    times = [datetime.fromisoformat(r['sampled_at']) for r in active]
    if (max(times)-min(times)).total_seconds() < 7200:
        return None
    # User-time weighted average; idle observations cannot dilute demand.
    demand = sum(r['tx_bps'] for r in active)/sum(r['users'] for r in active)/1e6
    used = sum(r['tx_bps'] for r in rows)/len(rows)/1e6
    capacity = min(r['receiver_mbps'] for r in benchmark)*.7
    p95 = summary['p95']
    if p95['cpu_pct'] is None or p95['mem_pct'] is None:
        return None
    additional = math.floor(max(0,capacity-used)/demand)
    resource_rows=[r for r in active if r.get('cpu_pct') is not None and r.get('mem_pct') is not None]
    if len(resource_rows)<12:
        return None
    mean_users=sum(r['users'] for r in resource_rows)/len(resource_rows)
    limits={}
    for field,ceiling in (('cpu_pct',70),('mem_pct',80)):
        per_user=sum(r[field] for r in resource_rows)/sum(r['users'] for r in resource_rows)
        if per_user<=0:
            return None
        # Include base OS usage rather than assuming it is free for new users.
        limits[field]=math.floor(max(0,ceiling/per_user-mean_users))
        additional=min(additional,limits[field])
    if p95['cpu_pct'] >= 85 or p95['mem_pct'] >= 90:
        additional = 0
    return {'additional_users':additional,'observed_mbps_per_user':round(demand,3),
            'average_mbps':round(used,2),'samples':len(active),'reserve_pct':30,
            'resource_limits':limits,'scope':'observed_average_resources','verified_user_capacity':False}
