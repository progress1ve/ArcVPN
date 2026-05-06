"""
Модуль для получения детальной статистики для админ панели.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'get_new_users_stats',
    'get_subscriptions_stats',
    'get_active_connections_stats',
    'get_revenue_stats',
    'get_traffic_stats',
]


def get_new_users_stats() -> Dict[str, int]:
    """
    Получает статистику новых пользователей за разные периоды.
    
    Returns:
        Словарь с количеством новых пользователей:
        - day: за последние 24 часа
        - week: за последние 7 дней
        - month: за последние 30 дней
        - year: за последний год
        - total: всего пользователей
    """
    with get_db() as conn:
        now = datetime.now()
        
        # За день
        day_ago = now - timedelta(days=1)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM users 
            WHERE created_at >= ?
        """, (day_ago.isoformat(),))
        day_count = cursor.fetchone()['cnt']
        
        # За неделю
        week_ago = now - timedelta(days=7)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM users 
            WHERE created_at >= ?
        """, (week_ago.isoformat(),))
        week_count = cursor.fetchone()['cnt']
        
        # За месяц
        month_ago = now - timedelta(days=30)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM users 
            WHERE created_at >= ?
        """, (month_ago.isoformat(),))
        month_count = cursor.fetchone()['cnt']
        
        # За год
        year_ago = now - timedelta(days=365)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM users 
            WHERE created_at >= ?
        """, (year_ago.isoformat(),))
        year_count = cursor.fetchone()['cnt']
        
        # Всего
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM users")
        total_count = cursor.fetchone()['cnt']
        
        return {
            'day': day_count,
            'week': week_count,
            'month': month_count,
            'year': year_count,
            'total': total_count
        }


def get_subscriptions_stats() -> Dict[str, Any]:
    """
    Получает статистику покупок подписок за разные периоды.
    
    Returns:
        Словарь с количеством купленных подписок:
        - day: за последние 24 часа
        - week: за последние 7 дней
        - month: за последние 30 дней
        - year: за последний год
        - total: всего подписок
        - active: активных подписок (не истекших)
        - expired: истекших подписок
    """
    with get_db() as conn:
        now = datetime.now()
        
        # За день
        day_ago = now - timedelta(days=1)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE created_at >= ?
        """, (day_ago.isoformat(),))
        day_count = cursor.fetchone()['cnt']
        
        # За неделю
        week_ago = now - timedelta(days=7)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE created_at >= ?
        """, (week_ago.isoformat(),))
        week_count = cursor.fetchone()['cnt']
        
        # За месяц
        month_ago = now - timedelta(days=30)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE created_at >= ?
        """, (month_ago.isoformat(),))
        month_count = cursor.fetchone()['cnt']
        
        # За год
        year_ago = now - timedelta(days=365)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE created_at >= ?
        """, (year_ago.isoformat(),))
        year_count = cursor.fetchone()['cnt']
        
        # Всего
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM vpn_keys")
        total_count = cursor.fetchone()['cnt']
        
        # Активных (не истекших)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys 
            WHERE expires_at > datetime('now')
        """)
        active_count = cursor.fetchone()['cnt']
        
        # Истекших
        expired_count = total_count - active_count
        
        return {
            'day': day_count,
            'week': week_count,
            'month': month_count,
            'year': year_count,
            'total': total_count,
            'active': active_count,
            'expired': expired_count
        }


def get_active_connections_stats() -> Dict[str, int]:
    """
    Получает статистику активных подключений (пользователей, которые используют VPN).
    Определяется по наличию трафика у активных подписок.
    
    Returns:
        Словарь с количеством активных пользователей:
        - day: использовали VPN за последние 24 часа (имеют активную подписку с трафиком)
        - week: использовали VPN за последние 7 дней
        - month: использовали VPN за последние 30 дней
        - total_with_traffic: всего пользователей с трафиком
    """
    with get_db() as conn:
        now = datetime.now()
        
        # За день - пользователи с активными подписками, созданными за последние 24 часа и имеющими трафик
        day_ago = now - timedelta(days=1)
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT vk.user_id) as cnt 
            FROM vpn_keys vk
            WHERE vk.traffic_used > 0
            AND vk.expires_at > datetime('now')
            AND vk.created_at >= ?
        """, (day_ago.isoformat(),))
        day_count = cursor.fetchone()['cnt']
        
        # За неделю
        week_ago = now - timedelta(days=7)
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT vk.user_id) as cnt 
            FROM vpn_keys vk
            WHERE vk.traffic_used > 0
            AND vk.expires_at > datetime('now')
            AND vk.created_at >= ?
        """, (week_ago.isoformat(),))
        week_count = cursor.fetchone()['cnt']
        
        # За месяц
        month_ago = now - timedelta(days=30)
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT vk.user_id) as cnt 
            FROM vpn_keys vk
            WHERE vk.traffic_used > 0
            AND vk.expires_at > datetime('now')
            AND vk.created_at >= ?
        """, (month_ago.isoformat(),))
        month_count = cursor.fetchone()['cnt']
        
        # Всего пользователей с активными подписками и трафиком
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as cnt 
            FROM vpn_keys 
            WHERE traffic_used > 0
            AND expires_at > datetime('now')
        """)
        total_count = cursor.fetchone()['cnt']
        
        return {
            'day': day_count,
            'week': week_count,
            'month': month_count,
            'total_with_traffic': total_count
        }


def get_revenue_stats() -> Dict[str, Any]:
    """
    Получает статистику доходов за разные периоды.
    
    Returns:
        Словарь с доходами по периодам и типам оплаты:
        - day/week/month/year: {total_rub, total_usd, total_stars, count}
        - total: общая статистика за все время
    """
    with get_db() as conn:
        now = datetime.now()
        
        periods = {
            'day': now - timedelta(days=1),
            'week': now - timedelta(days=7),
            'month': now - timedelta(days=30),
            'year': now - timedelta(days=365),
        }
        
        result = {}
        
        for period_name, period_start in periods.items():
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(SUM(CASE WHEN p.payment_type = 'yookassa' THEN t.price_rub ELSE 0 END), 0) as total_rub,
                    COALESCE(SUM(CASE WHEN p.payment_type = 'crypto' THEN p.amount_cents ELSE 0 END), 0) as total_cents,
                    COALESCE(SUM(CASE WHEN p.payment_type = 'stars' THEN p.amount_stars ELSE 0 END), 0) as total_stars
                FROM payments p
                LEFT JOIN tariffs t ON p.tariff_id = t.id
                WHERE p.status = 'paid'
                AND p.paid_at >= ?
            """, (period_start.isoformat(),))
            
            row = cursor.fetchone()
            result[period_name] = {
                'count': row['count'],
                'total_rub': row['total_rub'],
                'total_usd': row['total_cents'] / 100,  # центы в доллары
                'total_stars': row['total_stars']
            }
        
        # Всего за все время
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(CASE WHEN p.payment_type = 'yookassa' THEN t.price_rub ELSE 0 END), 0) as total_rub,
                COALESCE(SUM(CASE WHEN p.payment_type = 'crypto' THEN p.amount_cents ELSE 0 END), 0) as total_cents,
                COALESCE(SUM(CASE WHEN p.payment_type = 'stars' THEN p.amount_stars ELSE 0 END), 0) as total_stars
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid'
        """)
        
        row = cursor.fetchone()
        result['total'] = {
            'count': row['count'],
            'total_rub': row['total_rub'],
            'total_usd': row['total_cents'] / 100,
            'total_stars': row['total_stars']
        }
        
        return result


def get_traffic_stats(page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Получает статистику использования трафика.
    
    Args:
        page: Номер страницы (начиная с 1)
        per_page: Количество пользователей на странице
    
    Returns:
        Словарь со статистикой трафика:
        - total_used_gb: всего использовано трафика (ГБ)
        - avg_per_user_gb: средний трафик на пользователя (ГБ)
        - top_users: список пользователей по трафику
        - total_users: общее количество пользователей с трафиком
        - current_page: текущая страница
        - total_pages: всего страниц
    """
    with get_db() as conn:
        # Всего использовано трафика
        cursor = conn.execute("""
            SELECT COALESCE(SUM(traffic_used), 0) as total_bytes
            FROM vpn_keys
        """)
        total_bytes = cursor.fetchone()['total_bytes']
        total_gb = total_bytes / (1024**3)
        
        # Средний трафик на пользователя
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as user_count
            FROM vpn_keys
            WHERE traffic_used > 0
        """)
        user_count = cursor.fetchone()['user_count']
        avg_gb = total_gb / user_count if user_count > 0 else 0
        
        # Общее количество пользователей с трафиком
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT vk.user_id) as total
            FROM vpn_keys vk
            WHERE vk.traffic_used > 0
        """)
        total_users = cursor.fetchone()['total']
        
        # Вычисляем offset
        offset = (page - 1) * per_page
        
        # Топ пользователей по трафику с пагинацией
        cursor = conn.execute("""
            SELECT 
                u.telegram_id,
                u.username,
                SUM(vk.traffic_used) as total_traffic
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            WHERE vk.traffic_used > 0
            GROUP BY vk.user_id
            ORDER BY total_traffic DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        
        top_users = []
        for row in cursor.fetchall():
            traffic_gb = row['total_traffic'] / (1024**3)
            top_users.append({
                'telegram_id': row['telegram_id'],
                'username': row['username'],
                'traffic_gb': traffic_gb
            })
        
        # Вычисляем общее количество страниц
        total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
        
        return {
            'total_used_gb': total_gb,
            'avg_per_user_gb': avg_gb,
            'top_users': top_users,
            'total_users': total_users,
            'current_page': page,
            'total_pages': total_pages
        }
