#!/usr/bin/env python3
"""
Subscription API для VPN бота.

Возвращает base64-encoded список VPN ключей пользователя.
Клиенты VPN подключаются по ссылке и автоматически получают обновления.
"""

import asyncio
import base64
import concurrent.futures
import hashlib
import html
import json
import logging
import os
import re
import secrets
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Coroutine, Deque, Dict, Iterable, Optional

from flask import Flask, Response, jsonify, redirect, request, send_from_directory

from bot.services.panels.base import VPNAPIError
from bot.services.panels.xui import XUIClient
from bot.utils.key_generator import generate_link
from bot.utils.telegram_webapp import get_telegram_id
import config
from database.connection import get_db
from database.db_servers import get_server_by_id
from database.requests import (
    get_user_keys_for_display,
    get_user_internal_id,
    ensure_user_referral_code,
    get_user_balance,
    get_referral_stats,
    get_referral_friends,
    get_referral_earned_days,
    is_referral_enabled,
    get_referral_reward_type,
    get_all_tariffs,
    get_setting,
)
from bot.services.reserve import get_reserve_client_info
from subscription_pages import render_import_page

# Конфиг читаем через getattr с дефолтами: устаревший config.py (а он не
# версионируется — лежит в .gitignore) НЕ должен ронять сервис из-за отсутствия
# какой-либо новой опции. Обязательным остаётся только SUBSCRIPTION_URL.
SUBSCRIPTION_URL = config.SUBSCRIPTION_URL
ENABLE_SPLIT_TUNNELING = getattr(config, "ENABLE_SPLIT_TUNNELING", True)
SPLIT_TUNNELING_DIRECT_IP = getattr(config, "SPLIT_TUNNELING_DIRECT_IP", ["geoip:ru", "geoip:private"])
SPLIT_TUNNELING_DIRECT_SITES = getattr(config, "SPLIT_TUNNELING_DIRECT_SITES", ["geosite:category-ru"])
SPLIT_TUNNELING_MODE = getattr(config, "SPLIT_TUNNELING_MODE", "speed")
SPLIT_TUNNELING_REMOTE_DNS_DOMAIN = getattr(config, "SPLIT_TUNNELING_REMOTE_DNS_DOMAIN", "https://cloudflare-dns.com/dns-query")
SPLIT_TUNNELING_REMOTE_DNS_IP = getattr(config, "SPLIT_TUNNELING_REMOTE_DNS_IP", "1.1.1.1")
RESERVE_ACCESS_ENABLED = getattr(config, "RESERVE_ACCESS_ENABLED", False)
RESERVE_CLIENT_EMAIL = getattr(config, "RESERVE_CLIENT_EMAIL", "reserve_shared_fallback")
RESERVE_PROXY_SITES = getattr(config, "RESERVE_PROXY_SITES", ["geosite:telegram"])
RESERVE_PROXY_IP = getattr(config, "RESERVE_PROXY_IP", ["geoip:telegram"])
# Имя, которое видит пользователь в VPN-клиенте, когда подписка истекла
# (вместо обычного "ArcVPN - <тариф>"). Призыв к действию — продлить.
RESERVE_DISPLAY_NAME = getattr(config, "RESERVE_DISPLAY_NAME", "⚠️ Оплатите VPN — подписка истекла")
# Домены платёжных систем, которые тоже пускаем через резерв — чтобы при истёкшей
# подписке можно было не только открыть Telegram, но и оплатить (страница ЮKassa
# и т.п.). Всегда добавляются к резервному роутингу, можно расширить в config.py.
RESERVE_PAYMENT_SITES = getattr(config, "RESERVE_PAYMENT_SITES", [
    "yoomoney.ru",
    "yookassa.ru",
    "qr.nspk.ru",          # СБП QR (НСПК)
])

# CDN-обход белых списков: inbound на порту CDN_PORT отдаётся через CDN_DOMAIN
# (Yandex Cloud CDN, IP в белом списке). Клиент коннектится к домену:443+TLS,
# CDN форвардит на origin (наш сервер). В link подменяем host/port/security.
CDN_DOMAIN = getattr(config, "CDN_DOMAIN", "")
CDN_PORTS = set(getattr(config, "CDN_PORTS", []))



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
# Брендинг можно переопределить в config.py; по умолчанию — текущие значения ArcVPN.
PROFILE_TITLE = getattr(config, "PROFILE_TITLE", "ArcVPN")
PROFILE_TITLE_BASE64 = base64.b64encode(PROFILE_TITLE.encode("utf-8")).decode("ascii")
SUPPORT_URL = getattr(config, "SUPPORT_URL", "https://t.me/Turan11627")
PROFILE_WEB_PAGE_URL = getattr(config, "PROFILE_WEB_PAGE_URL", "https://t.me/arcvpn1")

# --- Telegram Mini App ---------------------------------------------------------
# Собранный Svelte+Vite фронтенд лежит в webapp_dist/ (коммитится в репо, чтобы
# деплой на сервер был обычным git pull — Node на сервере не нужен).
WEBAPP_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp_dist")
BOT_TOKEN = getattr(config, "BOT_TOKEN", "")
# Возраст initData, после которого считаем её протухшей (сек). Mini App
# переоткрывают часто, сутки — безопасный дефолт.
WEBAPP_INITDATA_MAX_AGE = getattr(config, "WEBAPP_INITDATA_MAX_AGE", 24 * 60 * 60)

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
    direct_ip_rules = list(dict.fromkeys([*SPLIT_TUNNELING_DIRECT_IP, *LOCAL_AND_RESERVED_CIDRS]))

    profile: Dict[str, Any] = {
        "Name": "ArcVPN - Smart Route",
        "GlobalProxy": True,
        "RemoteDNSType": "DoH" if use_remote_doh else "System",
        "DomesticDNSType": "System",
        "DirectSites": list(SPLIT_TUNNELING_DIRECT_SITES),
        "DirectIp": direct_ip_rules,
        "ProxySites": [],
        "ProxyIp": [],
        "BlockSites": [],
        "BlockIp": [],
        "DomainStrategy": "IPIfNonMatch" if mode == "speed" else "AsIs",
        "FakeDNS": False,
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
    # ВНИМАНИЕ: доверяем X-Forwarded-For только потому, что сервис всегда стоит
    # за доверенным обратным прокси (nginx: 2053 -> 127.0.0.1:8080). Если фронт
    # изменится и сервис станет доступен напрямую — заголовок можно подделать,
    # обойдя IP-rate-limit; тогда эту логику нужно пересмотреть.
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


def _build_reserve_routing_profile() -> Dict[str, Any]:
    """
    Happ routing-профиль для резервного доступа: через VPN идут только Telegram
    и платёжные домены (чтобы можно было открыть бота и оплатить продление).
    Всё остальное — напрямую.
    """
    proxy_sites = list(dict.fromkeys([*RESERVE_PROXY_SITES, *RESERVE_PAYMENT_SITES]))
    return {
        "Name": "ArcVPN - Reserve (Telegram + Pay)",
        "GlobalProxy": False,
        "RemoteDNSType": "System",
        "DomesticDNSType": "System",
        "DirectSites": [],
        "DirectIp": [],
        "ProxySites": proxy_sites,
        "ProxyIp": list(RESERVE_PROXY_IP),
        "BlockSites": [],
        "BlockIp": [],
        "DomainStrategy": "AsIs",
        "FakeDNS": False,
    }


def _build_reserve_routing_link() -> str:
    """
    Резервный routing-профиль отдаётся всегда (независимо от ENABLE_SPLIT_TUNNELING),
    т.к. Telegram-only маршрутизация — суть резервного доступа.
    """
    profile_json = json.dumps(
        _build_reserve_routing_profile(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    encoded_profile = base64.b64encode(profile_json.encode("utf-8")).decode("ascii")
    return f"happ://routing/onadd/{encoded_profile}"


RESERVE_ROUTING_LINK = _build_reserve_routing_link()
# Срок «годности» для резервного конфига в userinfo (далеко в будущем — клиент
# не считает подписку истёкшей и продолжает опрашивать тот же /sub/<sub_id>).
RESERVE_EXPIRES_AT = "2999-01-01T00:00:00+00:00"


def _content_type_for_format(output_format: str) -> str:
    if output_format == "json":
        return "application/json; charset=utf-8"
    if output_format == "base64":
        return "application/octet-stream"
    return "text/plain; charset=utf-8"


def _prepare_headers_only_subscription(
    key: ActiveKeyRecord,
    output_format: str,
    routing_link_override: Optional[str] = None,
) -> PreparedSubscription:
    routing_link = routing_link_override if routing_link_override is not None else ROUTING_LINK
    return PreparedSubscription(
        body="",
        content_type=_content_type_for_format(output_format),
        userinfo_header=_build_subscription_userinfo(key),
        routing_link=routing_link if output_format != "json" else None,
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
    subscription_host = urllib.parse.urlparse(SUBSCRIPTION_URL).hostname or ""

    flow = params.get("flow", [""])[0] or ""
    sni = (params.get("sni", [""])[0] or parsed.hostname or "")
    pbk = (params.get("pbk", [""])[0] or "")
    sid = (params.get("sid", [""])[0] or "")
    fp = params.get("fp", ["firefox"])[0]
    spx = params.get("spx", ["/"])[0]
    network = params.get("type", ["tcp"])[0]
    http_user = "happ-http"
    http_pass = hashlib.sha256(f"happ-http-{key.id}".encode()).hexdigest()[:16]

    direct_domains = list(dict.fromkeys([
        "geosite:category-ru",
        *SPLIT_TUNNELING_DIRECT_SITES,
    ]))

    stream_settings: Dict[str, Any] = {
        "network": network,
        "security": "reality",
        "realitySettings": {
            "fingerprint": fp,
            "publicKey": pbk,
            "serverName": sni,
            "shortId": sid,
            "spiderX": spx,
        },
    }
    if network == "tcp":
        stream_settings["tcpSettings"] = {}
    elif network == "xhttp":
        stream_settings["xhttpSettings"] = {
            "host": "",
            "mode": params.get("mode", ["auto"])[0],
            "path": params.get("path", ["/"])[0],
            "scMaxConcurrentPosts": 10,
            "scMaxEachPostBytes": 1000000,
            "scMinPostsIntervalMs": 30,
        }

    payload = {
        "dns": {
            "hosts": {"dns.google": "8.8.8.8"},
            "queryStrategy": "IPIfNonMatch",
            "servers": [
                {
                    "address": "https://dns.google/dns-query",
                    "skipFallback": False,
                },
                {
                    "address": "77.88.8.8",
                    "domains": [
                        "geosite:category-ru",
                        "regexp:\\.ru$",
                        "regexp:\\.su$",
                        "regexp:xn--p1ai$",
                    ],
                    "port": 53,
                    "skipFallback": True,
                },
            ],
            "tag": "dns_out",
        },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": 10808,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                    "userLevel": 8,
                },
                "sniffing": {
                    "destOverride": ["http", "tls", "quic"],
                    "enabled": True,
                },
                "tag": "socks",
            },
            {
                "listen": "127.0.0.1",
                "port": 10809,
                "protocol": "http",
                "settings": {
                    "accounts": [{"user": http_user, "pass": http_pass}],
                    "userLevel": 8,
                },
                "sniffing": {
                    "destOverride": ["http", "tls", "quic"],
                    "enabled": True,
                },
                "tag": "http",
            },
        ],
        "log": {
            "loglevel": "warning",
        },
        "meta": None,
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": parsed.hostname,
                            "port": parsed.port or 443,
                            "users": [
                                {
                                    "encryption": "none",
                                    "flow": flow,
                                    "id": parsed.username,
                                }
                            ],
                        }
                    ]
                },
                "streamSettings": stream_settings,
                "tag": "proxy",
            },
            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP",
                },
                "tag": "direct",
            },
            {
                "protocol": "blackhole",
                "tag": "block",
            },
        ],
        "policy": {
            "levels": {
                "0": {
                    "statsUserDownlink": True,
                    "statsUserUplink": True,
                },
                "8": {
                    "connIdle": 300,
                    "downlinkOnly": 1,
                    "handshake": 4,
                    "uplinkOnly": 1,
                },
            },
            "system": {
                "statsInboundDownlink": True,
                "statsInboundUplink": True,
                "statsOutboundDownlink": True,
                "statsOutboundUplink": True,
            },
        },
        "remarks": key.tariff_name,
        "routing": {
            "domainMatcher": "hybrid",
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "ip": ["geoip:private"],
                    "outboundTag": "direct",
                    "type": "field",
                },
                {
                    "domain": ["geosite:private"],
                    "outboundTag": "direct",
                    "type": "field",
                },
                {
                    "ip": ["77.88.8.8"],
                    "outboundTag": "direct",
                    "port": 53,
                    "type": "field",
                },
                {
                    "domain": direct_domains,
                    "outboundTag": "direct",
                    "type": "field",
                },
                {
                    "network": "tcp,udp",
                    "outboundTag": "proxy",
                    "type": "field",
                },
            ],
        },
        "stats": {},
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _prepare_subscription(
    key: ActiveKeyRecord,
    link: str,
    output_format: str,
    routing_link_override: Optional[str] = None,
) -> PreparedSubscription:
    routing_link = routing_link_override if routing_link_override is not None else ROUTING_LINK
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

            if hasattr(client, "get_all_client_configs"):
                # {email: [config, ...]} — по конфигу на каждый inbound сервера
                configs = await asyncio.wait_for(
                    client.get_all_client_configs(sorted(unresolved_emails)),
                    timeout=XUI_CONFIG_FETCH_TIMEOUT_SECONDS,
                )
            else:
                logger.warning(
                    "XUIClient на сервере %s без get_all_client_configs(); используем совместимый fallback",
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
                    email: [config]
                    for email, config in results
                    if config is not None
                }

            # В кэше — список конфигов на (server_id, email).
            for email, cfg_list in configs.items():
                if cfg_list:
                    CLIENT_CONFIG_CACHE.set(_client_config_cache_key(server_id, email), cfg_list)
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
        configs = CLIENT_CONFIG_CACHE.get(cache_key)
        server = servers_by_id.get(key.server_id)
        if not configs or not server:
            logger.warning(
                "Пропущен ключ %s: не удалось получить конфиг для %s",
                key.id,
                _mask_email(key.panel_email),
            )
            continue

        # В кэше — список конфигов (по одному на inbound сервера). Генерируем
        # отдельную ссылку на каждый inbound; имя берём из remark inbound.
        for config in configs:
            link_payload = dict(config)
            if key.id == -1:
                # Резервный (аварийный) ключ — призыв к действию вместо имени inbound.
                display_name = key.tariff_name
            else:
                # Имя конфига = remark inbound (например "🇩🇪 Германия", "Hysteria2").
                display_name = config.get("inbound_name") or f"ArcVPN - {key.tariff_name} ({server.name})"
            link_payload["server_name"] = display_name
            link_payload["remark"] = display_name

            # CDN-обход: подменяем адрес/порт/TLS чтобы клиент шёл через CDN-домен,
            # а не напрямую на сервер. Origin (наш сервер) видит только CDN.
            # Yandex CDN режет POST, но пропускает OPTIONS: клиент шлёт XHTTP-аплинк
            # методом OPTIONS (uplinkHTTPMethod), nginx на origin переписывает
            # OPTIONS->POST. alpn=h2 обязателен — CDN отвечает по HTTP/2.
            if CDN_DOMAIN and config.get("port") in CDN_PORTS:
                link_payload["host"] = CDN_DOMAIN
                link_payload["port"] = 443
                ss = dict(config.get("stream_settings") or {})
                ss["security"] = "tls"
                ss["tlsSettings"] = {
                    "serverName": CDN_DOMAIN,
                    "alpn": ["h2", "http/1.1"],
                }
                # Гарантируем host/mode в xhttpSettings (клиент шлёт Host=CDN,
                # packet-up — единственный режим, совместимый с OPTIONS-трюком).
                xs = dict(ss.get("xhttpSettings") or {})
                xs["host"] = CDN_DOMAIN
                xs["mode"] = "packet-up"
                ss["xhttpSettings"] = xs
                link_payload["stream_settings"] = ss

                # extra-поля XHTTP (uplinkHTTPMethod + padding-обфускация).
                # padding-поля берём из inbound (панель), чтобы клиент и сервер
                # совпадали; uplinkHTTPMethod и sc* добавляем для OPTIONS-трюка.
                extra: Dict[str, Any] = {
                    "uplinkHTTPMethod": "OPTIONS",
                    "scMaxEachPostBytes": 1000000,
                    "scMinPostsIntervalMs": 30,
                    "scMaxBufferedPosts": 30,
                }
                for pad_key in (
                    "xPaddingObfsMode", "xPaddingKey", "xPaddingHeader",
                    "xPaddingMethod", "xPaddingPlacement",
                ):
                    if pad_key in xs:
                        extra[pad_key] = xs[pad_key]
                link_payload["xhttp_extra"] = extra

            links.append(generate_link(link_payload))

    # Сортировка: XHTTP (Основной) первым, затем TCP (Запасной/YouTube)
    links.sort(key=lambda l: 0 if "type=xhttp" in l else 1)
    return links


def _select_links(links: list[str], output_format: str) -> str:
    """
    Склеивает ссылки для тела подписки.

    plain/base64 (Happ/Hiddify) — все inbound одной подписки (VLESS, …),
    каждая ссылка отдельной строкой. json — берём первую (TCP Reality).
    """
    if not links:
        return ""
    if output_format == "json":
        return links[0]
    return "\n".join(links)


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


def subscription_id_is_known(sub_id: str) -> bool:
    """
    Проверяет, что sub_id принадлежит реальному (пусть и истёкшему) ключу.

    Резервный доступ выдаётся только тем, кто когда-то был платным клиентом,
    а не любому корректному по формату идентификатору.
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM vpn_keys WHERE sub_id = ? LIMIT 1",
            (sub_id,),
        )
        return cursor.fetchone() is not None


def _build_reserve_active_key(reserve_info: Dict[str, Any]) -> ActiveKeyRecord:
    """Синтезирует виртуальную запись ключа для общего резервного клиента."""
    return ActiveKeyRecord(
        id=-1,
        server_id=int(reserve_info["server_id"]),
        panel_email=str(reserve_info.get("panel_email") or RESERVE_CLIENT_EMAIL),
        expires_at=RESERVE_EXPIRES_AT,
        traffic_limit=0,
        traffic_used=0,
        tariff_name=RESERVE_DISPLAY_NAME,
        telegram_id=0,
        sub_id=None,
    )


def _build_reserve_response(sub_id: str, output_format: str, is_head: bool) -> Optional[Response]:
    """
    Пытается отдать резервный (Telegram-only) конфиг для истёкшей/исчерпанной подписки.

    Возвращает Response при успехе либо None — тогда вызывающий код отдаёт 404.
    """
    if not RESERVE_ACCESS_ENABLED:
        return None
    # Telegram-only маршрутизация задаётся Happ routing-профилем, который есть
    # только в plain/base64 (Happ/Hiddify). Для json (clash/sing-box/v2ray)
    # ограничить трафик роутингом нельзя — резерв там не выдаём.
    if output_format == "json":
        return None
    if not subscription_id_is_known(sub_id):
        return None
    reserve_info = get_reserve_client_info()
    if not reserve_info:
        return None

    reserve_key = _build_reserve_active_key(reserve_info)

    if is_head:
        prepared = _prepare_headers_only_subscription(
            reserve_key, output_format, routing_link_override=RESERVE_ROUTING_LINK
        )
        return _response_from_prepared(prepared)

    links = ASYNC_EXECUTOR.run(_generate_links_for_keys([reserve_key]))
    link = _select_links(links, output_format)
    if not link:
        logger.warning("Резервный конфиг недоступен для %s (нет ссылки)", _mask_token(sub_id))
        return None

    prepared = _prepare_subscription(
        reserve_key, link, output_format, routing_link_override=RESERVE_ROUTING_LINK
    )
    logger.info("Выдан резервный доступ для %s, format=%s", _mask_token(sub_id), output_format)
    return _response_from_prepared(prepared)


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
            # Подписка истекла или исчерпан трафик — пробуем выдать резервный
            # (Telegram-only) доступ, чтобы пользователь смог продлить через бота.
            reserve_response = _build_reserve_response(
                sub_id, output_format, request.method == "HEAD"
            )
            if reserve_response is not None:
                return reserve_response
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
        link = _select_links(links, output_format)
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


def _load_logo_svg() -> Optional[str]:
    """Читает SVG-логотип с диска один раз при старте (кэшируется в памяти)."""
    import os
    logo_path = os.path.join(os.path.dirname(__file__), 'arcLOGOsvg.svg')
    try:
        with open(logo_path, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError as exc:
        logger.warning("Не удалось прочитать логотип %s: %s", logo_path, exc)
        return None


LOGO_SVG = _load_logo_svg()


@app.route('/logo.svg')
def logo():
    """Отдаёт SVG-логотип из памяти."""
    if LOGO_SVG is None:
        return Response("", status=404)
    return Response(LOGO_SVG, mimetype='image/svg+xml')


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
    html_page = render_import_page(
        safe_happ_deeplink=safe_happ_deeplink,
        safe_subscription_url=safe_subscription_url,
        js_subscription_url=js_subscription_url,
        profile_title=PROFILE_TITLE,
    )
    response = Response(html_page, mimetype='text/html')
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# --- Telegram Mini App: API + раздача SPA --------------------------------------

# Username бота нужен для реферальной ссылки (t.me/<bot>?start=ref_...). В initData
# его нет, поэтому резолвим один раз через getMe и кэшируем. config.BOT_USERNAME
# (если задан) имеет приоритет — на случай оффлайна/проблем с сетью при старте.
_BOT_USERNAME_CACHE: Optional[str] = None
_BOT_USERNAME_LOCK = threading.Lock()


def _get_bot_username() -> str:
    global _BOT_USERNAME_CACHE
    configured = getattr(config, "BOT_USERNAME", "") or ""
    if configured:
        return configured.lstrip("@")
    if _BOT_USERNAME_CACHE is not None:
        return _BOT_USERNAME_CACHE
    with _BOT_USERNAME_LOCK:
        if _BOT_USERNAME_CACHE is not None:
            return _BOT_USERNAME_CACHE
        username = ""
        if BOT_TOKEN:
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                username = (data.get("result") or {}).get("username", "") or ""
            except Exception as exc:
                logger.warning("Не удалось получить username бота через getMe: %s", exc)
        _BOT_USERNAME_CACHE = username
        return username


def _webapp_telegram_id() -> Optional[int]:
    """
    Достаёт и валидирует telegram_id из initData запроса Mini App.

    initData ждём в заголовке X-Telegram-Init-Data (фронт ставит его на каждый
    запрос). Подпись проверяется HMAC по токену бота — клиенту доверять нельзя.
    """
    if not BOT_TOKEN:
        return None
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        return None
    return get_telegram_id(init_data, BOT_TOKEN, WEBAPP_INITDATA_MAX_AGE)


def _api_no_store(response: Response) -> Response:
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _api_error(message: str, status: int) -> Response:
    response = jsonify({"ok": False, "error": message})
    response.status_code = status
    return _api_no_store(response)


def _import_url_for(sub_id: Optional[str]) -> Optional[str]:
    if not sub_id:
        return None
    return f"{SUBSCRIPTION_URL}/import/{sub_id}"


def _public_links() -> Dict[str, str]:
    """Ссылки сервиса для Mini App (канал, поддержка, бот)."""
    support = get_setting("support_channel_link", "") or SUPPORT_URL
    channel = get_setting("news_channel_link", "") or ""
    username = _get_bot_username()
    return {
        "support_url": support,
        "channel_url": channel,
        "bot_url": f"https://t.me/{username}" if username else "",
        "bot_username": username,
    }


@app.route('/api/status')
def api_status():
    """Статус подписок пользователя для Mini App."""
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)

    keys = []
    for key in get_user_keys_for_display(telegram_id):
        sub_id = key.get("sub_id")
        expires_dt = _parse_db_datetime(key.get("expires_at"))
        keys.append({
            "id": key.get("id"),
            "display_name": key.get("display_name"),
            "server_name": key.get("server_name"),
            "is_active": bool(key.get("is_active")),
            "is_trial": key.get("tariff_id") is None,
            "expires_at": key.get("expires_at"),
            "expires_at_unix": int(expires_dt.timestamp()) if expires_dt else 0,
            "traffic_used": int(key.get("traffic_used") or 0),
            "traffic_limit": int(key.get("traffic_limit") or 0),
            "online_devices": int(key.get("online_devices") or 0),
            "has_sub": bool(sub_id),
            "import_url": _import_url_for(sub_id),
            "sub_url": f"{SUBSCRIPTION_URL}/sub/{sub_id}?format=plain" if sub_id else None,
        })

    response = jsonify({
        "ok": True,
        "telegram_id": telegram_id,
        "keys": keys,
        "links": _public_links(),
    })
    return _api_no_store(response)


@app.route('/api/tariffs')
def api_tariffs():
    """Список тарифов для покупки (покупка идёт в боте)."""
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)

    tariffs = []
    for t in get_all_tariffs():
        price_rub = t.get("price_rub")
        if price_rub in (None, 0):
            price_rub = round(int(t.get("price_cents") or 0) / 100)
        tariffs.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "duration_days": int(t.get("duration_days") or 0),
            "price_rub": int(price_rub or 0),
            "price_stars": int(t.get("price_stars") or 0),
            "traffic_limit_gb": int(t.get("traffic_limit_gb") or 0),
        })

    response = jsonify({"ok": True, "tariffs": tariffs})
    return _api_no_store(response)


@app.route('/api/referral')
def api_referral():
    """Данные реферальной программы для Mini App."""
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)

    if not is_referral_enabled():
        return _api_no_store(jsonify({"ok": True, "enabled": False}))

    user_id = get_user_internal_id(telegram_id)
    if not user_id:
        return _api_error("user_not_found", 404)

    code = ensure_user_referral_code(user_id)
    username = _get_bot_username()
    link = f"https://t.me/{username}?start=ref_{code}" if username else ""

    stats = get_referral_stats(user_id) or []
    total_invited = sum(int(s.get("count") or 0) for s in stats)

    friends_raw = get_referral_friends(user_id)
    # telegram_id друзей наружу не отдаём — только отображаемые поля.
    friends = [
        {
            "name": (f.get("first_name") or f.get("username") or "Без имени"),
            "username": f.get("username"),
            "created_at": f.get("created_at"),
            "has_paid": bool(f.get("has_paid")),
        }
        for f in friends_raw
    ]
    paid_invited = sum(1 for f in friends if f["has_paid"])

    response = jsonify({
        "ok": True,
        "enabled": True,
        "code": code,
        "link": link,
        "balance_cents": int(get_user_balance(user_id) or 0),
        "reward_type": get_referral_reward_type(),
        "earned_days": int(get_referral_earned_days(user_id) or 0),
        "trial_bonus_days": int(get_setting('referral_trial_bonus_days', '3') or 3),
        "purchase_bonus_days": int(get_setting('referral_purchase_bonus_days', '5') or 5),
        "total_invited": total_invited,
        "paid_invited": paid_invited,
        "friends": friends,
    })
    return _api_no_store(response)


@app.route('/app')
@app.route('/app/')
@app.route('/app/<path:path>')
def webapp(path: str = ""):
    """
    Раздаёт собранный Svelte SPA из webapp_dist/.

    Любой неизвестный путь возвращает index.html — клиентский роутинг разрулит
    его сам. send_from_directory защищает от path traversal.
    """
    if path:
        candidate = os.path.join(WEBAPP_DIST_DIR, path)
        if os.path.isfile(candidate):
            return send_from_directory(WEBAPP_DIST_DIR, path)
    index_path = os.path.join(WEBAPP_DIST_DIR, "index.html")
    if not os.path.isfile(index_path):
        return Response("Mini App не собран (webapp_dist отсутствует)", status=404,
                        mimetype="text/plain")
    return send_from_directory(WEBAPP_DIST_DIR, "index.html")


if __name__ == '__main__':
    # Запуск сервера на внутреннем порту 8080
    # Nginx проксирует с порта 2053 на 8080
    #
    # threaded=True — обрабатываем запросы параллельно (кэши и AsyncExecutor
    # потокобезопасны). Для продакшена предпочтителен gunicorn с потоками,
    # например: gunicorn -w 1 --threads 8 -b 127.0.0.1:8080 subscription_api:app
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)
