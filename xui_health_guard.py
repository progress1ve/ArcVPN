#!/usr/bin/env python3
"""ArcVPN production guard for the local 3x-ui master.

The guard is intentionally independent from the bot scheduler.  It protects
the panel database/inbound topology and reconciles active ArcVPN keys with the
3x-ui v3 client registry.  It never deletes panel clients or resets traffic.
"""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import config
from bot.services.panels.xui import XUIClient
from database.db_keys import get_all_active_keys_with_server, update_vpn_key_config
from database.db_servers import get_server_by_id


LOGGER = logging.getLogger("arcvpn.xui_guard")
XUI_DB = Path(os.getenv("ARCVPN_XUI_DB", "/etc/x-ui/x-ui.db"))
BACKUP_DIR = Path(os.getenv("ARCVPN_XUI_BACKUP_DIR", "/root/ArcVPN/backup/xui-guard"))
BASELINE_DB = BACKUP_DIR / "last-known-good.db"
LOCK_FILE = Path(os.getenv("ARCVPN_XUI_GUARD_LOCK", "/run/arcvpn-xui-health.lock"))
PROTECTED_SERVER_ID = int(os.getenv("ARCVPN_PROTECTED_SERVER_ID", "10"))
EXPECTED_INBOUND_IDS = {
    int(item)
    for item in os.getenv("ARCVPN_EXPECTED_INBOUND_IDS", "3,5,7,13,14,15,16,17").split(",")
    if item.strip()
}
GIB = 1024**3


class GuardError(RuntimeError):
    pass


def _notify_admins(text: str) -> None:
    token = getattr(config, "BOT_TOKEN", "")
    if not token:
        return
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    for admin_id in getattr(config, "ADMIN_IDS", []):
        try:
            body = json.dumps(
                {"chat_id": admin_id, "text": text, "disable_web_page_preview": True}
            ).encode("utf-8")
            request = urllib.request.Request(
                endpoint, data=body, headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(request, timeout=8).read()
        except Exception as exc:
            LOGGER.warning("Admin health notification failed: %s", exc)


def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
    dst = sqlite3.connect(temporary, timeout=30)
    try:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise GuardError(f"Backup integrity check failed: {destination}")
    finally:
        dst.close()
        src.close()
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)


def _database_state(path: Path = XUI_DB) -> tuple[str, set[int]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=20)
    try:
        integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        inbound_ids = {
            int(row[0]) for row in connection.execute("SELECT id FROM inbounds")
        }
        return integrity, inbound_ids
    finally:
        connection.close()


def _run_systemctl(action: str) -> None:
    subprocess.run(
        ["systemctl", action, "x-ui.service"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )


def _service_active(name: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    return result.returncode == 0


def _xray_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "xray-linux-amd64"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )
    return result.returncode == 0


def _wait_for_xui(timeout: int = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["systemctl", "is-active", "--quiet", "x-ui.service"],
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            time.sleep(2)
            return
        time.sleep(1)
    raise GuardError("x-ui.service did not become active")


def _ensure_runtime() -> None:
    if not _service_active("x-ui.service"):
        _run_systemctl("restart")
        _wait_for_xui()

    if not _xray_running():
        LOGGER.warning("Xray child is absent; restarting x-ui")
        _run_systemctl("restart")
        _wait_for_xui()
        if not _xray_running():
            integrity, inbound_ids = _database_state()
            if integrity != "ok":
                raise GuardError(f"Xray is down and DB quick_check failed: {integrity}")
            _restore_topology_from_baseline(inbound_ids)
            if not _xray_running():
                raise GuardError("Xray is still down after restoring the known-good topology")

    if not _service_active("arcvpn-hysteria.service"):
        subprocess.run(
            ["systemctl", "restart", "arcvpn-hysteria.service"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if not _service_active("arcvpn-hysteria.service"):
            raise GuardError("arcvpn-hysteria.service did not recover")


def _repair_sqlite_journal() -> None:
    LOGGER.warning("Repairing the 3x-ui SQLite journal state")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _sqlite_backup(XUI_DB, BACKUP_DIR / f"before-journal-repair-{stamp}.db")
    _run_systemctl("stop")
    try:
        connection = sqlite3.connect(XUI_DB, timeout=30)
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("PRAGMA journal_mode=DELETE")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise GuardError("3x-ui DB failed integrity_check during journal repair")
        finally:
            connection.close()
        XUI_DB.with_name(XUI_DB.name + "-wal").unlink(missing_ok=True)
        XUI_DB.with_name(XUI_DB.name + "-shm").unlink(missing_ok=True)
    finally:
        _run_systemctl("start")
        _wait_for_xui()


def _restore_topology_from_baseline(actual_ids: set[int]) -> None:
    if not BASELINE_DB.exists():
        raise GuardError(
            f"Inbound topology changed ({sorted(actual_ids)}), but no baseline exists"
        )
    baseline_integrity, baseline_ids = _database_state(BASELINE_DB)
    if baseline_integrity != "ok" or baseline_ids != EXPECTED_INBOUND_IDS:
        raise GuardError("The last-known-good topology backup is not usable")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _sqlite_backup(XUI_DB, BACKUP_DIR / f"before-topology-restore-{stamp}.db")
    _run_systemctl("stop")
    try:
        temporary = XUI_DB.with_suffix(".restore")
        shutil.copy2(BASELINE_DB, temporary)
        os.chmod(temporary, 0o644)
        os.replace(temporary, XUI_DB)
        XUI_DB.with_name(XUI_DB.name + "-wal").unlink(missing_ok=True)
        XUI_DB.with_name(XUI_DB.name + "-shm").unlink(missing_ok=True)
    finally:
        _run_systemctl("start")
        _wait_for_xui()


def _expiry_ms(value: Any) -> int:
    if not value:
        return 0
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def _remaining_minutes(value: Any) -> int:
    expiry = _expiry_ms(value)
    if expiry <= 0:
        return 10 * 365 * 24 * 60
    return max(1, math.ceil((expiry / 1000 - time.time()) / 60))


async def _reconcile_clients() -> list[str]:
    server = get_server_by_id(PROTECTED_SERVER_ID)
    if not server or not server.get("is_active"):
        raise GuardError(f"Protected server {PROTECTED_SERVER_ID} is inactive")

    keys = [
        item
        for item in get_all_active_keys_with_server()
        if int(item["server_id"]) == PROTECTED_SERVER_ID
    ]
    client = XUIClient(server)
    changes: list[str] = []
    try:
        inbounds = await client.get_inbounds()
        supported_ids = {
            int(item["id"])
            for item in inbounds
            if item.get("protocol") in client.SUPPORTED_PROTOCOLS
        }
        if supported_ids != EXPECTED_INBOUND_IDS:
            raise GuardError(
                f"Panel API inbound mismatch: expected={sorted(EXPECTED_INBOUND_IDS)} "
                f"actual={sorted(supported_ids)}"
            )

        panel_clients = await client._v3_list_clients()
        panel_by_email = {
            str(item.get("email", "")): item
            for item in panel_clients
            if item.get("email")
        }

        for key in keys:
            key_id = int(key["id"])
            email = str(key["panel_email"])
            panel = panel_by_email.get(email)
            expected_expiry = _expiry_ms(key.get("expires_at"))
            expected_total = int(key.get("traffic_limit") or 0)

            if panel is None:
                total_gb = math.ceil(expected_total / GIB) if expected_total else 0
                result = await client.provision_client_all_inbounds(
                    email=email,
                    total_gb=total_gb,
                    expire_minutes=_remaining_minutes(key.get("expires_at")),
                    limit_ip=1,
                    enable=True,
                    tg_id=str(key.get("telegram_id") or ""),
                    secret=str(key.get("client_uuid") or ""),
                )
                secret = str(result["uuid"])
                update_vpn_key_config(
                    key_id,
                    PROTECTED_SERVER_ID,
                    int(result["primary_inbound_id"]),
                    email,
                    secret,
                )
                panel = await client._v3_get_client(email)
                if panel is None:
                    raise GuardError(f"Client {key_id} could not be recreated")
                changes.append(f"recreated:{key_id}")

            secret = str(panel.get("uuid") or panel.get("password") or "")
            if secret and secret != str(key.get("client_uuid") or ""):
                update_vpn_key_config(
                    key_id,
                    PROTECTED_SERVER_ID,
                    int(key.get("panel_inbound_id") or min(EXPECTED_INBOUND_IDS)),
                    email,
                    secret,
                )
                changes.append(f"uuid:{key_id}")

            attached = {int(value) for value in (panel.get("inboundIds") or [])}
            missing_inbounds = sorted(EXPECTED_INBOUND_IDS - attached)
            if missing_inbounds:
                await client._v3_attach(email, missing_inbounds)
                changes.append(f"attached:{key_id}")

            panel_expiry = int(panel.get("expiryTime") or 0)
            panel_total = int(panel.get("totalGB") or 0)
            needs_update = (
                not bool(panel.get("enable", True))
                or abs(panel_expiry - expected_expiry) > 60_000
                or panel_total != expected_total
            )
            if needs_update:
                await client.update_client_full(
                    inbound_id=int(key.get("panel_inbound_id") or min(EXPECTED_INBOUND_IDS)),
                    client_uuid=secret or str(key.get("client_uuid") or ""),
                    email=email,
                    expiry_time_ms=expected_expiry,
                    total_gb_bytes=expected_total,
                    enable=True,
                )
                changes.append(f"synced:{key_id}")
    finally:
        await client.close()
    return changes


async def _guard_once() -> list[str]:
    _ensure_runtime()
    integrity, actual_ids = _database_state()
    if integrity != "ok":
        raise GuardError(f"3x-ui quick_check failed: {integrity}")
    if actual_ids != EXPECTED_INBOUND_IDS:
        LOGGER.error(
            "Inbound topology mismatch: expected=%s actual=%s",
            sorted(EXPECTED_INBOUND_IDS),
            sorted(actual_ids),
        )
        _restore_topology_from_baseline(actual_ids)

    try:
        changes = await _reconcile_clients()
    except Exception as exc:
        if "disk I/O error" not in str(exc):
            raise
        _repair_sqlite_journal()
        changes = await _reconcile_clients()
        changes.insert(0, "sqlite-journal")

    integrity, actual_ids = _database_state()
    if integrity != "ok" or actual_ids != EXPECTED_INBOUND_IDS:
        raise GuardError("Post-repair database/topology verification failed")

    _sqlite_backup(XUI_DB, BASELINE_DB)
    daily = BACKUP_DIR / f"x-ui-{date.today().isoformat()}.db"
    if not daily.exists():
        _sqlite_backup(XUI_DB, daily)
    return changes


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            LOGGER.info("Another health guard run is still active")
            return 0

        try:
            changes = asyncio.run(_guard_once())
        except Exception as exc:
            LOGGER.exception("ArcVPN x-ui health guard failed")
            _notify_admins(f"🚨 ArcVPN: проверка x-ui не пройдена\n{type(exc).__name__}: {exc}")
            return 1

    if changes:
        summary = ", ".join(changes)
        LOGGER.warning("ArcVPN x-ui auto-recovery applied: %s", summary)
        _notify_admins(f"🛠 ArcVPN: x-ui автоматически восстановлен\n{summary}")
    else:
        LOGGER.info("ArcVPN x-ui health check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
