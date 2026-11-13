"""Scheduled operator-side VPN checks for the delivered LTE CDN transports."""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from database.connection import DB_PATH
from monitoring.cdn_origin import active_origin
from monitoring.cdn_fallbacks import HOST
from monitoring.latencylab_client import Client, LatencyLabError, OPERATORS
from monitoring.lte_operator_alerts import Attempt, record_batch

LOG = logging.getLogger(__name__)
KEY_FILE = Path("/etc/arcvpn/latencylab.key")
LOCK_FILE = Path("/run/lock/arcvpn-lte-monitor.lock")

def variant_links(profiles):
    """Serialize distinct CDN outbounds from the effective customer renderer."""
    links = {}
    for profile in profiles:
        for outbound in profile.get("outbounds", []):
            stream = outbound.get("streamSettings", {})
            xhttp = stream.get("xhttpSettings", {})
            if (outbound.get("protocol"), stream.get("network"), stream.get("security"), xhttp.get("host")) != (
                "vless", "xhttp", "tls", HOST
            ):
                continue
            target = outbound["settings"]["vnext"][0]
            user = target["users"][0]
            tls = stream["tlsSettings"]
            address, path = target["address"], xhttp["path"]
            # Keep the real path in history and distinguish the alternate edge.
            probe_id = path if address == HOST else f"{path}@{address}"
            query = {
                "type": "xhttp", "security": "tls", "encryption": user.get("encryption", "none"),
                "sni": tls["serverName"], "host": xhttp["host"], "fp": tls["fingerprint"],
                "alpn": ",".join(tls["alpn"]), "path": path, "mode": xhttp["mode"],
                "extra": json.dumps(xhttp.get("extra", {}), separators=(",", ":"), sort_keys=True),
            }
            if user.get("flow"):
                query["flow"] = user["flow"]
            authority = f'[{address}]' if ":" in address else address
            uri = f'vless://{user["id"]}@{authority}:{target["port"]}?{urllib.parse.urlencode(query)}'
            if probe_id in links and links[probe_id] != uri:
                raise RuntimeError("conflicting_cdn_probe_variants")
            links[probe_id] = uri
    return links
OPERATOR_NAMES = {"tmobile": "Т-Мобайл", "megafon": "МегаФон",
                  "beeline": "Билайн", "mts": "МТС", "t2": "Т2"}


async def owner_links() -> dict[str, str]:
    """Read the final customer profiles so delivery overlays are included."""
    import subscription_api as api
    profiles = await asyncio.to_thread(api._effective_customer_profiles)
    links = variant_links(profiles)
    if not links:
        raise RuntimeError("managed_links_unavailable")
    return links


def rows_by_operator(result: dict) -> dict[str, dict]:
    rows = result.get("results")
    if not isinstance(rows, list):
        return {}
    return {row["operator"]: row for row in rows
            if isinstance(row, dict) and row.get("operator") in OPERATORS}


def outcome(row: dict | None) -> bool | None:
    return row.get("ok") if row and isinstance(row.get("ok"), bool) else None


async def notify(events: list[dict]) -> None:
    host = active_origin()
    events = [event for event in events if event["node_host"] == host]
    if not events:
        return
    from aiogram import Bot
    import config
    bot = Bot(token=config.BOT_TOKEN)
    try:
        for event in events:
            node = f'{host} · {event["target_path"]}'
            operator = OPERATOR_NAMES.get(event["operator"], event["operator"])
            if event["type"] == "alert":
                message = (f"🚨 LTE-подключение недоступно\nНода: {node}\nОператор: {operator}\n"
                           f"Три последовательные проверки VPN-ключа не прошли.\n"
                           f"Первая ошибка: {event['incident_started_at']} UTC\n"
                           "Статус режима ограничений смотрите отдельно в админке.")
            else:
                message = (f"✅ LTE-подключение восстановилось\nНода: {node}\nОператор: {operator}\n"
                           "Две последовательные проверки VPN-ключа прошли.")
            from bot.services.admin_recipients import admin_notification_ids
            for admin_id in admin_notification_ids():
                try:
                    await bot.send_message(admin_id, message)
                except Exception:
                    LOG.warning("telegram_delivery_failed")
    finally:
        await bot.session.close()


async def run(*, client: Client | None = None, links: dict[str, str] | None = None) -> dict:
    token = KEY_FILE.read_text(encoding="utf-8").strip() if client is None else None
    client = client or Client(token)
    host = active_origin()
    links = links if links is not None else await owner_links()
    if not links:
        raise RuntimeError("managed_links_unavailable")
    if client.remaining_quota() < 2 + len(links):
        raise LatencyLabError("insufficient_free_quota")
    online = client.operators()
    selected = [name for name in OPERATORS if name in online]
    if not selected:
        raise LatencyLabError("no_online_operators")
    # Controls are only TCP indicators of restrictions, not proof of filtering.
    controls = {}
    for label, target in (("allowed", "yandex.ru"), ("blocked", "google.com")):
        try:
            controls[label] = rows_by_operator(client.control_multiscan(target, selected))
        except LatencyLabError:
            controls[label] = {}
    events = []
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Complete external probes before opening a database write transaction.
    # External probes can take minutes; API telemetry must remain writable.
    attempts = []
    for path, uri in links.items():
        try:
            rows = rows_by_operator(client.vpn_multiscan(uri, selected))
        except LatencyLabError as error:
            LOG.warning("vpn_probe_failed variant=%s reason=%s", path, error)
            rows = {}
        for operator in OPERATORS:
            row = rows.get(operator)
            reason = ("operator_offline" if operator not in online else
                      "provider_result_missing" if row is None else None)
            latency = row.get("latency_ms") if row else None
            attempt = Attempt(
                operator={"tmobile": "t_mobile"}.get(operator, operator),
                target_path=path, test_kind="client_tunnel", provider="latencylab",
                region="Орёл", allowed_control_ok=outcome(controls["allowed"].get(operator)),
                blocked_control_ok=outcome(controls["blocked"].get(operator)),
                target_ok=outcome(row),
                rtt_ms=latency if isinstance(latency, (int, float)) and 0 <= latency < 1_000_000 else None,
                reason=reason)
            attempts.append((host, attempt))
    with sqlite3.connect(str(DB_PATH), timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        for host, attempt in attempts:
            event = record_batch(conn, batch_id, host, [attempt])
            if event:
                events.append(event)
        conn.commit()
    await notify(events)
    return {"variants": len(links), "online_operators": len(selected), "transitions": len(events)}


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
            LOG.info("completed variants=%s online_operators=%s transitions=%s", *result.values())
        except Exception as exc:
            # No exception text: upstream errors may contain a private URI.
            LOG.error("check_failed type=%s", type(exc).__name__)
            raise SystemExit(1) from None


if __name__ == "__main__":
    main()
