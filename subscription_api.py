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
# Используется для split-tunneling в Happ клиенте.
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
    "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
    "RemoteDNSIP": "1.1.1.1",
    "DomesticDNSType": "DoH",
    "DomesticDNSDomain": "https://dns.google/dns-query",
    "DomesticDNSIP": "8.8.8.8",
    "Geoipurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat",
    "Geositeurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
    "DnsHosts": {
        "cloudflare-dns.com": "1.1.1.1",
        "dns.google": "8.8.8.8"
    },
    "DirectSites": [
        "geosite:category-ru",  # Все российские сайты из базы
        "geosite:yandex",       # Все сервисы Яндекса
        "geosite:vk",           # VK и связанные сервисы
    ] + [f"domain:{domain}" for domain in DIRECT_DOMAIN_RULES],  # Добавляем наш список
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
    "BlockSites": [
        "geosite:category-ads-all",  # Блокировка рекламы (опционально)
    ],
    "BlockIp": [],
    "DomainStrategy": "IPIfNonMatch",
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
        VPN ключ в формате vless:// (plain text или base64)
    """
    from flask import request
    
    try:
        # Логируем User-Agent для отладки Happ
        user_agent = request.headers.get('User-Agent', 'Unknown')
        logger.info(f"Запрос subscription для sub_id={sub_id}, User-Agent: {user_agent}")
        
        # Получаем формат из query параметров
        # По умолчанию base64 для совместимости
        output_format = request.args.get('format', 'base64').lower()
        
        # Находим ключ по sub_id
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT 
                    vk.id, vk.client_uuid, vk.panel_email, vk.server_id,
                    vk.panel_inbound_id, vk.expires_at, vk.traffic_limit, vk.traffic_used,
                    s.host, s.port, s.protocol, s.name as server_name,
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
        
        # Генерируем ссылку для ключа
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            link = loop.run_until_complete(generate_key_link(key))
        finally:
            loop.close()
        
        if not link:
            logger.error(f"Не удалось сгенерировать ссылку для sub_id={sub_id}")
            return Response("Failed to generate key", status=500, mimetype='text/plain')
        
        if output_format == 'json':
            # JSON формат для Happ (Sing-box format)
            import json
            
            # Парсим VLESS ссылку
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)
            subscription_host = urllib.parse.urlparse(SUBSCRIPTION_URL).hostname or "arcc.mooo.com"
            
            # Формируем конфиг в формате Sing-box с routing rules
            # 1) Локальные важные домены -> direct
            # 2) Домен подписки -> direct (чтобы обновление профиля не ломалось)
            # 3) Локальные/private подсети -> direct
            # 4) Все остальное -> proxy (final)
            json_data = {
                "outbounds": [
                    {
                        "type": "vless",
                        "tag": key.get('tariff_name', 'ArcVPN'),
                        "server": parsed.hostname,
                        "server_port": parsed.port or 443,
                        "uuid": parsed.username,
                        "flow": params.get('flow', [''])[0] or "",
                        "tls": {
                            "enabled": True,
                            "server_name": params.get('sni', [''])[0] or parsed.hostname,
                            "utls": {
                                "enabled": True,
                                "fingerprint": params.get('fp', ['chrome'])[0]
                            },
                            "reality": {
                                "enabled": True,
                                "public_key": params.get('pbk', [''])[0],
                                "short_id": params.get('sid', [''])[0]
                            }
                        }
                    },
                    {
                        "type": "direct",
                        "tag": "direct"
                    }
                ],
                "route": {
                    "rules": [
                        {
                            "domain": DIRECT_DOMAIN_RULES,
                            "outbound": "direct"
                        },
                        {
                            "domain": [subscription_host],
                            "outbound": "direct"
                        },
                        {
                            "ip_cidr": [
                                "10.0.0.0/8",
                                "172.16.0.0/12",
                                "192.168.0.0/16",
                                "169.254.0.0/16",
                                "224.0.0.0/4",
                                "255.255.255.255/32"
                            ],
                            "outbound": "direct"
                        }
                    ],
                    "final": key.get('tariff_name', 'ArcVPN')
                }
            }
            
            subscription_data = json.dumps(json_data, ensure_ascii=False, indent=2)
            logger.info(f"✅ Сгенерирована JSON подписка для sub_id={sub_id}")
            
            response = Response(subscription_data)
            response.headers['Content-Type'] = 'application/json'
            response.headers['profile-update-interval'] = '24'
            response.headers['Content-Disposition'] = 'inline'
            response.headers['Cache-Control'] = 'no-cache'
            return response
        
        # ============================================================================
        # ГЕНЕРАЦИЯ ROUTING ПРОФИЛЯ ДЛЯ HAPP
        # ============================================================================
        
        routing_link = None
        
        # Проверяем, включен ли split-tunneling в конфигурации
        if ENABLE_SPLIT_TUNNELING:
            # Создаём routing профиль для автоматического обхода российских сайтов
            import json
            routing_profile_json = json.dumps(HAPP_ROUTING_PROFILE, ensure_ascii=False)
            routing_profile_base64 = base64.b64encode(routing_profile_json.encode()).decode()
            
            # Формируем ссылку для автоматической активации профиля в Happ
            # happ://routing/onadd/ - автоматически активирует профиль при импорте
            routing_link = f"happ://routing/onadd/{routing_profile_base64}"
            
            logger.info(f"🔀 Создан routing профиль для Happ: {len(HAPP_ROUTING_PROFILE['DirectSites'])} правил DirectSites")
        
        # ВАЖНО: Happ лучше работает с plain text форматом для routing
        # Формируем plain text версию с routing ссылкой
        if routing_link:
            plain_text_subscription = (
                f"#profile-title: base64:QXJjVlBO\n"
                f"#profile-update-interval: 24\n"
                f"{routing_link}\n"
                f"{link}\n"
            )
        else:
            plain_text_subscription = (
                f"#profile-title: base64:QXJjVlBO\n"
                f"#profile-update-interval: 24\n"
                f"{link}\n"
            )
        
        # Кодируем в base64 если запрошен этот формат
        if output_format == 'base64':
            subscription_data = base64.b64encode(plain_text_subscription.encode()).decode()
        else:
            subscription_data = plain_text_subscription
        
        logger.info(f"✅ Сгенерирована подписка для sub_id={sub_id}, длина: {len(subscription_data)} байт, format: {output_format}, split-tunneling: {ENABLE_SPLIT_TUNNELING}")
        
        # Создаём Response с правильными заголовками для Happ
        response = Response(subscription_data)
        
        # Happ требует application/octet-stream для подписок
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['profile-update-interval'] = '24'
        
        # ВАЖНО: Добавляем HTTP-заголовок routing для автоматической активации профиля
        # Happ автоматически импортирует профиль при получении этого заголовка
        if routing_link:
            response.headers['routing'] = routing_link
        
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
    
    # HTML страница с кнопкой в стиле monopo saigon
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArcVPN — Импорт подписки</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Raleway:wght@400&display=swap" rel="stylesheet">
    <style>
        :root {{
            --color-midnight-canvas: #000000;
            --color-frost-white: #ffffff;
            --color-whisper-gray: #6d6d6d;
            --color-misty-gray: #636363;
            --gradient-deep-ocean: linear-gradient(90deg, rgb(160, 224, 171), rgb(255, 172, 46) 50%, rgb(165, 45, 37));
            --font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, system-ui, sans-serif;
            --font-heading: 'Raleway', serif;
            --radius-buttons: 75.024px;
            --spacing-unit: 4px;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: var(--font-primary);
            background: var(--gradient-deep-ocean);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: var(--color-frost-white);
            position: relative;
            overflow: hidden;
        }}
        
        /* Animated gradient background */
        body::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: var(--gradient-deep-ocean);
            animation: gradientShift 15s ease infinite;
            z-index: 0;
        }}
        
        @keyframes gradientShift {{
            0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
            33% {{ transform: translate(5%, 5%) rotate(120deg); }}
            66% {{ transform: translate(-5%, 5%) rotate(240deg); }}
        }}
        
        .container {{
            position: relative;
            z-index: 1;
            max-width: 480px;
            width: 100%;
            text-align: center;
        }}
        
        .card {{
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 48px 34px;
        }}
        
        .logo {{
            font-size: 64px;
            margin-bottom: 24px;
            filter: drop-shadow(0 4px 12px rgba(255, 255, 255, 0.2));
        }}
        
        h1 {{
            font-family: var(--font-heading);
            font-size: 54px;
            font-weight: 400;
            line-height: 1.39;
            color: var(--color-frost-white);
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }}
        
        .status {{
            font-size: 16px;
            line-height: 1.25;
            color: rgb(160, 224, 171);
            margin-bottom: 28px;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        
        .status::before {{
            content: '● ';
            color: rgb(160, 224, 171);
        }}
        
        .subtitle {{
            font-size: 16px;
            line-height: 1.25;
            color: var(--color-whisper-gray);
            margin-bottom: 40px;
        }}
        
        .btn {{
            display: block;
            width: 100%;
            padding: 16px 34px;
            border-radius: var(--radius-buttons);
            font-size: 16px;
            line-height: 1.25;
            font-weight: 400;
            text-decoration: none;
            margin-bottom: 14px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            cursor: pointer;
            font-family: var(--font-primary);
        }}
        
        .btn-primary {{
            background: rgba(255, 255, 255, 0.95);
            color: var(--color-midnight-canvas);
            border-color: var(--color-frost-white);
        }}
        
        .btn-primary:hover {{
            background: var(--color-frost-white);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(255, 255, 255, 0.2);
        }}
        
        .btn-secondary {{
            background: rgba(55, 55, 55, 0.78);
            color: var(--color-frost-white);
            border-color: rgba(255, 255, 255, 0.3);
        }}
        
        .btn-secondary:hover {{
            background: rgba(55, 55, 55, 0.95);
            border-color: rgba(255, 255, 255, 0.5);
        }}
        
        .divider {{
            margin: 40px 0;
            height: 1px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
        }}
        
        .copy-section {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 28px;
        }}
        
        .copy-section p {{
            color: var(--color-whisper-gray);
            font-size: 14px;
            line-height: 1.25;
            margin-bottom: 14px;
        }}
        
        .url {{
            background: rgba(0, 0, 0, 0.5);
            color: rgb(160, 224, 171);
            padding: 12px 16px;
            border-radius: 10px;
            font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
            font-size: 11px;
            line-height: 1.58;
            word-break: break-all;
            margin-bottom: 14px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .success-message {{
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: rgba(160, 224, 171, 0.95);
            color: var(--color-midnight-canvas);
            padding: 16px 34px;
            border-radius: var(--radius-buttons);
            font-size: 16px;
            font-weight: 400;
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1000;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }}
        
        .success-message.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}
        
        @media (max-width: 640px) {{
            h1 {{
                font-size: 39px;
            }}
            
            .card {{
                padding: 34px 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="logo">🔐</div>
            <h1>ArcVPN</h1>
            <p class="status">Активна</p>
            <p class="subtitle">Нажмите кнопку для импорта подписки в Happ</p>
            
            <a href="{happ_deeplink}" class="btn btn-primary">Открыть в Happ</a>
            
            <div class="divider"></div>
            
            <div class="copy-section">
                <p>Или скопируйте ссылку вручную</p>
                <div class="url">{subscription_url}</div>
                <button onclick="copyUrl()" class="btn btn-secondary">Копировать ссылку</button>
            </div>
        </div>
    </div>
    
    <div class="success-message" id="successMessage">
        ✓ Ссылка скопирована
    </div>
    
    <script>
        function copyUrl() {{
            const successMsg = document.getElementById('successMessage');
            
            navigator.clipboard.writeText('{subscription_url}').then(() => {{
                showSuccess();
            }}).catch(() => {{
                // Fallback для старых браузеров
                const textarea = document.createElement('textarea');
                textarea.value = '{subscription_url}';
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showSuccess();
            }});
            
            function showSuccess() {{
                successMsg.classList.add('show');
                setTimeout(() => {{
                    successMsg.classList.remove('show');
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
