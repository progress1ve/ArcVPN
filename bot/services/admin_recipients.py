"""Notification audience is independent from administrator authorization."""
import json
import logging

from database.db_settings import get_setting

logger = logging.getLogger(__name__)
SETTING = "admin_notification_ids"


def admin_notification_ids():
    import config
    admins = list(dict.fromkeys(int(value) for value in config.ADMIN_IDS))
    try:
        value = get_setting(SETTING)
        if value is None:
            return admins
        selected = json.loads(value)
        if not isinstance(selected, list):
            return []
        return [value for value in admins if value in selected]
    except Exception:
        # An unreadable opt-out must never re-enable notifications to everyone.
        logger.warning("Administrator notification audience unavailable")
        return []
