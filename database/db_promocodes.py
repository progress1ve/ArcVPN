"""
Модуль для работы с промокодами.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'create_promocode',
    'get_promocode_by_code',
    'get_all_promocodes',
    'delete_promocode',
    'use_promocode',
    'is_promocode_valid',
    'get_promocode_usage_count',
    'compute_discount_rub',
    'format_promocode_discount',
]


def create_promocode(
    code: str,
    discount_rub: int,
    max_uses: int,
    duration_days: int,
    discount_type: str = 'fixed',
    discount_percent: int = 0,
) -> Optional[int]:
    """
    Создает новый промокод.

    Args:
        code: Код промокода (уникальный)
        discount_rub: Скидка в рублях (для discount_type='fixed')
        max_uses: Максимальное количество использований
        duration_days: Длительность действия в днях
        discount_type: 'fixed' (рубли) или 'percent' (процент от цены тарифа)
        discount_percent: Процент скидки 1-100 (для discount_type='percent')

    Returns:
        ID созданного промокода или None при ошибке
    """
    expires_at = datetime.now() + timedelta(days=duration_days)

    with get_db() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO promocodes (code, discount_rub, max_uses, expires_at, created_at, discount_type, discount_percent)
                VALUES (?, ?, ?, ?, datetime('now'), ?, ?)
            """, (code.upper(), discount_rub, max_uses, expires_at.isoformat(), discount_type, discount_percent))

            promocode_id = cursor.lastrowid
            logger.info(f"Создан промокод: {code} (ID: {promocode_id}, type={discount_type})")
            return promocode_id

        except sqlite3.IntegrityError:
            logger.warning(f"Промокод {code} уже существует")
            return None


def compute_discount_rub(promocode: Dict[str, Any], price_rub: float) -> int:
    """
    Вычисляет рублёвую скидку промокода для конкретной цены тарифа.

    Для 'fixed' возвращает discount_rub. Для 'percent' — процент от price_rub,
    округлённый вниз, но не больше самой цены.
    """
    dtype = promocode.get('discount_type', 'fixed')
    if dtype == 'percent':
        percent = promocode.get('discount_percent', 0) or 0
        discount = int(price_rub * percent / 100)
        return max(0, min(discount, int(price_rub)))
    return int(promocode.get('discount_rub', 0) or 0)


def format_promocode_discount(promocode: Dict[str, Any]) -> str:
    """Человекочитаемое описание скидки промокода (для UI)."""
    if promocode.get('discount_type') == 'percent':
        return f"{promocode.get('discount_percent', 0)}%"
    return f"{promocode.get('discount_rub', 0)} ₽"


def get_promocode_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Получает промокод по коду.
    
    Args:
        code: Код промокода
    
    Returns:
        Словарь с данными промокода или None
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT * FROM promocodes WHERE code = ?
        """, (code.upper(),))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_promocodes() -> List[Dict[str, Any]]:
    """
    Получает все промокоды.
    
    Returns:
        Список промокодов
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                p.*,
                (SELECT COUNT(*) FROM promocode_usage WHERE promocode_id = p.id) as used_count
            FROM promocodes p
            ORDER BY p.created_at DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]


def delete_promocode(promocode_id: int) -> bool:
    """
    Удаляет промокод.
    
    Args:
        promocode_id: ID промокода
    
    Returns:
        True если успешно удален
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM promocodes WHERE id = ?", (promocode_id,))
        success = cursor.rowcount > 0
        
        if success:
            logger.info(f"Удален промокод ID: {promocode_id}")
        
        return success


def use_promocode(promocode_id: int, user_id: int) -> bool:
    """
    Отмечает использование промокода пользователем.
    
    Args:
        promocode_id: ID промокода
        user_id: ID пользователя
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO promocode_usage (promocode_id, user_id, used_at)
                VALUES (?, ?, datetime('now'))
            """, (promocode_id, user_id))
            
            logger.info(f"Промокод {promocode_id} использован пользователем {user_id}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Пользователь {user_id} уже использовал промокод {promocode_id}")
            return False


def is_promocode_valid(code: str, user_id: int) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Проверяет валидность промокода для пользователя.
    
    Args:
        code: Код промокода
        user_id: ID пользователя
    
    Returns:
        Кортеж (валиден, сообщение об ошибке, данные промокода)
    """
    promocode = get_promocode_by_code(code)
    
    if not promocode:
        return False, "❌ Промокод не найден", None
    
    # Проверяем срок действия
    expires_at = datetime.fromisoformat(promocode['expires_at'])
    if datetime.now() > expires_at:
        return False, "❌ Срок действия промокода истек", None
    
    # Проверяем количество использований
    used_count = get_promocode_usage_count(promocode['id'])
    if used_count >= promocode['max_uses']:
        return False, "❌ Промокод исчерпан", None
    
    # Проверяем, использовал ли пользователь этот промокод
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 1 FROM promocode_usage 
            WHERE promocode_id = ? AND user_id = ?
        """, (promocode['id'], user_id))
        
        if cursor.fetchone():
            return False, "❌ Вы уже использовали этот промокод", None
    
    return True, None, promocode


def get_promocode_usage_count(promocode_id: int) -> int:
    """
    Получает количество использований промокода.
    
    Args:
        promocode_id: ID промокода
    
    Returns:
        Количество использований
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM promocode_usage 
            WHERE promocode_id = ?
        """, (promocode_id,))
        
        return cursor.fetchone()['cnt']
