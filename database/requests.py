"""
Модуль запросов к базе данных.

Единственная точка доступа к БД для всех хендлеров.
Прямой SQL в хендлерах запрещён — используйте функции из этого модуля.
"""

from database.db_users import *
from database.db_keys import *
from database.db_payments import *
from database.db_servers import *
from database.db_tariffs import *
from database.db_stats import *
from database.db_groups import *
from database.db_settings import *


# Subscription URL
def get_user_subscription_url(telegram_id: int) -> str:
    """
    Получает subscription URL для пользователя.
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        URL для subscription
    """
    from bot.utils.subscription import get_subscription_url
    return get_subscription_url(telegram_id)
