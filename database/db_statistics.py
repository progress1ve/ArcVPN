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
    'get_payers_stats',
    'get_online_users',
    'get_servers_stats',
    'get_conversion_stats',
    'get_recent_payments',
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

        # Активных (не истёкших)
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM vpn_keys
            WHERE expires_at > datetime('now')
        """)
        active_count = cursor.fetchone()['cnt']

        # Истёкших
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
    """
    with get_db() as conn:
        now = datetime.now()

        # За день
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
                    COALESCE(SUM(CASE WHEN p.payment_type IN ('yookassa', 'yookassa_qr', 'cards') THEN t.price_rub ELSE 0 END), 0) as total_rub,
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
                'total_usd': row['total_cents'] / 100,
                'total_stars': row['total_stars']
            }

        # Всего за всё время
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


def get_payers_stats(page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Получает статистику пользователей, которые оплачивали VPN.
    
    Returns:
        Словарь с информацией о плательщиках:
        - total_payers: всего плательщиков
        - total_payments: всего платежей
        - total_revenue_rub: общая сумма в рублях
        - payers: список плательщиков с пагинацией
    """
    with get_db() as conn:
        # Общая статистика
        cursor = conn.execute("""
            SELECT 
                COUNT(DISTINCT p.user_id) as total_payers,
                COUNT(*) as total_payments,
                COALESCE(SUM(CASE WHEN p.payment_type = 'yookassa' THEN t.price_rub ELSE 0 END), 0) as total_rub,
                COALESCE(SUM(CASE WHEN p.payment_type = 'crypto' THEN p.amount_cents ELSE 0 END), 0) as total_cents,
                COALESCE(SUM(CASE WHEN p.payment_type = 'stars' THEN p.amount_stars ELSE 0 END), 0) as total_stars
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid'
        """)
        stats = cursor.fetchone()
        
        # Вычисляем offset
        offset = (page - 1) * per_page
        
        # Список плательщиков с пагинацией
        cursor = conn.execute("""
            SELECT 
                u.telegram_id,
                u.username,
                COUNT(*) as payment_count,
                COALESCE(SUM(CASE WHEN p.payment_type = 'yookassa' THEN t.price_rub ELSE 0 END), 0) as total_rub,
                COALESCE(SUM(CASE WHEN p.payment_type = 'crypto' THEN p.amount_cents ELSE 0 END), 0) as total_cents,
                COALESCE(SUM(CASE WHEN p.payment_type = 'stars' THEN p.amount_stars ELSE 0 END), 0) as total_stars,
                MAX(p.paid_at) as last_payment
            FROM payments p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid'
            GROUP BY p.user_id
            ORDER BY total_rub DESC, total_cents DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        
        payers = []
        for row in cursor.fetchall():
            payers.append({
                'telegram_id': row['telegram_id'],
                'username': row['username'],
                'payment_count': row['payment_count'],
                'total_rub': row['total_rub'],
                'total_usd': row['total_cents'] / 100,
                'total_stars': row['total_stars'],
                'last_payment': row['last_payment']
            })
        
        # Общее количество страниц
        total_payers = stats['total_payers'] or 0
        total_pages = (total_payers + per_page - 1) // per_page if total_payers > 0 else 1
        
        return {
            'total_payers': total_payers,
            'total_payments': stats['total_payments'] or 0,
            'total_rub': stats['total_rub'] or 0,
            'total_usd': (stats['total_cents'] or 0) / 100,
            'total_stars': stats['total_stars'] or 0,
            'payers': payers,
            'current_page': page,
            'total_pages': total_pages
        }


def get_online_users() -> Dict[str, Any]:
    """
    Получает список пользователей, которые сейчас онлайн (имеют активную подписку и трафик).
    
    Returns:
        Словарь с информацией об онлайн пользователях:
        - count: количество онлайн
        - users: список пользователей
    """
    with get_db() as conn:
        # Считаем онлайн пользователей (с активной подпиской)
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT vk.user_id) as cnt
            FROM vpn_keys vk
            WHERE vk.expires_at > datetime('now')
            AND vk.server_id IS NOT NULL
        """)
        count = cursor.fetchone()['cnt']
        
        # Получаем список
        cursor = conn.execute("""
            SELECT DISTINCT
                u.telegram_id,
                u.username,
                MAX(vk.expires_at) as expires_at,
                SUM(vk.traffic_used) as total_traffic
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            WHERE vk.expires_at > datetime('now')
            AND vk.server_id IS NOT NULL
            GROUP BY u.id
            ORDER BY vk.expires_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            traffic_gb = (row['total_traffic'] or 0) / (1024**3)
            users.append({
                'telegram_id': row['telegram_id'],
                'username': row['username'],
                'expires_at': row['expires_at'],
                'traffic_gb': traffic_gb
            })
        
        return {
            'count': count,
            'users': users
        }


def get_servers_stats() -> List[Dict[str, Any]]:
    """
    Получает статистику по каждому серверу.
    
    Returns:
        Список словарей с информацией о серверах:
        - id, name, host
        - clients_count: количество клиентов
        - active_clients: активных клиентов
        - total_traffic_gb: общий трафик
    """
    with get_db() as conn:
        # Один запрос с LEFT JOIN + агрегацией вместо N+1 (3 запроса на сервер).
        rows = conn.execute("""
            SELECT
                s.id, s.name, s.host, s.is_active,
                COUNT(vk.id) AS clients_count,
                COALESCE(SUM(CASE WHEN vk.expires_at > datetime('now') THEN 1 ELSE 0 END), 0) AS active_clients,
                COALESCE(SUM(vk.traffic_used), 0) AS total_traffic
            FROM servers s
            LEFT JOIN vpn_keys vk ON vk.server_id = s.id
            GROUP BY s.id, s.name, s.host, s.is_active
            ORDER BY s.name
        """).fetchall()

        return [{
            'id': r['id'],
            'name': r['name'],
            'host': r['host'],
            'is_active': r['is_active'],
            'clients_count': r['clients_count'],
            'active_clients': r['active_clients'],
            'total_traffic_gb': r['total_traffic'] / (1024**3),
        } for r in rows]


def get_conversion_stats() -> Dict[str, Any]:
    """
    Получает статистику конверсии (пробные → платные).
    
    Returns:
        Словарь с конверсией:
        - trial_users: пользователей с пробными ключами
        - paid_users: пользователей с платными ключами
        - converted: пользователей которые были пробными и стали платными
        - conversion_rate: процент конверсии
    """
    # Пробные ключи в этой схеме = vpn_keys.tariff_id IS NULL (см. trial.py);
    # колонки tariffs.is_trial не существует — раньше эти запросы падали.
    with get_db() as conn:
        # Пользователи, у которых есть/был пробный ключ
        trial_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) AS cnt
            FROM vpn_keys WHERE tariff_id IS NULL
        """).fetchone()['cnt']

        # Пользователи с платными ключами
        paid_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) AS cnt
            FROM vpn_keys WHERE tariff_id IS NOT NULL
        """).fetchone()['cnt']

        # Были пробными И стали платными
        converted = conn.execute("""
            SELECT COUNT(DISTINCT user_id) AS cnt
            FROM vpn_keys
            WHERE user_id IN (SELECT user_id FROM vpn_keys WHERE tariff_id IS NULL)
              AND tariff_id IS NOT NULL
        """).fetchone()['cnt']

        # Процент конверсии
        conversion_rate = (converted / trial_users * 100) if trial_users > 0 else 0
        
        return {
            'trial_users': trial_users,
            'paid_users': paid_users,
            'converted': converted,
            'conversion_rate': conversion_rate
        }


def get_recent_payments(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Получает последние платежи.
    
    Args:
        limit: количество платежей
    
    Returns:
        Список последних платежей
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                p.id,
                p.order_id,
                p.payment_type,
                p.paid_at,
                u.telegram_id,
                u.username,
                t.name as tariff_name,
                t.price_rub,
                p.amount_cents,
                p.amount_stars
            FROM payments p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid'
            ORDER BY p.paid_at DESC
            LIMIT ?
        """, (limit,))
        
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row['id'],
                'order_id': row['order_id'],
                'payment_type': row['payment_type'],
                'paid_at': row['paid_at'],
                'telegram_id': row['telegram_id'],
                'username': row['username'],
                'tariff_name': row['tariff_name'],
                'price_rub': row['price_rub'],
                'amount_cents': row['amount_cents'],
                'amount_stars': row['amount_stars']
            })
        
        return payments
