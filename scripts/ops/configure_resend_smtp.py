#!/usr/bin/env python3
"""Install protected Resend SMTP configuration on the ArcVPN control plane."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from pathlib import Path

import paramiko


def quote_env(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def put_atomic(sftp: paramiko.SFTPClient, path: str, payload: str, mode: int) -> None:
    parent = posixpath.dirname(path)
    try:
        sftp.stat(parent)
    except FileNotFoundError:
        sftp.mkdir(parent, mode=0o700)
    temporary = f"{path}.tmp-{os.getpid()}"
    with sftp.file(temporary, "w") as handle:
        handle.write(payload)
        handle.flush()
    sftp.chmod(temporary, mode)
    try:
        sftp.posix_rename(temporary, path)
    except OSError:
        try:
            sftp.remove(path)
        except FileNotFoundError:
            pass
        sftp.rename(temporary, path)


def exec_checked(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=30)
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    if status:
        raise RuntimeError(error.strip() or f"remote command failed with status {status}")
    return output.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--from-address", default="ArcVPN <login@arccnet.space>")
    parser.add_argument("--send-test", action="store_true")
    args = parser.parse_args()

    ssh_password = os.environ.pop("ARCVPN_SSH_PASSWORD", None)
    api_key = os.environ.pop("RESEND_API_KEY", None)
    if not ssh_password or not api_key:
        raise SystemExit("ARCVPN_SSH_PASSWORD and RESEND_API_KEY must be set")

    known_hosts = Path.home() / ".ssh" / "known_hosts"
    client = paramiko.SSHClient()
    client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        hostname=args.host,
        username=args.user,
        password=ssh_password,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    try:
        env_path = "/root/ArcVPN/.secrets/resend-smtp.env"
        dropin_path = "/etc/systemd/system/arcvpn-subscription.service.d/resend-smtp.conf"
        env_payload = "\n".join(
            (
                "SMTP_HOST=smtp.resend.com",
                "SMTP_PORT=2587",
                "SMTP_USERNAME=resend",
                f"SMTP_PASSWORD={quote_env(api_key)}",
                f"SMTP_FROM={quote_env(args.from_address)}",
                "SMTP_USE_TLS=true",
                "",
            )
        )
        dropin_payload = "[Service]\nEnvironmentFile=/root/ArcVPN/.secrets/resend-smtp.env\n"
        with client.open_sftp() as sftp:
            put_atomic(sftp, env_path, env_payload, 0o600)
            put_atomic(sftp, dropin_path, dropin_payload, 0o644)

        exec_checked(client, "systemctl daemon-reload && systemctl restart arcvpn-subscription.service")
        time.sleep(2)
        active = exec_checked(client, "systemctl is-active arcvpn-subscription.service")

        smtp = smtplib.SMTP("smtp.resend.com", 2587, timeout=15)
        try:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login("resend", api_key)
            if args.send_test:
                message = EmailMessage()
                message["From"] = args.from_address
                message["To"] = "delivered@resend.dev"
                message["Subject"] = "ArcVPN SMTP acceptance"
                message["Resend-Idempotency-Key"] = "arcvpn-resend-cutover-2026-08-29"
                message.set_content("ArcVPN Resend SMTP production acceptance check.")
                smtp.send_message(message)
        finally:
            try:
                smtp.quit()
            except smtplib.SMTPException:
                pass

        print(json.dumps({"configured": True, "service": active, "smtp_auth": True, "test_sent": args.send_test}))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
