#!/usr/bin/env python3
"""Read an API key from stdin and place it on Poland over fingerprint-pinned SSH."""
import argparse
import getpass
import os

from enroll_node_telemetry import connect, put_private, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--fingerprint", required=True)
    args = parser.parse_args()
    password = os.environ.pop("ARCVPN_CONTROL_PASSWORD", "")
    if not password:
        raise SystemExit("missing_ssh_credential")
    key = getpass.getpass("LatencyLab API key: ").strip()
    if not key.startswith("ll_") or len(key) > 256 or len(key) < 30:
        raise SystemExit("invalid_key")
    with connect(args.host, password, args.fingerprint) as client:
        run(client, "install -d -m 0700 /etc/arcvpn")
        with client.open_sftp() as sftp:
            put_private(sftp, (key + "\n").encode(), "/etc/arcvpn/latencylab.key", 0o600)
    print("LatencyLab key installed outside Git with mode 0600")


if __name__ == "__main__":
    main()
