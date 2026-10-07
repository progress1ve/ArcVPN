#!/usr/bin/env python3
"""Install the existing read-only telemetry agent over two pinned SSH sessions.

Passwords come from the caller's process environment and are never printed.
The control-plane token stays in process memory and travels to the node by SFTP.
"""

import argparse
import base64
import hashlib
import io
import os
from pathlib import Path

import paramiko


class PinnedKey(paramiko.MissingHostKeyPolicy):
    def __init__(self, expected):
        self.expected = expected

    def missing_host_key(self, client, hostname, key):
        actual = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        if actual != self.expected:
            raise paramiko.SSHException("SSH host key mismatch")


def connect(host, password, fingerprint):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedKey(fingerprint))
    client.connect(
        hostname=host, username="root", password=password, timeout=10,
        auth_timeout=10, banner_timeout=10, allow_agent=False, look_for_keys=False,
    )
    return client


def run(client, command, timeout=20):
    _, output, errors = client.exec_command(command, timeout=timeout)
    stdout = output.read()
    stderr = errors.read()
    if output.channel.recv_exit_status():
        raise RuntimeError(f"Remote operation failed: {stderr.decode('utf-8', 'replace')[:200]}")
    return stdout


def put_private(sftp, data, destination, mode):
    temporary = destination + ".arcvpn-new"
    sftp.putfo(io.BytesIO(data), temporary)
    sftp.chmod(temporary, mode)
    sftp.posix_rename(temporary, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-host", required=True)
    parser.add_argument("--control-fingerprint", required=True)
    parser.add_argument("--node-host", required=True)
    parser.add_argument("--node-fingerprint", required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--cdn-collector", action="store_true")
    args = parser.parse_args()
    control_password = os.environ.pop("ARCVPN_CONTROL_PASSWORD", "")
    node_password = os.environ.pop("ARCVPN_NODE_PASSWORD", "")
    if not control_password or not node_password:
        raise SystemExit("Both SSH credentials are required in the environment")

    with connect(args.control_host, control_password, args.control_fingerprint) as control:
        token = run(control, "cd /root/ArcVPN && venv/bin/python -c 'import config; print(config.NODE_METRICS_TOKEN, end=\"\")'").decode().strip()
    if len(token) < 24 or "\n" in token:
        raise RuntimeError("Control-plane metrics token is missing or malformed")

    root = Path(__file__).resolve().parents[2]
    files = {
        "/usr/local/lib/arcvpn/arcvpn_node_agent.py": (root / "monitoring/arcvpn_node_agent.py").read_bytes().replace(b"\r\n", b"\n"),
        "/etc/systemd/system/arcvpn-node-agent.service": (root / "monitoring/arcvpn-node-agent.service").read_bytes().replace(b"\r\n", b"\n"),
        "/etc/systemd/system/arcvpn-node-agent.timer": (root / "monitoring/arcvpn-node-agent.timer").read_bytes().replace(b"\r\n", b"\n"),
    }
    if args.cdn_collector:
        if args.node_host != "136.148.220.228":
            raise RuntimeError("CDN origin must be Sweden")
        files.update({
            "/usr/local/lib/arcvpn/cdn_connection_agent.py": (root / "monitoring/cdn_connection_agent.py").read_bytes().replace(b"\r\n", b"\n"),
            "/usr/local/lib/arcvpn/cdn_connections.py": (root / "monitoring/cdn_connections.py").read_bytes().replace(b"\r\n", b"\n"),
            "/etc/systemd/system/arcvpn-cdn-connections.service": (root / "monitoring/arcvpn-cdn-connections.service").read_bytes().replace(b"\r\n", b"\n"),
        })
    env = (
        f"ARCVPN_METRICS_TOKEN={token}\n"
        f"ARCVPN_NODE_HOST={args.node_host}\n"
        f"ARCVPN_NODE_NAME={args.node_name}\n"
        "ARCVPN_PROBE_INTERVAL_SECONDS=1800\n"
    ).encode()
    with connect(args.node_host, node_password, args.node_fingerprint) as node:
        run(node, "install -d -m 0755 /usr/local/lib/arcvpn /etc/arcvpn /var/lib/arcvpn-node-agent")
        with node.open_sftp() as sftp:
            for destination, contents in files.items():
                put_private(sftp, contents, destination, 0o755 if destination.endswith(".py") else 0o644)
            put_private(sftp, env, "/etc/arcvpn/node-agent.env", 0o600)
        run(node, "systemctl daemon-reload && systemctl enable --now arcvpn-node-agent.timer && systemctl start arcvpn-node-agent.service", timeout=90)
        if args.cdn_collector:
            run(node, "systemctl enable --now arcvpn-cdn-connections.service")
        result = run(node, "systemctl is-active arcvpn-node-agent.timer && systemctl show arcvpn-node-agent.service -p Result --value")
        print(result.decode().strip())


if __name__ == "__main__":
    main()
