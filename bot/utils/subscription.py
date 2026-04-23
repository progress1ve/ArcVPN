"""
Утилиты для работы с subscription ссылками.
"""

import logging
import urllib.parse
from config import SUBSCRIPTION_URL

logger = logging.getLogger(__name__)


def get_subscription_url(telegram_id: int) -> str:
    """
    Генерирует subscription URL для пользователя.
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        URL для subscription
    """
    return f"{SUBSCRIPTION_URL}/sub/{telegram_id}"


def get_subscription_import_url(telegram_id: int, client_type: str = "auto") -> str:
    """
    Генерирует URL для автоматического импорта подписки в VPN клиент.
    
    Args:
        telegram_id: Telegram ID пользователя
        client_type: Тип клиента (auto, v2ray, clash, hiddify)
        
    Returns:
        URL с протоколом для автоматического импорта
    """
    base_url = get_subscription_url(telegram_id)
    
    # Для большинства клиентов используем схему sub://
    # Кодируем URL в base64 для некоторых клиентов
    if client_type == "v2ray":
        # v2rayNG и подобные клиенты
        return f"v2sub://{urllib.parse.quote(base_url)}"
    elif client_type == "clash":
        # Clash клиенты
        return f"clash://install-config?url={urllib.parse.quote(base_url)}"
    elif client_type == "hiddify":
        # Hiddify и Happ
        return f"hiddify://import/{urllib.parse.quote(base_url)}"
    else:
        # Универсальная схема для большинства клиентов
        return f"sub://{urllib.parse.quote(base_url)}"


def format_subscription_message(telegram_id: int, key_count: int = 0) -> str:
    """
    Форматирует сообщение с subscription ссылкой.
    
    Args:
        telegram_id: Telegram ID пользователя
        key_count: Количество активных ключей (опционально)
        
    Returns:
        Отформатированное сообщение
    """
    url = get_subscription_url(telegram_id)
    
    message = (
        "🔑 <b>Ваша subscription ссылка</b>\n\n"
        f"<code>{url}</code>\n\n"
        "📱 <b>Как использовать:</b>\n"
        "1. Скопируйте ссылку выше\n"
        "2. Откройте VPN клиент (v2rayNG, NekoBox, Shadowrocket)\n"
        "3. Добавьте подписку (Add Subscription)\n"
        "4. Вставьте ссылку\n\n"
        "✅ <b>Преимущества subscription:</b>\n"
        "• Автоматическое обновление серверов\n"
        "• Не нужно обновлять ключи вручную\n"
        "• Доступ ко всем вашим серверам\n"
    )
    
    if key_count > 0:
        message += f"\n📊 Активных серверов: {key_count}"
    
    return message
