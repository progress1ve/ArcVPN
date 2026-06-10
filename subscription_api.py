#!/usr/bin/env python3
"""
Subscription API для VPN бота.

Возвращает base64-encoded список VPN ключей пользователя.
Клиенты VPN подключаются по ссылке и автоматически получают обновления.
"""

import base64
import asyncio
import logging
import urllib.parse
from flask import Flask, Response
from database.connection import get_db
from bot.services.panels.xui import XUIClient
from bot.utils.key_generator import generate_link
from database.db_servers import get_server_by_id
from config import SUBSCRIPTION_URL, ENABLE_SPLIT_TUNNELING

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# ROUTING CONFIGURATION ДЛЯ HAPP
# ============================================================================

# Домены, которые должны идти напрямую (без VPN) для российских пользователей.
# ВАЖНО: Этот список используется только для документации и справки.
# В реальной конфигурации используются geosite правила (geosite:category-ru),
# которые уже содержат все эти домены и многие другие.
# Это сделано для уменьшения размера конфигурации и избежания ошибки
# "Лимит памяти туннеля превышен (50 МБ)" в XrayCore.
DIRECT_DOMAIN_RULES = [
    # === МАРКЕТПЛЕЙСЫ ===
    "ozon.ru",
    "ozon.travel",
    "wildberries.ru",
    "wb.ru",
    "market.yandex.ru",
    "sbermegamarket.ru",
    "megamarket.ru",
    "goods.ru",
    "avito.ru",
    "youla.ru",
    "aliexpress.ru",
    
    # === СТРИМИНГ И МЕДИА ===
    "kinopoisk.ru",
    "okko.tv",
    "more.tv",
    "ivi.ru",
    "premier.one",
    "start.ru",
    "wink.ru",
    "kion.ru",
    "smotrim.ru",
    "rutube.ru",
    
    # === СОЦСЕТИ И МЕССЕНДЖЕРЫ ===
    "vk.com",
    "vk.ru",
    "ok.ru",
    "mail.ru",
    "dzen.ru",
    "vk-portal.net",
    "vkvideo.ru",
    "vkuser.net",
    "okcdn.ru",
    "vk-analytics.ru",
    "max.ru",
    "web.max.ru",
    
    # === ЯНДЕКС СЕРВИСЫ ===
    "yandex.ru",
    "ya.ru",
    "yandex.net",
    "yandex.com",
    "yandex.by",
    "yandex.kz",
    "yandex.ua",
    
    # === БАНКИ ===
    "sberbank.ru",
    "sber.ru",
    "alfabank.ru",
    "tbank.ru",
    "tinkoff.ru",
    "vtb.ru",
    "psbank.ru",
    "gazprombank.ru",
    "rosbank.ru",
    "unicredit.ru",
    "banki.ru",
    "raiffeisen.ru",
    "homecredit.ru",
    "sovcombank.ru",
    "mironline.ru",
    "nspk.ru",
    
    # === ДОСТАВКА И ЛОГИСТИКА ===
    "sdek.ru",
    "sdek.shopping",
    "pochta.ru",
    "cdek.ru",
    "cdek.shopping",
    "boxberry.ru",
    "pickpoint.ru",
    "dpd.ru",
    
    # === ОПЕРАТОРЫ СВЯЗИ ===
    "mts.ru",
    "beeline.ru",
    "megafon.ru",
    "tele2.ru",
    "yota.ru",
    "rt.ru",
    
    # === ГОСУСЛУГИ ===
    "gosuslugi.ru",
    "mos.ru",
    "nalog.gov.ru",
    "pfr.gov.ru",
    
    # === ПРОДУКТОВЫЕ РИТЕЙЛЕРЫ ===
    "vkusvill.ru",
    "5ka.ru",
    "magnit.ru",
    "perekrestok.ru",
    "auchan.ru",
    "spar.ru",
    "metro-cc.ru",
    "lenta.com",
    "dixy.ru",
    
    # === ДОСТАВКА ЕДЫ ===
    "samokat.ru",
    "delivery.ru",
    "yandex.eda",
    "chizhik.club",
    
    # === НЕДВИЖИМОСТЬ ===
    "cian.ru",
    "domclick.ru",
    "avito.ru",
    
    # === ДРУГИЕ ПОПУЛЯРНЫЕ СЕРВИСЫ ===
    "2gis.ru",
    "vkusnoitochka.ru",
    "petrovich.ru",
    "goldapple.ru",
    "dns.ru",
    "mvideo.ru",
    "eldorado.ru",
    "detmir.ru",
    "lamoda.ru",
    "sportmaster.ru",
    "leroy-merlin.ru",
    "obi.ru",
    "hh.ru",
    "superjob.ru",
    "rambler.ru",
    "trace-flow.ru",
    "ifconfig.me",
]

# Geo-правила для Happ (используют встроенные geosite/geoip базы)
# geosite:category-ru - все российские сайты из базы V2Ray
# geoip:ru - все российские IP-адреса
HAPP_ROUTING_PROFILE = {
    "Name": "ArcVPN - Обход РФ",
    "GlobalProxy": "true",
    "RemoteDNSType": "DoH",
    "RemoteDNSDomain": "https://1.1.1.1/dns-query",  # Cloudflare DoH (быстрее)
    "RemoteDNSIP": "1.1.1.1",
    "DomesticDNSType": "System",  # Используем системный DNS для российских сайтов (быстрее)
    "DomesticDNSDomain": "",
    "DomesticDNSIP": "",
    "Geoipurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat",
    "Geositeurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
    "DnsHosts": {
        "1.1.1.1": "1.1.1.1",
        "dns.google": "8.8.8.8"
    },
    "DirectSites": [
        "geosite:category-ru",  # Все российские сайты из базы (включает все домены из DIRECT_DOMAIN_RULES)
        "geosite:yandex",       # Все сервисы Яндекса
        "geosite:vk",           # VK и связанные сервисы
        "geosite:mailru",       # Mail.ru и связанные сервисы
    ],
    "DirectIp": [
        "geoip:ru",             # Все российские IP
        "geoip:private",        # Локальные сети
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "224.0.0.0/4",
        "255.255.255.255/32"
    ],
    "ProxySites": [],
    "ProxyIp": [],
    "BlockSites": [],  # Отключаем блокировку рекламы для уменьшения задержек
    "BlockIp": [],
    "DomainStrategy": "AsIs",  # Изменено с IPIfNonMatch на AsIs для уменьшения задержек DNS
    "FakeDNS": "false"
}


def get_user_active_keys(user_id: int) -> list:
    """
    Получает активные ключи пользователя из базы данных.
    
    Args:
        user_id: Telegram ID пользователя
        
    Returns:
        Список словарей с данными ключей
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id, vk.client_uuid, vk.panel_email, vk.server_id,
                vk.panel_inbound_id, vk.expires_at, vk.traffic_limit, vk.traffic_used,
                s.host, s.port, s.protocol, s.name as server_name,
                u.telegram_id,
                COALESCE(vk.custom_name, t.name) as tariff_name
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
        
        keys = []
        for row in cursor.fetchall():
            key_dict = dict(row)
            # Проверка трафика
            traffic_limit = key_dict.get('traffic_limit', 0) or 0
            traffic_used = key_dict.get('traffic_used', 0) or 0
            
            # Пропускаем ключи с исчерпанным трафиком
            if traffic_limit > 0 and traffic_used >= traffic_limit:
                continue
                
            keys.append(key_dict)
        
        return keys


async def generate_key_link(key: dict) -> str:
    """
    Генерирует VPN ссылку для ключа с красивым названием.
    
    Args:
        key: Словарь с данными ключа из БД
        
    Returns:
        VPN ссылка (vless://, vmess://, trojan://, ss://)
    """
    try:
        # Получаем сервер
        server = get_server_by_id(key['server_id'])
        if not server:
            logger.error(f"Сервер {key['server_id']} не найден")
            return ""
        
        # Создаём клиент для получения конфигурации
        client = XUIClient(server)
        
        # Получаем полную конфигурацию клиента
        config = await client.get_client_config(key['panel_email'])
        
        await client.close()
        
        if not config:
            logger.error(f"Не удалось получить конфигурацию для {key['panel_email']}")
            return ""
        
        # Формируем красивое название для ключа
        # Формат: ArcVPN - {название тарифа} ({название сервера})
        tariff_name = key.get('tariff_name', 'VPN')
        server_name = server.get('name', 'Server')
        
        # Обновляем remark в конфигурации
        config['remark'] = f"ArcVPN - {tariff_name} ({server_name})"
        
        logger.info(f"Генерация ключа: tariff_name={tariff_name}, server_name={server_name}, final_remark={config['remark']}")
        
        # Генерируем ссылку
        link = generate_link(config)
        return link
        
    except Exception as e:
        logger.error(f"Ошибка генерации ключа для {key.get('panel_email')}: {e}")
        return ""


def format_traffic(bytes_value: int) -> str:
    """
    Форматирует трафик в читаемый вид.
    
    Args:
        bytes_value: Трафик в байтах
        
    Returns:
        Строка вида "1.5GB" или "500MB"
    """
    if bytes_value >= 1024**3:  # GB
        return f"{bytes_value / 1024**3:.1f}GB"
    elif bytes_value >= 1024**2:  # MB
        return f"{bytes_value / 1024**2:.0f}MB"
    elif bytes_value >= 1024:  # KB
        return f"{bytes_value / 1024:.0f}KB"
    else:
        return f"{bytes_value}B"


def generate_info_block(key: dict) -> str:
    """
    Генерирует информационный блок для подписки.
    
    Args:
        key: Словарь с данными ключа
        
    Returns:
        Многострочный текст с информацией о подписке
    """
    from datetime import datetime, timezone
    
    # Трафик
    traffic_used = key.get('traffic_used', 0) or 0
    traffic_limit = key.get('traffic_limit', 0) or 0
    
    if traffic_limit > 0:
        used_str = format_traffic(traffic_used)
        limit_str = format_traffic(traffic_limit)
        traffic_line = f"{used_str} / {limit_str}"
    else:
        traffic_line = "Безлимит"
    
    # Дата истечения
    expires_at = key.get('expires_at')
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            expires_str = expires_dt.strftime('%d.%m.%Y')
            
            # Оставшееся время
            now = datetime.now(timezone.utc)
            delta = expires_dt - now
            if delta.total_seconds() > 0:
                days_left = max(0, delta.days)
                if delta.seconds > 0 and days_left == 0:
                    days_left = 0  # Меньше суток
            else:
                days_left = 0
        except:
            expires_str = "—"
            days_left = 0
    else:
        expires_str = "—"
        days_left = 0
    
    # Название тарифа
    tariff_name = key.get('tariff_name') or "Подписка"
    
    # Статус
    if expires_at and days_left > 0 and (traffic_limit == 0 or traffic_used < traffic_limit):
        status = "✅ Active"
    else:
        status = "🔴 Expired"
    
    # Формируем блок
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{traffic_line}          Истекает: {expires_str}",
        "",
        f"⏱ {days_left} дн | 📦 {tariff_name}",
        status,
        "",
        "❗ Не работает VPN? Жми кнопку - 🔄 обновить подписку",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    return "\n".join(lines)


def generate_best_server_config(user_uuid: str, current_server: dict, all_servers: list = None) -> str:
    """
    Генерирует конфигурацию "Лучший сервер" с автоматической балансировкой.
    Выбирает сервер с наименьшей нагрузкой (меньше всего онлайн пользователей).
    
    Args:
        user_uuid: UUID пользователя
        current_server: Текущий сервер пользователя (dict с host, pbk, sid и т.д.)
        all_servers: Список всех доступных серверов (опционально)
        
    Returns:
        JSON конфигурация в виде строки для Happ
    """
    import json
    
    # Если не передан список серверов, используем только текущий
    if not all_servers:
        all_servers = [current_server]
    
    # Создаем outbound'ы для каждого сервера
    outbounds = []
    
    for idx, server in enumerate(all_servers):
        server_address = server.get('host', server.get('address', 'unknown'))
        pbk = server.get('pbk', server.get('public_key', ''))
        sid = server.get('sid', server.get('short_id', ''))
        fp = server.get('fp', server.get('fingerprint', 'chrome'))
        sni = server.get('sni', server_address)
        flow = server.get('flow', 'xtls-rprx-vision')
        
        outbound = {
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": server_address,
                    "port": 443,
                    "users": [{
                        "encryption": "none",
                        "flow": flow,
                        "id": user_uuid
                    }]
                }]
            },
            "streamSettings": {
                "network": "tcp",
                "realitySettings": {
                    "fingerprint": fp,
                    "publicKey": pbk,
                    "serverName": sni,
                    "shortId": sid
                },
                "security": "reality",
                "tcpSettings": {}
            },
            "tag": f"proxy-{idx + 1}"
        }
        outbounds.append(outbound)
    
    # Добавляем direct и block outbound'ы
    outbounds.extend([
        {
            "protocol": "freedom",
            "tag": "direct"
        },
        {
            "protocol": "blackhole",
            "tag": "block"
        }
    ])
    
    # Создаем селектор для балансировщика (все proxy outbound'ы)
    proxy_tags = [f"proxy-{i + 1}" for i in range(len(all_servers))]
    
    # Базовая конфигурация с балансировкой
    config = {
        "burstObservatory": {
            "pingConfig": {
                "connectivity": "http://www.gstatic.com/generate_204",
                "destination": "",
                "httpMethod": "HEAD",
                "interval": "60s",
                "sampling": 10,
                "timeout": "5s"
            },
            "subjectSelector": proxy_tags  # Все proxy серверы участвуют в балансировке
        },
        "dns": {
            "queryStrategy": "UseIPv4",
            "servers": ["1.1.1.1", "1.0.0.1"]
        },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": 10808,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {
                    "destOverride": ["http", "tls", "quic"],
                    "enabled": True,
                    "routeOnly": False
                },
                "tag": "socks"
            },
            {
                "listen": "127.0.0.1",
                "port": 10809,
                "protocol": "http",
                "settings": {"allowTransparent": False},
                "sniffing": {
                    "destOverride": ["http", "tls", "quic"],
                    "enabled": True,
                    "routeOnly": False
                },
                "tag": "http"
            }
        ],
        "outbounds": outbounds,
        "remarks": "🚀 Лучший сервер",
        "routing": {
            "balancers": [
                {
                    "selector": proxy_tags,
                    "strategy": {
                        "type": "leastPing"  # Выбирает сервер с наименьшим пингом
                    },
                    "tag": "best_server_balancer"
                }
            ],
            "domainMatcher": "hybrid",
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "ip": ["1.1.1.1", "1.0.0.1"],
                    "outboundTag": "direct",
                    "port": 53,
                    "type": "field"
                },
                {
                    "domain": ["full:www.gstatic.com", "full:cp.cloudflare.com"],
                    "outboundTag": "direct",
                    "type": "field"
                },
                {
                    "ip": ["geoip:private"],
                    "outboundTag": "direct",
                    "type": "field"
                },
                {
                    "domain": ["geosite:private"],
                    "outboundTag": "direct",
                    "type": "field"
                },
                {
                    "outboundTag": "direct",
                    "protocol": ["bittorrent"],
                    "type": "field"
                },
                {
                    "domain": ["geosite:category-ru", "geosite:yandex", "geosite:vk", "geosite:mailru"],
                    "outboundTag": "direct",
                    "type": "field"
                },
                {
                    "ip": ["geoip:ru"],
                    "outboundTag": "direct",
                    "type": "field"
                },
                {
                    "balancerTag": "best_server_balancer",  # Используем балансировщик
                    "network": "tcp,udp",
                    "type": "field"
                }
            ]
        }
    }
    
    # Конвертируем в JSON и возвращаем
    return json.dumps(config, ensure_ascii=False, separators=(',', ':'))


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
        logger.info(f"Нет активных ключей для пользователя {user_id}")
        return ""
    
    # Генерируем ссылки для всех ключей
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    links = []
    for key in keys:
        try:
            link = loop.run_until_complete(generate_key_link(key))
            if link:
                links.append(link)
        except Exception as e:
            logger.error(f"Ошибка генерации ключа {key['id']}: {e}")
    
    loop.close()
    
    if not links:
        logger.warning(f"Не удалось сгенерировать ни одного ключа для пользователя {user_id}")
        return ""
    
    # Объединяем ключи через перенос строки
    keys_text = "\n".join(links)
    
    # Кодируем в base64 если нужно
    if encode_base64:
        encoded = base64.b64encode(keys_text.encode()).decode()
        logger.info(f"Сгенерирована подписка для пользователя {user_id}: {len(links)} ключей (base64)")
        return encoded
    else:
        logger.info(f"Сгенерирована подписка для пользователя {user_id}: {len(links)} ключей (plain text)")
        return keys_text


@app.route('/sub/<sub_id>')
def subscription(sub_id: str):
    """
    Endpoint для получения subscription по уникальному sub_id ключа.
    
    Args:
        sub_id: Уникальный идентификатор подписки (sub_id из vpn_keys)
        
    Query параметры:
        format: 'base64' (по умолчанию) или 'plain' (без кодирования)
        
    Returns:
        VPN ключи с информационным блоком (plain text или base64)
    """
    from flask import request
    
    try:
        # Логируем User-Agent для отладки Happ
        user_agent = request.headers.get('User-Agent', 'Unknown')
        logger.info(f"Запрос subscription для sub_id={sub_id}, User-Agent: {user_agent}")
        
        # Получаем формат из query параметров
        output_format = request.args.get('format', 'base64').lower()
        
        # Находим ключ по sub_id
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT 
                    vk.id, vk.client_uuid, vk.panel_email, vk.server_id,
                    vk.panel_inbound_id, vk.expires_at, vk.traffic_limit, vk.traffic_used,
                    s.host, s.port, s.protocol, s.name as server_name,
                    u.telegram_id,
                    COALESCE(vk.custom_name, t.name, 'Подписка') as tariff_name
                FROM vpn_keys vk
                JOIN servers s ON vk.server_id = s.id
                JOIN users u ON vk.user_id = u.id
                LEFT JOIN tariffs t ON vk.tariff_id = t.id
                WHERE vk.sub_id = ?
                AND vk.expires_at > datetime('now')
                AND vk.panel_email IS NOT NULL
                AND s.is_active = 1
            """, (sub_id,))
            
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Ключ не найден для sub_id={sub_id}")
                return Response("No active key found", status=404, mimetype='text/plain')
            
            key = dict(row)
            
            # Проверка трафика
            traffic_limit = key.get('traffic_limit', 0) or 0
            traffic_used = key.get('traffic_used', 0) or 0
            
            # Если трафик исчерпан
            if traffic_limit > 0 and traffic_used >= traffic_limit:
                logger.warning(f"Трафик исчерпан для sub_id={sub_id}")
                return Response("Traffic limit exceeded", status=404, mimetype='text/plain')
        
        # Генерируем стандартную VLESS ссылку
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            link = loop.run_until_complete(generate_key_link(key))
        finally:
            loop.close()
        
        if not link:
            logger.error(f"Не удалось сгенерировать ссылку для sub_id={sub_id}")
            return Response("Failed to generate key", status=500, mimetype='text/plain')
        
        # ============================================================================
        # ГЕНЕРАЦИЯ ROUTING ПРОФИЛЯ ДЛЯ HAPP
        # ============================================================================
        
        routing_link = None
        
        if ENABLE_SPLIT_TUNNELING:
            import json
            routing_profile_json = json.dumps(HAPP_ROUTING_PROFILE, ensure_ascii=False)
            routing_profile_base64 = base64.b64encode(routing_profile_json.encode()).decode()
            routing_link = f"happ://routing/onadd/{routing_profile_base64}"
            logger.info(f"� Создан routing профиль для Happ")
        
        # Формируем заголовок подписки
        profile_title = "ArcVPN"
        profile_title_base64 = base64.b64encode(profile_title.encode()).decode()
        
        # ЭКСПЕРИМЕНТ: Добавляем информационный блок ПРЯМО В ТЕКСТ (не в заголовок)
        # Генерируем информацию о подписке
        info_block = generate_info_block(key)
        
        # Формируем подписку
        if routing_link:
            plain_text_subscription = (
                f"#profile-title: base64:{profile_title_base64}\n"
                f"#profile-update-interval: 24\n"
                f"#support-url: https://t.me/Turan11627\n"
                f"#profile-web-page-url: https://t.me/arcvpn1\n"
                f"\n"
                f"{info_block}\n"
                f"\n"
                f"{routing_link}\n"
                f"{link}\n"
            )
        else:
            plain_text_subscription = (
                f"#profile-title: base64:{profile_title_base64}\n"
                f"#profile-update-interval: 24\n"
                f"#support-url: https://t.me/Turan11627\n"
                f"#profile-web-page-url: https://t.me/arcvpn1\n"
                f"\n"
                f"{info_block}\n"
                f"\n"
                f"{link}\n"
            )
        
        # Кодируем в base64 если запрошен этот формат
        if output_format == 'base64':
            subscription_data = base64.b64encode(plain_text_subscription.encode()).decode()
        else:
            subscription_data = plain_text_subscription
        
        logger.info(f"✅ Сгенерирована подписка для sub_id={sub_id}, длина: {len(subscription_data)} байт, format: {output_format}")
        
        # Создаём Response с правильными заголовками для Happ
        response = Response(subscription_data)
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['profile-update-interval'] = '24'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации подписки для sub_id={sub_id}: {e}", exc_info=True)
        return Response("Internal server error", status=500, mimetype='text/plain')


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
    from flask import request
    
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Если это Happ или другой VPN клиент — отдаём подписку
    if 'happ' in user_agent or 'v2ray' in user_agent or 'clash' in user_agent:
        subscription_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}?format=base64"
        from flask import redirect
        return redirect(subscription_url)
    
    # Для браузера — HTML страница с кнопкой импорта
    subscription_url = f"{SUBSCRIPTION_URL}/sub/{sub_id}"
    
    # Правильный формат Happ deeplink: happ://add/{URL}
    happ_deeplink = f"happ://add/{subscription_url}"
    
    # HTML страница с новым дизайном на основе референса
    html = f"""<!DOCTYPE html>
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
        <a href="{happ_deeplink}" class="btn btn-primary">Открыть в Happ</a>
        
        <p class="divider-text">Или скопируйте ссылку вручную</p>
        
        <!-- Кнопка копирования -->
        <button onclick="copyUrl()" class="btn btn-secondary">Копировать вручную</button>
    </div>
    
    <!-- Уведомление -->
    <div class="toast" id="toast">
        ✓ Ссылка скопирована
    </div>
    
    <script>
        function copyUrl() {{
            const url = '{subscription_url}';
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
    return Response(html, mimetype='text/html')


if __name__ == '__main__':
    # Запуск сервера на внутреннем порту 8080
    # Nginx проксирует с порта 2053 на 8080
    app.run(host='127.0.0.1', port=8080, debug=False)
