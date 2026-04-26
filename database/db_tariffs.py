import sqlite3
import logging
import secrets
import string
import datetime
from typing import Optional, List, Dict, Any, Tuple
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'get_all_tariffs',
    'get_tariff_by_id',
    'get_tariff_by_external_id',
    'add_tariff',
    'update_tariff',
    'update_tariff_field',
    'toggle_tariff_active',
    'delete_tariff',
    'get_tariffs_count',
    'get_admin_tariff',
    'get_exchange_rate',
    'update_exchange_rate',
]

def get_all_tariffs(include_hidden: bool = False) -> List[Dict[str, Any]]:
    """
    Получает список всех тарифов.
    
    Args:
        include_hidden: Включать скрытые тарифы (is_active = 0)
        
    Returns:
        Список словарей с данными тарифов
    """
    with get_db() as conn:
        if include_hidden:
            cursor = conn.execute("""
                SELECT id, name, duration_days, price_cents, price_stars, price_rub, 
                       external_id, display_order, is_active, traffic_limit_gb, group_id
                FROM tariffs
                ORDER BY display_order, id
            """)
        else:
            cursor = conn.execute("""
                SELECT id, name, duration_days, price_cents, price_stars, price_rub, 
                       external_id, display_order, is_active, traffic_limit_gb, group_id
                FROM tariffs
                WHERE is_active = 1
                ORDER BY display_order, id
            """)
        return [dict(row) for row in cursor.fetchall()]

def get_tariff_by_id(tariff_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает тариф по ID.
    
    Args:
        tariff_id: ID тарифа
        
    Returns:
        Словарь с данными тарифа или None
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, duration_days, price_cents, price_stars, price_rub, 
                   external_id, display_order, is_active, traffic_limit_gb, group_id
            FROM tariffs
            WHERE id = ?
        """, (tariff_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_tariff_by_external_id(external_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает тариф по external_id (ID в Ya.Seller).
    
    Args:
        external_id: Номер тарифа в Ya.Seller (1-9)
        
    Returns:
        Словарь с данными тарифа или None
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, duration_days, price_cents, price_stars, price_rub, 
                   external_id, display_order, is_active, traffic_limit_gb, group_id
            FROM tariffs
            WHERE external_id = ? AND is_active = 1
        """, (external_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_tariff(
    name: str,
    duration_days: int,
    price_cents: int,
    price_stars: int,
    price_rub: int = 0,
    external_id: Optional[int] = None,
    display_order: int = 0,
    traffic_limit_gb: int = 0,
    group_id: int = 1
) -> int:
    """
    Добавляет новый тариф.
    
    Args:
        name: Название тарифа
        duration_days: Длительность в днях
        price_cents: Цена в центах (USDT * 100)
        price_stars: Цена в Telegram Stars
        price_rub: Цена в рублях
        external_id: Номер тарифа в Ya.Seller (1-9), опционально
        display_order: Порядок отображения
        traffic_limit_gb: Лимит трафика в ГБ (0 = безлимит)
        group_id: ID группы тарифов (по умолчанию 1 — «Основная»)
        
    Returns:
        ID созданного тарифа
    """
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO tariffs (name, duration_days, price_cents, price_stars, price_rub, 
                                external_id, display_order, is_active, traffic_limit_gb, group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (name, duration_days, price_cents, price_stars, price_rub, external_id, display_order, traffic_limit_gb, group_id))
        tariff_id = cursor.lastrowid
        logger.info(f"Добавлен тариф: {name} (ID: {tariff_id}, трафик: {traffic_limit_gb} ГБ, группа: {group_id})")
        return tariff_id

def update_tariff(tariff_id: int, **fields) -> bool:
    """
    Обновляет поля тарифа.
    
    Args:
        tariff_id: ID тарифа
        **fields: Поля для обновления
        
    Returns:
        True если обновление успешно
    """
    allowed_fields = {'name', 'duration_days', 'price_cents', 'price_stars', 'price_rub',
                      'external_id', 'display_order', 'is_active', 'group_id', 'traffic_limit_gb'}
    fields = {k: v for k, v in fields.items() if k in allowed_fields}
    
    if not fields:
        return False
    
    set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values()) + [tariff_id]
    
    with get_db() as conn:
        cursor = conn.execute(f"""
            UPDATE tariffs
            SET {set_clause}
            WHERE id = ?
        """, values)
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Обновлён тариф ID {tariff_id}: {list(fields.keys())}")
        return success

def update_tariff_field(tariff_id: int, field: str, value: Any) -> bool:
    """
    Обновляет одно поле тарифа.
    
    Args:
        tariff_id: ID тарифа
        field: Название поля
        value: Новое значение
        
    Returns:
        True если обновление успешно
    """
    return update_tariff(tariff_id, **{field: value})

def toggle_tariff_active(tariff_id: int) -> Optional[bool]:
    """
    Переключает активность тарифа (скрыть/показать).
    
    Args:
        tariff_id: ID тарифа
        
    Returns:
        Новый статус (True = активен) или None если тариф не найден
    """
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        return None
    
    new_status = 0 if tariff['is_active'] else 1
    
    with get_db() as conn:
        conn.execute("""
            UPDATE tariffs
            SET is_active = ?
            WHERE id = ?
        """, (new_status, tariff_id))
        status_text = "активирован" if new_status else "скрыт"
        logger.info(f"Тариф ID {tariff_id}: {status_text}")
        return bool(new_status)


def delete_tariff(tariff_id: int) -> bool:
    """
    Удаляет тариф из базы данных.
    
    Args:
        tariff_id: ID тарифа
        
    Returns:
        True если успешно удален, False если тариф используется или ошибка
    """
    with get_db() as conn:
        # Проверяем, используется ли тариф в ключах
        cursor = conn.execute("""
            SELECT COUNT(*) as count FROM vpn_keys WHERE tariff_id = ?
        """, (tariff_id,))
        keys_count = cursor.fetchone()['count']
        
        logger.info(f"🔍 Проверка тарифа ID {tariff_id}: найдено {keys_count} ключей")
        
        if keys_count > 0:
            # Показываем какие ключи используют этот тариф
            cursor = conn.execute("""
                SELECT id, user_id, expires_at FROM vpn_keys WHERE tariff_id = ? LIMIT 5
            """, (tariff_id,))
            sample_keys = cursor.fetchall()
            logger.warning(f"Невозможно удалить тариф ID {tariff_id}: используется в {keys_count} ключах. Примеры: {[dict(k) for k in sample_keys]}")
            return False
        
        # Проверяем, используется ли тариф в платежах
        cursor = conn.execute("""
            SELECT COUNT(*) as count FROM payments WHERE tariff_id = ?
        """, (tariff_id,))
        payments_count = cursor.fetchone()['count']
        
        logger.info(f"🔍 Проверка тарифа ID {tariff_id}: найдено {payments_count} платежей")
        
        if payments_count > 0:
            # Показываем какие платежи используют этот тариф
            cursor = conn.execute("""
                SELECT id, user_id, status, paid_at FROM payments WHERE tariff_id = ? LIMIT 5
            """, (tariff_id,))
            sample_payments = cursor.fetchall()
            logger.warning(f"Невозможно удалить тариф ID {tariff_id}: используется в {payments_count} платежах. Примеры: {[dict(p) for p in sample_payments]}")
            return False
        
        # Если тариф не используется - удаляем
        try:
            logger.info(f"✅ Тариф ID {tariff_id} не используется, удаляем...")
            cursor = conn.execute("""
                DELETE FROM tariffs
                WHERE id = ?
            """, (tariff_id,))
            success = cursor.rowcount > 0
            if success:
                logger.info(f"✅ Тариф ID {tariff_id} успешно удален из БД")
            else:
                logger.warning(f"⚠️ Тариф ID {tariff_id} не найден в БД (rowcount=0)")
            return success
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении тарифа ID {tariff_id}: {e}")
            return False

def get_tariffs_count() -> int:
    """
    Возвращает количество активных тарифов.
    
    Returns:
        Количество активных тарифов
    """
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM tariffs WHERE is_active = 1")
        row = cursor.fetchone()
        return row['cnt'] if row else 0

def get_admin_tariff() -> Optional[Dict[str, Any]]:
    """
    Получает скрытый Admin Tariff для админского добавления ключей.
    
    Если тариф не существует, создаёт его автоматически.
    
    Returns:
        Словарь с данными тарифа
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT id, name, duration_days, price_cents, price_stars, price_rub, 
                   external_id, display_order, is_active
            FROM tariffs
            WHERE name = 'Admin Tariff'
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        
        # Если тариф не найден, создаём его
        cursor = conn.execute("""
            INSERT INTO tariffs (name, duration_days, price_cents, price_stars, price_rub, display_order, is_active)
            VALUES ('Admin Tariff', 30, 0, 0, 0, 999, 0)
        """)
        logger.info("Создан Admin Tariff")
        
        return {
            'id': cursor.lastrowid,
            'name': 'Admin Tariff',
            'duration_days': 30,
            'price_cents': 0,
            'price_stars': 0,
            'price_rub': 0,
            'external_id': None,
            'display_order': 999,
            'is_active': 0
        }

def get_exchange_rate(currency_pair: str) -> Optional[int]:
    """
    Получить курс из БД (fallback).
    
    Args:
        currency_pair: Пара валют (например, 'USD_RUB')
    
    Returns:
        Курс в копейках или None
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT rate FROM exchange_rates WHERE currency_pair = ?",
            (currency_pair,)
        )
        row = cursor.fetchone()
        return row['rate'] if row else None

def update_exchange_rate(currency_pair: str, rate: int) -> bool:
    """
    Сохранить курс в БД.
    
    Args:
        currency_pair: Пара валют (например, 'USD_RUB')
        rate: Курс в копейках
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        conn.execute("""
            INSERT INTO exchange_rates (currency_pair, rate, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(currency_pair) DO UPDATE SET
                rate = excluded.rate,
                updated_at = CURRENT_TIMESTAMP
        """, (currency_pair, rate))
        logger.info(f"Курс {currency_pair} обновлён: {rate}")
        return True
