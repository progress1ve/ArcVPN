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
import hmac
import html
import json
import logging
import os
import re
import secrets
import shutil
import socket
import smtplib
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Coroutine, Deque, Dict, Iterable, Optional

from flask import Flask, Response, jsonify, redirect, request, send_from_directory

from bot.services.panels.base import VPNAPIError
from bot.services.panels.xui import XUIClient
from bot.services.panels.remnawave import RemnawaveClient
from bot.utils.key_generator import generate_link
from bot.utils.telegram_webapp import get_telegram_id
import config
from database.connection import get_db
from database.db_webapp import adopt_import_device_identity
from database.db_servers import get_server_by_id
from database.db_statistics import (
    get_new_users_stats,
    get_subscriptions_stats,
    get_revenue_stats,
    get_servers_stats,
    get_conversion_stats,
    get_usage_activity_stats,
)
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
    get_webapp_account,
    get_notification_preferences,
    update_notification_preferences,
    get_user_devices,
    rename_user_device,
    revoke_user_device,
    register_import_device,
    import_device_is_allowed,
    get_import_device_access_state,
    resolve_device_subscription,
    subscription_requires_device_token,
    subscription_device_slots_full,
    get_user_entitlements,
    get_subscription_device_limit,
    set_payment_requested_entitlements,
    save_email_code,
    get_email_code,
    increment_email_attempts,
    link_verified_email,
    unlink_email,
    get_user_by_verified_email,
    create_web_session,
    telegram_id_from_session,
    revoke_web_session,
    get_support_messages,
    add_user_support_message,
    get_tariff_by_id,
    prepare_payment_order,
    find_order_by_order_id,
    find_order_by_yookassa_id,
    save_yookassa_payment_id,
)
from database.db_support import get_support_thread, add_admin_support_message
from database.db_recurring import disable_recurring_methods, get_active_recurring_method, get_recurring_summary, save_recurring_method
from bot.services.billing import create_yookassa_qr_payment, check_yookassa_payment_status, get_yookassa_payment_details, process_payment_order
from bot.services.vpn_api import get_client_from_server_data
from bot.services.reserve import get_reserve_client_info
from subscription_pages import render_import_page, render_silent_import_page, render_user_agreement

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
# Лимит трафика на CDN-инкапсуляцию (ГБ, 0 = безлимит). 
# Если превышен — CDN-ссылка пропадает из подписки.
# Берётся из settings БД, с fallback на config.py.
CDN_TRAFFIC_LIMIT_GB = int(get_setting("cdn_traffic_limit_gb", "0") or "0")

# Публичный порт, который клиенты видят в VLESS-ссылке, может отличаться от
# реального порта xray на сервере (например, nginx stream проксирует 443→xray).
PORT_OVERRIDES = getattr(config, "PORT_OVERRIDES", {})

# Информационные строки в подписке — отображаются как комментарии в VPN-клиенте.
# Каждая строка — отдельный #-комментарий. Переопределяется в config.py.
SUBSCRIPTION_INFO_LINES = [
    "#",
    "# ❗ Не работает VPN? Жми кнопку - 🔁 обновить подписку.",
    "# 🔥РФ сервисы РАБОТАЮТ с VPN",
    "#",
    "# 🎁 Приглашайте друзей",
    "# +5 дней — за вход друга в бот",
    "# +15 дней каждому — когда друг продлит подписку",
    "#",
]

# Переопределение имён inbound для серверов, где remark нельзя менять
# через панель мастера (ноды 3x-ui синхронизируют remark обратно).
# Ключ: "host" или "host:port" → display_name.
# Пустой = всегда берём remark из панели (рекомендуется).
INBOUND_DISPLAY_OVERRIDES = getattr(config, "INBOUND_DISPLAY_OVERRIDES", {})

# Zero-downtime Remnawave migration: the public ArcVPN subscription URL remains
# stable while profiles managed by Remnawave are appended to the legacy XUI
# profiles.  All values are public connection parameters; user credentials are
# always taken from the existing ArcVPN VLESS UUID.
REMNAWAVE_FRANCE_ENABLED = bool(getattr(config, "REMNAWAVE_FRANCE_ENABLED", False))
REMNAWAVE_FRANCE_HOST = str(getattr(config, "REMNAWAVE_FRANCE_HOST", "")).strip()
REMNAWAVE_FRANCE_TCP_PORT = int(getattr(config, "REMNAWAVE_FRANCE_TCP_PORT", 20140))
REMNAWAVE_FRANCE_HY2_PORT = int(getattr(config, "REMNAWAVE_FRANCE_HY2_PORT", 20141))
REMNAWAVE_FRANCE_PUBLIC_KEY = str(getattr(config, "REMNAWAVE_FRANCE_PUBLIC_KEY", "")).strip()
REMNAWAVE_FRANCE_SHORT_ID = str(getattr(config, "REMNAWAVE_FRANCE_SHORT_ID", "")).strip()

# Public RemnaNode transport metadata. Private Reality keys stay only inside
# Remnawave profiles; subscription clients require the derived public keys.
REMNAWAVE_PUBLIC_NODES = (
    {
        "enabled": bool(getattr(config, "REMNAWAVE_FRANCE2_ENABLED", False)),
        "country": "FR",
        "flag": "🇫🇷",
        "label": "Франция",
        "host": "fr2.sfxu.ru",
        "tcp_port": 20086,
        "hy2_port": 20087,
        "public_key": "IRmahen2BbN-2-_exw4TNoeJBGAF0bvVSobxdBQ_Bn0",
        "short_id": "ba5b0807589028e6",
        "tcp_number": 1,
        "hy2_number": 2,
    },
    {
        "enabled": bool(getattr(config, "REMNAWAVE_FINLAND_ENABLED", False)),
        "country": "FI",
        "flag": "🇫🇮",
        "label": "Финляндия",
        "host": "fin.arccnet.space",
        "reality_sni": "fin.arccnet.space",
        "tcp_port": 22201,
        "hy2_port": 22202,
        "xhttp_port": 22203,
        "xhttp_path": "/arc",
        "public_key": "q0fq0bbIj61zgT2ybYQKqv5UxA1Y0d6uzc53R2CL-Ds",
        "short_id": "41fb55d5b8ebefda",
        "xhttp_number": 1,
        "tcp_number": 2,
        "hy2_number": 3,
    },
    {
        "enabled": bool(getattr(config, "REMNAWAVE_GERMANY_ENABLED", False)),
        "country": "DE",
        "flag": "🇩🇪",
        "label": "Германия",
        "host": "de.arccnet.space",
        "reality_sni": "sub.arccnet.space",
        "tcp_port": 22101,
        "hy2_port": 22102,
        "xhttp_port": 22103,
        "xhttp_path": "/arc",
        "public_key": "n9XYMi3bet3VPNYabKCFB_qgTb2DDB9vPaRGnLmwM3E",
        "short_id": "9c77d8e5531124d3",
        "xhttp_number": 1,
        "tcp_number": 2,
        "hy2_number": 3,
    },
)
REMNAWAVE_LTE_ENABLED = bool(getattr(config, "REMNAWAVE_LTE_ENABLED", False))
REMNAWAVE_LTE_HOST = "cdn-fi.arccnet.space"

# 3x-ui API обычно отдаёт inbound по ID, а не в пользовательском порядке.
# Имена остаются редактируемыми в панели; этот список задаёт только порядок
# известных конфигураций в подписке. Неизвестные конфиги идут после них.
SUBSCRIPTION_INBOUND_ORDER = getattr(config, "SUBSCRIPTION_INBOUND_ORDER", [
    "Финляндия ⭐⚡ [АВТОВЫБОР]",
    "Германия ⭐ [АВТОВЫБОР]",
    "Финляндия #1",
    "Германия #1",
    "Финляндия #2⚡",
    "Германия #2⚡",
    "Обход глушилок (LTE, трафик ×10) #1",
    "Обход глушилок (LTE, трафик ×10) #2",
])
_SUBSCRIPTION_INBOUND_ORDER_INDEX = {
    name: index for index, name in enumerate(SUBSCRIPTION_INBOUND_ORDER)
}


def _subscription_inbound_order(name: str) -> int:
    """Возвращает порядок подписки, игнорируя флаг страны в remark панели."""
    normalized = name or ""
    for prefix in ("🇫🇮 ", "🇩🇪 ", "🇷🇺 "):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    normalized = normalized.replace("(LTE)", "(LTE, трафик ×10)")
    return _SUBSCRIPTION_INBOUND_ORDER_INDEX.get(
        normalized, len(_SUBSCRIPTION_INBOUND_ORDER_INDEX)
    )


def _subscription_display_name(name: str) -> str:
    """Keep the expensive LTE route explicit in every client UI."""
    value = str(name or "")
    if "Обход глушилок" in value:
        return "🇷🇺 Обход глушилок (трафик ×10, LTE)"
    return value


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
# VPN-клиенты обновляют подписку раз в час; на сервере можно переопределить
# PROFILE_UPDATE_INTERVAL_HOURS через config.py без изменения кода.
PROFILE_UPDATE_INTERVAL_HOURS = int(getattr(config, "PROFILE_UPDATE_INTERVAL_HOURS", 1))
# Happ only accepts subscription-wide automatic server selection for registered
# providers.  The public eight-character provider id is configured separately
# from the code, while the behaviour itself stays enabled by default.
HAPP_PROVIDER_ID = str(
    os.getenv("HAPP_PROVIDER_ID")
    or getattr(config, "HAPP_PROVIDER_ID", "O7YLTHgc")
).strip()
HAPP_LOWEST_DELAY_AUTOCONNECT = bool(
    getattr(config, "HAPP_LOWEST_DELAY_AUTOCONNECT", True)
)
NODE_METRICS_TOKEN = str(getattr(config, "NODE_METRICS_TOKEN", ""))
NODE_INVENTORY = {
    "2.26.84.210": {"provider": "Play2Go", "location": "Германия", "monthly_cost_rub": 340, "capacity_mbps": 1000},
    "195.226.92.37": {"provider": "rdp-onedash.ru", "location": "Финляндия", "monthly_cost_rub": 365, "capacity_mbps": 10000},
}
XUI_CONFIG_FETCH_TIMEOUT_SECONDS = 7
ASYNC_EXECUTOR_RESULT_TIMEOUT_SECONDS = 12
RATE_LIMITER_MAX_KEYS = 10000
VALID_SUBSCRIPTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
# Брендинг можно переопределить в config.py; по умолчанию — текущие значения ArcVPN.
PROFILE_TITLE = "ArcVPN"
PROFILE_TITLE_BASE64 = base64.b64encode(PROFILE_TITLE.encode("utf-8")).decode("ascii")
SUBSCRIPTION_ANNOUNCE = (
    "❗ Не работает VPN? Жми кнопку - 🔁 обновить подписку.\n"
    "🔥РФ сервисы РАБОТАЮТ с VPN\n\n"
    "🎁 Приглашайте друзей\n"
    "+5 дней — за вход друга в бот\n"
    "+15 дней каждому — когда друг продлит подписку"
)
SUBSCRIPTION_ANNOUNCE_BASE64 = base64.b64encode(
    SUBSCRIPTION_ANNOUNCE.encode("utf-8")
).decode("ascii")
SUPPORT_URL = getattr(config, "SUPPORT_URL", "https://t.me/Turan11627")
PROFILE_WEB_PAGE_URL = getattr(config, "PROFILE_WEB_PAGE_URL", "https://t.me/arcvpn1")

# --- Telegram Mini App ---------------------------------------------------------
# Собранный Svelte+Vite фронтенд лежит в webapp_dist/ (коммитится в репо, чтобы
# деплой на сервер был обычным git pull — Node на сервере не нужен).
WEBAPP_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp_dist")
BOT_TOKEN = getattr(config, "BOT_TOKEN", "")
ADMIN_CONSOLE_PASSWORD = os.getenv("ADMIN_CONSOLE_PASSWORD", "")
ADMIN_CONSOLE_COOKIE = "arcvpn_admin"
ADMIN_CONSOLE_SESSION_SECONDS = 12 * 60 * 60
# Возраст initData, после которого считаем её протухшей (сек). Mini App
# переоткрывают часто, сутки — безопасный дефолт.
WEBAPP_INITDATA_MAX_AGE = getattr(config, "WEBAPP_INITDATA_MAX_AGE", 24 * 60 * 60)
SMTP_HOST = os.getenv("SMTP_HOST", getattr(config, "SMTP_HOST", ""))
SMTP_PORT = int(os.getenv("SMTP_PORT", getattr(config, "SMTP_PORT", 587)) or 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", getattr(config, "SMTP_USERNAME", ""))
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", getattr(config, "SMTP_PASSWORD", ""))
SMTP_FROM = os.getenv("SMTP_FROM", getattr(config, "SMTP_FROM", SMTP_USERNAME or ""))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", str(getattr(config, "SMTP_USE_TLS", True))).lower() not in {"0", "false", "no"}
WEB_SESSION_COOKIE = "arcvpn_session"
LEGAL_LAST_UPDATED = "29 июля 2026"
LEGAL_OPERATOR_NAME = os.getenv("LEGAL_OPERATOR_NAME", getattr(config, "LEGAL_OPERATOR_NAME", "[УКАЖИТЕ ФИО ИЛИ НАЗВАНИЕ]"))
LEGAL_OPERATOR_INN = os.getenv("LEGAL_OPERATOR_INN", getattr(config, "LEGAL_OPERATOR_INN", "[УКАЖИТЕ ИНН]"))
LEGAL_OPERATOR_REGISTRATION = os.getenv("LEGAL_OPERATOR_REGISTRATION", getattr(config, "LEGAL_OPERATOR_REGISTRATION", "[УКАЖИТЕ ОГРНИП/ОГРН]"))
LEGAL_OPERATOR_ADDRESS = os.getenv("LEGAL_OPERATOR_ADDRESS", getattr(config, "LEGAL_OPERATOR_ADDRESS", "[УКАЖИТЕ АДРЕС]"))
LEGAL_CONTACT_EMAIL = os.getenv("LEGAL_CONTACT_EMAIL", getattr(config, "LEGAL_CONTACT_EMAIL", "[УКАЖИТЕ EMAIL]"))

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
    client_uuid: Optional[str] = None

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

    def run(self, coro: Coroutine[Any, Any, Any], timeout: Optional[float] = None) -> Any:
        loop = self._ensure_started()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout or ASYNC_EXECUTOR_RESULT_TIMEOUT_SECONDS)
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
        client_uuid=row["client_uuid"] if "client_uuid" in row.keys() else None,
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
        f"#announce: base64:{SUBSCRIPTION_ANNOUNCE_BASE64}",
        f"#profile-update-interval: {PROFILE_UPDATE_INTERVAL_HOURS}",
        f"#subscription-userinfo: {userinfo_header}",
        f"#support-url: {SUPPORT_URL}",
        f"#profile-web-page-url: {PROFILE_WEB_PAGE_URL}",
    ]
    if HAPP_LOWEST_DELAY_AUTOCONNECT:
        lines.extend([
            "#subscription-autoconnect: 1",
            "#subscription-autoconnect-type: lowestdelay",
            "#subscription-ping-onopen-enabled: 1",
        ])
    if re.fullmatch(r"[A-Za-z0-9_-]{8}", HAPP_PROVIDER_ID):
        lines.append(f"#providerid {HAPP_PROVIDER_ID}")
    # Информационный блок (как у конкурентов — подсказки для пользователей)
    if SUBSCRIPTION_INFO_LINES:
        lines.extend(SUBSCRIPTION_INFO_LINES)
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


def _json_outbound_from_share_link(link: str, tag: str) -> Optional[Dict[str, Any]]:
    """Convert an ArcVPN share link into an Xray outbound for Happ JSON arrays."""
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    host = parsed.hostname or ""
    port = parsed.port or 443
    credential = urllib.parse.unquote(parsed.username or "")

    if parsed.scheme == "vless":
        flow = params.get("flow", [""])[0]
        network = params.get("type", ["tcp"])[0]
        security = params.get("security", ["none"])[0]
        stream: Dict[str, Any] = {"network": network, "security": security}
        if security == "reality":
            stream["realitySettings"] = {
                "fingerprint": params.get("fp", ["firefox"])[0],
                "publicKey": params.get("pbk", [""])[0],
                "serverName": params.get("sni", [host])[0],
                "shortId": params.get("sid", [""])[0],
            }
        elif security == "tls":
            stream["tlsSettings"] = {
                "alpn": [item for item in params.get("alpn", ["h2,http/1.1"])[0].split(",") if item],
                "fingerprint": params.get("fp", ["firefox"])[0],
                "serverName": params.get("sni", [host])[0],
            }
        if network == "tcp":
            stream["tcpSettings"] = {}
        elif network == "xhttp":
            xhttp: Dict[str, Any] = {
                "host": params.get("host", [""])[0],
                "mode": params.get("mode", ["auto"])[0],
                "path": params.get("path", ["/"])[0],
            }
            extra_raw = params.get("extra", [""])[0]
            if extra_raw:
                try:
                    xhttp["extra"] = json.loads(extra_raw)
                except (TypeError, ValueError):
                    pass
            stream["xhttpSettings"] = xhttp
        return {
            "protocol": "vless",
            "settings": {"vnext": [{
                "address": host,
                "port": port,
                "users": [{"encryption": "none", "flow": flow, "id": credential}],
            }]},
            "streamSettings": stream,
            "tag": tag,
        }

    if parsed.scheme in {"hysteria2", "hy2"}:
        return {
            "protocol": "hysteria",
            "settings": {"address": host, "port": port, "version": 2},
            "streamSettings": {
                "finalmask": {"quicParams": {"congestion": "bbr", "debug": False}},
                "hysteriaSettings": {"auth": credential, "version": 2},
                "network": "hysteria",
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["h3"],
                    "fingerprint": "firefox",
                    "serverName": params.get("sni", [host])[0],
                },
            },
            "tag": tag,
        }
    return None


def _json_local_inbounds(key: ActiveKeyRecord) -> list[Dict[str, Any]]:
    password = hashlib.sha256(f"happ-http-{key.id}".encode()).hexdigest()[:16]
    sniffing = {"destOverride": ["http", "tls", "quic"], "enabled": True, "routeOnly": False}
    return [
        {
            "listen": "127.0.0.1", "port": 10808, "protocol": "socks",
            "settings": {"auth": "noauth", "udp": True}, "sniffing": sniffing, "tag": "socks",
        },
        {
            "listen": "127.0.0.1", "port": 10809, "protocol": "http",
            "settings": {"accounts": [{"pass": password, "user": "happ-http"}], "allowTransparent": False},
            "sniffing": sniffing, "tag": "http",
        },
    ]


def _build_happ_json_subscription(key: ActiveKeyRecord, links_text: str) -> str:
    """Return a Happ JSON array with a real least-load profile and regular rows."""
    links = [item.strip() for item in links_text.splitlines() if item.strip()]
    regular: list[Dict[str, Any]] = []
    auto_outbounds: list[Dict[str, Any]] = []
    lte_fallback: Optional[Dict[str, Any]] = None
    for index, link in enumerate(links, start=1):
        name = urllib.parse.unquote(link.rsplit("#", 1)[-1]) if "#" in link else f"ArcVPN #{index}"
        outbound = _json_outbound_from_share_link(link, "proxy")
        if outbound is None:
            continue
        regular.append({
            "dns": {"queryStrategy": "UseIP", "servers": ["1.1.1.1", "1.0.0.1"]},
            "inbounds": _json_local_inbounds(key),
            "log": {"loglevel": "none"},
            "meta": None,
            "outbounds": [outbound, {"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "block"}],
            "remarks": name,
            "routing": {
                "domainMatcher": "hybrid", "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"outboundTag": "direct", "protocol": ["bittorrent"], "type": "field"},
                    {"network": "tcp,udp", "outboundTag": "proxy", "type": "field"},
                ],
            },
        })
        if "Обход глушилок" in name and lte_fallback is None:
            lte_fallback = _json_outbound_from_share_link(link, "lte_backup")
        elif "Обход глушилок" not in name:
            candidate = _json_outbound_from_share_link(link, "proxy" if not auto_outbounds else f"proxy-{len(auto_outbounds) + 1}")
            if candidate is not None:
                auto_outbounds.append(candidate)

    if not auto_outbounds:
        return json.dumps(regular, ensure_ascii=False, separators=(",", ":"))
    auto_profile = {
        "burstObservatory": {
            "pingConfig": {
                "connectivity": "", "destination": "http://www.gstatic.com/generate_204",
                "interval": "1m", "sampling": 1, "timeout": "3s",
            },
            "subjectSelector": ["proxy"],
        },
        "dns": {"queryStrategy": "UseIP", "servers": ["1.1.1.1", "1.0.0.1"]},
        "inbounds": _json_local_inbounds(key),
        "log": {"loglevel": "none"},
        "meta": None,
        "outbounds": [*auto_outbounds, *([lte_fallback] if lte_fallback else []), {"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "block"}],
        "remarks": "⚡ Автовыбор",
        "routing": {
            "balancers": [{
                # LTE is excluded from observation/least-load and is used only
                # when every normal server fails the connectivity probe.
                "fallbackTag": "lte_backup" if lte_fallback else "direct", "selector": ["proxy"],
                "strategy": {"settings": {"baselines": ["1s"], "expected": 2, "maxRTT": "1s", "tolerance": 0.01}, "type": "leastLoad"},
                "tag": "Auto_Select",
            }],
            "domainMatcher": "hybrid", "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"outboundTag": "direct", "protocol": ["bittorrent"], "type": "field"},
                {"balancerTag": "Auto_Select", "network": "tcp,udp", "type": "field"},
            ],
        },
    }
    return json.dumps([auto_profile, *regular], ensure_ascii=False, separators=(",", ":"))


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
            body=_build_happ_json_subscription(key, link),
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


def _prepare_device_limit_subscription(
    key: ActiveKeyRecord,
    output_format: str,
    reason: str = "limit",
) -> PreparedSubscription:
    """A visible three-row profile explaining why this device is blocked."""
    variants = {
        "revoked": (
            "⛔ Подписка удалена на этом устройстве",
            "📱 Подключите устройство заново в ArcVPN",
            "💬 Если это ошибка — напишите в поддержку",
        ),
        "legacy": (
            "🔄 Требуется обновить подключение",
            "📱 Импортируйте подписку заново",
            "⚙️ ArcVPN → Настройки → Устройства",
        ),
        "limit": (
            "⛔ Превышен лимит устройств",
            "➕ Докупите дополнительное устройство",
            "⚙️ ArcVPN → Настройки → Устройства",
        ),
    }
    notices = variants.get(reason, variants["limit"])
    links = [
        (
            "vless://00000000-0000-4000-8000-00000000000"
            f"{index}@127.0.0.1:1?encryption=none&security=none&type=tcp"
            f"#{urllib.parse.quote(text)}"
        )
        for index, text in enumerate(notices, start=1)
    ]
    userinfo_header = _build_subscription_userinfo(key)

    if output_format == "json":
        body = json.dumps(
            {
                "remarks": PROFILE_TITLE,
                "message": " ".join(notices),
                "outbounds": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return PreparedSubscription(body, "application/json; charset=utf-8", userinfo_header)

    plain = "\n".join(links)
    if output_format == "base64":
        return PreparedSubscription(
            base64.b64encode(plain.encode("utf-8")).decode("ascii"),
            "application/octet-stream",
            userinfo_header,
        )
    return PreparedSubscription(plain, "text/plain; charset=utf-8", userinfo_header)


def _subscription_not_available() -> Response:
    return Response("Subscription not available", status=404, mimetype="text/plain")


def _subscription_temporarily_unavailable() -> Response:
    return Response("Subscription temporarily unavailable", status=503, mimetype="text/plain")


def _happ_device_identity() -> Optional[Dict[str, str]]:
    """Return the stable identity Happ sends while fetching a subscription."""
    hwid = (request.headers.get("X-Hwid") or "").strip()
    if not hwid or len(hwid) > 128 or not re.fullmatch(r"[A-Za-z0-9._:-]{6,128}", hwid):
        return None
    platform = _clean_text(request.headers.get("X-Device-Os"), 32).lower() or "unknown"
    model = _clean_text(request.headers.get("X-Device-Model"), 96)
    display_name = model or {
        "ios": "iPhone / iPad",
        "android": "Android",
        "windows": "Windows",
        "macos": "Mac",
        "linux": "Linux",
    }.get(platform, "Устройство Happ")
    return {
        "token": "happ-hwid-v1:" + hwid,
        "platform": platform,
        "model": model,
        "display_name": display_name,
    }


def _response_from_prepared(
    prepared: PreparedSubscription,
    profile_title: str = PROFILE_TITLE,
) -> Response:
    # One stable product name in every client. Access state is expressed by the
    # generated inbound remarks, not by renaming the whole subscription.
    profile_title = PROFILE_TITLE
    encoded_profile_title = base64.b64encode(profile_title.encode("utf-8")).decode("ascii")
    response = Response(prepared.body)
    filename = f"{profile_title}.txt"
    response.headers["Content-Type"] = prepared.content_type
    response.headers["Content-Disposition"] = (
        f"inline; filename={json.dumps(filename)}; "
        f"filename*=UTF-8''{urllib.parse.quote(filename)}"
    )
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["profile-update-interval"] = str(PROFILE_UPDATE_INTERVAL_HOURS)
    response.headers["profile-title"] = f"base64:{encoded_profile_title}"
    response.headers["announce"] = f"base64:{SUBSCRIPTION_ANNOUNCE_BASE64}"
    response.headers["support-url"] = SUPPORT_URL
    response.headers["profile-web-page-url"] = PROFILE_WEB_PAGE_URL
    response.headers["Subscription-Userinfo"] = prepared.userinfo_header
    if HAPP_LOWEST_DELAY_AUTOCONNECT:
        response.headers["subscription-autoconnect"] = "1"
        response.headers["subscription-autoconnect-type"] = "lowestdelay"
        response.headers["subscription-ping-onopen-enabled"] = "1"
    response.headers["subscription-always-hwid-enable"] = "1"
    if re.fullmatch(r"[A-Za-z0-9_-]{8}", HAPP_PROVIDER_ID):
        response.headers["providerid"] = HAPP_PROVIDER_ID
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
        if REMNAWAVE_LTE_ENABLED and key.id != -1 and key.client_uuid:
            continue
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
    migrated_countries = {
        str(node.get("country") or "").upper()
        for node in REMNAWAVE_PUBLIC_NODES
        if node.get("enabled", True)
    }
    for key in ordered_keys:
        cache_key = _client_config_cache_key(key.server_id, key.panel_email)
        configs = CLIENT_CONFIG_CACHE.get(cache_key)
        server = servers_by_id.get(key.server_id)
        remnawave_only = bool(
            REMNAWAVE_LTE_ENABLED and key.id != -1 and key.client_uuid
        )
        if (not configs or not server) and not remnawave_only:
            logger.warning(
                "Пропущен ключ %s: не удалось получить конфиг для %s",
                key.id,
                _mask_email(key.panel_email),
            )
            continue
        configs = configs or []

        # В кэше — список конфигов (по одному на inbound сервера). Генерируем
        # отдельную ссылку на каждый inbound; имя берём из remark inbound.
        remnawave_uuid = str(key.client_uuid or "").strip()
        for config in sorted(
            configs,
            key=lambda item: (
                _subscription_inbound_order(item.get("inbound_name", "")),
                item.get("id", 0),
            ),
        ):
            if not remnawave_uuid:
                remnawave_uuid = str(config.get("uuid") or "").strip()
            link_payload = dict(config)
            if key.id == -1:
                # Резервный (аварийный) ключ — призыв к действию вместо имени inbound.
                display_name = key.tariff_name
            else:
                # Имя конфига = remark из панели 3x-ui. Для нод, чьи remark
                # синхронизируются с мастера, можно задать override в config.py
                # через INBOUND_DISPLAY_OVERRIDES = {"host": "имя"} или {"host:port": "имя"}.
                host = config.get("host", "")
                port = config.get("port", "")
                override = (
                    INBOUND_DISPLAY_OVERRIDES.get(f"{host}:{port}")
                    or INBOUND_DISPLAY_OVERRIDES.get(host)
                )
                if override:
                    display_name = override
                else:
                    display_name = config.get("inbound_name") or f"ArcVPN - {key.tariff_name} ({server.name})"

                stream = config.get("stream_settings") or {}
                network = str(stream.get("network") or "").lower()
                protocol = str(config.get("protocol") or "").lower()

                # Stop publishing legacy 3x-ui rows after the corresponding
                # country has passed its Remnawave canary. The Finnish LTE
                # origin remains legacy until its isolated x10 migration.
                is_lte = "Обход глушилок" in display_name
                if is_lte and REMNAWAVE_LTE_ENABLED:
                    continue
                if not is_lte and (
                    ("Финляндия" in display_name and "FI" in migrated_countries)
                    or ("Германия" in display_name and "DE" in migrated_countries)
                ):
                    continue

                # The legacy German host is now only a disaster-recovery TCP
                # Reality route.  Do not expose its XHTTP/Hysteria duplicates.
                if "Германия" in display_name:
                    if not (
                        protocol == "vless"
                        and network in {"tcp", "raw"}
                        and str(stream.get("security") or "").lower() == "reality"
                    ):
                        continue
                    display_name = "🇩🇪 Германия"

                # Customer-facing names are deliberately protocol-agnostic.
                elif "Финляндия" in display_name:
                    if network == "xhttp":
                        display_name = "🇫🇮 Финляндия #1"
                    elif network in {"tcp", "raw"}:
                        display_name = "🇫🇮 Финляндия #2"
                    elif protocol in {"hysteria", "hysteria2"} or network == "hysteria":
                        display_name = "🇫🇮 Финляндия #3"
                display_name = _subscription_display_name(display_name)
            link_payload["server_name"] = display_name
            link_payload["remark"] = display_name

            # CDN-обход: подменяем адрес/порт/TLS чтобы клиент шёл через CDN-домен,
            # а не напрямую на сервер. Origin (наш сервер) видит только CDN.
            # Yandex CDN режет POST, но пропускает OPTIONS: клиент шлёт XHTTP-аплинк
            # методом OPTIONS (uplinkHTTPMethod), nginx на origin переписывает
            # OPTIONS->POST. alpn=h2 обязателен — CDN отвечает по HTTP/2.
            inbound_stream_settings = dict(config.get("stream_settings") or {})
            inbound_xhttp_settings = dict(
                inbound_stream_settings.get("xhttpSettings") or {}
            )
            # У каждого CDN-inbound домен хранится в панели. Это позволяет
            # направлять финский LTE через отдельный cdn-fi ресурс, а немецкий
            # продолжать через основной CDN. Старые inbound без host используют
            # прежний глобальный домен как fallback.
            inbound_cdn_domain = inbound_xhttp_settings.get("host") or CDN_DOMAIN
            if inbound_cdn_domain and config.get("port") in CDN_PORTS:
                # The German CDN path is retired from the public catalogue.
                # Keep only the Finnish LTE origin; it remains the tested
                # fallback while the Remnawave LTE topology is prepared.
                if inbound_cdn_domain != "cdn-fi.arccnet.space":
                    continue
                # Проверка лимита CDN-трафика
                if _cdn_traffic_exceeded(key.panel_email):
                    logger.info("CDN-трафик превышен для %s — исключаем CDN-ссылку", _mask_email(key.panel_email))
                    continue
                link_payload["host"] = inbound_cdn_domain
                link_payload["port"] = 443
                ss = inbound_stream_settings
                ss["security"] = "tls"
                ss["tlsSettings"] = {
                    "serverName": inbound_cdn_domain,
                    "alpn": ["h2", "http/1.1"],
                }
                # Гарантируем host/mode в xhttpSettings (клиент шлёт Host=CDN,
                # packet-up — единственный режим, совместимый с OPTIONS-трюком).
                xs = inbound_xhttp_settings
                xs["host"] = inbound_cdn_domain
                xs["mode"] = "packet-up"
                ss["xhttpSettings"] = xs
                link_payload["stream_settings"] = ss

                # extra-поля XHTTP (uplinkHTTPMethod + padding-обфускация).
                # padding-поля берём из inbound (панель), чтобы клиент и сервер
                # совпадали; uplinkHTTPMethod и sc* добавляем для OPTIONS-трюка.
                extra: Dict[str, Any] = {
                    "uplinkHTTPMethod": "OPTIONS",
                    "scMaxEachPostBytes": 5000000,
                    "scMinPostsIntervalMs": 10,
                    "scMaxBufferedPosts": 50,
                }
                for pad_key in (
                    "xPaddingObfsMode", "xPaddingKey", "xPaddingHeader",
                    "xPaddingMethod", "xPaddingPlacement",
                ):
                    if pad_key in xs:
                        extra[pad_key] = xs[pad_key]
                link_payload["xhttp_extra"] = extra

            # XHTTP (не CDN): тоже добавляем extra с padding из inbound,
            # чтобы клиент и сервер совпадали.
            elif config.get("stream_settings", {}).get("network") == "xhttp":
                xs = config.get("stream_settings", {}).get("xhttpSettings") or {}
                extra: Dict[str, Any] = {
                    "scMaxEachPostBytes": 5000000,
                    "scMinPostsIntervalMs": 10,
                    "scMaxBufferedPosts": 50,
                }
                for pad_key in (
                    "xPaddingObfsMode", "xPaddingKey", "xPaddingHeader",
                    "xPaddingMethod", "xPaddingPlacement",
                ):
                    if pad_key in xs:
                        extra[pad_key] = xs[pad_key]
                if any(k in extra for k in (
                    "xPaddingObfsMode", "xPaddingKey", "xPaddingHeader",
                    "xPaddingMethod", "xPaddingPlacement",
                )):
                    link_payload["xhttp_extra"] = extra

            _orig_port = link_payload.get("port")
            if _orig_port in PORT_OVERRIDES:
                link_payload["port"] = PORT_OVERRIDES[_orig_port]

            links.append(generate_link(link_payload))

        # Production RemnaNodes share the migrated VLESS UUID, so existing
        # ArcVPN customers receive new countries on the same subscription URL.
        if key.id != -1 and remnawave_uuid:
            credential = urllib.parse.quote(remnawave_uuid, safe="")
            for node in REMNAWAVE_PUBLIC_NODES:
                if not node.get("enabled", True):
                    continue
                tcp_query = urllib.parse.urlencode({
                    "encryption": "none",
                    "flow": "xtls-rprx-vision",
                    "type": "tcp",
                    "security": "reality",
                    "sni": node.get("reality_sni") or node["host"],
                    "fp": "firefox",
                    "pbk": node["public_key"],
                    "sid": node["short_id"],
                })
                tcp_name = urllib.parse.quote(
                    f"{node['flag']} {node['label']} #{node['tcp_number']}", safe=""
                )
                links.append(
                    f"vless://{credential}@{node['host']}:{node['tcp_port']}?"
                    f"{tcp_query}#{tcp_name}"
                )

                if node.get("xhttp_port"):
                    xhttp_query = urllib.parse.urlencode({
                        "encryption": "none",
                        "type": "xhttp",
                        "path": node.get("xhttp_path") or "/arc",
                        "mode": "auto",
                        "security": "reality",
                        "sni": node.get("reality_sni") or node["host"],
                        "fp": "firefox",
                        "pbk": node["public_key"],
                        "sid": node["short_id"],
                    })
                    xhttp_name = urllib.parse.quote(
                        f"{node['flag']} {node['label']} #{node['xhttp_number']}",
                        safe="",
                    )
                    links.append(
                        f"vless://{credential}@{node['host']}:{node['xhttp_port']}?"
                        f"{xhttp_query}#{xhttp_name}"
                    )

                hy2_query = urllib.parse.urlencode({
                    "sni": node["host"],
                    "fm": json.dumps(
                        {"quicParams": {"debug": False, "congestion": "bbr"}},
                        separators=(",", ":"),
                    ),
                })
                hy2_name = urllib.parse.quote(
                    f"{node['flag']} {node['label']} #{node['hy2_number']}", safe=""
                )
                links.append(
                    f"hysteria2://{credential}@{node['host']}:{node['hy2_port']}?"
                    f"{hy2_query}#{hy2_name}"
                )

            if REMNAWAVE_LTE_ENABLED:
                lte_extra = json.dumps(
                    {
                        "uplinkHTTPMethod": "OPTIONS",
                        "scMaxEachPostBytes": 5000000,
                        "scMinPostsIntervalMs": 10,
                        "scMaxBufferedPosts": 50,
                        "xPaddingObfsMode": True,
                        "xPaddingKey": "dc",
                        "xPaddingBytes": "100-1000",
                        "xPaddingHeader": "X-Cache",
                        "xPaddingMethod": "tokenish",
                        "xPaddingPlacement": "queryInHeader",
                    },
                    separators=(",", ":"),
                )
                lte_query = urllib.parse.urlencode({
                    "type": "xhttp",
                    "encryption": "none",
                    "path": "/api-test",
                    "host": REMNAWAVE_LTE_HOST,
                    "mode": "packet-up",
                    "x_padding_bytes": "100-1000",
                    "security": "tls",
                    "sni": REMNAWAVE_LTE_HOST,
                    "alpn": "h2,http/1.1",
                    "extra": lte_extra,
                })
                lte_name = urllib.parse.quote(
                    "🇷🇺 Обход глушилок (трафик ×10, LTE)", safe=""
                )
                links.append(
                    f"vless://{credential}@{REMNAWAVE_LTE_HOST}:443?"
                    f"{lte_query}#{lte_name}"
                )

        # Compatibility block for the first France canary. It stays disabled
        # after the production France profile has moved into
        # REMNAWAVE_PUBLIC_NODES, so the old node cannot reappear in catalogs.
        if (
            key.id != -1
            and REMNAWAVE_FRANCE_ENABLED
            and REMNAWAVE_FRANCE_HOST
            and REMNAWAVE_FRANCE_PUBLIC_KEY
            and REMNAWAVE_FRANCE_SHORT_ID
            and remnawave_uuid
        ):
            credential = urllib.parse.quote(remnawave_uuid, safe="")
            tcp_query = urllib.parse.urlencode({
                "encryption": "none",
                "flow": "xtls-rprx-vision",
                "type": "tcp",
                "security": "reality",
                "sni": REMNAWAVE_FRANCE_HOST,
                "fp": "firefox",
                "pbk": REMNAWAVE_FRANCE_PUBLIC_KEY,
                "sid": REMNAWAVE_FRANCE_SHORT_ID,
            })
            france2_enabled = any(
                node.get("enabled", True) and node.get("country") == "FR"
                for node in REMNAWAVE_PUBLIC_NODES
            )
            tcp_name = urllib.parse.quote(
                f"🇫🇷 Франция #{3 if france2_enabled else 1}", safe=""
            )
            links.append(
                f"vless://{credential}@{REMNAWAVE_FRANCE_HOST}:"
                f"{REMNAWAVE_FRANCE_TCP_PORT}?{tcp_query}#{tcp_name}"
            )

            hy2_query = urllib.parse.urlencode({
                "sni": REMNAWAVE_FRANCE_HOST,
                "fm": json.dumps(
                    {"quicParams": {"debug": False, "congestion": "bbr"}},
                    separators=(",", ":"),
                ),
            })
            hy2_name = urllib.parse.quote(
                f"🇫🇷 Франция #{4 if france2_enabled else 2}", safe=""
            )
            links.append(
                f"hysteria2://{credential}@{REMNAWAVE_FRANCE_HOST}:"
                f"{REMNAWAVE_FRANCE_HY2_PORT}?{hy2_query}#{hy2_name}"
            )

    def _catalog_order(link: str) -> tuple[int, int, str]:
        name = urllib.parse.unquote(link.rsplit("#", 1)[-1]) if "#" in link else link
        number_match = re.search(r"#([1-9][0-9]*)", name)
        protocol_order = int(number_match.group(1)) if number_match else 99
        if "Франция" in name:
            country_order = 10
        elif "Финляндия" in name:
            country_order = 20
        elif "Германия" in name:
            country_order = 30
        elif "Польша" in name:
            country_order = 40
        elif "Обход глушилок" in name:
            country_order = 60
        else:
            country_order = 45
        return country_order, protocol_order, name

    return sorted(links, key=_catalog_order)


def _cdn_traffic_exceeded(email: str) -> bool:
    """Проверяет не превышен ли лимит CDN-трафика для клиента."""
    if CDN_TRAFFIC_LIMIT_GB <= 0 or not CDN_DOMAIN:
        return False
    limit_bytes = CDN_TRAFFIC_LIMIT_GB * 1024 ** 3
    try:
        conn = sqlite3.connect("/etc/x-ui/x-ui.db", timeout=5)
        row = conn.execute(
            "SELECT COALESCE(SUM(up + down), 0) FROM client_traffics "
            "WHERE email = ? AND inbound_id = (SELECT id FROM inbounds WHERE port IN ({}))"
            .format(",".join(str(p) for p in CDN_PORTS)),
            (email,)
        ).fetchone()
        conn.close()
        total = row[0] if row else 0
        return total > limit_bytes
    except Exception:
        return False


def _select_links(links: list[str], output_format: str) -> str:
    """
    Склеивает ссылки для тела подписки.

    plain/base64 (Happ/Hiddify) — все inbound одной подписки (VLESS, …),
    каждая ссылка отдельной строкой. json — берём первую (TCP Reality).
    """
    if not links:
        return ""
    return "\n".join(links)


def get_active_key_by_subscription_id(sub_id: str) -> Optional[ActiveKeyRecord]:
    """Находит активный ключ по subscription id."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id, vk.panel_email, vk.client_uuid, vk.server_id, vk.expires_at,
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
        client_uuid=None,
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


@app.route('/sub/<sub_id>', defaults={'path_device_token': ''}, methods=['GET', 'HEAD'])
@app.route('/sub/<sub_id>/<path_device_token>', methods=['GET', 'HEAD'])
def subscription(sub_id: str, path_device_token: str = ''):
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

        default_limit = int(getattr(config, "DEFAULT_LIMIT_IP", 2) or 2)
        device_alias = resolve_device_subscription(sub_id, default_limit)
        profile_title = PROFILE_TITLE
        if device_alias:
            sub_id = device_alias["sub_id"]
            platform_names = {
                "iphone": "iPhone / iPad",
                "ios": "iPhone / iPad",
                "android": "Android",
                "windows": "Windows",
                "macos": "Mac",
                "linux": "Linux",
            }
            device_name = (
                device_alias.get("display_name")
                or platform_names.get(str(device_alias.get("platform", "")).lower())
                or "Устройство"
            )
            profile_title = f"{PROFILE_TITLE} • {device_name}"

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

        device_token = (path_device_token or request.args.get("device") or "").strip()
        if device_alias and device_alias["state"] in {"revoked", "limit"}:
            blocked_title = (
                f"{PROFILE_TITLE} • УСТРОЙСТВО УДАЛЕНО"
                if device_alias["state"] == "revoked"
                else f"{PROFILE_TITLE} • ЛИМИТ УСТРОЙСТВ"
            )
            return _response_from_prepared(
                _prepare_device_limit_subscription(key, output_format, device_alias["state"]),
                blocked_title,
            )
        if device_alias:
            pass
        elif device_token and re.fullmatch(r"[A-Za-z0-9_-]{16,128}", device_token):
            access_state = get_import_device_access_state(
                sub_id,
                device_token,
                get_subscription_device_limit(
                    sub_id,
                    int(getattr(config, "DEFAULT_LIMIT_IP", 2) or 2),
                ),
            )
            if access_state in {"revoked", "limit"}:
                logger.info("Device access %s for %s", access_state, masked_sub_id)
                return _response_from_prepared(
                    _prepare_device_limit_subscription(key, output_format, access_state),
                    f"{PROFILE_TITLE} • " + (
                        "УСТРОЙСТВО УДАЛЕНО" if access_state == "revoked" else "ЛИМИТ УСТРОЙСТВ"
                    ),
                )
            if access_state is None:
                logger.warning("Unknown device token rejected for %s", masked_sub_id)
                return _response_from_prepared(
                    _prepare_device_limit_subscription(key, output_format, "legacy"),
                    f"{PROFILE_TITLE} • СТАРАЯ ПОДПИСКА",
                )
        elif subscription_requires_device_token(sub_id):
            # The public subscription URL is also the recovery path when Telegram/WebApp
            # is unavailable. Reserve one deterministic managed slot for direct imports
            # instead of trapping the user in a WebApp-only bootstrap loop.
            happ_device = _happ_device_identity()
            recovery_token = (
                happ_device["token"] if happ_device else hashlib.sha256(
                    f"arcvpn-direct-import-v1:{sub_id}".encode("utf-8")
                ).hexdigest()
            )
            recovery_state = get_import_device_access_state(
                sub_id,
                recovery_token,
                get_subscription_device_limit(sub_id, default_limit),
            )
            if recovery_state is None and happ_device and adopt_import_device_identity(
                sub_id,
                recovery_token,
                happ_device["platform"],
                happ_device["model"],
            ):
                recovery_state = get_import_device_access_state(
                    sub_id,
                    recovery_token,
                    get_subscription_device_limit(sub_id, default_limit),
                )
            can_reactivate_same_device = recovery_state == "revoked" and happ_device is not None
            can_register_new_device = recovery_state is None and not subscription_device_slots_full(sub_id)
            if can_reactivate_same_device or can_register_new_device:
                import_platform = happ_device["platform"] if happ_device else "unknown"
                import_model = happ_device["model"] if happ_device else ""
                register_import_device(
                    sub_id,
                    recovery_token,
                    import_platform,
                    import_model,
                    "Устройство Happ",
                    client_family,
                    "",
                )
                recovery_state = get_import_device_access_state(
                    sub_id,
                    recovery_token,
                    get_subscription_device_limit(sub_id, default_limit),
                )

            if recovery_state != "allowed":
                reason = "revoked" if recovery_state == "revoked" else "limit"
                logger.info("Direct subscription access %s for %s", reason, masked_sub_id)
                return _response_from_prepared(
                    _prepare_device_limit_subscription(key, output_format, reason),
                    f"{PROFILE_TITLE} • " + (
                        "УСТРОЙСТВО УДАЛЕНО" if reason == "revoked" else "ЛИМИТ УСТРОЙСТВ"
                    ),
                )

            profile_title = PROFILE_TITLE
            logger.info("Direct recovery subscription issued for %s", masked_sub_id)

        if request.method == "HEAD":
            prepared = _prepare_headers_only_subscription(key, output_format)
            logger.info(
                "HEAD подписка выдана без генерации ссылок: %s, client=%s, format=%s",
                masked_sub_id,
                client_family,
                output_format,
            )
            return _response_from_prepared(prepared, profile_title)

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
        return _response_from_prepared(prepared, profile_title)

    except Exception:
        logger.exception("Ошибка генерации подписки для %s", masked_sub_id)
        return _subscription_temporarily_unavailable()


@app.route('/<sub_id>', methods=['GET', 'HEAD'])
def subscription_clean(sub_id: str):
    """Clean subscription route — без /sub/ префикса (как у конкурентов)."""
    return subscription(sub_id)


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

    subscription_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}?format=json"
    safe_subscription_url = html.escape(subscription_url, quote=True)
    js_subscription_url = json.dumps(subscription_url)

    # Правильный формат Happ deeplink: happ://add/{URL}
    happ_deeplink = f"happ://add/{subscription_url}"
    safe_happ_deeplink = html.escape(happ_deeplink, quote=True)

    # HTML страница с новым дизайном на основе референса
    html_page = render_silent_import_page(
        js_subscription_url=js_subscription_url,
        js_device_registration_url=json.dumps(f"{SUBSCRIPTION_URL}/api/device/import/{sub_id}"),
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
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data and BOT_TOKEN:
        telegram_id = get_telegram_id(init_data, BOT_TOKEN, WEBAPP_INITDATA_MAX_AGE)
        if telegram_id is not None:
            return telegram_id

    # Вход по подтверждённому email создаёт HttpOnly-сессию. Сырой токен в БД
    # не хранится: при утечке базы его нельзя использовать как cookie.
    session_token = request.cookies.get(WEB_SESSION_COOKIE, "")
    if session_token and 32 <= len(session_token) <= 128:
        return telegram_id_from_session(hashlib.sha256(session_token.encode("utf-8")).hexdigest())
    return None


def _admin_telegram_id() -> Optional[int]:
    telegram_id = _webapp_telegram_id()
    return telegram_id if telegram_id in set(getattr(config, "ADMIN_IDS", [])) else None


def _admin_cookie_signature(issued_at: str, nonce: str) -> str:
    secret = f"{BOT_TOKEN}:{ADMIN_CONSOLE_PASSWORD}:admin-console".encode("utf-8")
    return hmac.new(secret, f"{issued_at}.{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()


def _admin_cookie_valid() -> bool:
    if not ADMIN_CONSOLE_PASSWORD:
        return False
    try:
        issued_at, nonce, signature = request.cookies.get(ADMIN_CONSOLE_COOKIE, "").split(".", 2)
        age = int(time.time()) - int(issued_at)
        return (
            0 <= age <= ADMIN_CONSOLE_SESSION_SECONDS
            and 16 <= len(nonce) <= 64
            and secrets.compare_digest(signature, _admin_cookie_signature(issued_at, nonce))
        )
    except (TypeError, ValueError):
        return False


def _admin_authorized() -> bool:
    return _admin_telegram_id() is not None or _admin_cookie_valid()


_ADMIN_LOGIN_LOCK = threading.Lock()
_ADMIN_LOGIN_ATTEMPTS: Dict[str, Deque[float]] = defaultdict(deque)


def _admin_login_allowed() -> bool:
    now = time.monotonic()
    key = request.remote_addr or "unknown"
    with _ADMIN_LOGIN_LOCK:
        attempts = _ADMIN_LOGIN_ATTEMPTS[key]
        while attempts and now - attempts[0] > 15 * 60:
            attempts.popleft()
        if len(attempts) >= 8:
            return False
        attempts.append(now)
        return True


_EMAIL_RATE_LOCK = threading.Lock()
_EMAIL_RATE: Dict[str, float] = {}


def _clean_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _email_code_hash(code: str, purpose: str) -> str:
    secret = BOT_TOKEN or SMTP_PASSWORD or "arcvpn-local"
    return hashlib.sha256(f"{secret}:{purpose}:{code}".encode("utf-8")).hexdigest()


def _valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}", value))


def _email_rate_allowed(email: str) -> bool:
    key = hashlib.sha256(f"{request.remote_addr}:{email.lower()}".encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _EMAIL_RATE_LOCK:
        previous = _EMAIL_RATE.get(key, 0.0)
        if now - previous < 60:
            return False
        _EMAIL_RATE[key] = now
        if len(_EMAIL_RATE) > 4096:
            cutoff = now - 900
            for old_key, stamp in list(_EMAIL_RATE.items()):
                if stamp < cutoff:
                    _EMAIL_RATE.pop(old_key, None)
    return True


def _send_email_code(email: str, code: str, purpose: str) -> bool:
    if not SMTP_HOST or not SMTP_FROM:
        return False

    subject = "Код входа в ArcVPN" if purpose == "login" else "Подтверждение email в ArcVPN"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = email
    message.set_content(
        f"Код подтверждения ArcVPN: {code}\n\n"
        "Он действует 10 минут. Если вы не запрашивали код, ничего не делайте."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USERNAME:
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("Не удалось отправить email-код на %s", _mask_email(email))
        return False


def _notify_support_admins(thread_id: int, telegram_id: int, body: str) -> None:
    """Передаёт новое WebApp-сообщение админам с кнопкой быстрого ответа."""
    if not BOT_TOKEN:
        return
    username = get_webapp_account(telegram_id) or {}
    user_label = username.get("username") or str(telegram_id)
    payload = {
        "text": (
            f"💬 <b>Новое сообщение ArcVPN</b>\n"
            f"Пользователь: <code>{html.escape(str(user_label))}</code>\n\n"
            f"{html.escape(body)}"
        ),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "Ответить",
                "callback_data": f"support_reply:{thread_id}",
            }]],
        },
    }
    endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for admin_id in getattr(config, "ADMIN_IDS", []):
        try:
            data = json.dumps({**payload, "chat_id": admin_id}).encode("utf-8")
            req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            logger.exception("Не удалось передать support thread %s админу %s", thread_id, admin_id)


def _notify_payment_applied(user_id: int, message: str) -> None:
    if not BOT_TOKEN:
        return
    user = get_user_by_id(user_id)
    if not user or not user.get("telegram_id"):
        return
    payload = {
        "chat_id": int(user["telegram_id"]),
        "text": (
            "✅ <b>Оплата получена</b>\n\n"
            f"{html.escape(message or 'Подписка и выбранные лимиты обновлены.')}\n\n"
            "Обновите подписку в VPN-приложении."
        ),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "Открыть ArcVPN",
                "web_app": {"url": f"{SUBSCRIPTION_URL.rstrip('/')}/app/"},
            }]],
        },
    }
    try:
        endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=6).read()
    except Exception:
        logger.exception("Не удалось отправить уведомление об оплате user=%s", user_id)


def _device_identity(payload: Dict[str, Any], user_agent: str) -> tuple[str, str, str, str]:
    ua = user_agent or ""
    platform_hint = _clean_text(payload.get("platform"), 40).lower()
    model = _clean_text(payload.get("model"), 80)
    browser = _clean_text(payload.get("browser"), 50)

    if "iphone" in ua.lower() or "iphone" in platform_hint:
        platform, fallback = "ios", "iPhone"
    elif "ipad" in ua.lower() or "ipad" in platform_hint:
        platform, fallback = "ios", "iPad"
    elif "android" in ua.lower() or "android" in platform_hint:
        platform, fallback = "android", "Android"
        if not model:
            match = re.search(r"Android[^;]*;\s*([^;)]+?)(?:\s+Build[/;]|\))", ua, re.I)
            if match:
                model = _clean_text(match.group(1), 80)
    elif "windows" in ua.lower() or "win" in platform_hint:
        platform, fallback = "windows", "Windows PC"
    elif "mac" in ua.lower() or "mac" in platform_hint:
        platform, fallback = "macos", "Mac"
    elif "linux" in ua.lower() or "linux" in platform_hint:
        platform, fallback = "linux", "Linux"
    else:
        platform, fallback = "unknown", "Новое устройство"

    # Chromium's reduced Android UA/Client Hints often reports the placeholder
    # model "K". Prefer a truthful platform label over a random one-letter name.
    if len(model.strip()) < 2 or model.lower() in {"unknown", "not available", "generic"}:
        model = ""
    display_name = model or fallback
    return platform, model, display_name, browser


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
    # Pure URL construction only. Registering here used to create a new ghost
    # device on every /api/status refresh, before the user clicked Import.
    # Telegram WebView does not reliably allow custom happ:// navigation from
    # an async handler.  Keep the WebApp link HTTPS; the import bridge registers
    # the device and only then opens the device-scoped Happ subscription.
    return f"{SUBSCRIPTION_URL.rstrip('/')}/import/{sub_id}"


def _public_links() -> Dict[str, str]:
    """Ссылки сервиса для Mini App (канал, поддержка, бот)."""
    support = get_setting("support_channel_link", "") or SUPPORT_URL
    channel = get_setting("news_channel_link", "") or ""
    username = _get_bot_username()
    return {
        "support_url": support,
        "legal_url": f"{SUBSCRIPTION_URL.rstrip('/')}/legal/user-agreement",
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
            "sub_url": f"{SUBSCRIPTION_URL}/sub/{sub_id}" if sub_id else None,
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


@app.route('/api/payments/sbp', methods=['POST'])
@app.route('/api/payments/card', methods=['POST'])
def api_create_sbp_payment():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    payload = request.get_json(silent=True) or {}
    method_type = "bank_card" if request.path.endswith("/card") else "sbp"
    recurring_requested = bool(payload.get("auto_renew", False))
    recurring_setting = "yookassa_recurring_enabled" if method_type == "bank_card" else "yookassa_sbp_recurring_enabled"
    recurring_ready = get_setting(recurring_setting, "0") == "1"
    if recurring_requested and not recurring_ready:
        return _api_error("recurring_method_not_enabled", 409)
    wants_recurring = recurring_requested and recurring_ready
    try:
        tariff_id = int(payload.get("tariff_id"))
        devices = int(payload.get("devices") or 2)
        lte_gb = int(payload.get("lte_gb") or 20)
    except (TypeError, ValueError):
        return _api_error("invalid_payment_request", 400)
    if not 2 <= devices <= 10 or not 20 <= lte_gb <= 500 or (lte_gb - 20) % 5:
        return _api_error("invalid_addons", 400)
    tariff = get_tariff_by_id(tariff_id)
    user_id = get_user_internal_id(telegram_id)
    if not tariff or not user_id:
        return _api_error("tariff_or_user_not_found", 404)
    current_entitlements = get_user_entitlements(telegram_id)
    if lte_gb != int(current_entitlements.get("lte_quota_gb") or 20):
        return _api_error("lte_addons_not_available", 409)
    price_rub = int(tariff.get("price_rub") or 0)
    if price_rub <= 0:
        price_rub = round(int(tariff.get("price_cents") or 0) / 100)
    if price_rub <= 0:
        return _api_error("invalid_amount", 400)
    months = max(1, round(int(tariff.get("duration_days") or 30) / 30))
    total_rub = price_rub
    total_rub += max(0, devices - 2) * 25 * months
    promocode = None
    promo_code = str(payload.get("promocode") or "").strip().upper()
    if promo_code:
        from database.db_promocodes import is_promocode_valid, compute_discount_rub
        valid, promo_error, promocode = is_promocode_valid(promo_code, user_id)
        if not valid:
            return _api_error(promo_error or "invalid_promocode", 400)
        total_rub = max(1, total_rub - int(compute_discount_rub(promocode, total_rub) or 0))
    # LTE add-on charging is enabled only after the weighted meter is active.
    keys = get_user_keys_for_display(telegram_id)
    key_id = keys[0].get("id") if keys else None
    order = prepare_payment_order(
        user_id=user_id, tariff_id=tariff_id, payment_type="yookassa_card" if method_type == "bank_card" else "yookassa_qr",
        vpn_key_id=key_id, amount_cents=total_rub * 100,
        operation_type="renew" if key_id else "new", promocode_id=promocode.get("id") if promocode else None,
    )
    if wants_recurring:
        with get_db() as conn:
            conn.execute("UPDATE payments SET auto_renew_requested=1 WHERE order_id=?", (order["order_id"],))
    if not set_payment_requested_entitlements(order["order_id"], devices, lte_gb):
        logger.error("Не удалось сохранить add-ons заказа %s", order["order_id"])
        return _api_error("payment_initialization_failed", 500)
    try:
        payment = ASYNC_EXECUTOR.run(create_yookassa_qr_payment(
            amount_rub=total_rub,
            order_id=order["order_id"],
            description=f"ArcVPN — {tariff.get('name') or 'подписка'}",
            bot_name=_get_bot_username(),
            metadata={"telegram_id": str(telegram_id), "source": "webapp"},
            return_url=f"{SUBSCRIPTION_URL.rstrip('/')}/app/?payment={order['order_id']}",
            save_payment_method=wants_recurring,
            payment_method_type=method_type,
        ), timeout=45)
        save_yookassa_payment_id(order["order_id"], payment["yookassa_payment_id"])
    except Exception:
        logger.exception("Не удалось создать СБП-платёж для user=%s", telegram_id)
        return _api_error("payment_provider_unavailable", 503)
    return _api_no_store(jsonify({
        "ok": True, "order_id": order["order_id"],
        "confirmation_url": payment["qr_url"], "status": payment["status"],
        "amount_rub": total_rub,
    }))


@app.route('/api/payments/yookassa/webhook', methods=['POST'])
def api_yookassa_webhook():
    """Verify YooKassa events with the provider before applying an order."""
    payload = request.get_json(silent=True) or {}
    event = str(payload.get("event") or "")
    payment = payload.get("object") if isinstance(payload.get("object"), dict) else {}
    provider_id = str(payment.get("id") or "")
    if event not in {"payment.succeeded", "payment.canceled", "payment.waiting_for_capture"}:
        return jsonify({"ok": True, "ignored": True})
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", provider_id):
        return _api_error("invalid_webhook", 400)

    order = find_order_by_yookassa_id(provider_id)
    if not order:
        logger.warning("YooKassa webhook для неизвестного payment %s", _mask_token(provider_id))
        return _api_error("payment_not_found", 404)
    if event != "payment.succeeded":
        return jsonify({"ok": True, "status": event.removeprefix("payment.")})

    was_applied = (
        order.get("status") == "paid"
        and order.get("fulfillment_status") == "applied"
    )
    try:
        payment_details = ASYNC_EXECUTOR.run(get_yookassa_payment_details(provider_id), timeout=45)
        verified_status = str(payment_details.get("status") or "pending")
        if verified_status != "succeeded":
            logger.warning(
                "YooKassa webhook status mismatch: payment=%s api=%s",
                _mask_token(provider_id),
                verified_status,
            )
            return _api_error("payment_not_confirmed", 409)
        payment_method = payment_details.get("payment_method") or {}
        if bool(payment_method.get("saved")) and int(order.get("auto_renew_requested") or 0):
            method_type = str(payment_method.get("type") or "bank_card")
            card = payment_method.get("card") or {}
            title = (
                f"Карта •••• {card.get('last4')}" if card.get("last4")
                else "СБП" if method_type == "sbp"
                else "Сохранённый способ оплаты"
            )
            save_recurring_method(
                int(order["user_id"]), str(payment_method.get("id") or ""), method_type, title,
                vpn_key_id=order.get("vpn_key_id"), tariff_id=order.get("tariff_id"),
                amount_cents=order.get("amount_cents"), period_days=order.get("period_days"),
            )
        success, message, updated = ASYNC_EXECUTOR.run(
            process_payment_order(order["order_id"]),
            timeout=60,
        )
        if not success:
            return _api_error("payment_fulfillment_failed", 503)
        if not was_applied and updated and updated.get("fulfillment_status") == "applied":
            threading.Thread(
                target=_notify_payment_applied,
                args=(int(order["user_id"]), message),
                daemon=True,
            ).start()
        return jsonify({
            "ok": True,
            "status": "succeeded",
            "applied": bool(updated and updated.get("fulfillment_status") == "applied"),
        })
    except Exception:
        logger.exception("Ошибка YooKassa webhook payment=%s", _mask_token(provider_id))
        return _api_error("payment_webhook_retry", 503)


@app.route('/api/payments/sbp/<order_id>')
def api_sbp_payment_status(order_id: str):
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    order = find_order_by_order_id(order_id)
    user_id = get_user_internal_id(telegram_id)
    if not order or not user_id or int(order.get("user_id") or 0) != int(user_id):
        return _api_error("payment_not_found", 404)
    if order.get("status") == "paid" and order.get("fulfillment_status") == "applied":
        return _api_no_store(jsonify({
            "ok": True,
            "status": "succeeded",
            "applied": True,
            "fulfillment_status": "applied",
        }))
    provider_id = order.get("yookassa_payment_id")
    if not provider_id:
        return _api_error("payment_not_initialized", 409)
    try:
        payment_details = ASYNC_EXECUTOR.run(get_yookassa_payment_details(provider_id), timeout=45)
        status = str(payment_details.get("status") or "pending")
        applied = False
        fulfillment_status = order.get("fulfillment_status") or "pending"
        if status == "succeeded":
            payment_method = payment_details.get("payment_method") or {}
            if bool(payment_method.get("saved")) and int(order.get("auto_renew_requested") or 0):
                method_type = str(payment_method.get("type") or "bank_card")
                card = payment_method.get("card") or {}
                title = f"Карта •••• {card.get('last4')}" if card.get("last4") else "СБП" if method_type == "sbp" else "Сохранённый способ оплаты"
                save_recurring_method(
                    int(order["user_id"]), str(payment_method.get("id") or ""), method_type, title,
                    vpn_key_id=order.get("vpn_key_id"), tariff_id=order.get("tariff_id"),
                    amount_cents=order.get("amount_cents"), period_days=order.get("period_days"),
                )
            success, _, updated = ASYNC_EXECUTOR.run(process_payment_order(order_id), timeout=45)
            applied = bool(success and updated and updated.get("fulfillment_status") == "applied")
            fulfillment_status = (updated or {}).get("fulfillment_status") or fulfillment_status
        return _api_no_store(jsonify({
            "ok": True,
            "status": status,
            "applied": applied,
            "fulfillment_status": fulfillment_status,
            "review_required": status == "succeeded" and fulfillment_status == "manual_review",
        }))
    except Exception:
        logger.exception("Не удалось проверить СБП-платёж %s", order_id)
        return _api_error("payment_status_unavailable", 503)


@app.route('/api/billing/recurring', methods=['GET', 'DELETE'])
def api_recurring_payment_method():
    """Show or revoke a saved method without a support request."""
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    account = get_webapp_account(telegram_id)
    if not account:
        return _api_error("account_not_found", 404)
    user_id = int(account["id"])
    if request.method == 'DELETE':
        disabled = disable_recurring_methods(user_id)
        return _api_no_store(jsonify({"ok": True, "disabled": bool(disabled)}))
    method = get_active_recurring_method(user_id)
    return _api_no_store(jsonify({
        "ok": True,
        "enabled": bool(method),
        "method": method,
        "provider_ready": bool(get_setting("yookassa_recurring_enabled", "0") == "1"),
    }))


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
        "site_link": f"{SUBSCRIPTION_URL.rstrip('/')}/invite/{urllib.parse.quote(code, safe='')}",
        "balance_cents": int(get_user_balance(user_id) or 0),
        "reward_type": get_referral_reward_type(),
        "earned_days": int(get_referral_earned_days(user_id) or 0),
        "trial_bonus_days": int(get_setting('referral_trial_bonus_days', '5') or 5),
        "purchase_bonus_days": int(get_setting('referral_purchase_bonus_days', '15') or 15),
        "total_invited": total_invited,
        "paid_invited": paid_invited,
        "friends": friends,
    })
    return _api_no_store(response)


@app.route('/api/account')
def api_account():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    account = get_webapp_account(telegram_id)
    if not account:
        return _api_error("user_not_found", 404)
    response = jsonify({
        "ok": True,
        "telegram_id": telegram_id,
        "username": account.get("username"),
        "email": account.get("email"),
        "email_verified": bool(account.get("email_verified_at")),
        "email_available": bool(SMTP_HOST and SMTP_FROM),
    })
    return _api_no_store(response)


@app.route('/api/preferences', methods=['GET', 'POST'])
def api_preferences():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        values = {key: payload[key] for key in ("expiry", "traffic", "connection") if isinstance(payload.get(key), bool)}
        if not values or not update_notification_preferences(telegram_id, values):
            return _api_error("invalid_preferences", 400)
    response = jsonify({"ok": True, "notifications": get_notification_preferences(telegram_id)})
    return _api_no_store(response)


@app.route('/api/devices')
def api_devices():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    devices = get_user_devices(telegram_id)
    online_total = sum(int(key.get("online_devices") or 0) for key in get_user_keys_for_display(telegram_id))
    entitlements = get_user_entitlements(telegram_id)
    response = jsonify({
        "ok": True,
        "online_total": online_total,
        "devices": devices,
        **entitlements,
    })
    return _api_no_store(response)


@app.route('/api/devices/<int:device_id>', methods=['PATCH', 'DELETE'])
def api_manage_device(device_id: int):
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    if request.method == 'DELETE':
        if not revoke_user_device(telegram_id, device_id):
            return _api_error("device_not_found", 404)
        return _api_no_store(jsonify({"ok": True, "released": True}))

    payload = request.get_json(silent=True) or {}
    display_name = _clean_text(payload.get("display_name"), 60)
    if len(display_name) < 2:
        return _api_error("invalid_device_name", 400)
    if not rename_user_device(telegram_id, device_id, display_name):
        return _api_error("device_not_found", 404)
    return _api_no_store(jsonify({
        "ok": True,
        "device_id": device_id,
        "display_name": display_name,
    }))


@app.route('/api/support/messages', methods=['GET', 'POST'])
def api_support_messages():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None:
        return _api_error("unauthorized", 401)
    if request.method == 'GET':
        try:
            after_id = max(0, int(request.args.get("after", "0")))
        except ValueError:
            after_id = 0
        result = get_support_messages(telegram_id, after_id=after_id)
        return _api_no_store(jsonify({"ok": True, **result}))

    if (request.content_length or 0) > 8192:
        return _api_error("message_too_large", 413)
    payload = request.get_json(silent=True) or {}
    body = str(payload.get("body") or "").replace("\x00", "").strip()
    body = re.sub(r"[ \t]+", " ", body)[:2000]
    if not body:
        return _api_error("empty_message", 400)
    result = add_user_support_message(telegram_id, body)
    if not result:
        return _api_error("user_not_found", 404)
    if result.get("rate_limited"):
        return _api_error("try_later", 429)
    threading.Thread(
        target=_notify_support_admins,
        args=(int(result["thread_id"]), telegram_id, body),
        daemon=True,
        name=f"support-notify-{result['thread_id']}",
    ).start()
    return _api_no_store(jsonify({"ok": True, **result}))


@app.route('/api/device/import/<sub_id>', methods=['POST'])
def api_register_import_device(sub_id: str):
    """Регистрирует устройство в момент нажатия «Открыть в Happ»."""
    if not _is_valid_subscription_id(sub_id) or (request.content_length or 0) > 8192:
        return _api_error("invalid_device_request", 400)
    payload = request.get_json(silent=True) or {}
    device_token = _clean_text(payload.get("device_token"), 128)
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", device_token):
        return _api_error("invalid_device_token", 400)
    platform, model, display_name, browser = _device_identity(
        payload, request.headers.get("User-Agent", "")
    )
    screen_size = _clean_text(payload.get("screen_size"), 30)
    device_sub_id = register_import_device(
        sub_id, device_token, platform, model, display_name, browser, screen_size
    )
    if not device_sub_id:
        return _api_error("subscription_not_found", 404)
    return _api_no_store(jsonify({
        "ok": True,
        "device_name": display_name,
        "device_sub_id": device_sub_id,
        "import_url": f"happ://add/{SUBSCRIPTION_URL}/sub/{device_sub_id}?format=json",
    }))


@app.route('/api/auth/email/request', methods=['POST'])
def api_email_request():
    payload = request.get_json(silent=True) or {}
    email = _clean_text(payload.get("email"), 254).lower()
    purpose = _clean_text(payload.get("purpose"), 12)
    if purpose not in {"link", "login"} or not _valid_email(email):
        return _api_error("invalid_email", 400)
    if not SMTP_HOST or not SMTP_FROM:
        return _api_error("email_unavailable", 503)
    if not _email_rate_allowed(email):
        return _api_error("try_later", 429)

    if purpose == "link":
        telegram_id = _webapp_telegram_id()
        account = get_webapp_account(telegram_id) if telegram_id is not None else None
        if not account:
            return _api_error("unauthorized", 401)
        user = {"id": account["id"]}
    else:
        user = get_user_by_verified_email(email)
        # Не раскрываем, привязан ли email. Для неизвестного адреса ответ такой же.
        if not user:
            return _api_no_store(jsonify({"ok": True, "sent": True}))

    code = f"{secrets.randbelow(1_000_000):06d}"
    save_email_code(int(user["id"]), email, purpose, _email_code_hash(code, purpose))
    if not _send_email_code(email, code, purpose):
        return _api_error("email_delivery_failed", 502)
    return _api_no_store(jsonify({"ok": True, "sent": True}))


@app.route('/api/auth/email/verify', methods=['POST'])
def api_email_verify():
    payload = request.get_json(silent=True) or {}
    email = _clean_text(payload.get("email"), 254).lower()
    purpose = _clean_text(payload.get("purpose"), 12)
    code = _clean_text(payload.get("code"), 6)
    if purpose not in {"link", "login"} or not _valid_email(email) or not re.fullmatch(r"\d{6}", code):
        return _api_error("invalid_code", 400)

    if purpose == "link":
        telegram_id = _webapp_telegram_id()
        account = get_webapp_account(telegram_id) if telegram_id is not None else None
        user = {"id": account["id"]} if account else None
    else:
        user = get_user_by_verified_email(email)
    if not user:
        return _api_error("invalid_code", 400)

    record = get_email_code(int(user["id"]), purpose)
    if not record or int(record.get("attempts") or 0) >= 5:
        return _api_error("invalid_code", 400)
    if not secrets.compare_digest(record["code_hash"], _email_code_hash(code, purpose)):
        increment_email_attempts(int(record["id"]))
        return _api_error("invalid_code", 400)

    response = jsonify({"ok": True, "email": email})
    if purpose == "link":
        try:
            link_verified_email(int(user["id"]), email)
        except sqlite3.IntegrityError:
            return _api_error("email_in_use", 409)
    else:
        raw_token = secrets.token_urlsafe(48)
        create_web_session(int(user["id"]), hashlib.sha256(raw_token.encode("utf-8")).hexdigest())
        response.set_cookie(
            WEB_SESSION_COOKIE, raw_token, max_age=30 * 86400,
            secure=True, httponly=True, samesite="Lax", path="/",
        )
    return _api_no_store(response)


@app.route('/api/auth/email/unlink', methods=['POST'])
def api_email_unlink():
    telegram_id = _webapp_telegram_id()
    if telegram_id is None or not unlink_email(telegram_id):
        return _api_error("unauthorized", 401)
    response = jsonify({"ok": True})
    response.delete_cookie(WEB_SESSION_COOKIE, path="/")
    return _api_no_store(response)


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    raw_token = request.cookies.get(WEB_SESSION_COOKIE, "")
    if raw_token:
        revoke_web_session(hashlib.sha256(raw_token.encode("utf-8")).hexdigest())
    response = jsonify({"ok": True})
    response.delete_cookie(WEB_SESSION_COOKIE, path="/")
    return _api_no_store(response)


@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    if not ADMIN_CONSOLE_PASSWORD:
        return _api_error("admin_password_unavailable", 503)
    if not _admin_login_allowed():
        return _api_error("try_later", 429)
    payload = request.get_json(silent=True) or {}
    supplied = str(payload.get("password") or "")[:256]
    if not secrets.compare_digest(supplied, ADMIN_CONSOLE_PASSWORD):
        time.sleep(0.35)
        return _api_error("invalid_password", 403)
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    response = jsonify({"ok": True})
    response.set_cookie(
        ADMIN_CONSOLE_COOKIE,
        f"{issued_at}.{nonce}.{_admin_cookie_signature(issued_at, nonce)}",
        max_age=ADMIN_CONSOLE_SESSION_SECONDS,
        secure=True,
        httponly=True,
        samesite="Strict",
        path="/",
    )
    return _api_no_store(response)


@app.route('/api/internal/node-metrics', methods=['POST'])
def api_internal_node_metrics():
    """Receive authenticated host telemetry without depending on x-ui."""
    supplied = request.headers.get("Authorization", "")
    expected = f"Bearer {NODE_METRICS_TOKEN}" if NODE_METRICS_TOKEN else ""
    if not expected or not secrets.compare_digest(supplied, expected):
        return _api_error("unauthorized", 401)
    payload = request.get_json(silent=True) or {}
    host = _clean_text(payload.get("host"), 255)
    if host not in NODE_INVENTORY:
        return _api_error("unknown_node", 400)

    def number(name, low=0.0, high=1_000_000_000_000.0):
        value = payload.get(name)
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return round(min(high, max(low, value)), 3)

    xui_active = bool(payload.get("xui_active"))
    xray_state = _clean_text(payload.get("xray_state"), 32) or ("running" if xui_active else "unknown")
    state = "healthy" if xui_active else "degraded"
    with get_db() as conn:
        server = conn.execute("SELECT id FROM servers WHERE host=?", (host,)).fetchone()
        server_id = int(server["id"]) if server else None
        conn.execute("""
            INSERT INTO server_health_samples(
              server_id,host,state,cpu_pct,mem_pct,xray_state,telemetry_available,latency_ms,
              source,load_1m,disk_used_pct,net_rx_bps,net_tx_bps,tcp_established,
              uptime_seconds,xui_active,hysteria_active,boot_id,cpu_steal_pct,
              packet_loss_pct,jitter_ms,dns_ms,https_ms,download_mbps,probed_at
            ) VALUES (?,?,?,?,?,?,1,?,'agent',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            server_id, host, state, number("cpu_pct", 0, 100), number("mem_pct", 0, 100), xray_state,
            number("latency_ms", 0, 60_000),
            number("load_1m"), number("disk_used_pct", 0, 100), number("net_rx_bps"), number("net_tx_bps"),
            int(number("tcp_established", 0, 10_000_000) or 0),
            int(number("uptime_seconds", 0) or 0), int(xui_active), int(bool(payload.get("hysteria_active"))),
            _clean_text(payload.get("boot_id"), 64), number("cpu_steal_pct", 0, 100),
            number("packet_loss_pct", 0, 100), number("jitter_ms", 0, 60_000),
            number("dns_ms", 0, 60_000), number("https_ms", 0, 60_000),
            number("download_mbps", 0, 100_000), int(number("probed_at", 0) or 0),
        ))
        if server_id is not None:
            conn.execute("UPDATE servers SET lifecycle_state=? WHERE id=?", (state, server_id))
    return _api_no_store(jsonify({"ok": True}))


@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    response = jsonify({"ok": True})
    response.delete_cookie(ADMIN_CONSOLE_COOKIE, path="/")
    return _api_no_store(response)


@app.route('/api/admin/diagnostics/run', methods=['POST'])
def api_admin_diagnostics_run():
    """Run a bounded reachability test for one registered RemnaNode."""
    if not _admin_authorized():
        return _api_error("admin_unauthorized", 403)
    payload = request.get_json(silent=True) or {}
    requested_uuid = _clean_text(payload.get("node_uuid"), 64)
    remna_env: Dict[str, str] = {}
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env.remnawave-staging"), "r", encoding="utf-8") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    remna_env[key.strip()] = value.strip()

        async def get_nodes():
            client = RemnawaveClient({
                "panel_api_url": remna_env.get("REMNAWAVE_PANEL_URL", ""),
                "panel_api_token": remna_env.get("REMNAWAVE_API_TOKEN", ""),
            })
            try:
                return await client._request("GET", "/api/nodes")
            finally:
                await client.close()

        nodes = ASYNC_EXECUTOR.run(get_nodes(), timeout=12) or []
        node = next((item for item in nodes if str(item.get("uuid")) == requested_uuid), None)
        if not node:
            return _api_error("unknown_node", 404)
        host = _clean_text(node.get("address"), 255)
        ports = sorted({
            int(item.get("port")) for item in ((node.get("configProfile") or {}).get("activeInbounds") or [])
            if str(item.get("port") or "").isdigit()
            and 1 <= int(item.get("port")) <= 65535
            and not any(marker in " ".join(str(item.get(key) or "") for key in ("network", "type", "protocol", "tag")).lower()
                        for marker in ("hysteria", "udp", "quic"))
        })
        completed = subprocess.run(
            [os.sys.executable, os.path.join(os.path.dirname(__file__), "monitoring", "deep_node_diagnostics.py"),
             "--host", host, "--ports", ",".join(map(str, ports))],
            capture_output=True, text=True, timeout=45, check=False,
        )
        result = json.loads(completed.stdout or "{}")
        result.update({"node_uuid": requested_uuid, "node_name": node.get("name") or host})
        with get_db() as conn:
            conn.execute(
                "INSERT INTO node_diagnostic_runs(host,result_json,ok) VALUES(?,?,?)",
                (host, json.dumps(result, ensure_ascii=False), int(bool(result.get("ok")))),
            )
        return _api_no_store(jsonify({"ok": True, "diagnostic": result}))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.exception("Manual node diagnostic failed")
        return _api_error(type(exc).__name__, 503)


@app.route('/api/admin/overview', methods=['GET'])
def api_admin_overview():
    """Read-only first slice of ArcVPN Business Console."""
    if not _admin_authorized():
        return _api_error("admin_unauthorized", 403)

    with get_db() as conn:
        support_open = conn.execute(
            "SELECT COUNT(*) AS count FROM support_threads WHERE status != 'closed'"
        ).fetchone()["count"]
        pending_payments = conn.execute(
            "SELECT COUNT(*) AS count FROM payments WHERE status IN ('pending', 'created')"
        ).fetchone()["count"]
        device_security = dict(conn.execute("""
            SELECT
              (SELECT COUNT(*) FROM user_devices WHERE COALESCE(is_active,1)=1) AS active_devices,
              (SELECT COUNT(*) FROM user_devices WHERE COALESCE(is_active,1)=0) AS revoked_devices,
              (SELECT COUNT(*) FROM users WHERE COALESCE(enforce_device_tokens,0)=1) AS protected_users,
              (SELECT COUNT(*) FROM users u WHERE
                 (SELECT COUNT(*) FROM user_devices d
                  WHERE d.user_id=u.id AND COALESCE(d.is_active,1)=1) > COALESCE(u.device_limit,2)
               ) AS users_over_limit,
              (SELECT COUNT(*) FROM users u WHERE COALESCE(u.enforce_device_tokens,0)=1 AND
                 NOT EXISTS(SELECT 1 FROM user_devices d WHERE d.user_id=u.id AND COALESCE(d.is_active,1)=1)
               ) AS awaiting_reimport
        """).fetchone())
        # Historical YooKassa rows used amount_cents as RUB, while the current
        # checkout stores kopecks.  Normalize both generations at the read
        # boundary; never rewrite payment history because fulfilment is keyed
        # to the original order values.
        rub_amount_sql = """
            CASE
              WHEN COALESCE(p.payment_type,'') IN ('yookassa','yookassa_qr','cards','balance')
                THEN CASE WHEN COALESCE(p.amount_cents,0) >= 10000
                          THEN p.amount_cents / 100.0 ELSE COALESCE(p.amount_cents,0) END
              ELSE 0
            END
        """
        recent_users = [dict(row) for row in conn.execute(f"""
            SELECT u.telegram_id, u.username, u.first_name, u.created_at,
                   EXISTS(SELECT 1 FROM vpn_keys vk WHERE vk.user_id=u.id AND vk.expires_at > datetime('now')) AS active,
                   COALESCE((SELECT SUM(vk.online_devices) FROM vpn_keys vk WHERE vk.user_id=u.id), 0) AS online_devices,
                   (SELECT MAX(vk.last_online_at) FROM vpn_keys vk WHERE vk.user_id=u.id) AS last_online_at,
                   COALESCE((SELECT SUM({rub_amount_sql}) FROM payments p WHERE p.user_id=u.id AND p.status IN ('paid','succeeded') AND COALESCE(p.payment_type,'') != 'trial'), 0) AS paid_rub,
                   (SELECT MAX(vk.expires_at) FROM vpn_keys vk WHERE vk.user_id=u.id) AS expires_at
            FROM users u
            ORDER BY paid_rub DESC, u.created_at DESC LIMIT 200
        """).fetchall()]
        recent_payments = [dict(row) for row in conn.execute(f"""
            SELECT p.order_id, p.status, p.amount_cents, p.payment_type, p.paid_at,
                   u.telegram_id, u.username, t.name AS tariff_name, t.price_rub AS tariff_price_rub,
                   {rub_amount_sql} AS display_amount_rub,
                   CASE WHEN COALESCE(p.payment_type,'')='crypto' THEN p.amount_cents / 100.0 ELSE 0 END AS display_amount_usd
            FROM payments p JOIN users u ON u.id=p.user_id
            LEFT JOIN tariffs t ON t.id=p.tariff_id
            WHERE COALESCE(p.payment_type,'') != 'trial'
            ORDER BY p.id DESC LIMIT 200
        """).fetchall()]
        financials = dict(conn.execute(f"""
            SELECT
              SUM(CASE WHEN p.status IN ('paid','succeeded') THEN {rub_amount_sql} ELSE 0 END) AS lifetime_rub,
              SUM(CASE WHEN p.status IN ('paid','succeeded') AND p.paid_at >= datetime('now','-30 days') THEN {rub_amount_sql} ELSE 0 END) AS month_rub,
              SUM(CASE WHEN p.status IN ('paid','succeeded') AND COALESCE(p.payment_type,'')='crypto' THEN p.amount_cents / 100.0 ELSE 0 END) AS lifetime_usd,
              COUNT(DISTINCT CASE WHEN p.status IN ('paid','succeeded') AND (
                {rub_amount_sql} > 0 OR
                (COALESCE(p.payment_type,'')='crypto' AND COALESCE(p.amount_cents,0)>0) OR
                (COALESCE(p.payment_type,'')='stars' AND COALESCE(p.amount_cents,0)>0)
              ) THEN p.user_id END) AS paying_users,
              COUNT(CASE WHEN p.status IN ('paid','succeeded') AND (
                {rub_amount_sql} > 0 OR
                (COALESCE(p.payment_type,'')='crypto' AND COALESCE(p.amount_cents,0)>0) OR
                (COALESCE(p.payment_type,'')='stars' AND COALESCE(p.amount_cents,0)>0)
              ) THEN 1 END) AS successful_orders
            FROM payments p
            WHERE COALESCE(p.payment_type,'') != 'trial'
        """).fetchone())

    local_panel = {"healthy": False, "inbounds": 0, "detail": "unavailable"}
    try:
        panel_db = sqlite3.connect("file:/etc/x-ui/x-ui.db?mode=ro", uri=True, timeout=3)
        try:
            integrity = str(panel_db.execute("PRAGMA quick_check").fetchone()[0])
            inbound_count = int(panel_db.execute("SELECT COUNT(*) FROM inbounds").fetchone()[0])
            local_panel = {
                "healthy": integrity == "ok" and inbound_count == 8,
                "inbounds": inbound_count,
                "detail": integrity,
            }
        finally:
            panel_db.close()
    except sqlite3.Error as exc:
        local_panel["detail"] = type(exc).__name__

    server_stats = get_servers_stats()
    for server in server_stats:
        for key, value in NODE_INVENTORY.get(str(server.get("host") or ""), {}).items():
            if server.get(key) in (None, ""):
                server[key] = value
    inbound_health = []
    panel_online_total = None
    node_online_total = 0
    panel_api_healthy = False
    try:
        # Remnawave is authoritative after cutover. Do not poll the retired XUI
        # master: it only produces noisy connector/login errors in admin logs.
        master_row = None
        master = None

        async def _panel_telemetry():
            client = get_client_from_server_data(master)
            try:
                nodes = await client._request("GET", "/panel/api/nodes/list", retry=False, log_error=False)
                online = await client.get_online_emails()
                inbounds = await client.get_inbounds()
                return nodes, online, inbounds
            finally:
                await client.close()

        node_response, online_emails, panel_inbounds = (
            ASYNC_EXECUTOR.run(_panel_telemetry(), timeout=10) if master else ({}, set(), [])
        )
        panel_api_healthy = True
        panel_online_total = len(online_emails)
        for node in (node_response.get("obj") or []):
            host = str(node.get("address") or "")
            existing = next((item for item in server_stats if str(item.get("host")) == host), None)
            node_online = int(node.get("onlineCount") or 0)
            node_online_total += node_online
            values = {
                "id": f"node-{node.get('id')}", "name": node.get("name") or host, "host": host,
                "is_active": int(node.get("status") == "online" and node.get("xrayState") == "running"),
                "clients_count": int(node.get("clientCount") or 0), "active_clients": node_online,
                "total_traffic_gb": 0, "managed_externally": True, "latency_ms": int(node.get("latencyMs") or 0),
                "cpu_pct": round(float(node.get("cpuPct") or 0), 1), "mem_pct": round(float(node.get("memPct") or 0), 1),
                "inbound_count": int(node.get("inboundCount") or 0), "telemetry_available": True,
                "xray_state": node.get("xrayState") or "unknown", "source": "3x-ui node telemetry",
                **NODE_INVENTORY.get(host, {}),
            }
            if existing:
                existing.update(values)
            else:
                server_stats.append(values)

        local_client_emails = set()
        for inbound in panel_inbounds:
            node_id = inbound.get("nodeId")
            stats = inbound.get("clientStats") or []
            if node_id in (None, 0, "", "0"):
                local_client_emails.update(str(item.get("email")) for item in stats if item.get("email"))
            inbound_health.append({
                "id": int(inbound.get("id") or 0),
                "name": inbound.get("remark") or inbound.get("tag") or "Inbound",
                "location": "Финляндия" if node_id not in (None, 0, "", "0") else "Германия",
                "protocol": str(inbound.get("protocol") or "").upper(),
                "port": int(inbound.get("port") or 0),
                "enabled": bool(inbound.get("enable", True)),
                "clients": len(stats),
                "online": None,
            })

        if master_row is not None:
            master_row.update({
                "is_active": 1,
                "active_clients": max(0, panel_online_total - node_online_total),
                "clients_count": len(local_client_emails),
                "telemetry_available": True,
                "inbound_count": sum(1 for item in inbound_health if item["location"] == "Германия"),
                "xray_state": "running",
                "source": "global online − node online",
            })
    except Exception:
        logger.exception("Не удалось получить телеметрию 3x-ui nodes")
    if not any(str(node.get("host")) == "195.226.92.37" for node in server_stats):
        server_stats.append({"id": "fi-external", "name": "Финляндия", "host": "195.226.92.37", "is_active": 0,
                             "clients_count": None, "active_clients": None, "total_traffic_gb": 0,
                             "managed_externally": True, "telemetry_available": False,
                             **NODE_INVENTORY["195.226.92.37"]})

    # Prefer fresh independent agent data for host resources. Panel telemetry
    # remains the source for clients/inbounds and a fallback if an agent is stale.
    try:
        with get_db() as conn:
            latest_agents = conn.execute("""
                SELECT s.* FROM server_health_samples s
                JOIN (
                  SELECT host, MAX(id) id FROM server_health_samples
                  WHERE source='agent' GROUP BY host
                ) latest ON latest.id=s.id
                WHERE s.sampled_at >= datetime('now','-3 minutes')
            """).fetchall()
        by_host = {str(row["host"]): dict(row) for row in latest_agents}
        for server in server_stats:
            agent = by_host.get(str(server.get("host") or ""))
            if not agent:
                server["agent_online"] = False
                continue
            server.update({
                "agent_online": True,
                "agent_last_seen": agent.get("sampled_at"),
                "latency_ms": agent.get("latency_ms"),
                "cpu_pct": agent.get("cpu_pct"),
                "cpu_steal_pct": agent.get("cpu_steal_pct"),
                "mem_pct": agent.get("mem_pct"),
                "load_1m": agent.get("load_1m"),
                "disk_used_pct": agent.get("disk_used_pct"),
                "net_rx_bps": agent.get("net_rx_bps"),
                "net_tx_bps": agent.get("net_tx_bps"),
                "tcp_established": agent.get("tcp_established"),
                "uptime_seconds": agent.get("uptime_seconds"),
                "xui_active": bool(agent.get("xui_active")),
                "hysteria_active": bool(agent.get("hysteria_active")),
                "boot_id": agent.get("boot_id"),
                "packet_loss_pct": agent.get("packet_loss_pct"),
                "jitter_ms": agent.get("jitter_ms"),
                "dns_ms": agent.get("dns_ms"),
                "https_ms": agent.get("https_ms"),
                "download_mbps": agent.get("download_mbps"),
                "probed_at": agent.get("probed_at"),
            })
    except sqlite3.Error:
        logger.exception("Admin latest node-agent metrics failed")

    # Keep a bounded history for provider comparison and incident analysis.
    # Observability is best-effort and must never break the admin overview.
    health_history = {}
    try:
        with get_db() as conn:
            for server in server_stats:
                host = str(server.get("host") or "")
                if not host:
                    continue
                telemetry = server.get("telemetry_available") is not False
                xray_state = str(server.get("xray_state") or "unknown")
                is_up = bool(server.get("is_active")) and xray_state in {"running", "unknown"}
                state = "healthy" if telemetry and is_up else ("degraded" if is_up else "offline")
                server["health_state"] = state
                server_id = server.get("id") if isinstance(server.get("id"), int) else None
                conn.execute("""
                    INSERT INTO server_health_samples(
                      server_id,host,state,online_count,clients_count,latency_ms,
                      cpu_pct,mem_pct,inbound_count,xray_state,telemetry_available,source
                    )
                    SELECT ?,?,?,?,?,?,?,?,?,?,?,'panel'
                    WHERE NOT EXISTS (
                      SELECT 1 FROM server_health_samples
                      WHERE host=? AND sampled_at >= datetime('now','-1 minute')
                    )
                """, (
                    server_id, host, state, server.get("active_clients"), server.get("clients_count"),
                    server.get("latency_ms"), server.get("cpu_pct"), server.get("mem_pct"),
                    server.get("inbound_count"), xray_state, int(telemetry), host,
                ))
                if server_id is not None:
                    conn.execute("UPDATE servers SET lifecycle_state=? WHERE id=?", (state, server_id))
            conn.execute("DELETE FROM server_health_samples WHERE sampled_at < datetime('now','-30 days')")
            rows = conn.execute("""
                SELECT host, COUNT(*) samples,
                       ROUND(AVG(latency_ms),1) avg_latency_ms,
                       ROUND(MAX(latency_ms),1) max_latency_ms,
                       ROUND(AVG(cpu_pct),1) avg_cpu_pct,
                       ROUND(MAX(cpu_pct),1) max_cpu_pct,
                       ROUND(AVG(mem_pct),1) avg_mem_pct,
                       ROUND(AVG(packet_loss_pct),2) avg_packet_loss_pct,
                       ROUND(AVG(jitter_ms),1) avg_jitter_ms,
                       ROUND(AVG(dns_ms),1) avg_dns_ms,
                       ROUND(AVG(https_ms),1) avg_https_ms,
                       ROUND(AVG(download_mbps),1) avg_download_mbps,
                       SUM(CASE WHEN state='healthy' THEN 1 ELSE 0 END) healthy_samples
                FROM server_health_samples
                WHERE sampled_at >= datetime('now','-24 hours')
                  AND source='agent'
                GROUP BY host
            """).fetchall()
            for row in rows:
                item = dict(row)
                count = max(1, int(item.get("samples") or 0))
                item["availability_pct"] = round(int(item.get("healthy_samples") or 0) / count * 100, 2)
                health_history[str(item["host"])] = item
    except sqlite3.Error:
        logger.exception("Admin health history persistence failed")

    def _service_active(service: str) -> bool:
        try:
            return subprocess.run(
                ["systemctl", "is-active", "--quiet", service], timeout=3, check=False
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    guard_state = {}
    try:
        with open("/run/arcvpn-xui-health-state.json", "r", encoding="utf-8") as stream:
            guard_state = json.load(stream)
    except (OSError, ValueError):
        pass

    disk = shutil.disk_usage("/")
    db_integrity = "unknown"
    try:
        with get_db() as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
            db_integrity = str(row[0] if row else "unknown")
    except Exception:
        logger.exception("Admin health: database quick_check failed")

    remnawave = {"healthy": False, "users": 0, "nodes": [], "online_users": [], "detail": "not configured"}
    try:
        remna_env: Dict[str, str] = {}
        env_path = os.path.join(os.path.dirname(__file__), ".env.remnawave-staging")
        with open(env_path, "r", encoding="utf-8") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                remna_env[key.strip()] = value.strip()

        async def _remnawave_telemetry():
            client = RemnawaveClient({
                "panel_api_url": remna_env.get("REMNAWAVE_PANEL_URL", ""),
                "panel_api_token": remna_env.get("REMNAWAVE_API_TOKEN", ""),
            })
            try:
                nodes = await client._request("GET", "/api/nodes")
                users = await client._request("GET", "/api/users", params={"start": 0, "size": 500})
                return nodes, users
            finally:
                await client.close()

        remna_nodes, remna_users = ASYNC_EXECUTOR.run(_remnawave_telemetry(), timeout=12)
        node_names = {
            str(node.get("uuid")): node.get("name") or node.get("address") or "RemnaNode"
            for node in (remna_nodes or [])
        }
        online_cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
        online_users = []
        for user in (remna_users or {}).get("users", []):
            traffic = user.get("userTraffic") or {}
            raw_online_at = traffic.get("onlineAt")
            if not raw_online_at:
                continue
            try:
                online_at = datetime.fromisoformat(str(raw_online_at).replace("Z", "+00:00"))
            except ValueError:
                continue
            if online_at < online_cutoff:
                continue
            node_uuid = str(traffic.get("lastConnectedNodeUuid") or "")
            online_users.append({
                "username": user.get("username"),
                "telegram_id": user.get("telegramId"),
                "online_at": raw_online_at,
                "node_uuid": node_uuid or None,
                "node_name": node_names.get(node_uuid, "Узел не определён"),
            })
        latest_diagnostics = {}
        with get_db() as conn:
            rows = conn.execute("""
                SELECT d.host,d.result_json,d.ok,d.created_at
                FROM node_diagnostic_runs d
                JOIN (SELECT host,MAX(id) id FROM node_diagnostic_runs GROUP BY host) latest ON latest.id=d.id
            """).fetchall()
            for row in rows:
                try:
                    item = json.loads(row["result_json"] or "{}")
                except (TypeError, ValueError):
                    item = {}
                item.update({"ok": bool(row["ok"]), "created_at": row["created_at"]})
                latest_diagnostics[str(row["host"])] = item
        remnawave = {
            "healthy": True,
            "users": int((remna_users or {}).get("total") or 0),
            "online_users": sorted(online_users, key=lambda item: item["online_at"], reverse=True),
            "detail": "connected",
            "nodes": [{
                "uuid": node.get("uuid"),
                "name": node.get("name") or node.get("address") or "RemnaNode",
                "address": node.get("address"),
                "country_code": node.get("countryCode"),
                "connected": bool(node.get("isConnected")),
                "disabled": bool(node.get("isDisabled")),
                "users_online": int(node.get("usersOnline") or 0),
                "traffic_used_gb": round(int(node.get("trafficUsedBytes") or 0) / 1024 ** 3, 2),
                "xray_uptime_seconds": int(node.get("xrayUptime") or 0),
                "memory_used_pct": round(
                    int(((node.get("system") or {}).get("stats") or {}).get("memoryUsed") or 0)
                    / max(1, int(((node.get("system") or {}).get("info") or {}).get("memoryTotal") or 0)) * 100,
                    1,
                ),
                "load_1m": (((node.get("system") or {}).get("stats") or {}).get("loadAvg") or [None])[0],
                "rx_bps": int(((((node.get("system") or {}).get("stats") or {}).get("interface") or {}).get("rxBytesPerSec")) or 0),
                "tx_bps": int(((((node.get("system") or {}).get("stats") or {}).get("interface") or {}).get("txBytesPerSec")) or 0),
                "diagnostic": latest_diagnostics.get(str(node.get("address") or "")),
                "inbounds": [{
                    "tag": inbound.get("tag"),
                    "type": inbound.get("type"),
                    "network": inbound.get("network"),
                    "port": inbound.get("port"),
                } for inbound in ((node.get("configProfile") or {}).get("activeInbounds") or [])],
            } for node in (remna_nodes or [])],
        }
    except Exception as exc:
        remnawave["detail"] = type(exc).__name__
        logger.exception("Admin Remnawave telemetry failed")

    # Remnawave is authoritative for current presence after the panel cutover.
    # Merge it into the business user rows so the "Online" filter shows real
    # people and their last node instead of stale XUI counters.
    remna_online_by_tg = {
        str(item.get("telegram_id")): item
        for item in remnawave.get("online_users", [])
        if item.get("telegram_id") is not None
    }
    for user in recent_users:
        presence = remna_online_by_tg.get(str(user.get("telegram_id")))
        user["online_devices"] = 1 if presence else 0
        if presence:
            user["last_online_at"] = presence.get("online_at")
            user["online_node"] = presence.get("node_name")

    return _api_no_store(jsonify({
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "users": get_new_users_stats(),
        "subscriptions": get_subscriptions_stats(),
        "revenue": get_revenue_stats(),
        "conversion": get_conversion_stats(),
        "activity": get_usage_activity_stats(),
        "servers": server_stats,
        "server_health_24h": health_history,
        "operations": {
            "open_support_threads": int(support_open),
            "pending_payments": int(pending_payments),
            "panel_api_healthy": panel_api_healthy,
            "panel_online_total": panel_online_total,
            "xui_service": _service_active("x-ui.service"),
            "bot_service": _service_active("arcvpn-bot.service"),
            "subscription_service": _service_active("arcvpn-subscription.service"),
            "hysteria_service": _service_active("arcvpn-hysteria.service"),
            "guard": guard_state,
        },
        "device_security": device_security,
        "system": {
            "disk_total_gb": round(disk.total / 1024 ** 3, 1),
            "disk_used_gb": round(disk.used / 1024 ** 3, 1),
            "disk_used_pct": round(disk.used / max(1, disk.total) * 100, 1),
            "database_integrity": db_integrity,
        },
        "inbounds": inbound_health,
        "recent_users": recent_users,
        "recent_payments": recent_payments,
        "financials": financials,
        "remnawave": remnawave,
        "recurring": {
            **get_recurring_summary(),
            "provider_ready": bool(get_setting("yookassa_recurring_enabled", "0") == "1"),
        },
        "local_panel": local_panel,
    }))


@app.route('/api/admin/support/threads', methods=['GET'])
def api_admin_support_threads():
    if not _admin_authorized():
        return _api_error("admin_unauthorized", 403)
    with get_db() as conn:
        rows = conn.execute("""SELECT t.id,t.status,t.updated_at,u.telegram_id,u.username,u.first_name,
            (SELECT body FROM support_messages m WHERE m.thread_id=t.id ORDER BY m.id DESC LIMIT 1) last_message,
            (SELECT COUNT(*) FROM support_messages m WHERE m.thread_id=t.id AND m.sender='user' AND m.read_at IS NULL) unread
            FROM support_threads t JOIN users u ON u.id=t.user_id
            ORDER BY CASE WHEN t.status='open' THEN 0 ELSE 1 END,t.updated_at DESC LIMIT 100""").fetchall()
    return _api_no_store(jsonify({"ok": True, "threads": [dict(row) for row in rows]}))


@app.route('/api/admin/support/threads/<int:thread_id>', methods=['GET', 'POST'])
def api_admin_support_thread(thread_id: int):
    if not _admin_authorized():
        return _api_error("admin_unauthorized", 403)
    thread = get_support_thread(thread_id)
    if not thread:
        return _api_error("thread_not_found", 404)
    if request.method == 'POST':
        body = str((request.get_json(silent=True) or {}).get('body') or '').strip()
        if not body or len(body) > 4000:
            return _api_error("invalid_message", 400)
        message = add_admin_support_message(thread_id, 0, body)
        token = getattr(config, 'BOT_TOKEN', '')
        if token:
            try:
                encoded = urllib.parse.urlencode({"chat_id": thread["telegram_id"], "text": f"💬 Поддержка ArcVPN\n\n{body}"}).encode()
                urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=encoded, timeout=8).read()
            except Exception:
                logger.exception("Не удалось отправить ответ поддержки thread=%s", thread_id)
        return _api_no_store(jsonify({"ok": True, "message": message}))
    with get_db() as conn:
        rows = conn.execute("SELECT id,sender,body,created_at,read_at FROM support_messages WHERE thread_id=? ORDER BY id", (thread_id,)).fetchall()
        conn.execute("UPDATE support_messages SET read_at=CURRENT_TIMESTAMP WHERE thread_id=? AND sender='user' AND read_at IS NULL", (thread_id,))
    return _api_no_store(jsonify({"ok": True, "thread": thread, "messages": [dict(row) for row in rows]}))


@app.route('/legal/user-agreement')
def user_agreement():
    response = Response(
        render_user_agreement(
            profile_title=PROFILE_TITLE.replace("✨", "").strip(),
            updated_date=LEGAL_LAST_UPDATED,
            support_url=_public_links()["support_url"],
            operator_name=LEGAL_OPERATOR_NAME,
            operator_inn=LEGAL_OPERATOR_INN,
            operator_registration=LEGAL_OPERATOR_REGISTRATION,
            operator_address=LEGAL_OPERATOR_ADDRESS,
            contact_email=LEGAL_CONTACT_EMAIL,
        ),
        mimetype="text/html",
    )
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route('/invite/<code>')
def referral_invite(code: str):
    """Fast, self-contained referral landing page on the ArcVPN domain."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", code or ""):
        return Response("Referral link not found", status=404, mimetype="text/plain")

    username = _get_bot_username()
    if not username:
        return Response("ArcVPN bot is temporarily unavailable", status=503, mimetype="text/plain")

    target = f"https://t.me/{username}?start=ref_{urllib.parse.quote(code, safe='')}"
    safe_target = html.escape(target, quote=True)
    page = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#050a12"><title>Приглашение в ArcVPN</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;font-family:Inter,system-ui,-apple-system,sans-serif}}
body{{min-height:100dvh;display:grid;place-items:center;padding:24px;color:#f5f9ff;background:#050a12;
background-image:radial-gradient(55% 65% at 0 100%,#174b7355,transparent 72%),radial-gradient(50% 60% at 100% 0,#58b9ed38,transparent 74%)}}
main{{width:min(100%,520px);padding:36px 28px;border:1px solid #b9ddf31a;border-radius:36px;background:#0a1320e8;
box-shadow:0 30px 90px #0008;text-align:center}}.logo{{width:64px;height:64px;display:grid;place-items:center;margin:auto;
border-radius:22px;background:linear-gradient(145deg,#bceaff,#65bff2);color:#06121d;font-weight:900;font-size:25px}}
h1{{margin:24px 0 12px;font-size:clamp(30px,7vw,46px);line-height:1.05;letter-spacing:-.045em}}
p{{margin:0 auto;color:#aebdca;font-size:16px;line-height:1.55}}.bonus{{color:#8ed5fa}}
a{{min-height:58px;display:flex;align-items:center;justify-content:center;margin-top:28px;border-radius:999px;
color:#06121d;background:linear-gradient(135deg,#bceaff,#69c1f2);font-weight:800;text-decoration:none}}
small{{display:block;margin-top:16px;color:#718296;line-height:1.45}}
</style></head><body><main><div class="logo">A</div><h1>ArcVPN уже ждёт</h1>
<p>Перейдите по приглашению и подключите VPN. Пригласивший получит <b class="bonus">+5 дней</b>, а после первой покупки вы оба получите <b class="bonus">по 15 дней</b>.</p>
<a href="{safe_target}">Продолжить в Telegram</a><small>Ссылка откроет официального бота ArcVPN и сохранит приглашение.</small>
</main></body></html>"""
    response = Response(page, mimetype="text/html")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=86400"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


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


@app.route('/admin')
@app.route('/admin/')
@app.route('/admin/<path:path>')
def admin_webapp(path: str = ""):
    """Serve the signed SPA bundle; the client selects the admin console."""
    return webapp(path)


if __name__ == '__main__':
    # Запуск сервера на внутреннем порту 8080
    # Nginx проксирует с порта 2053 на 8080
    #
    # threaded=True — обрабатываем запросы параллельно (кэши и AsyncExecutor
    # потокобезопасны). Для продакшена предпочтителен gunicorn с потоками,
    # например: gunicorn -w 1 --threads 8 -b 127.0.0.1:8080 subscription_api:app
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)
