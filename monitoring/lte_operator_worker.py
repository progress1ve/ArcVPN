"""Scheduled operator-side VPN checks for the two managed LTE/CDN exits."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from database.connection import DB_PATH
from monitoring.latencylab_client import Client, LatencyLabError, OPERATORS
from monitoring.lte_operator_alerts import Attempt, record_batch

LOG = logging.getLogger(__name__)
KEY_FILE = Path("/etc/arcvpn/latencylab.key")
LOCK_FILE = Path("/run/lock/arcvpn-lte-monitor.lock")
NODES = (("87.251.19.197", "/api-test", "Эстония"),
         ("151.241.137.174", "/api-fin", "Финляндия"))
OPERATOR_NAMES = {"tmobile": "Т-Мобайл", "megafon": "МегаФон",
                  "beeline": "Билайн", "mts": "МТС", "t2": "Т2"}


async def owner_links() -> dict[str, str]:
    """Resolve current owner links in memory; never persist or log their URI."""
    import subscription_api as api
    with sqlite3.connect(str(DB_PATH)) as conn:
        row = conn.execute("""SELECT k.sub_id FROM vpn_keys k JOIN users u ON u.id=k.user_id
            WHERE lower(u.username)='progressive_dev' AND k.expires_at>datetime('now')
            ORDER BY k.expires_at DESC LIMIT 1""").fetchone()
    if row is None:
        raise RuntimeError("owner_key_unavailable")
    key = api.get_active_key_by_subscription_id(row[0])
    if key is None:
        raise RuntimeError("owner_key_unavailable")
    links = await api._native_remnawave_links(key)
    result = {}
    for uri in links:
        parsed = urllib.parse.urlsplit(uri)
        if parsed.scheme != "vless" or parsed.hostname != "cdn-de.arccnet.space":
            continue
        path = urllib.parse.parse_qs(parsed.query).get("path", [None])[0]
        if path in {"/api-test", "/api-fin"}:
            result[path] = api._normalize_native_share_link(uri)
    if set(result) != {"/api-test", "/api-fin"}:
        raise RuntimeError("managed_links_unavailable")
    return result


def rows_by_operator(result: dict) -> dict[str, dict]:
    rows = result.get("results")
    if not isinstance(rows, list):
        return {}
    return {row["operator"]: row for row in rows
            if isinstance(row, dict) and row.get("operator") in OPERATORS}


def outcome(row: dict | None) -> bool | None:
    return row.get("ok") if row and isinstance(row.get("ok"), bool) else None


async def notify(events: list[dict]) -> None:
    if not events:
        return
    from aiogram import Bot
    import config
    bot = Bot(token=config.BOT_TOKEN)
    try:
        for event in events:
            node = next((name for host, path, name in NODES if host == event["node_host"]), event["node_host"])
            operator = OPERATOR_NAMES.get(event["operator"], event["operator"])
            if event["type"] == "alert":
                message = (f"🚨 LTE-подключение недоступно\nНода: {node}\nОператор: {operator}\n"
                           f"Три последовательные проверки VPN-ключа не прошли.\n"
                           f"Первая ошибка: {event['incident_started_at']} UTC\n"
                           "Статус режима ограничений смотрите отдельно в админке.")
            else:
                message = (f"✅ LTE-подключение восстановилось\nНода: {node}\nОператор: {operator}\n"
                           "Две последовательные проверки VPN-ключа прошли.")
            for admin_id in config.ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, message)
                except Exception:
                    LOG.warning("telegram_delivery_failed")
    finally:
        await bot.session.close()


async def run(*, client: Client | None = None, links: dict[str, str] | None = None) -> dict:
    token = KEY_FILE.read_text(encoding="utf-8").strip() if client is None else None
    client = client or Client(token)
    if client.remaining_quota() < 4:
        raise LatencyLabError("insufficient_free_quota")
    online = client.operators()
    selected = [name for name in OPERATORS if name in online]
    if not selected:
        raise LatencyLabError("no_online_operators")
    links = links or await owner_links()
    # Controls are only TCP indicators of restrictions, not proof of filtering.
    controls = {}
    for label, target in (("allowed", "yandex.ru"), ("blocked", "google.com")):
        try:
            controls[label] = rows_by_operator(client.control_multiscan(target, selected))
        except LatencyLabError:
            controls[label] = {}
    events = []
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        for host, path, _name in NODES:
            try:
                rows = rows_by_operator(client.vpn_multiscan(links[path], selected))
            except LatencyLabError:
                rows = {}
            for operator in OPERATORS:
                row = rows.get(operator)
                reason = None if row is not None else "operator_unavailable_or_job_incomplete"
                latency = row.get("latency_ms") if row else None
                attempt = Attempt(
                    operator={"tmobile": "t_mobile"}.get(operator, operator),
                    target_path=path, test_kind="client_tunnel", provider="latencylab",
                    region="Орёл", allowed_control_ok=outcome(controls["allowed"].get(operator)),
                    blocked_control_ok=outcome(controls["blocked"].get(operator)),
                    target_ok=outcome(row),
                    rtt_ms=latency if isinstance(latency, (int, float)) and 0 <= latency < 1_000_000 else None,
                    reason=reason)
                event = record_batch(conn, batch_id, host, [attempt])
                if event:
                    events.append(event)
        conn.commit()
    await notify(events)
    return {"nodes": len(NODES), "online_operators": len(selected), "transitions": len(events)}


def main() -> None:
    import fcntl
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with LOCK_FILE.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            LOG.info("already_running")
            return
        try:
            result = asyncio.run(run())
            LOG.info("completed nodes=%s online_operators=%s transitions=%s", *result.values())
        except Exception as exc:
            # No exception text: upstream errors may contain a private URI.
            LOG.error("check_failed type=%s", type(exc).__name__)
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
