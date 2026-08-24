#!/usr/bin/env python3
"""Run a bounded SSH command with a password supplied only through process env."""

import argparse
import os
import sys
from pathlib import Path

import paramiko


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("command")
    args = parser.parse_args()

    password = os.environ.pop("ARCVPN_SSH_PASSWORD", None)
    if not password:
        raise SystemExit("ARCVPN_SSH_PASSWORD is not set")

    known_hosts = Path.home() / ".ssh" / "known_hosts"
    if not known_hosts.exists():
        raise SystemExit(f"known_hosts is missing: {known_hosts}")

    client = paramiko.SSHClient()
    client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        hostname=args.host,
        port=args.port,
        username=args.user,
        password=password,
        timeout=args.timeout,
        allow_agent=False,
        look_for_keys=False,
    )
    try:
        _, stdout, stderr = client.exec_command(args.command, timeout=args.timeout)
        out = stdout.read()
        err = stderr.read()
        if out:
            sys.stdout.buffer.write(out)
        if err:
            sys.stderr.buffer.write(err)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
