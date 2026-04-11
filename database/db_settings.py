import sqlite3
import logging
import secrets
import string
import datetime
from typing import Optional, List, Dict, Any, Tuple
from .connection import get_db

logger = logging.getLogger(__name__)

__all__ = [
    'get_setting',
    'set_setting',
    'delete_setting',
    'is_crypto_enabled',
    'is_stars_enabled',
    'is_crypto_configured',
    'get_crypto_integration_mode',
    'set_crypto_integration_mode',
    'is_cards_enabled',
    'is_cards_configured',
    'is_yookassa_qr_enabled',
    'is_yookassa_qr_configured',
    'get_yookassa_credentials',
    'is_trial_enabled',
    'get_trial_tariff_id',
    'is_demo_payment_enabled',
]

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Получает значение настройки.
    
    Args:
        key: Ключ настройки
        default: Значение по умолчанию
        
    Returns:
        Значение настройки или default
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else default

def set_setting(key: str, value: str) -> None:
    """
    Устанавливает значение настройки.
    
    Args:
        key: Ключ настройки
        value: Значение настройки
    """
    with get_db() as conn:
        conn.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        logger.info(f"Настройка обновлена: {key}")

def delete_setting(key: str) -> bool:
    """
    Удаляет настройку.
    
    Args:
        key: Ключ настройки
        
    Returns:
        True если настройка была удалена
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        return cursor.rowcount > 0

def is_crypto_enabled() -> bool:
    """Проверяет, включены ли крипто-платежи."""
    return get_setting('crypto_enabled', '0') == '1'

def is_stars_enabled() -> bool:
    """Проверяет, включены ли Telegram Stars."""
    return get_setting('stars_enabled', '0') == '1'

def is_crypto_configured() -> bool:
    """
    Проверяет, настроены ли крипто-платежи полностью.
    
    Returns:
        True если крипто включены И есть ссылка на товар (для стандартного режима) или просто включены
    """
    if not is_crypto_enabled():
        return False
    crypto_item_url = get_setting('crypto_item_url')
    return bool(crypto_item_url and crypto_item_url.strip())

def get_crypto_integration_mode() -> str:
    """
    Возвращает текущий режим интеграции с Ya.Seller.
    Возможные значения: 'simple' или 'standard'.
    """
    # Если настройка не задана (миграция почему-то не прошла), то по умолчанию "standard",
    # чтобы не сломать текущим пользователям
    return get_setting('crypto_integration_mode', 'standard')

def set_crypto_integration_mode(mode: str) -> None:
    """
    Устанавливает режим интеграции с Ya.Seller.
    """
    if mode not in ('simple', 'standard'):
        raise ValueError("Invalid crypto integration mode")
    set_setting('crypto_integration_mode', mode)

def is_cards_enabled() -> bool:
    """Проверяет, включена ли оплата картами (ЮКасса)."""
    return get_setting('cards_enabled', '0') == '1'

def is_cards_configured() -> bool:
    """
    Проверяет, настроена ли оплата картами.
    
    Returns:
        True если оплата картами включена И есть provider_token
    """
    if not is_cards_enabled():
        return False
    token = get_setting('cards_provider_token')
    return bool(token and token.strip())

def is_yookassa_qr_enabled() -> bool:
    """Проверяет, включена ли QR-оплата через ЮКассу."""
    return get_setting('yookassa_qr_enabled', '0') == '1'

def is_yookassa_qr_configured() -> bool:
    """
    Проверяет, настроена ли QR-оплата через ЮКассу полностью.

    Returns:
        True если QR включена И есть shop_id и secret_key
    """
    if not is_yookassa_qr_enabled():
        return False
    shop_id = get_setting('yookassa_shop_id', '')
    secret_key = get_setting('yookassa_secret_key', '')
    return bool(shop_id and shop_id.strip() and secret_key and secret_key.strip())

def get_yookassa_credentials() -> tuple[str, str]:
    """
    Возвращает учётные данные ЮКасса для прямого API.

    Returns:
        Кортеж (shop_id, secret_key)
    """
    shop_id = get_setting('yookassa_shop_id', '')
    secret_key = get_setting('yookassa_secret_key', '')
    return shop_id, secret_key

def is_trial_enabled() -> bool:
    """Включена ли функция пробной подписки."""
    return get_setting('trial_enabled', '0') == '1'

def get_trial_tariff_id() -> Optional[int]:
    """
    Возвращает ID тарифа для пробной подписки.
    
    Returns:
        ID тарифа или None если тариф не задан
    """
    val = get_setting('trial_tariff_id', '')
    return int(val) if val and val.isdigit() else None

def is_demo_payment_enabled() -> bool:
    """Включена ли демонстрационная оплата РФ картой."""
    return get_setting('demo_payment_enabled', '0') == '1'
