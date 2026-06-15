#!/usr/bin/env python3
"""
Subscription API для VPN бота.

Возвращает base64-encoded список VPN ключей пользователя.
Клиенты VPN подключаются по ссылке и автоматически получают обновления.
"""

import asyncio
import base64
import concurrent.futures
import html
import json
import logging
import re
import threading
import time
import urllib.parse
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Coroutine, Deque, Dict, Iterable, Optional

from flask import Flask, Response, redirect, request

from bot.services.panels.base import VPNAPIError
from bot.services.panels.xui import XUIClient
from bot.utils.key_generator import generate_link
from config import (
    SUBSCRIPTION_URL,
    ENABLE_SPLIT_TUNNELING,
    SPLIT_TUNNELING_DIRECT_IP,
    SPLIT_TUNNELING_DIRECT_SITES,
    SPLIT_TUNNELING_MODE,
    SPLIT_TUNNELING_REMOTE_DNS_DOMAIN,
    SPLIT_TUNNELING_REMOTE_DNS_IP,
)
from database.connection import get_db
from database.db_servers import get_server_by_id

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

SERVER_CACHE_TTL_SECONDS = 300
CLIENT_CONFIG_CACHE_TTL_SECONDS = 180
MAX_CACHE_ITEMS = 2048
SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS = 60
SUBSCRIPTION_RATE_LIMIT_PER_TOKEN = 12
SUBSCRIPTION_RATE_LIMIT_PER_IP = 120
PROFILE_UPDATE_INTERVAL_HOURS = 24
XUI_CONFIG_FETCH_TIMEOUT_SECONDS = 7
ASYNC_EXECUTOR_RESULT_TIMEOUT_SECONDS = 12
RATE_LIMITER_MAX_KEYS = 10000
VALID_SUBSCRIPTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
PROFILE_TITLE = "ArcVPN"
PROFILE_TITLE_BASE64 = base64.b64encode(PROFILE_TITLE.encode("utf-8")).decode("ascii")
SUPPORT_URL = "https://t.me/Turan11627"
PROFILE_WEB_PAGE_URL = "https://t.me/arcvpn1"

LOCAL_AND_RESERVED_CIDRS = [
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "224.0.0.0/4",
    "255.255.255.255/32",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]


def _build_happ_routing_profile() -> Dict[str, Any]:
    mode = (SPLIT_TUNNELING_MODE or "speed").strip().lower()
    use_remote_doh = mode == "compatibility"

    profile: Dict[str, Any] = {
        "Name": "ArcVPN - Smart Route",
        "GlobalProxy": "true",
        "RemoteDNSType": "DoH" if use_remote_doh else "System",
        "DomesticDNSType": "System",
        "DirectSites": list(SPLIT_TUNNELING_DIRECT_SITES),
        "DirectIp": list(SPLIT_TUNNELING_DIRECT_IP),
        "ProxySites": [],
        "ProxyIp": [],
        "BlockSites": [],
        "BlockIp": [],
        "DomainStrategy": "IPIfNonMatch" if mode == "speed" else "AsIs",
        "FakeDNS": "false",
    }

    if use_remote_doh:
        profile["RemoteDNSDomain"] = SPLIT_TUNNELING_REMOTE_DNS_DOMAIN
        profile["RemoteDNSIP"] = SPLIT_TUNNELING_REMOTE_DNS_IP

    return profile


HAPP_ROUTING_PROFILE = _build_happ_routing_profile()


@dataclass(frozen=True)
class ActiveKeyRecord:
    id: int
    server_id: int
    panel_email: str
    expires_at: str
    traffic_limit: int
    traffic_used: int
    tariff_name: str
    telegram_id: int
    sub_id: Optional[str] = None

    @property
    def traffic_exhausted(self) -> bool:
        return self.traffic_limit > 0 and self.traffic_used >= self.traffic_limit

    @property
    def has_available_traffic(self) -> bool:
        return not self.traffic_exhausted

    @property
    def expires_at_unix(self) -> int:
        parsed = _parse_db_datetime(self.expires_at)
        return int(parsed.timestamp()) if parsed else 0


@dataclass(frozen=True)
class ServerRecord:
    id: int
    name: str
    host: str
    port: int
    protocol: str
    web_base_path: str
    login: str
    password: str

    def to_panel_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "web_base_path": self.web_base_path,
            "login": self.login,
            "password": self.password,
        }


@dataclass(frozen=True)
class PreparedSubscription:
    body: str
    content_type: str
    userinfo_header: str
    routing_link: Optional[str] = None


class TTLCache:
    """Простой потокобезопасный TTL-кэш для данных подписок."""

    def __init__(self, ttl_seconds: int, max_items: int):
        self._ttl_seconds = ttl_seconds
        self._max_items = max_items
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def _purge_expired_locked(self, now: float) -> None:
        expired_keys = [
            key for key, (expires_at, _) in self._store.items()
            if expires_at <= now
        ]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        now = time.monotonic()
        with self._lock:
            self._purge_expired_locked(now)
            if key in self._store:
                self._store.pop(key, None)
            elif len(self._store) >= self._max_items:
                self._store.popitem(last=False)
            self._store[key] = (now + self._ttl_seconds, value)


class SlidingWindowRateLimiter:
    """Ограничивает частоту обновления подписки по токену и IP."""

    def __init__(self, limit: int, window_seconds: int, max_keys: int = RATE_LIMITER_MAX_KEYS):
        self._limit = limit
        self._window_seconds = window_seconds
        self._max_keys = max_keys
        self._events: OrderedDict[str, Deque[float]] = OrderedDict()
        self._lock = threading.RLock()

    def _cleanup_locked(self, now: float) -> None:
        cutoff = now - self._window_seconds
        while self._events:
            oldest_key, bucket = next(iter(self._events.items()))
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if bucket:
                break
            self._events.pop(oldest_key, None)

        # При аномально большом количестве уникальных ключей удерживаем память bounded.
        while len(self._events) > self._max_keys:
            self._events.popitem(last=False)

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            self._cleanup_locked(now)
            bucket = self._events.get(key)
            if bucket is None:
                bucket = deque()
                self._events[key] = bucket
            else:
                self._events.move_to_end(key)
            while bucket and bucket[0] <= now - self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry_after = max(1, int(self._window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            if len(self._events) > self._max_keys:
                self._events.popitem(last=False)
            return True, 0


class AsyncExecutor:
    """Один общий asyncio loop в фоне вместо создания loop на каждый запрос."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()

    def _ensure_started(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._ready.clear()
                self._thread = threading.Thread(
                    target=self._run_loop,
                    name="subscription-api-loop",
                    daemon=True,
                )
                self._thread.start()
        self._ready.wait()
        if self._loop is None:
            raise RuntimeError("Async loop was not initialized")
        return self._loop

    def run(self, coro: Coroutine[Any, Any, Any]) -> Any:
        loop = self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=ASYNC_EXECUTOR_RESULT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError("Subscription generation timed out")


SERVER_CACHE = TTLCache(SERVER_CACHE_TTL_SECONDS, 256)
CLIENT_CONFIG_CACHE = TTLCache(CLIENT_CONFIG_CACHE_TTL_SECONDS, MAX_CACHE_ITEMS)
TOKEN_RATE_LIMITER = SlidingWindowRateLimiter(
    SUBSCRIPTION_RATE_LIMIT_PER_TOKEN,
    SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS,
)
IP_RATE_LIMITER = SlidingWindowRateLimiter(
    SUBSCRIPTION_RATE_LIMIT_PER_IP,
    SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS,
)
ASYNC_EXECUTOR = AsyncExecutor()
SERVER_FETCH_LOCKS: Dict[int, asyncio.Lock] = {}
SERVER_FETCH_LOCKS_GUARD = threading.Lock()


def _parse_db_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = str(value).strip().replace("Z", "+00:00").replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def _mask_email(email: str) -> str:
    if "@" not in email:
        return _mask_token(email)
    local_part, _, domain = email.partition("@")
    if len(local_part) <= 2:
        return f"***@{domain}"
    return f"{local_part[:2]}***@{domain}"


def _detect_client_family(user_agent: str) -> str:
    agent = user_agent.lower()
    if "happ" in agent:
        return "happ"
    if "hiddify" in agent:
        return "hiddify"
    if "clash" in agent or "meta" in agent:
        return "clash"
    if "sing-box" in agent or "singbox" in agent:
        return "sing-box"
    if "v2ray" in agent or "nekobox" in agent:
        return "v2ray"
    return "generic"


def _extract_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_valid_subscription_id(sub_id: str) -> bool:
    return bool(VALID_SUBSCRIPTION_ID_PATTERN.fullmatch(sub_id))


def _row_to_active_key(row: Any) -> ActiveKeyRecord:
    return ActiveKeyRecord(
        id=int(row["id"]),
        server_id=int(row["server_id"]),
        panel_email=str(row["panel_email"]),
        expires_at=str(row["expires_at"]),
        traffic_limit=int(row["traffic_limit"] or 0),
        traffic_used=int(row["traffic_used"] or 0),
        tariff_name=str(row["tariff_name"] or "Subscription"),
        telegram_id=int(row["telegram_id"]),
        sub_id=row["sub_id"],
    )


def _build_subscription_userinfo(key: ActiveKeyRecord) -> str:
    parts = [
        "upload=0",
        f"download={max(0, key.traffic_used)}",
    ]
    if key.traffic_limit > 0:
        parts.append(f"total={key.traffic_limit}")
    if key.expires_at_unix > 0:
        parts.append(f"expire={key.expires_at_unix}")
    return "; ".join(parts)


def _build_routing_link() -> Optional[str]:
    if not ENABLE_SPLIT_TUNNELING:
        return None
    routing_profile_json = json.dumps(
        HAPP_ROUTING_PROFILE,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    encoded_profile = base64.b64encode(routing_profile_json.encode("utf-8")).decode("ascii")
    return f"happ://routing/onadd/{encoded_profile}"


ROUTING_LINK = _build_routing_link()


def _content_type_for_format(output_format: str) -> str:
    if output_format == "json":
        return "application/json; charset=utf-8"
    if output_format == "base64":
        return "application/octet-stream"
    return "text/plain; charset=utf-8"


def _prepare_headers_only_subscription(key: ActiveKeyRecord, output_format: str) -> PreparedSubscription:
    return PreparedSubscription(
        body="",
        content_type=_content_type_for_format(output_format),
        userinfo_header=_build_subscription_userinfo(key),
        routing_link=ROUTING_LINK if output_format != "json" else None,
    )


def _normalize_output_format(raw_format: str, client_family: str) -> str:
    output_format = raw_format.strip().lower()
    if not output_format:
        return "plain" if client_family in {"happ", "hiddify"} else "base64"
    output_format = output_format.partition("?")[0].partition("&")[0].strip()
    return output_format


def _build_plain_text_subscription(
    link: str,
    routing_link: Optional[str],
    userinfo_header: str,
) -> str:
    lines = [
        f"#profile-title: base64:{PROFILE_TITLE_BASE64}",
        f"#profile-update-interval: {PROFILE_UPDATE_INTERVAL_HOURS}",
        f"#subscription-userinfo: {userinfo_header}",
        f"#support-url: {SUPPORT_URL}",
        f"#profile-web-page-url: {PROFILE_WEB_PAGE_URL}",
    ]
    if routing_link:
        lines.append(routing_link)
    lines.append(link)
    return "\n".join(lines) + "\n"


def _build_json_subscription(key: ActiveKeyRecord, link: str) -> str:
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    subscription_host = urllib.parse.urlparse(SUBSCRIPTION_URL).hostname or "arcc.mooo.com"

    payload = {
        "outbounds": [
            {
                "type": "vless",
                "tag": key.tariff_name,
                "server": parsed.hostname,
                "server_port": parsed.port or 443,
                "uuid": parsed.username,
                "flow": params.get("flow", [""])[0] or "",
                "tls": {
                    "enabled": True,
                    "server_name": params.get("sni", [""])[0] or parsed.hostname,
                    "utls": {
                        "enabled": True,
                        "fingerprint": params.get("fp", ["chrome"])[0],
                    },
                    "reality": {
                        "enabled": True,
                        "public_key": params.get("pbk", [""])[0],
                        "short_id": params.get("sid", [""])[0],
                    },
                },
            },
            {
                "type": "direct",
                "tag": "direct",
            },
        ],
        "route": {
            "rules": [
                {
                    "domain": [subscription_host],
                    "outbound": "direct",
                },
                {
                    "ip_cidr": [
                        *LOCAL_AND_RESERVED_CIDRS,
                    ],
                    "outbound": "direct",
                },
            ],
            "final": key.tariff_name,
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _prepare_subscription(key: ActiveKeyRecord, link: str, output_format: str) -> PreparedSubscription:
    routing_link = ROUTING_LINK
    userinfo_header = _build_subscription_userinfo(key)

    if output_format == "json":
        return PreparedSubscription(
            body=_build_json_subscription(key, link),
            content_type="application/json; charset=utf-8",
            userinfo_header=userinfo_header,
        )

    plain_text_subscription = _build_plain_text_subscription(link, routing_link, userinfo_header)
    if output_format == "base64":
        body = base64.b64encode(plain_text_subscription.encode("utf-8")).decode("ascii")
        content_type = "application/octet-stream"
    else:
        body = plain_text_subscription
        content_type = "text/plain; charset=utf-8"

    return PreparedSubscription(
        body=body,
        content_type=content_type,
        userinfo_header=userinfo_header,
        routing_link=routing_link,
    )


def _subscription_not_available() -> Response:
    return Response("Subscription not available", status=404, mimetype="text/plain")


def _subscription_temporarily_unavailable() -> Response:
    return Response("Subscription temporarily unavailable", status=503, mimetype="text/plain")


def _response_from_prepared(prepared: PreparedSubscription) -> Response:
    response = Response(prepared.body)
    filename = f"{PROFILE_TITLE}.txt"
    response.headers["Content-Type"] = prepared.content_type
    response.headers["Content-Disposition"] = (
        f"inline; filename={json.dumps(filename)}; "
        f"filename*=UTF-8''{urllib.parse.quote(filename)}"
    )
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["profile-update-interval"] = str(PROFILE_UPDATE_INTERVAL_HOURS)
    response.headers["profile-title"] = f"base64:{PROFILE_TITLE_BASE64}"
    response.headers["support-url"] = SUPPORT_URL
    response.headers["profile-web-page-url"] = PROFILE_WEB_PAGE_URL
    response.headers["Subscription-Userinfo"] = prepared.userinfo_header
    if prepared.routing_link:
        response.headers["routing"] = prepared.routing_link
    return response


def _client_config_cache_key(server_id: int, panel_email: str) -> str:
    return f"{server_id}:{panel_email.lower()}"


def _get_server_fetch_lock(server_id: int) -> asyncio.Lock:
    with SERVER_FETCH_LOCKS_GUARD:
        lock = SERVER_FETCH_LOCKS.get(server_id)
        if lock is None:
            lock = asyncio.Lock()
            SERVER_FETCH_LOCKS[server_id] = lock
        return lock


def _get_cached_server(server_id: int) -> Optional[ServerRecord]:
    cache_key = str(server_id)
    cached = SERVER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    server = get_server_by_id(server_id)
    if not server or not server.get("is_active"):
        return None

    result = ServerRecord(
        id=int(server["id"]),
        name=str(server["name"]),
        host=str(server["host"]),
        port=int(server["port"]),
        protocol=str(server.get("protocol", "https")),
        web_base_path=str(server.get("web_base_path", "")),
        login=str(server["login"]),
        password=str(server["password"]),
    )
    SERVER_CACHE.set(cache_key, result)
    return result


async def _fetch_missing_configs_for_server(server_id: int, emails: set[str]) -> None:
    server = _get_cached_server(server_id)
    if not server:
        logger.warning("Активный сервер %s не найден при генерации подписки", server_id)
        return

    client = XUIClient(server.to_panel_dict())
    try:
        async with _get_server_fetch_lock(server_id):
            unresolved_emails = {
                email for email in emails
                if CLIENT_CONFIG_CACHE.get(_client_config_cache_key(server_id, email)) is None
            }
            if not unresolved_emails:
                return

            if hasattr(client, "get_client_configs"):
                configs = await asyncio.wait_for(
                    client.get_client_configs(sorted(unresolved_emails)),
                    timeout=XUI_CONFIG_FETCH_TIMEOUT_SECONDS,
                )
            else:
                logger.warning(
                    "XUIClient на сервере %s без get_client_configs(); используем совместимый fallback",
                    server.name,
                )

                async def _load_single(email: str) -> tuple[str, Optional[Dict[str, Any]]]:
                    config = await client.get_client_config(email)
                    return email, config

                results = await asyncio.wait_for(
                    asyncio.gather(*(_load_single(email) for email in sorted(unresolved_emails))),
                    timeout=XUI_CONFIG_FETCH_TIMEOUT_SECONDS,
                )
                configs = {
                    email: config
                    for email, config in results
                    if config is not None
                }

            for email, config in configs.items():
                CLIENT_CONFIG_CACHE.set(_client_config_cache_key(server_id, email), config)
    except asyncio.TimeoutError:
        logger.warning(
            "XUI сервер %s не ответил за %s сек, продолжаем с остальными",
            server.name,
            XUI_CONFIG_FETCH_TIMEOUT_SECONDS,
        )
    except VPNAPIError as exc:
        logger.warning("XUI недоступен для сервера %s: %s", server.name, exc)
    except Exception as exc:
        logger.error("Ошибка загрузки конфигов с сервера %s: %s", server.name, exc)
    finally:
        await client.close()


async def _generate_links_for_keys(keys: Iterable[ActiveKeyRecord]) -> list[str]:
    ordered_keys = [key for key in keys if key.has_available_traffic]
    if not ordered_keys:
        return []

    servers_by_id = {
        server_id: _get_cached_server(server_id)
        for server_id in {key.server_id for key in ordered_keys}
    }
    missing_by_server: Dict[int, set[str]] = defaultdict(set)
    for key in ordered_keys:
        if not servers_by_id.get(key.server_id):
            continue
        cache_key = _client_config_cache_key(key.server_id, key.panel_email)
        if CLIENT_CONFIG_CACHE.get(cache_key) is None:
            missing_by_server[key.server_id].add(key.panel_email)

    if missing_by_server:
        await asyncio.gather(
            *(
                _fetch_missing_configs_for_server(server_id, emails)
                for server_id, emails in missing_by_server.items()
            )
        )

    links: list[str] = []
    for key in ordered_keys:
        cache_key = _client_config_cache_key(key.server_id, key.panel_email)
        config = CLIENT_CONFIG_CACHE.get(cache_key)
        server = servers_by_id.get(key.server_id)
        if not config or not server:
            logger.warning(
                "Пропущен ключ %s: не удалось получить конфиг для %s",
                key.id,
                _mask_email(key.panel_email),
            )
            continue

        link_payload = dict(config)
        display_name = f"ArcVPN - {key.tariff_name} ({server.name})"
        link_payload["server_name"] = display_name
        link_payload["remark"] = display_name
        links.append(generate_link(link_payload))

    return links


def get_user_active_keys(user_id: int) -> list[ActiveKeyRecord]:
    """
    Получает активные ключи пользователя из базы данных.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Список активных ключей пользователя
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id, vk.panel_email, vk.server_id,
                vk.expires_at, vk.traffic_limit, vk.traffic_used,
                u.telegram_id,
                vk.sub_id,
                COALESCE(vk.custom_name, t.name, 'Subscription') as tariff_name
            FROM vpn_keys vk
            JOIN servers s ON vk.server_id = s.id
            JOIN users u ON vk.user_id = u.id
            LEFT JOIN tariffs t ON vk.tariff_id = t.id
            WHERE u.telegram_id = ? 
            AND vk.expires_at > datetime('now')
            AND vk.panel_email IS NOT NULL
            AND s.is_active = 1
            ORDER BY vk.expires_at DESC
        """, (user_id,))
        keys = [_row_to_active_key(row) for row in cursor.fetchall()]
        return [key for key in keys if key.has_available_traffic]


def get_active_key_by_subscription_id(sub_id: str) -> Optional[ActiveKeyRecord]:
    """Находит активный ключ по subscription id."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id, vk.panel_email, vk.server_id, vk.expires_at,
                vk.traffic_limit, vk.traffic_used, vk.sub_id,
                u.telegram_id,
                COALESCE(vk.custom_name, t.name, 'Subscription') as tariff_name
            FROM vpn_keys vk
            JOIN servers s ON vk.server_id = s.id
            JOIN users u ON vk.user_id = u.id
            LEFT JOIN tariffs t ON vk.tariff_id = t.id
            WHERE vk.sub_id = ?
            AND vk.expires_at > datetime('now')
            AND vk.panel_email IS NOT NULL
            AND s.is_active = 1
            LIMIT 1
        """, (sub_id,))
        row = cursor.fetchone()
        return _row_to_active_key(row) if row else None


def generate_subscription(user_id: int, encode_base64: bool = True) -> str:
    """
    Генерирует subscription в формате base64 или plain text.
    
    Args:
        user_id: Telegram ID пользователя
        encode_base64: Кодировать ли результат в base64 (по умолчанию True)
        
    Returns:
        Base64-encoded строка с ключами или plain text
    """
    keys = get_user_active_keys(user_id)
    if not keys:
        logger.info("Нет активных ключей для пользователя %s", user_id)
        return ""

    try:
        links = ASYNC_EXECUTOR.run(_generate_links_for_keys(keys))
    except Exception as exc:
        logger.error("Ошибка генерации подписки пользователя %s: %s", user_id, exc)
        return ""

    if not links:
        logger.warning("Не удалось сгенерировать ни одного ключа для пользователя %s", user_id)
        return ""

    keys_text = "\n".join(links)
    if encode_base64:
        encoded = base64.b64encode(keys_text.encode("utf-8")).decode("ascii")
        logger.info("Сгенерирована подписка для пользователя %s: %s ключей (base64)", user_id, len(links))
        return encoded

    logger.info("Сгенерирована подписка для пользователя %s: %s ключей (plain text)", user_id, len(links))
    return keys_text


@app.route('/sub/<sub_id>', methods=['GET', 'HEAD'])
def subscription(sub_id: str):
    """
    Endpoint для получения subscription по уникальному sub_id ключа.
    
    Args:
        sub_id: Уникальный идентификатор подписки (sub_id из vpn_keys)
        
    Query параметры:
        format: 'base64' (по умолчанию) или 'plain' (без кодирования)
        
    Returns:
        VPN ключ в формате vless:// (plain text или base64)
    """
    masked_sub_id = _mask_token(sub_id)
    try:
        if not _is_valid_subscription_id(sub_id):
            logger.warning("Отклонен subscription-запрос с некорректным ID: %s", masked_sub_id)
            return _subscription_not_available()

        client_family = _detect_client_family(request.headers.get("User-Agent", ""))
        client_ip = _extract_client_ip()

        token_allowed, token_retry_after = TOKEN_RATE_LIMITER.allow(sub_id)
        if not token_allowed:
            logger.warning("Превышен rate limit обновления подписки: %s", masked_sub_id)
            response = Response("Too many refresh requests", status=429, mimetype="text/plain")
            response.headers["Retry-After"] = str(token_retry_after)
            return response

        ip_allowed, ip_retry_after = IP_RATE_LIMITER.allow(client_ip)
        if not ip_allowed:
            logger.warning("Превышен rate limit по IP для подписки %s", masked_sub_id)
            response = Response("Too many refresh requests", status=429, mimetype="text/plain")
            response.headers["Retry-After"] = str(ip_retry_after)
            return response

        output_format = _normalize_output_format(request.args.get("format", ""), client_family)
        if output_format not in {"base64", "plain", "json"}:
            return Response("Unsupported format", status=400, mimetype="text/plain")

        key = get_active_key_by_subscription_id(sub_id)
        if not key or not key.has_available_traffic:
            logger.info("Подписка недоступна: %s", masked_sub_id)
            return _subscription_not_available()

        if request.method == "HEAD":
            prepared = _prepare_headers_only_subscription(key, output_format)
            logger.info(
                "HEAD подписка выдана без генерации ссылок: %s, client=%s, format=%s",
                masked_sub_id,
                client_family,
                output_format,
            )
            return _response_from_prepared(prepared)

        links = ASYNC_EXECUTOR.run(_generate_links_for_keys([key]))
        link = links[0] if links else ""
        if not link:
            logger.warning("Не удалось сгенерировать ссылку для %s", masked_sub_id)
            return _subscription_temporarily_unavailable()

        prepared = _prepare_subscription(key, link, output_format)
        logger.info(
            "Подписка выдана: %s, client=%s, format=%s",
            masked_sub_id,
            client_family,
            output_format,
        )
        return _response_from_prepared(prepared)

    except Exception:
        logger.exception("Ошибка генерации подписки для %s", masked_sub_id)
        return _subscription_temporarily_unavailable()


@app.route('/health')
def health():
    """Health check endpoint."""
    return Response("OK", mimetype='text/plain')


@app.route('/logo.svg')
def logo():
    """Отдает SVG логотип."""
    import os
    logo_path = os.path.join(os.path.dirname(__file__), 'arcLOGOsvg.svg')
    try:
        with open(logo_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        return Response(svg_content, mimetype='image/svg+xml')
    except:
        return Response("", status=404)


@app.route('/import/<sub_id>')
def import_to_happ(sub_id: str):
    """
    Страница для импорта подписки в Happ.
    Определяет User-Agent и отдаёт разный контент:
    - Браузер → HTML страница с кнопкой импорта
    - Happ/VPN клиент → subscription данные
    """
    if not _is_valid_subscription_id(sub_id):
        return _subscription_not_available()

    client_family = _detect_client_family(request.headers.get("User-Agent", ""))

    if client_family != "generic":
        output_format = "plain" if client_family in {"happ", "hiddify"} else "base64"
        subscription_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}?format={output_format}"
        return redirect(subscription_url)

    subscription_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}?format=plain"
    safe_subscription_url = html.escape(subscription_url, quote=True)
    js_subscription_url = json.dumps(subscription_url)

    # Правильный формат Happ deeplink: happ://add/{URL}
    happ_deeplink = f"happ://add/{subscription_url}"
    safe_happ_deeplink = html.escape(happ_deeplink, quote=True)
    
    # HTML страница с новым дизайном на основе референса
    html_page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArcVPN - Импорт подписки</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(180deg, #3d5a9e 0%, #516db3 50%, #7a8fc4 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}
        
        /* Анимированные звезды на фоне */
        .stars {{
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        
        .star {{
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: twinkle 3s infinite;
        }}
        
        @keyframes twinkle {{
            0%, 100% {{ opacity: 0.3; }}
            50% {{ opacity: 1; }}
        }}
        
        /* Генерируем звезды */
        .star:nth-child(1) {{ top: 10%; left: 20%; animation-delay: 0s; }}
        .star:nth-child(2) {{ top: 20%; left: 80%; animation-delay: 0.5s; }}
        .star:nth-child(3) {{ top: 30%; left: 50%; animation-delay: 1s; }}
        .star:nth-child(4) {{ top: 40%; left: 10%; animation-delay: 1.5s; }}
        .star:nth-child(5) {{ top: 50%; left: 90%; animation-delay: 2s; }}
        .star:nth-child(6) {{ top: 60%; left: 30%; animation-delay: 2.5s; }}
        .star:nth-child(7) {{ top: 70%; left: 70%; animation-delay: 0.3s; }}
        .star:nth-child(8) {{ top: 80%; left: 40%; animation-delay: 0.8s; }}
        .star:nth-child(9) {{ top: 15%; left: 60%; animation-delay: 1.2s; }}
        .star:nth-child(10) {{ top: 85%; left: 15%; animation-delay: 1.8s; }}
        .star:nth-child(11) {{ top: 25%; left: 85%; animation-delay: 0.6s; }}
        .star:nth-child(12) {{ top: 45%; left: 25%; animation-delay: 1.4s; }}
        .star:nth-child(13) {{ top: 65%; left: 75%; animation-delay: 2.2s; }}
        .star:nth-child(14) {{ top: 35%; left: 45%; animation-delay: 0.9s; }}
        .star:nth-child(15) {{ top: 75%; left: 55%; animation-delay: 1.7s; }}
        
        /* Большие яркие звезды */
        .star.bright {{
            width: 3px;
            height: 3px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}
        
        .star:nth-child(3), .star:nth-child(7), .star:nth-child(12) {{
            width: 3px;
            height: 3px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}
        
        .container {{
            position: relative;
            z-index: 1;
            text-align: center;
            max-width: 480px;
            width: 100%;
        }}
        
        /* Логотип с свечением */
        .logo {{
            width: 360px;
            height: 360px;
            margin: 0 auto 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 0 50px rgba(255, 255, 255, 0.5));
            animation: glow 3s ease-in-out infinite;
        }}
        
        .logo img {{
            width: 360px;
            height: 360px;
            object-fit: contain;
        }}
        
        @keyframes glow {{
            0%, 100% {{ filter: drop-shadow(0 0 50px rgba(255, 255, 255, 0.5)); }}
            50% {{ filter: drop-shadow(0 0 70px rgba(255, 255, 255, 0.7)); }}
        }}
        
        h1 {{
            font-size: 96px;
            font-weight: 400;
            color: white;
            margin-bottom: 70px;
            letter-spacing: 3px;
            font-family: 'Playfair Display', serif;
        }}
        
        /* Кнопки */
        .btn {{
            display: block;
            width: 100%;
            max-width: 440px;
            margin: 0 auto 20px;
            padding: 20px 40px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
            font-family: 'Geist', sans-serif;
        }}
        
        .btn-primary {{
            background: white;
            color: #516db3;
            box-shadow: 0 4px 20px rgba(255, 255, 255, 0.3);
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 30px rgba(255, 255, 255, 0.4);
        }}
        
        .btn-secondary {{
            background: transparent;
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.5);
        }}
        
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.8);
        }}
        
        .divider-text {{
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
            margin: 30px 0 20px;
        }}
        
        /* Уведомление об успешном копировании */
        .toast {{
            position: fixed;
            top: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: rgba(255, 255, 255, 0.95);
            color: #516db3;
            padding: 16px 32px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.4s ease;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }}
        
        .toast.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}
        
        @media (max-width: 640px) {{
            .logo {{
                width: 240px;
                height: 240px;
                margin-bottom: 40px;
            }}
            
            .logo img {{
                width: 240px;
                height: 240px;
            }}
            
            h1 {{
                font-size: 64px;
                margin-bottom: 50px;
                letter-spacing: 2px;
            }}
            
            .btn {{
                padding: 18px 32px;
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <!-- Звезды на фоне -->
    <div class="stars">
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
        <div class="star"></div>
    </div>
    
    <div class="container">
        <!-- Логотип SVG -->
        <div class="logo">
            <img src="/logo.svg" alt="ArcVPN Logo">
        </div>
        
        <h1>ArcVPN</h1>
        
        <!-- Кнопка открытия в Happ -->
        <a href="{safe_happ_deeplink}" class="btn btn-primary" rel="noopener noreferrer">Открыть в Happ</a>
        
        <p class="divider-text">Или скопируйте ссылку вручную</p>
        
        <!-- Кнопка копирования -->
        <button onclick="copyUrl()" class="btn btn-secondary">Копировать вручную</button>
        <a href="{safe_subscription_url}" class="btn btn-secondary" rel="noopener noreferrer">Открыть URL подписки</a>
    </div>
    
    <!-- Уведомление -->
    <div class="toast" id="toast">
        ✓ Ссылка скопирована
    </div>
    
    <script>
        function copyUrl() {{
            const url = {js_subscription_url};
            const toast = document.getElementById('toast');
            
            navigator.clipboard.writeText(url).then(() => {{
                showToast();
            }}).catch(() => {{
                // Fallback для старых браузеров
                const textarea = document.createElement('textarea');
                textarea.value = url;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast();
            }});
            
            function showToast() {{
                toast.classList.add('show');
                setTimeout(() => {{
                    toast.classList.remove('show');
                }}, 2500);
            }}
        }}
    </script>
</body>
</html>"""
    response = Response(html_page, mimetype='text/html')
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


if __name__ == '__main__':
    # Запуск сервера на внутреннем порту 8080
    # Nginx проксирует с порта 2053 на 8080
    app.run(host='127.0.0.1', port=8080, debug=False)
