import sqlite3
import logging
import secrets
import string
import datetime
from typing import Optional, List, Dict, Any, Tuple
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'get_all_servers',
    'get_server_by_id',
    'get_active_servers',
    'add_server',
    'update_server',
    'update_server_field',
    'delete_server',
    'toggle_server_active',
]

def get_all_servers() -> List[Dict[str, Any]]:
    """
    Получает список всех VPN-серверов.
    
    Returns:
        Список словарей с данными серверов
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, host, port, web_base_path, login, password, is_active, protocol
            FROM servers
            ORDER BY id
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_server_by_id(server_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает сервер по ID.
    
    Args:
        server_id: ID сервера
        
    Returns:
        Словарь с данными сервера или None
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, host, port, web_base_path, login, password, is_active, protocol
            FROM servers
            WHERE id = ?
        """, (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_active_servers() -> List[Dict[str, Any]]:
    """
    Получает список активных VPN-серверов.
    
    Returns:
        Список словарей с данными активных серверов
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, host, port, web_base_path, login, password, is_active, protocol
            FROM servers
            WHERE is_active = 1
            ORDER BY id
        """)
        return [dict(row) for row in cursor.fetchall()]

def add_server(
    name: str,
    host: str,
    port: int,
    web_base_path: str,
    login: str,
    password: str,
    protocol: str = 'https',
    group_id: int = 1
) -> int:
    """
    Добавляет новый VPN-сервер.
    
    Args:
        name: Название сервера
        host: IP-адрес или домен
        port: Порт панели 3X-UI
        web_base_path: Секретный путь API
        login: Логин для панели
        password: Пароль для панели
        protocol: Протокол подключения (http/https)
        group_id: ID группы тарифов (по умолчанию 1 — «Основная»)
        
    Returns:
        ID созданного сервера
    """
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO servers (name, host, port, web_base_path, login, password, is_active, protocol)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (name, host, port, web_base_path, login, password, protocol))
        server_id = cursor.lastrowid
        
        # Добавляем сервер в таблицу связей server_groups
        conn.execute(
            "INSERT INTO server_groups (server_id, group_id) VALUES (?, ?)",
            (server_id, group_id)
        )
        
        logger.info(f"Добавлен сервер: {name} (ID: {server_id}, группа: {group_id})")
        return server_id

def update_server(server_id: int, **fields) -> bool:
    """
    Обновляет поля сервера.
    
    Args:
        server_id: ID сервера
        **fields: Поля для обновления (name, host, port, web_base_path, login, password, protocol)
        
    Returns:
        True если обновление успешно
    """
    allowed_fields = {'name', 'host', 'port', 'web_base_path', 'login', 'password', 'is_active', 'protocol'}
    fields = {k: v for k, v in fields.items() if k in allowed_fields}
    
    if not fields:
        return False
    
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [server_id]
    
    with get_db() as conn:
        cursor = conn.execute(f"""
            UPDATE servers
            SET {set_clause}
            WHERE id = ?
        """, values)
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Обновлён сервер ID {server_id}: {list(fields.keys())}")
        return success

def update_server_field(server_id: int, field: str, value: Any) -> bool:
    """
    Обновляет одно поле сервера.
    
    Args:
        server_id: ID сервера
        field: Название поля
        value: Новое значение
        
    Returns:
        True если обновление успешно
    """
    return update_server(server_id, **{field: value})

def delete_server(server_id: int) -> bool:
    """
    Удаляет сервер.
    
    Args:
        server_id: ID сервера
        
    Returns:
        True если удаление успешно
    """
    with get_db() as conn:
        # Сначала отвязываем ключи от этого сервера, чтобы не нарушить Foreign Key
        conn.execute("UPDATE vpn_keys SET server_id = NULL WHERE server_id = ?", (server_id,))
        
        cursor = conn.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Удалён сервер ID {server_id}")
        return success

def toggle_server_active(server_id: int) -> Optional[bool]:
    """
    Переключает активность сервера.
    
    Args:
        server_id: ID сервера
        
    Returns:
        Новый статус (True = активен) или None если сервер не найден
    """
    server = get_server_by_id(server_id)
    if not server:
        return None
    
    new_status = 0 if server['is_active'] else 1
    
    with get_db() as conn:
        conn.execute("""
            UPDATE servers
            SET is_active = ?
            WHERE id = ?
        """, (new_status, server_id))
        logger.info(f"Сервер ID {server_id}: is_active = {new_status}")
        return bool(new_status)
