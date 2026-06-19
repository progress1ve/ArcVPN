"""
Резервный (аварийный) доступ.

Когда подписка пользователя истекла или исчерпан трафик, subscription_api
вместо 404 отдаёт «резервный» конфиг с роутингом только на Telegram. Для этого
на резервном сервере (servers.is_reserve = 1) поднимается ОДИН общий клиент,
конфиг которого и отдаётся всем истёкшим подпискам.

Разделение ответственности:
- здесь (в боте) выполняется ЗАПИСЬ на панель — создание общего клиента;
- subscription_api только ЧИТАЕТ сохранённые параметры (settings.reserve_client)
  и сам конфиг клиента (с кэшем).
"""
import json
import logging
from typing import Any, Dict, Optional

import config
from database.db_settings import get_setting, set_setting
from database.requests import get_server_by_id

# getattr с дефолтом: устаревший (невёрсионируемый) config.py не должен ломать импорт.
RESERVE_CLIENT_EMAIL = getattr(config, "RESERVE_CLIENT_EMAIL", "reserve_shared_fallback")

logger = logging.getLogger(__name__)

RESERVE_CLIENT_SETTING_KEY = "reserve_client"

# Срок жизни резервного клиента на панели (большой, периодически продлевается
# повторным вызовом ensure_reserve_client).
RESERVE_CLIENT_EXPIRE_DAYS = 3650


async def ensure_reserve_client(server_id: int) -> Dict[str, Any]:
    """
    Создаёт (или пересоздаёт) общий резервный клиент на резервном сервере и
    сохраняет его параметры в settings.

    add_client на панели сам дедуплицирует по email, поэтому повторные вызовы
    безопасны и просто продлевают/обновляют клиента.

    Args:
        server_id: ID резервного сервера

    Returns:
        dict с {server_id, inbound_id, panel_email, client_uuid}

    Raises:
        ValueError / VPNAPIError: если сервер не найден или панель недоступна
    """
    from bot.services.vpn_api import get_client

    client = await get_client(server_id)
    inbounds = await client.get_inbounds()
    if not inbounds:
        raise ValueError(f"На резервном сервере {server_id} нет доступных протоколов (inbound)")

    inbound = inbounds[0]
    inbound_id = inbound["id"]
    flow = await client.get_inbound_flow(inbound_id)

    res = await client.add_client(
        inbound_id=inbound_id,
        email=RESERVE_CLIENT_EMAIL,
        total_gb=0,            # без лимита трафика — доступ к боту не должен «кончиться»
        expire_days=RESERVE_CLIENT_EXPIRE_DAYS,
        limit_ip=0,            # общий клиент: не ограничиваем число устройств
        enable=True,
        flow=flow,
    )

    info = {
        "server_id": int(server_id),
        "inbound_id": int(inbound_id),
        "panel_email": RESERVE_CLIENT_EMAIL,
        "client_uuid": res["uuid"],
    }
    set_setting(RESERVE_CLIENT_SETTING_KEY, json.dumps(info))
    logger.info("Резервный клиент готов на сервере %s (inbound %s)", server_id, inbound_id)
    return info


def get_reserve_client_info() -> Optional[Dict[str, Any]]:
    """
    Возвращает сохранённые параметры резервного клиента, если он настроен и его
    сервер всё ещё помечен как резервный и активен.

    Returns:
        dict с {server_id, inbound_id, panel_email, client_uuid} или None
    """
    raw = get_setting(RESERVE_CLIENT_SETTING_KEY)
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Некорректное значение settings.%s", RESERVE_CLIENT_SETTING_KEY)
        return None

    server = get_server_by_id(info.get("server_id"))
    if not server or not server.get("is_active") or not server.get("is_reserve"):
        return None
    return info


def clear_reserve_client_info() -> None:
    """Сбрасывает сохранённые параметры резервного клиента."""
    set_setting(RESERVE_CLIENT_SETTING_KEY, "")
