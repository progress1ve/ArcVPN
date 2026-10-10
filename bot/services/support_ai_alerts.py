"""Persisted incident notifications; never include provider bodies or credentials."""
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request

from database.db_settings import get_setting, set_setting

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_memory = {}
SETTING = "support_ai_provider_incident"
COOLDOWN = 6 * 60 * 60


def _send(text):
    import config
    token = getattr(config, "BOT_TOKEN", "")
    destination = os.getenv("SUPPORT_AI_ALERT_CHAT_ID", "").strip()
    from bot.services.admin_recipients import admin_notification_ids
    allowed = admin_notification_ids()
    recipients = [int(destination)] if destination.lstrip("-").isdigit() and int(destination) in allowed else ([] if destination else allowed)
    if not token or not recipients:
        return False
    sent = False
    for recipient in recipients:
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=json.dumps({"chat_id": recipient, "text": text}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                sent = bool(json.loads(response.read(10000)).get("ok")) or sent
        except Exception:
            logger.warning("AI incident notification delivery failed")
    return sent


def provider_health(healthy, error=None):
    """Alert first failed inference, remind after 6 h, announce verified recovery."""
    global _memory
    try:
        with _lock:
            try:
                state = json.loads(get_setting(SETTING, "{}"))
            except Exception:
                state = dict(_memory)
            provider = os.getenv("SUPPORT_AI_PROVIDER", "openai").lower()
            if provider not in {"openai", "groq", "openrouter", "gemini"}:
                provider = "unknown"
            now = time.time()
            if healthy:
                if not state.get("down"):
                    return
                if not _send(f"✅ ArcVPN: API ИИ-поддержки ({provider}) снова отвечает. Проверен успешный ответ."):
                    return
                state = {"down": False, "last_alert": 0}
            else:
                last = state.get("last_alert", 0)
                if state.get("down") and now - last < COOLDOWN:
                    return
                code = error.code if isinstance(error, urllib.error.HTTPError) else None
                reason = {401: "ключ отклонён", 403: "доступ запрещён", 404: "модель недоступна", 429: "исчерпан лимит или перегрузка"}.get(code, "таймаут или ошибка провайдера")
                suffix = f" (HTTP {code})" if isinstance(code, int) else ""
                delivered = _send(f"⚠️ ArcVPN: API ИИ-поддержки ({provider}) не отвечает: {reason}{suffix}.\nПользователи передаются менеджеру. Проверьте лимиты, ключ и доступность модели.\nПовторное уведомление — не чаще раза в 6 часов.")
                state = {"down": True, "last_alert": now if delivered else 0}
            _memory = state
            try:
                set_setting(SETTING, json.dumps(state))
            except Exception:
                logger.warning("AI incident state persistence unavailable")
    except Exception:
        logger.warning("AI incident handling failed; manager handoff retained")
