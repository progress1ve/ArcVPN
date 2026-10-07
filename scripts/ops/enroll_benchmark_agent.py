"""Enroll only a pinned benchmark agent. No benchmark is queued or executed."""
import json
import os
from pathlib import Path
import secrets
from enroll_node_telemetry import connect, run, put_private
import argparse
import hashlib


def main():
    parser = argparse.ArgumentParser()
    for name in ('control-host','control-fingerprint','node-host','node-fingerprint'):
        parser.add_argument('--'+name,required=True)
    args = parser.parse_args()
    if args.node_host not in {'87.251.19.197','136.148.220.228','85.198.101.79'}:
        raise SystemExit('Unknown active node')
    token = secrets.token_urlsafe(48)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connect(args.control_host,os.environ.pop('ARCVPN_CONTROL_PASSWORD'),args.control_fingerprint) as control:
        command = "cd /root/ArcVPN && venv/bin/python -c \"from database.connection import get_connection; from monitoring.benchmark_jobs import schema; c=get_connection(); schema(c); c.execute('INSERT INTO node_benchmark_agents(host,token_hash) VALUES(?,?) ON CONFLICT(host) DO UPDATE SET token_hash=excluded.token_hash',('"+args.node_host+"','"+digest+"')); c.commit(); c.close()\""
        run(control,command)
    root = Path(__file__).resolve().parents[2]
    files = {'/usr/local/lib/arcvpn/benchmark_agent.py':'monitoring/benchmark_agent.py',
             '/usr/local/lib/arcvpn/russian-iperf3.sh':'monitoring/vendor/russian-iperf3.sh',
             '/etc/systemd/system/arcvpn-benchmark-agent.service':'monitoring/arcvpn-benchmark-agent.service',
             '/etc/systemd/system/arcvpn-benchmark-agent.timer':'monitoring/arcvpn-benchmark-agent.timer'}
    with connect(args.node_host,os.environ.pop('ARCVPN_NODE_PASSWORD'),args.node_fingerprint) as node:
        run(node,'install -d -m 0755 /usr/local/lib/arcvpn /etc/arcvpn')
        with node.open_sftp() as sftp:
            for destination, source in files.items():
                data=(root/source).read_bytes()
                if not source.endswith('.sh'):
                    data=data.replace(b'\r\n',b'\n')
                put_private(sftp,data,destination,0o644)
            put_private(sftp,json.dumps({'host':args.node_host,'token':token}).encode(),'/etc/arcvpn/benchmark-agent.json',0o600)
        run(node,'systemctl daemon-reload && systemctl enable --now arcvpn-benchmark-agent.timer && systemctl start arcvpn-benchmark-agent.service',timeout=30)
        print(run(node,'systemctl is-active arcvpn-benchmark-agent.timer && systemctl show arcvpn-benchmark-agent.service -p Result --value').decode().strip())


if __name__=='__main__':
    main()
