import sqlite3
import logging
import secrets
import string
import datetime
from typing import Optional, List, Dict, Any, Tuple
from .connection import get_db

logger = logging.getLogger(__name__)
BASE62_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

from .db_tariffs import get_tariff_by_id
from .db_settings import get_setting, set_setting


__all__ = [
    'save_yookassa_payment_id',
    'find_order_by_yookassa_id',
    'get_reconcilable_yookassa_orders',
    'get_user_payments_stats',
    'get_daily_payments_stats',
    'get_key_payments_history',
    '_int_to_base62',
    'create_pending_order',
    'create_paid_order_external',
    'find_order_by_order_id',
    'complete_order',
    'update_order_tariff',
    'update_payment_type',
    'update_payment_key_id',
    'update_payment_yookassa_id',
    'update_order_fulfillment',
    'prepare_payment_order',
    'is_order_already_paid',
    'get_key_payments_history',
    'get_referral_levels',
    'get_active_referral_levels',
    'update_referral_level',
    'get_referral_stats',
    'get_referral_friends',
    'update_referral_stat',
    'grant_referral_bonus_once',
    'get_referral_earned_days',
    'is_referral_enabled',
    'get_referral_reward_type',
    'get_referral_conditions_text',
    'update_referral_setting',
    'get_payment_token',
    'infer_order_operation_type',
]


def infer_order_operation_type(
    vpn_key_id: Optional[int],
    payment_type: Optional[str] = None,
    explicit_operation_type: Optional[str] = None,
    tariff_id: Optional[int] = None,
) -> str:
    """
    Определяет доменную операцию ордера.

    Приоритет:
    1. Явно переданный operation_type
    2. Trial-платеж
    3. Пополнение баланса
    4. Продление существующего ключа
    5. Новая подписка
    """
    if explicit_operation_type:
        return explicit_operation_type
    if payment_type == 'trial':
        return 'trial_start'
    if tariff_id is None and vpn_key_id is None:
        return 'topup'
    if vpn_key_id is not None:
        return 'renew'
    return 'new'

def save_yookassa_payment_id(order_id: str, yookassa_payment_id: str) -> bool:
    """
    Сохраняет ID платежа ЮКасса в запись ордера.

    Args:
        order_id: Наш внутренний order_id
        yookassa_payment_id: ID платежа в системе ЮКассы

    Returns:
        True если успешно
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE payments SET yookassa_payment_id = ? WHERE order_id = ?",
            (yookassa_payment_id, order_id)
        )
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Сохранён yookassa_payment_id={yookassa_payment_id} для order_id={order_id}")
        return success

def find_order_by_yookassa_id(yookassa_payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Находит ордер по ID платежа ЮКасса.

    Args:
        yookassa_payment_id: ID платежа в системе ЮКассы

    Returns:
        Словарь с данными ордера или None
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM payments WHERE yookassa_payment_id = ?",
            (yookassa_payment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_reconcilable_yookassa_orders(
    lookback_hours: int = 48,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return recent YooKassa orders that still need verification or delivery."""
    safe_hours = max(1, min(int(lookback_hours), 168))
    safe_limit = max(1, min(int(limit), 200))
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT *
            FROM payments
            WHERE payment_type = 'yookassa_qr'
              AND yookassa_payment_id IS NOT NULL
              AND yookassa_payment_id != ''
              AND datetime(COALESCE(paid_at, CURRENT_TIMESTAMP))
                    >= datetime('now', ?)
              AND (
                    status = 'pending'
                    OR (
                        status = 'paid'
                        AND COALESCE(fulfillment_status, 'pending')
                            IN ('pending', 'failed')
                        AND COALESCE(attempt_count, 0) < 5
                    )
              )
            ORDER BY id ASC
            LIMIT ?
            """,
            (f"-{safe_hours} hours", safe_limit),
        )
        return [dict(row) for row in cursor.fetchall()]

def get_user_payments_stats(user_id: int) -> Dict[str, Any]:
    """
    Получает статистику оплат пользователя.
    
    Args:
        user_id: Внутренний ID пользователя
    
    Returns:
        Словарь со статистикой:
        - total_payments: количество платежей
        - total_amount_cents: общая сумма в центах
        - total_amount_stars: общая сумма в звёздах
        - last_payment_at: дата последней оплаты
        - tariffs: список уникальных тарифов
    """
    with get_db() as conn:
        # Общая статистика (исключаем пробные подписки)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_payments,
                COALESCE(SUM(CASE WHEN payment_type = 'crypto' THEN amount_cents ELSE 0 END), 0) as total_amount_cents,
                COALESCE(SUM(CASE WHEN payment_type = 'stars' THEN amount_stars ELSE 0 END), 0) as total_amount_stars,
                COALESCE(SUM(CASE WHEN payment_type = 'cards' THEN t.price_rub ELSE 0 END), 0) as total_amount_rub,
                MAX(paid_at) as last_payment_at
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.user_id = ? AND p.status = 'paid' AND p.payment_type != 'trial'
        """, (user_id,))
        stats = dict(cursor.fetchone())
        
        # Уникальные тарифы
        cursor = conn.execute("""
            SELECT DISTINCT t.name 
            FROM payments p
            JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.user_id = ?
        """, (user_id,))
        stats['tariffs'] = [row['name'] for row in cursor.fetchall()]
        
        return stats

def get_daily_payments_stats() -> Dict[str, Any]:
    """
    Получает статистику платежей за последние 24 часа.
    
    Returns:
        Словарь со статистикой:
        - paid_count: количество успешных платежей
        - paid_cents: сумма успешных в центах
        - paid_stars: сумма успешных в звёздах
        - pending_count: количество ожидающих (неоплаченных)
    """
    with get_db() as conn:
        # 1. Считаем USDT (crypto)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(amount_cents), 0) as total_cents
            FROM payments
            WHERE status = 'paid' 
            AND payment_type = 'crypto'
            AND paid_at >= datetime('now', '-1 day')
        """)
        crypto_row = cursor.fetchone()
        
        # 2. Считаем Stars
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(amount_stars), 0) as total_stars
            FROM payments
            WHERE status = 'paid' 
            AND payment_type = 'stars'
            AND paid_at >= datetime('now', '-1 day')
        """)
        stars_row = cursor.fetchone()
        
        # 3. Считаем Карты (Cards - Рубли)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(t.price_rub), 0) as total_rub
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid' 
            AND p.payment_type = 'cards'
            AND p.paid_at >= datetime('now', '-1 day')
        """)
        cards_row = cursor.fetchone()
        
        # 4. Считаем QR-оплату (ЮКасса QR/СБП - Рубли)
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(t.price_rub), 0) as total_rub
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.status = 'paid' 
            AND p.payment_type = 'yookassa_qr'
            AND p.paid_at >= datetime('now', '-1 day')
        """)
        qr_row = cursor.fetchone()
        
        paid_count = (crypto_row['count'] if crypto_row else 0) + \
                     (stars_row['count'] if stars_row else 0) + \
                     (cards_row['count'] if cards_row else 0) + \
                     (qr_row['count'] if qr_row else 0)
        total_cents = crypto_row['total_cents'] if crypto_row else 0
        total_stars = stars_row['total_stars'] if stars_row else 0
        total_rub = (cards_row['total_rub'] if cards_row else 0) + \
                    (qr_row['total_rub'] if qr_row else 0)
        
        return {
            'paid_count': paid_count,
            'paid_cents': total_cents,
            'paid_stars': total_stars,
            'paid_rub': total_rub,
            'pending_count': 0 
        }

def get_key_payments_history(key_id: int) -> List[Dict[str, Any]]:
    """
    Получает историю платежей по конкретному ключу.
    Исключает пробные подписки (payment_type='trial').
    
    Args:
        key_id: ID ключа
    
    Returns:
        Список платежей, отсортированный по дате (по убыванию).
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                p.id, p.paid_at, p.payment_type, p.amount_cents, p.amount_stars,
                t.name as tariff_name, t.price_rub
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.vpn_key_id = ? AND p.status = 'paid' AND p.payment_type != 'trial'
            ORDER BY p.paid_at DESC
        """, (key_id,))
        return [dict(row) for row in cursor.fetchall()]

def _int_to_base62(num: int) -> str:
    """
    Конвертирует число в base62 строку.
    
    Args:
        num: Положительное целое число
        
    Returns:
        Base62 строка (0-9, A-Z, a-z)
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    
    result = []
    while num > 0:
        result.append(BASE62_ALPHABET[num % 62])
        num //= 62
    
    return ''.join(reversed(result))

def create_pending_order(
    user_id: int,
    tariff_id: Optional[int],
    payment_type: Optional[str],
    vpn_key_id: Optional[int] = None,
    amount_cents: Optional[int] = None,
    amount_stars: Optional[int] = None,
    promocode_id: Optional[int] = None,
    discount_rub: int = 0,
    operation_type: Optional[str] = None,
) -> tuple[int, str]:
    """
    Создаёт pending order и генерирует уникальный order_id.
    
    Order_id генерируется из внутреннего ID записи в base62 формате,
    что гарантирует уникальность и соответствие формату криптопроцессинга
    (макс 8 символов A-Za-z0-9).
    
    Args:
        user_id: Внутренний ID пользователя
        tariff_id: ID тарифа (может быть None для пополнения баланса)
        payment_type: 'crypto', 'stars' или None (если выбирается при оплате)
        vpn_key_id: ID ключа для продления (None для нового ключа)
        amount_cents: Сумма в копейках (для пополнения баланса)
        amount_stars: Сумма в звездах (для пополнения баланса)
        promocode_id: ID примененного промокода
        discount_rub: Скидка в рублях от промокода
    
    Returns:
        Кортеж (payment_id, order_id)
    """
    tariff = get_tariff_by_id(tariff_id) if tariff_id else None
    
    # Явно рассчитанная платёжным каналом сумма имеет приоритет. Это важно для
    # рублёвых каналов: историческое price_cents некоторых тарифов хранит
    # расчётную валютную цену, тогда как YooKassa получает price_rub * 100.
    final_amount_cents = amount_cents if amount_cents is not None else (tariff['price_cents'] if tariff else 0)
    final_amount_stars = tariff['price_stars'] if tariff else (amount_stars or 0)
    final_period_days = tariff['duration_days'] if tariff else None
    final_operation_type = infer_order_operation_type(
        vpn_key_id=vpn_key_id,
        payment_type=payment_type,
        explicit_operation_type=operation_type,
        tariff_id=tariff_id,
    )
    
    with get_db() as conn:
        # Шаг 1: создаём запись с временным order_id
        cursor = conn.execute("""
            INSERT INTO payments 
            (user_id, tariff_id, order_id, payment_type, vpn_key_id, 
             amount_cents, amount_stars, period_days, status, paid_at,
             promocode_id, discount_rub, operation_type, target_tariff_id,
             fulfillment_status, fulfilled_at, fulfillment_error, attempt_count)
            VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, 'pending', NULL, ?, ?, ?, ?, 'pending', NULL, NULL, 0)
        """, (
            user_id, tariff_id, payment_type, vpn_key_id,
            final_amount_cents,
            final_amount_stars,
            final_period_days,
            promocode_id,
            discount_rub,
            final_operation_type,
            tariff_id,
        ))
        payment_id = cursor.lastrowid
        
        # Шаг 2: генерируем order_id из ID записи (base62)
        # Добавляем префикс '00' для исключения конфликтов с внешними ID
        order_id = "00" + _int_to_base62(payment_id)
        
        # Шаг 3: обновляем order_id
        conn.execute("""
            UPDATE payments SET order_id = ? WHERE id = ?
        """, (order_id, payment_id))
        
        logger.info(
            "Создан pending order: %s (id=%s, user=%s, type=%s, operation=%s, promo=%s, discount=%s₽)",
            order_id,
            payment_id,
            user_id,
            payment_type,
            final_operation_type,
            promocode_id,
            discount_rub,
        )
        return payment_id, order_id

def create_paid_order_external(
    order_id: str,
    user_id: int,
    tariff_id: int,
    payment_type: str,
    amount_cents: int,
    amount_stars: int,
    period_days: int,
    operation_type: Optional[str] = None,
) -> bool:
    """
    Создаёт сразу оплаченный ордер (для внешних платежей).
    
    Используется когда оплата пришла извне (без предварительного pending order).
    
    Args:
        order_id: Внешний ID ордера
        user_id: ID пользователя
        tariff_id: ID тарифа
        payment_type: Тип оплаты ('crypto', 'stars')
        amount_cents: Сумма в центах
        amount_stars: Сумма в звёздах
        period_days: Срок действия
        
    Returns:
        True если успешно
    """
    try:
        final_operation_type = infer_order_operation_type(
            vpn_key_id=None,
            payment_type=payment_type,
            explicit_operation_type=operation_type,
            tariff_id=tariff_id,
        )
        with get_db() as conn:
            conn.execute("""
                INSERT INTO payments 
                (user_id, tariff_id, order_id, payment_type, vpn_key_id, 
                 amount_cents, amount_stars, period_days, status, paid_at,
                 operation_type, target_tariff_id, fulfillment_status,
                 fulfilled_at, fulfillment_error, attempt_count)
                VALUES (?, ?, ?, ?, NULL, ?, ?, ?, 'pending', NULL, ?, ?, 'pending', NULL, NULL, 0)
            """, (
                user_id, tariff_id, order_id, payment_type,
                amount_cents, amount_stars, period_days,
                final_operation_type, tariff_id,
            ))
            logger.info(
                "Создан external pending order: %s (user=%s, operation=%s)",
                order_id,
                user_id,
                final_operation_type,
            )
            return True
    except Exception as e:
        logger.error(f"Ошибка создания external order {order_id}: {e}")
        return False

def find_order_by_order_id(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Находит платёж по order_id.
    
    Args:
        order_id: Уникальный ID ордера
    
    Returns:
        Словарь с данными платежа или None
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT p.*, t.duration_days, t.name as tariff_name
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.order_id = ?
        """, (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def complete_order(order_id: str) -> bool:
    """
    Завершает платёж: меняет статус на 'paid'.
    
    Args:
        order_id: ID ордера
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE payments 
            SET status = 'paid', paid_at = CURRENT_TIMESTAMP
            WHERE order_id = ? AND status = 'pending'
        """, (order_id,))
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Order {order_id} завершён (paid)")
        return success

def update_order_tariff(order_id: str, tariff_id: int, payment_type: Optional[str] = None) -> bool:
    """
    Обновляет тариф и суммы в ордере.
    
    Args:
        order_id: ID ордера
        tariff_id: ID нового тарифа
        payment_type: Тип оплаты (опционально)
    
    Returns:
        True если успешно
    """
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        return False
        
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE payments 
            SET tariff_id = ?, 
                target_tariff_id = ?,
                amount_cents = ?, 
                amount_stars = ?, 
                period_days = ?,
                payment_type = COALESCE(?, payment_type)
            WHERE order_id = ?
        """, (
            tariff_id, 
            tariff_id,
            tariff['price_cents'], 
            tariff['price_stars'], 
            tariff['duration_days'], 
            payment_type,
            order_id
        ))
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Order {order_id} обновлен на тариф {tariff_id} (тип: {payment_type})")
        return success

def update_payment_type(order_id: str, payment_type: str) -> bool:
    """
    Обновляет тип оплаты в ордере.
    
    Args:
        order_id: ID ордера
        payment_type: Новый тип оплаты ('crypto', 'stars')
        
    Returns:
        True если успешно
    """
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE payments 
            SET payment_type = ?
            WHERE order_id = ?
        """, (payment_type, order_id))
        success = cursor.rowcount > 0
        if success:
             logger.info(f"Order {order_id} тип оплаты обновлен на {payment_type}")
        return success

def update_payment_key_id(order_id: str, vpn_key_id: int) -> bool:
    """
    Привязывает созданный VPN-ключ к платежу.
    
    Args:
        order_id: ID ордера
        vpn_key_id: ID ключа
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE payments 
            SET vpn_key_id = ?
            WHERE order_id = ?
        """, (vpn_key_id, order_id))
        return cursor.rowcount > 0

def update_payment_yookassa_id(order_id: str, yookassa_payment_id: str) -> bool:
    """
    Сохраняет ID платежа ЮКасса в запись ордера.
    
    Args:
        order_id: Наш внутренний order_id
        yookassa_payment_id: ID платежа в системе ЮКассы
    
    Returns:
        True если успешно
    """
    return save_yookassa_payment_id(order_id, yookassa_payment_id)


def update_order_fulfillment(
    order_id: str,
    fulfillment_status: str,
    error_message: Optional[str] = None,
    increment_attempt_count: bool = False,
) -> bool:
    """
    Обновляет статус исполнения ордера после оплаты.

    fulfillment_status:
    - pending
    - applied
    - failed
    - manual_review
    """
    fulfilled_at_sql = "CURRENT_TIMESTAMP" if fulfillment_status == 'applied' else "NULL"
    with get_db() as conn:
        cursor = conn.execute(f"""
            UPDATE payments
            SET fulfillment_status = ?,
                fulfilled_at = {fulfilled_at_sql},
                fulfillment_error = ?,
                attempt_count = attempt_count + CASE WHEN ? THEN 1 ELSE 0 END
            WHERE order_id = ?
        """, (fulfillment_status, error_message, 1 if increment_attempt_count else 0, order_id))
        success = cursor.rowcount > 0
        if success:
            logger.info(
                "Order %s fulfillment updated: status=%s attempts+1=%s",
                order_id,
                fulfillment_status,
                increment_attempt_count,
            )
        return success


def prepare_payment_order(
    user_id: int,
    tariff_id: Optional[int],
    payment_type: Optional[str],
    vpn_key_id: Optional[int] = None,
    order_id: Optional[str] = None,
    amount_cents: Optional[int] = None,
    amount_stars: Optional[int] = None,
    promocode_id: Optional[int] = None,
    discount_rub: int = 0,
    operation_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Единая точка create/update pending order для payment handlers.

    Если order_id существует, заказ обновляется с сохранением промокода и скидки.
    Иначе создается новый pending order.
    """
    final_operation_type = infer_order_operation_type(
        vpn_key_id=vpn_key_id,
        payment_type=payment_type,
        explicit_operation_type=operation_type,
        tariff_id=tariff_id,
    )

    existing_order = find_order_by_order_id(order_id) if order_id else None
    if existing_order:
        tariff = get_tariff_by_id(tariff_id) if tariff_id else None
        final_amount_cents = amount_cents if amount_cents is not None else (tariff['price_cents'] if tariff else None)
        final_amount_stars = tariff['price_stars'] if tariff else amount_stars
        final_period_days = tariff['duration_days'] if tariff else None
        with get_db() as conn:
            cursor = conn.execute("""
                UPDATE payments
                SET tariff_id = COALESCE(?, tariff_id),
                    target_tariff_id = COALESCE(?, target_tariff_id, tariff_id),
                    amount_cents = CASE WHEN ? IS NOT NULL THEN ? ELSE amount_cents END,
                    amount_stars = CASE WHEN ? IS NOT NULL THEN ? ELSE amount_stars END,
                    period_days = CASE WHEN ? IS NOT NULL THEN ? ELSE period_days END,
                    payment_type = COALESCE(?, payment_type),
                    vpn_key_id = COALESCE(?, vpn_key_id),
                    operation_type = ?,
                    promocode_id = COALESCE(?, promocode_id),
                    discount_rub = CASE WHEN ? > 0 THEN ? ELSE discount_rub END
                WHERE order_id = ?
            """, (
                tariff_id,
                tariff_id,
                final_amount_cents,
                final_amount_cents,
                final_amount_stars,
                final_amount_stars,
                final_period_days,
                final_period_days,
                payment_type,
                vpn_key_id,
                final_operation_type,
                promocode_id,
                discount_rub,
                discount_rub,
                order_id,
            ))
            if cursor.rowcount <= 0:
                raise RuntimeError(f"Не удалось обновить order {order_id}")

        updated_order = find_order_by_order_id(order_id)
        if not updated_order:
            raise RuntimeError(f"Не удалось перечитать order {order_id} после обновления")
        logger.info(
            "Prepared existing order %s: user=%s type=%s operation=%s tariff=%s key=%s",
            order_id,
            user_id,
            payment_type,
            final_operation_type,
            tariff_id,
            vpn_key_id,
        )
        return updated_order

    _, new_order_id = create_pending_order(
        user_id=user_id,
        tariff_id=tariff_id,
        payment_type=payment_type,
        vpn_key_id=vpn_key_id,
        amount_cents=amount_cents,
        amount_stars=amount_stars,
        promocode_id=promocode_id,
        discount_rub=discount_rub,
        operation_type=final_operation_type,
    )
    created_order = find_order_by_order_id(new_order_id)
    if not created_order:
        raise RuntimeError(f"Не удалось найти созданный order {new_order_id}")
    logger.info(
        "Prepared new order %s: user=%s type=%s operation=%s tariff=%s key=%s",
        new_order_id,
        user_id,
        payment_type,
        final_operation_type,
        tariff_id,
        vpn_key_id,
    )
    return created_order

def get_payment_token() -> Optional[str]:
    """
    Получает токен провайдера для оплаты картами.
    
    Returns:
        Токен провайдера или None
    """
    # Сначала пробуем payment_token, потом cards_provider_token (для обратной совместимости)
    token = get_setting('payment_token')
    if not token:
        token = get_setting('cards_provider_token')
    return token

def is_order_already_paid(order_id: str) -> bool:
    """
    Проверяет, был ли ордер уже оплачен.
    
    Args:
        order_id: ID ордера
    
    Returns:
        True если статус = 'paid'
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT status FROM payments WHERE order_id = ?",
            (order_id,)
        )
        row = cursor.fetchone()
        return row and row['status'] == 'paid'

def get_key_payments_history(key_id: int) -> List[Dict[str, Any]]:
    """
    Получает историю платежей по ключу.
    
    Args:
        key_id: ID ключа
    
    Returns:
        Список платежей с названиями тарифов и ценами
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT p.*, t.name as tariff_name, t.price_rub as amount_rub
            FROM payments p
            LEFT JOIN tariffs t ON p.tariff_id = t.id
            WHERE p.vpn_key_id = ?
            AND p.status = 'paid'
            AND p.payment_type != 'trial'
            ORDER BY p.paid_at DESC
        """, (key_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_referral_levels() -> List[Dict[str, Any]]:
    """
    Получить все уровни реферальной системы.
    
    Returns:
        Список [{level_number, percent, enabled}, ...]
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT level_number, percent, enabled FROM referral_levels ORDER BY level_number"
        )
        return [dict(row) for row in cursor.fetchall()]

def get_active_referral_levels() -> List[tuple]:
    """
    Получить только включённые уровни.
    
    Returns:
        Список кортежей [(level_num, percent), ...]
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT level_number, percent FROM referral_levels WHERE enabled = 1 ORDER BY level_number"
        )
        return [(row['level_number'], row['percent']) for row in cursor.fetchall()]

def update_referral_level(level_number: int, percent: int, enabled: bool) -> bool:
    """
    Обновить уровень реферальной системы.
    
    Args:
        level_number: Номер уровня (1, 2, 3)
        percent: Процент (1-100)
        enabled: Включён ли уровень
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE referral_levels SET percent = ?, enabled = ? WHERE level_number = ?",
            (percent, 1 if enabled else 0, level_number)
        )
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Уровень {level_number} обновлён: {percent}%, enabled={enabled}")
        return success

def get_referral_stats(user_id: int) -> List[Dict[str, Any]]:
    """
    Статистика по уровням для пользователя.
    
    Args:
        user_id: Внутренний ID пользователя (реферера)
    
    Returns:
        Список [{level, count, total_reward_cents, total_reward_days}, ...]
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                level,
                COUNT(*) as paying_count,
                COALESCE(SUM(total_reward_cents), 0) as total_reward_cents,
                COALESCE(SUM(total_reward_days), 0) as total_reward_days
            FROM referral_stats
            WHERE referrer_id = ?
            GROUP BY level
            ORDER BY level
        """, (user_id,))
        rewards = {row['level']: dict(row) for row in cursor.fetchall()}
        
        # Общее количество приглашенных по уровням
        # Используем рекурсивный CTE (WITH RECURSIVE) для получения дерева рефералов
        cursor = conn.execute("""
            WITH RECURSIVE referral_tree(id, level) AS (
                SELECT id, 1 
                FROM users 
                WHERE referred_by = ?
                UNION ALL
                SELECT u.id, rt.level + 1 
                FROM users u
                JOIN referral_tree rt ON u.referred_by = rt.id
                WHERE rt.level < 10
            )
            SELECT level, COUNT(*) as total_count 
            FROM referral_tree 
            GROUP BY level
        """, (user_id,))
        counts = {row['level']: row['total_count'] for row in cursor.fetchall()}
        
        result = []
        # Объединяем данные (и те, где есть вознаграждения, и те, где есть только регистрации)
        all_levels = set(list(rewards.keys()) + list(counts.keys()))
        for level in sorted(all_levels):
            rew = rewards.get(level, {
                'level': level,
                'total_reward_cents': 0,
                'total_reward_days': 0
            })
            # Заменяем 'count' на 'total_count', чтобы показывать всех приглашённых
            rew['count'] = counts.get(level, 0)
            result.append(rew)
            
        return result

def get_referral_friends(user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Список приглашённых напрямую друзей (уровень 1) с признаком оплаты.

    В отличие от get_referral_stats (агрегаты по уровням), возвращает
    поимённый список для отображения в Mini App.

    Args:
        user_id: Внутренний ID пользователя (реферера)
        limit: Максимум записей (защита от тяжёлого ответа)

    Returns:
        Список [{telegram_id, username, first_name, created_at, has_paid}, ...]
        отсортированный от новых к старым.
    """
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT
                u.telegram_id,
                u.username,
                u.first_name,
                u.created_at,
                CASE WHEN EXISTS(
                    SELECT 1 FROM payments p
                    WHERE p.user_id = u.id
                      AND p.status = 'paid'
                      AND p.payment_type != 'trial'
                ) THEN 1 ELSE 0 END AS has_paid
            FROM users u
            WHERE u.referred_by = ?
            ORDER BY u.created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def update_referral_stat(
    referrer_id: int,
    referral_id: int, 
    level: int, 
    reward_cents: int, 
    reward_days: int
) -> bool:
    """
    Обновить статистику реферала (INSERT ON CONFLICT DO UPDATE).
    
    Args:
        referrer_id: ID реферера
        referral_id: ID реферала
        level: Уровень (1, 2, 3)
        reward_cents: Вознаграждение в копейках
        reward_days: Вознаграждение в днях
    
    Returns:
        True если успешно
    """
    with get_db() as conn:
        conn.execute("""
            INSERT INTO referral_stats (referrer_id, referral_id, level, total_payments_count, total_reward_cents, total_reward_days)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(referrer_id, referral_id, level) DO UPDATE SET
                total_payments_count = total_payments_count + 1,
                total_reward_cents = total_reward_cents + excluded.total_reward_cents,
                total_reward_days = total_reward_days + excluded.total_reward_days
        """, (referrer_id, referral_id, level, reward_cents, reward_days))
        return True


# Какие колонки-флаги соответствуют типу бонуса (идемпотентность «раз на друга»)
_BONUS_FLAG_COLUMN = {
    'trial': 'bonus_trial_granted',
    'purchase': 'bonus_purchase_granted',
}


def grant_referral_bonus_once(referrer_id: int, referral_id: int, kind: str, days: int) -> bool:
    """
    Атомарно начисляет реферальный бонус ОДИН раз для пары (реферер, друг).

    Используется новой моделью «3 + 5»: kind='trial' (+3 за запуск друга),
    kind='purchase' (+5 за первую покупку друга). Повторный вызов с тем же
    kind для той же пары вернёт False и ничего не начислит.

    Дни накапливаются в referral_stats.total_reward_days (для статистики);
    фактическое продление ключа реферера делает вызывающий код (billing).

    Args:
        referrer_id: внутренний ID реферера (кому бонус)
        referral_id: внутренний ID приглашённого друга
        kind: 'trial' | 'purchase'
        days: сколько дней начислить (для статистики)

    Returns:
        True — бонус начислен впервые; False — уже был начислен (или kind неизвестен).
    """
    flag = _BONUS_FLAG_COLUMN.get(kind)
    if not flag:
        logger.warning("grant_referral_bonus_once: неизвестный kind=%r", kind)
        return False

    with get_db() as conn:
        # Гарантируем наличие строки статистики (level=1) — без инкремента счётчиков.
        conn.execute("""
            INSERT OR IGNORE INTO referral_stats
                (referrer_id, referral_id, level, total_payments_count, total_reward_cents, total_reward_days)
            VALUES (?, ?, 1, 0, 0, 0)
        """, (referrer_id, referral_id))

        # Ставим флаг и копим дни ТОЛЬКО если бонус ещё не выдан — атомарно.
        cursor = conn.execute(f"""
            UPDATE referral_stats
            SET {flag} = 1,
                total_reward_days = total_reward_days + ?
            WHERE referrer_id = ? AND referral_id = ? AND level = 1 AND {flag} = 0
        """, (days, referrer_id, referral_id))
        granted = cursor.rowcount > 0

    if granted:
        logger.info("Реф-бонус %s: +%s дн. рефереру %s за друга %s", kind, days, referrer_id, referral_id)
    return granted


def get_referral_earned_days(user_id: int) -> int:
    """Сколько всего реферальных бонус-дней заработал пользователь (для UI)."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT COALESCE(SUM(total_reward_days), 0) AS d FROM referral_stats WHERE referrer_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return int(row['d']) if row else 0


def is_referral_enabled() -> bool:
    """Включена ли реферальная система."""
    return get_setting('referral_enabled', '0') == '1'

def get_referral_reward_type() -> str:
    """Тип начисления: 'days' или 'balance'."""
    return get_setting('referral_reward_type', 'days')

def get_referral_conditions_text() -> str:
    """Текст условий реферальной программы."""
    return get_setting('referral_conditions_text', '')

def update_referral_setting(key: str, value: str) -> bool:
    """
    Обновить настройку реферальной системы.
    
    Args:
        key: Ключ настройки
        value: Значение
    
    Returns:
        True если успешно
    """
    return set_setting(key, value) is not None
