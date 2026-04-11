"""
Фасад для работы с API VPN-панелей.
"""
import logging
from typing import Optional, Dict, Any, List
import asyncio

from .panels.base import VPNAPIError, BaseVPNClient
from .panels.xui import XUIClient
from .panels.marzban import MarzbanClient

logger = logging.getLogger(__name__)

_clients: Dict[int, BaseVPNClient] = {}

def get_client_from_server_data(server: Dict[str, Any]) -> BaseVPNClient:
    """
    Создает или возвращает экземпляр клиента для API панели.
    """
    server_id = server['id']
    if server_id in _clients:
        return _clients[server_id]
        
    pass_type = server.get('panel_type', 'xui')
    if pass_type == 'marzban':
        client = MarzbanClient(server)
    else:
        client = XUIClient(server)
        
    _clients[server_id] = client
    return client

def invalidate_client_cache(server_id: int):
    """Инвалидирует сессию клиента."""
    if server_id in _clients:
        client = _clients[server_id]
        import asyncio
        asyncio.create_task(client.close())
        del _clients[server_id]
        logger.debug(f'Кэш клиента {server_id} очищен')

def format_traffic(bytes_count: int) -> str:
    """Форматирует байты в читабельный вид."""
    if bytes_count < 1024:
        return f'{bytes_count} B'
    elif bytes_count < 1024 ** 2:
        return f'{bytes_count / 1024:.1f} KB'
    elif bytes_count < 1024 ** 3:
        return f'{bytes_count / 1024 ** 2:.1f} MB'
    elif bytes_count < 1024 ** 4:
        return f'{bytes_count / 1024 ** 3:.2f} GB'
    else:
        return f'{bytes_count / 1024 ** 4:.2f} TB'

async def close_all_clients():
    """Закрывает все открытые сессии клиентов."""
    for client in list(_clients.values()):
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Ошибка при закрытии клиента: {e}")
    _clients.clear()

async def get_client(server_id: int) -> XUIClient:
    """
    Получает клиент для сервера по ID (из БД).
    
    Args:
        server_id: ID сервера в БД
        
    Returns:
        Экземпляр XUIClient
        
    Raises:
        ValueError: Если сервер не найден
    """
    from database.requests import get_server_by_id
    if server_id in _clients:
        return _clients[server_id]
    server = get_server_by_id(server_id)
    if not server:
        raise ValueError(f'Сервер с ID {server_id} не найден')
    return get_client_from_server_data(server)

async def test_server_connection(server_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверяет подключение к серверу.
    
    Args:
        server_data: Словарь с данными сервера
        
    Returns:
        Словарь с результатом:
        - success: True если подключение успешно
        - message: Сообщение о результате
        - stats: Статистика (если успешно)
    """
    client = XUIClient(server_data)
    try:
        await client.login()
        stats = await client.get_stats()
        return {'success': True, 'message': 'Подключение успешно!', 'stats': stats}
    except VPNAPIError as e:
        return {'success': False, 'message': f'Ошибка: {e}', 'stats': None}
    finally:
        await client.close()

async def reset_key_traffic_if_active(key_id: int) -> bool:
    """
    Сбрасывает израсходованный трафик ключа в панели 3X-UI,
    если сервер активен.
    
    Args:
        key_id: ID ключа (VPNKey.id)
        
    Returns:
        True при успешном сбросе, иначе False.
    """
    from database.requests import get_vpn_key_by_id
    key = get_vpn_key_by_id(key_id)
    if not key or not key.get('server_active'):
        return False
    server_data = {'id': key.get('server_id'), 'name': key.get('server_name'), 'host': key.get('host'), 'port': key.get('port'), 'web_base_path': key.get('web_base_path'), 'login': key.get('login'), 'password': key.get('password')}
    inbound_id = key.get('panel_inbound_id')
    email = key.get('panel_email')
    if not email:
        if key.get('username'):
            email = f"user_{key['username']}"
        else:
            email = f"user_{key['telegram_id']}"
    try:
        client = get_client_from_server_data(server_data)
        success = await client.reset_client_traffic(inbound_id, email)
        if success:
            logger.info(f'Трафик ключа {key_id} успешно сброшен при продлении.')
        return success
    except Exception as e:
        logger.error(f'Не удалось сбросить трафик ключа {key_id} при продлении: {e}')
        return False

async def extend_key_on_server(key_id: int, days: int) -> bool:
    """
    Продлевает срок действия ключа в панели 3X-UI, если сервер активен.
    
    Args:
        key_id: ID ключа (VPNKey.id)
        days: Количество дней для продления
        
    Returns:
        True при успешном продлении, иначе False.
    """
    from database.requests import get_vpn_key_by_id
    key = get_vpn_key_by_id(key_id)
    if not key or not key.get('server_active'):
        return False
    server_data = {'id': key.get('server_id'), 'name': key.get('server_name'), 'host': key.get('host'), 'port': key.get('port'), 'web_base_path': key.get('web_base_path'), 'login': key.get('login'), 'password': key.get('password')}
    inbound_id = key.get('panel_inbound_id')
    client_uuid = key.get('client_uuid')
    email = key.get('panel_email')
    if not email:
        email = f"user_{key.get('username') or key.get('telegram_id')}"
    try:
        client = get_client_from_server_data(server_data)
        success = await client.extend_client_expiry(inbound_id, client_uuid, email, days)
        if success:
            logger.info(f'Срок действия ключа {key_id} успешно продлен на сервере на {days} дней.')
        return success
    except Exception as e:
        logger.error(f'Не удалось продлить срок действия ключа {key_id} на сервере: {e}')
        return False


async def restore_key_traffic_limit(key_id: int) -> bool:
    """
    Восстанавливает полный лимит трафика тарифа на панели и обнуляет traffic_used в БД.
    Вызывается при продлении ключа (после reset_key_traffic_if_active).
    
    Делает 3 вещи:
    1. Получает лимит из тарифа ключа
    2. Обновляет totalGB на панели до полного лимита тарифа
    3. Обнуляет traffic_used и сбрасывает пороги уведомлений в БД
    
    Args:
        key_id: ID ключа
        
    Returns:
        True при успехе, False при ошибке
    """
    from database.requests import (
        get_vpn_key_by_id, get_tariff_by_id,
        reset_key_traffic_notification, update_key_traffic_limit
    )
    
    key = get_vpn_key_by_id(key_id)
    if not key:
        return False
    
    # Получаем лимит из тарифа
    tariff_id = key.get('tariff_id')
    traffic_limit = key.get('traffic_limit', 0) or 0
    
    if tariff_id:
        tariff = get_tariff_by_id(tariff_id)
        if tariff and (tariff.get('traffic_limit_gb', 0) or 0) > 0:
            traffic_limit = tariff['traffic_limit_gb'] * (1024**3)
    
    # Обнуляем traffic_used и сбрасываем пороги в БД
    reset_key_traffic_notification(key_id)
    
    # Обновляем traffic_limit в БД (на случай если тариф менялся)
    if traffic_limit > 0:
        update_key_traffic_limit(key_id, traffic_limit)
    
    # Обновляем totalGB на панели
    if key.get('server_active') and key.get('panel_email') and traffic_limit > 0:
        try:
            server_data = {
                'id': key.get('server_id'), 'name': key.get('server_name'),
                'host': key.get('host'), 'port': key.get('port'),
                'web_base_path': key.get('web_base_path'),
                'login': key.get('login'), 'password': key.get('password')
            }
            client = get_client_from_server_data(server_data)
            await client.update_client_limit(
                inbound_id=key.get('panel_inbound_id'),
                client_uuid=key.get('client_uuid'),
                email=key.get('panel_email'),
                total_gb_bytes=traffic_limit
            )
            logger.info(f'Лимит ключа {key_id} восстановлен на панели: {traffic_limit / 1024**3:.1f} ГБ')
        except Exception as e:
            logger.error(f'Не удалось восстановить лимит ключа {key_id} на панели: {e}')
            return False
    
    return True


async def push_key_to_panel(key_id: int, reset_traffic: bool = False) -> bool:
    """
    Пушит данные ключа из нашей БД на панель 3X-UI.
    
    Единственная точка записи на панель. Все данные (expiryTime, totalGB)
    формируются из нашей БД, а не читаются с панели.
    
    Args:
        key_id: ID ключа в нашей БД
        reset_traffic: True = обнулить счётчики up/down на панели перед обновлением
        
    Returns:
        True при успешном обновлении, False при ошибке
    """
    from database.requests import get_vpn_key_by_id
    from datetime import datetime
    
    key = get_vpn_key_by_id(key_id)
    if not key or not key.get('server_active'):
        logger.warning(f'push_key_to_panel: ключ {key_id} не найден или сервер неактивен')
        return False
    
    email = key.get('panel_email')
    inbound_id = key.get('panel_inbound_id')
    client_uuid = key.get('client_uuid')
    
    if not email or not inbound_id or not client_uuid:
        logger.warning(f'push_key_to_panel: ключ {key_id} — неполные данные панели')
        return False
    
    # Конвертируем expires_at из БД → expiryTime (ms)
    expires_at = key.get('expires_at')
    if expires_at:
        from datetime import datetime, timedelta, timezone
        
        # Если есть 'Z', убираем/заменяем, парсим
        dt_str = str(expires_at).replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str)
        
        # Убеждаемся что tzinfo установлен (в БД время всегда UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        now_utc = datetime.now(timezone.utc)
        
        # Если срок больше 90000 дней (бессрочный)
        if dt > now_utc + timedelta(days=90000):
            expiry_time_ms = 0
        else:
            expiry_time_ms = int(dt.timestamp() * 1000)
    else:
        expiry_time_ms = 0  # Бессрочный
    
    # Лимит трафика из БД (уже в байтах)
    traffic_limit = key.get('traffic_limit', 0) or 0
    
    try:
        server_data = {
            'id': key.get('server_id'),
            'name': key.get('server_name'),
            'host': key.get('host'),
            'port': key.get('port'),
            'web_base_path': key.get('web_base_path'),
            'login': key.get('login'),
            'password': key.get('password')
        }
        client = get_client_from_server_data(server_data)
        
        # Сброс счётчиков up/down на панели (если требуется)
        if reset_traffic:
            await client.reset_client_traffic(inbound_id, email)
            logger.info(f'Сброшены счётчики трафика ключа {key_id} на панели')
        
        # Обновляем ВСЕ данные клиента на панели из нашей БД
        success = await client.update_client_full(
            inbound_id=inbound_id,
            client_uuid=client_uuid,
            email=email,
            expiry_time_ms=expiry_time_ms,
            total_gb_bytes=traffic_limit
        )
        
        if success:
            logger.info(f'Данные ключа {key_id} ({email}) успешно запушены на панель')
        return success
        
    except Exception as e:
        logger.error(f'Ошибка пуша ключа {key_id} на панель: {e}')
        return False


def restore_traffic_limit_in_db(key_id: int) -> bool:
    """
    Восстанавливает полный лимит трафика тарифа в нашей БД.
    НЕ обращается к панели! Панель обновляется через push_key_to_panel.
    
    Делает:
    1. Получает лимит из тарифа ключа
    2. Обновляет traffic_limit в БД
    3. Обнуляет traffic_used и сбрасывает пороги уведомлений
    
    Args:
        key_id: ID ключа
        
    Returns:
        True при успехе
    """
    from database.requests import (
        get_vpn_key_by_id, get_tariff_by_id,
        reset_key_traffic_notification, update_key_traffic_limit
    )
    
    key = get_vpn_key_by_id(key_id)
    if not key:
        return False
    
    # Получаем лимит из тарифа
    tariff_id = key.get('tariff_id')
    traffic_limit = key.get('traffic_limit', 0) or 0
    
    if tariff_id:
        tariff = get_tariff_by_id(tariff_id)
        if tariff and (tariff.get('traffic_limit_gb', 0) or 0) > 0:
            traffic_limit = tariff['traffic_limit_gb'] * (1024**3)
    
    # Обнуляем traffic_used и пороги уведомлений
    reset_key_traffic_notification(key_id)
    
    # Обновляем traffic_limit (на случай если тариф менялся)
    if traffic_limit > 0:
        update_key_traffic_limit(key_id, traffic_limit)
    
    logger.info(f'Лимит трафика ключа {key_id} восстановлен в БД: {traffic_limit / 1024**3:.1f} ГБ')
    return True


__all__ = [
    "VPNAPIError", "get_client_from_server_data", "invalidate_client_cache",
    "format_traffic", "close_all_clients", "get_client", "test_server_connection",
    "reset_key_traffic_if_active", "extend_key_on_server", "restore_key_traffic_limit",
    "push_key_to_panel", "restore_traffic_limit_in_db"
]
