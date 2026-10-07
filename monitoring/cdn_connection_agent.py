#!/usr/bin/env python3
"""Discard raw Xray access records in RAM; report only classification metadata."""
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from cdn_connections import classify, WINDOW


def run():
    endpoint = 'https://arccnet.space/api/internal/cdn-connections'
    token = os.environ['ARCVPN_METRICS_TOKEN']
    activity = {}
    offset = 0
    last_inode = None
    gap_until = time.time() + WINDOW
    while True:
        now = time.time()
        available = False
        try:
            pid = int(subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Pid}}', 'remnanode'], timeout=3))
            path = Path(f'/proc/{pid}/root/dev/shm/arcvpn-access.log')
            stat = path.stat()
            identity = (pid, stat.st_ino)
            if identity != last_inode or stat.st_size < offset:
                # Existing records predate this collector session. Never present
                # historical connection starts as current user activity.
                offset = stat.st_size
                gap_until = now + WINDOW
                last_inode = identity
            # Read at most 4 MiB. Never print raw records or retain them on disk.
            with path.open('r+', encoding='utf-8', errors='replace') as stream:
                stream.seek(offset)
                for _ in range(50000):
                    start = stream.tell()
                    line = stream.readline(8193)
                    if not line:
                        break
                    if not line.endswith('\n'):
                        if len(line) == 8193:
                            # Discard an oversized record rather than blocking
                            # all subsequent events behind it.
                            while line and not line.endswith('\n'):
                                line = stream.readline(8193)
                            gap_until = now + WINDOW
                            continue
                        stream.seek(start)
                        break
                    record = classify(line)
                    if record:
                        key, kind = record
                        activity.setdefault(key, {})[kind + '_at'] = now
                    if stream.tell() - offset > 4 * 1024 * 1024:
                        gap_until = now + WINDOW
                        break
                offset = stream.tell()
                if offset > 4 * 1024 * 1024:
                    # A writer racing truncation can lose an event: mark negatives unknown.
                    stream.seek(0)
                    stream.truncate()
                    offset = 0
                    gap_until = now + WINDOW
            available = now >= gap_until
        except (OSError, ValueError, subprocess.SubprocessError):
            gap_until = now + WINDOW
        activity = {k: v for k, v in activity.items() if max(v.values()) >= now - WINDOW}
        payload = {'host': os.environ['ARCVPN_NODE_HOST'], 'available': available,
                   'identities': [{'hash': k, **v} for k, v in activity.items()]}
        try:
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), method='POST',
                headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                response.read(256)
        except (OSError, ValueError):
            pass  # Central heartbeat expires; never turn absence into healthy status.
        time.sleep(5)


if __name__ == '__main__':
    run()
