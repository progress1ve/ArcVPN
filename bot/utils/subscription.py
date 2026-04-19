"""
Утилиты для работы с subscription ссылками.
"""

import logging
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
