#!/usr/bin/env python3
"""
Subscription API для VPN бота.

Возвращает base64-encoded список VPN ключей пользователя.
Клиенты VPN подключаются по ссылке и автоматически получают обновления.
"""

import base64
import asyncio
import logging
from flask import Flask, Response
from database.connection import get_db
from bot.services.panels.xui import XUIClient
from bot.utils.key_generator import generate_link
from database.db_servers import get_server_by_id

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


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
        
        # Проверяем формат вывода
        if output_format == 'json':
            # JSON формат для Happ
            import json
            import urllib.parse
            
            # Парсим VLESS ссылку
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)
            
            json_data = {
                "version": 1,
                "rules": [],
                "servers": [{
                    "name": key.get('tariff_name', 'ArcVPN'),
                    "type": "vless",
                    "address": parsed.hostname,
                    "port": parsed.port or 443,
                    "uuid": parsed.username,
                    "flow": params.get('flow', [''])[0],
                    "encryption": params.get('encryption', ['none'])[0],
                    "security": params.get('security', [''])[0],
                    "sni": params.get('sni', [''])[0],
                    "fp": params.get('fp', [''])[0],
                    "pbk": params.get('pbk', [''])[0],
                    "sid": params.get('sid', [''])[0]
                }]
            }
            
            subscription_data = json.dumps(json_data, ensure_ascii=False, indent=2)
            logger.info(f"✅ Сгенерирована JSON подписка для sub_id={sub_id}")
            
            response = Response(subscription_data)
            response.headers['Content-Type'] = 'application/json'
            return response
        
        # Проверяем формат вывода
        if output_format == 'json':
            # JSON формат для Happ (Sing-box format)
            import json
            import urllib.parse
            
            # Парсим VLESS ссылку
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)
            
            # Формируем конфиг в формате Sing-box
            json_data = {
                "outbounds": [{
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
                }]
            }
            
            subscription_data = json.dumps(json_data, ensure_ascii=False, indent=2)
            logger.info(f"✅ Сгенерирована JSON подписка для sub_id={sub_id}")
            
            response = Response(subscription_data)
            response.headers['Content-Type'] = 'application/json'
            response.headers['profile-update-interval'] = '24'
            response.headers['Content-Disposition'] = 'inline'
            response.headers['Cache-Control'] = 'no-cache'
            return response
        
        # Кодируем в base64 если нужно
        if output_format == 'base64':
            # Для Happ - только чистый ключ без маркеров
            subscription_data = base64.b64encode(f"{link}\n".encode()).decode()
        else:
            # Plain text - только ключ
            subscription_data = f"{link}\n"
        
        logger.info(f"✅ Сгенерирована подписка для sub_id={sub_id}, длина: {len(subscription_data)} байт, format: {output_format}")
        
        # Создаём Response с правильными заголовками для Happ
        response = Response(subscription_data)
        
        # Для base64 используем text/plain или вообще без Content-Type
        if output_format == 'base64':
            # Happ ожидает text/plain для base64 подписок
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['profile-update-interval'] = '24'
            response.headers['subscription-userinfo'] = f'upload=0; download=0; total=107374182400; expire={int((key.get("expires_at") or 0))}'
        else:
            # Для plain text
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        
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


if __name__ == '__main__':
    # Запуск сервера на внутреннем порту 8080
    # Nginx проксирует с порта 2053 на 8080
    app.run(host='127.0.0.1', port=8080, debug=False)
