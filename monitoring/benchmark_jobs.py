"""Durable bounded original Multitest RU module jobs."""
import hashlib
import math
import re
import secrets
from datetime import datetime, timezone

HOSTS = {"87.251.19.197", "136.148.220.228", "85.198.101.79"}
SOURCE_SHA = "068d37703beab0ec7e44a24ed45f6e911af51511ea6476a85add7250fab3d3dc"


def schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS node_benchmark_jobs (
        id TEXT PRIMARY KEY,host TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',
        created_at TEXT NOT NULL,started_at TEXT,updated_at TEXT,output TEXT NOT NULL DEFAULT '',
        exit_code INTEGER,source_sha TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS node_benchmark_agents (
        host TEXT PRIMARY KEY,token_hash TEXT NOT NULL,last_seen TEXT)""")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def enqueue(conn, host):
    if host not in HOSTS:
        raise ValueError("unknown_node")
    conn.execute("BEGIN IMMEDIATE")
    if conn.execute("SELECT 1 FROM node_benchmark_jobs WHERE host=? AND status IN ('queued','running','cancelling')", (host,)).fetchone():
        raise ValueError("node_busy")
    if conn.execute("SELECT 1 FROM node_benchmark_jobs WHERE host=? AND created_at>datetime('now','-30 minutes')", (host,)).fetchone():
        raise ValueError("cooldown")
    identifier = secrets.token_hex(16)
    conn.execute("INSERT INTO node_benchmark_jobs(id,host,created_at,source_sha) VALUES(?,?,?,?)", (identifier, host, now(), SOURCE_SHA))
    return identifier


def clean_output(value):
    # Escape/control sequences never reach the terminal display or HTML.
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", str(value))
    return ''.join(c for c in value if c in '\n\t' or ord(c) >= 32)[-100000:]


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def results(output):
    cities = 'Moscow|Saint Petersburg|Nizhny Novgorod|Chelyabinsk|Tyumen|Tver|Yaroslavl|Magnitogorsk|Krasnoyarsk'
    pattern = rf'^\s*({cities})(\s+\(F\))?\s+([\d.]+) Mbps\s+([\d.]+) Mbps\s+([\d.]+|N/A) ms\s*$'
    rows = []
    for match in re.finditer(pattern,clean_output(output),re.MULTILINE):
        receiver,sender=float(match[3]),float(match[4])
        rows.append({'city':match[1],'fallback':bool(match[2]),'receiver_mbps':receiver,
                     'sender_mbps':sender,'ping_ms':None if match[5]=='N/A' else float(match[5]),
                     'valid':math.isfinite(receiver) and math.isfinite(sender) and receiver>0 and sender>0})
    return rows
