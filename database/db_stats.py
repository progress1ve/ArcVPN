import sqlite3
import logging
import secrets
import string
import datetime
from typing import Optional, List, Dict, Any, Tuple
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'get_users_for_broadcast',
    'count_users_for_broadcast',
    'get_expiring_keys',
    'get_expired_keys_today',
    'get_all_expired_keys',
    'is_notification_sent_today',
    'log_notification_sent',
    'get_keys_stats',
]

def get_users_for_broadcast(filter_type: str) -> List[int]:
    """
    Получает список telegram_id пользователей для рассылки.
    
    Args:
        filter_type: Тип фильтра:
            - 'all': все не забаненные пользователи
            - 'active': с активными (непросроченными) ключами
            - 'inactive': без активных ключей
            - 'never_paid': никогда не покупали VPN
            - 'expired': был ключ, но он истёк
    
    Returns:
        Список telegram_id пользователей
    """
    with get_db() as conn:
        if filter_type == 'all':
            # Все не забаненные
            cursor = conn.execute("""
                SELECT telegram_id FROM users WHERE is_banned = 0
            """)
        elif filter_type == 'active':
            # Есть хотя бы один непросроченный ключ
            cursor = conn.execute("""
                SELECT DISTINCT u.telegram_id 
                FROM users u
                JOIN vpn_keys vk ON u.id = vk.user_id
                WHERE u.is_banned = 0 
                AND vk.expires_at > datetime('now')
            """)
        elif filter_type == 'inactive':
            # Нет активных ключей (либо все истекли, либо никогда не было)
            cursor = conn.execute("""
                SELECT u.telegram_id 
                FROM users u
                WHERE u.is_banned = 0 
                AND u.id NOT IN (
                    SELECT DISTINCT user_id FROM vpn_keys 
                    WHERE expires_at > datetime('now')
                )
            """)
        elif filter_type == 'never_paid':
            # Никогда не покупали VPN (нет ключей вообще)
            cursor = conn.execute("""
                SELECT u.telegram_id 
                FROM users u
                WHERE u.is_banned = 0 
                AND u.id NOT IN (SELECT DISTINCT user_id FROM vpn_keys)
            """)
        elif filter_type == 'expired':
            # Был ключ, но он уже истёк (и нет активных)
            cursor = conn.execute("""
                SELECT DISTINCT u.telegram_id 
                FROM users u
                JOIN vpn_keys vk ON u.id = vk.user_id
                WHERE u.is_banned = 0 
                AND vk.expires_at <= datetime('now')
                AND u.id NOT IN (
                    SELECT DISTINCT user_id FROM vpn_keys 
                    WHERE expires_at > datetime('now')
                )
            """)
        else:
            return []
        
        return [row['telegram_id'] for row in cursor.fetchall()]

def count_users_for_broadcast(filter_type: str) -> int:
    """
    Считает количество пользователей для рассылки.
    
    Args:
        filter_type: Тип фильтра (см. get_users_for_broadcast)
    
    Returns:
        Количество пользователей
    """
    return len(get_users_for_broadcast(filter_type))

def get_expiring_keys(days: int) -> List[Dict[str, Any]]:
    """
    Получает ключи, истекающие в ближайшие N дней (но ещё не истёкшие).
    
    Args:
        days: Количество дней до истечения
    
    Returns:
        Список словарей: vpn_key_id, user_telegram_id, expires_at, custom_name, days_left
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id as vpn_key_id,
                u.telegram_id as user_telegram_id,
                vk.expires_at,
                vk.custom_name,
                -- Округляем вверх: если осталось хоть немного времени, показываем минимум 1 день
                CASE 
                    WHEN (julianday(vk.expires_at) - julianday('now')) < 1 THEN 1
                    ELSE CAST((julianday(vk.expires_at) - julianday('now')) + 0.5 AS INTEGER)
                END as days_left
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            WHERE u.is_banned = 0
            AND vk.expires_at > datetime('now')
            AND vk.expires_at <= datetime('now', '+' || ? || ' days')
        """, (days,))
        return [dict(row) for row in cursor.fetchall()]

def get_expired_keys_today() -> List[Dict[str, Any]]:
    """
    Получает ключи, которые истекли сегодня (в течение последних 24 часов).
    
    Returns:
        Список словарей: vpn_key_id, user_telegram_id, expires_at, custom_name
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id as vpn_key_id,
                u.telegram_id as user_telegram_id,
                vk.expires_at,
                vk.custom_name
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            WHERE u.is_banned = 0
            AND vk.expires_at <= datetime('now')
            AND vk.expires_at >= datetime('now', '-1 day')
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_all_expired_keys() -> List[Dict[str, Any]]:
    """
    Получает все истёкшие ключи (expires_at <= now).
    Используется для автоматического отключения на панели.
    
    Returns:
        Список словарей с данными ключей
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id,
                vk.server_id,
                vk.panel_email,
                vk.custom_name,
                vk.expires_at,
                u.telegram_id
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            WHERE vk.expires_at <= datetime('now')
            AND vk.server_id IS NOT NULL
            AND vk.panel_email IS NOT NULL
        """)
        return [dict(row) for row in cursor.fetchall()]

def is_notification_sent_today(vpn_key_id: int) -> bool:
    """
    Проверяет, было ли уже отправлено уведомление для этого ключа.
    Уведомление отправляется только один раз, повторное - через 7 дней после последнего.
    
    Args:
        vpn_key_id: ID VPN-ключа
    
    Returns:
        True если уведомление было отправлено в течение последних 7 дней
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT sent_at FROM notification_log
            WHERE vpn_key_id = ? 
            ORDER BY sent_at DESC
            LIMIT 1
        """, (vpn_key_id,))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        # Проверяем, прошло ли 7 дней с последнего уведомления
        last_sent = row['sent_at']
        cursor = conn.execute("""
            SELECT julianday('now') - julianday(?) as days_passed
        """, (last_sent,))
        days_passed = cursor.fetchone()['days_passed']
        
        # Если прошло меньше 7 дней - не отправляем
        return days_passed < 7

def log_notification_sent(vpn_key_id: int) -> None:
    """
    Записывает факт отправки уведомления.
    Каждое уведомление записывается как отдельная запись.
    
    Args:
        vpn_key_id: ID VPN-ключа
    """
    with get_db() as conn:
        conn.execute("""
            INSERT INTO notification_log (vpn_key_id, sent_at)
            VALUES (?, date('now'))
        """, (vpn_key_id,))
        logger.debug(f"Записано уведомление для ключа {vpn_key_id}")

def get_keys_stats() -> Dict[str, int]:
    """
    Получает статистику VPN-ключей.
    
    Returns:
        Словарь со статистикой:
        - total: всего ключей
        - active: активных (не истёкших)
        - expired: истёкших
        - created_today: созданных за последние 24 часа
    """
    with get_db() as conn:
        # Всего ключей
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM vpn_keys")
        total = cursor.fetchone()['cnt']
        
        # Активных (не истёкших)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE expires_at > datetime('now')
        """)
        active = cursor.fetchone()['cnt']
        
        # Созданных за сутки
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        created_today = cursor.fetchone()['cnt']
        
        return {
            'total': total,
            'active': active,
            'expired': total - active,
            'created_today': created_today
        }
