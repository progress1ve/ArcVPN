"""
Валидация Telegram Mini App initData.

Telegram Web App при открытии передаёт строку `initData` (query-string), которую
можно проверить на подлинность через HMAC-SHA256 на основе токена бота. Это
единственный способ доверенно узнать telegram_id пользователя внутри Mini App —
сам по себе клиент данным доверять нельзя.

Документация Telegram: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# initData считаем протухшей через сутки — Mini App переоткрывают часто, а старый
# initData мог утечь. Можно переопределить параметром max_age_seconds.
DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> Optional[Dict[str, Any]]:
    """
    Проверяет подпись Telegram Mini App initData.

    Args:
        init_data: сырая строка initData (window.Telegram.WebApp.initData).
        bot_token: токен бота (config.BOT_TOKEN).
        max_age_seconds: максимальный возраст auth_date; 0 — не проверять возраст.

    Returns:
        dict разобранных полей initData (с уже распарсенным JSON в 'user'),
        либо None если подпись/возраст невалидны.
    """
    if not init_data or not bot_token:
        return None

    # keep_blank_values — чтобы пустые поля не выкидывались и не ломали подпись.
    pairs = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
    data = dict(pairs)

    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    # data-check-string: все пары key=value кроме hash, отсортированы по ключу,
    # склеены через \n.
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        logger.warning("initData: неверная подпись")
        return None

    if max_age_seconds:
        try:
            auth_date = int(data.get("auth_date", "0"))
        except (TypeError, ValueError):
            auth_date = 0
        if auth_date <= 0 or (time.time() - auth_date) > max_age_seconds:
            logger.warning("initData: устаревший или отсутствующий auth_date")
            return None

    # Поле user — это JSON-строка; парсим её для удобства вызывающего кода.
    if "user" in data:
        try:
            data["user"] = json.loads(data["user"])
        except (TypeError, ValueError):
            logger.warning("initData: не удалось разобрать поле user")
            return None

    return data


def get_telegram_id(init_data: str, bot_token: str,
                    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS) -> Optional[int]:
    """
    Удобная обёртка: валидирует initData и возвращает telegram_id (int) или None.
    """
    parsed = validate_init_data(init_data, bot_token, max_age_seconds)
    if not parsed:
        return None
    user = parsed.get("user") or {}
    tg_id = user.get("id")
    try:
        return int(tg_id) if tg_id is not None else None
    except (TypeError, ValueError):
        return None
