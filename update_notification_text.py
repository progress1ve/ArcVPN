#!/usr/bin/env python3
"""
Скрипт для обновления текста уведомлений в базе данных.
Исправляет:
1. "VPN-ключ" → "VPN-подписка"
2. "Через %дней% дней" → "Через %дней%"
3. "%имяключа%" → "%имяподписки%"
"""
import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def update_notification_text():
    """Обновляет текст уведомлений в БД."""
    db_path = 'database/vpn_bot.db'
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем текущий текст уведомления
    cursor.execute("SELECT value FROM settings WHERE key = 'notification_text'")
    row = cursor.fetchone()
    
    if not row:
        logger.warning("Настройка notification_text не найдена в БД")
        conn.close()
        return
    
    current_value = row['value']
    logger.info(f"Текущее значение: {current_value[:100]}...")
    
    try:
        # Пробуем распарсить как JSON
        data = json.loads(current_value)
        if isinstance(data, dict) and 'text' in data:
            old_text = data['text']
            
            # Применяем исправления
            new_text = old_text
            new_text = new_text.replace('VPN-ключ', 'VPN-подписка')
            new_text = new_text.replace('вашего ключа', 'вашей подписки')
            new_text = new_text.replace('%дней% дней', '%дней%')
            new_text = new_text.replace('%имяключа%', '%имяподписки%')
            
            if new_text != old_text:
                data['text'] = new_text
                new_value = json.dumps(data, ensure_ascii=False)
                
                cursor.execute(
                    "UPDATE settings SET value = ? WHERE key = 'notification_text'",
                    (new_value,)
                )
                conn.commit()
                logger.info("✅ Текст уведомления обновлен (JSON формат)")
                logger.info(f"Новый текст: {new_text}")
            else:
                logger.info("Текст уже актуальный, обновление не требуется")
        else:
            logger.warning("JSON в неожиданном формате")
    
    except (json.JSONDecodeError, TypeError):
        # Это обычная строка
        old_text = current_value
        
        # Применяем исправления
        new_text = old_text
        new_text = new_text.replace('VPN-ключ', 'VPN-подписка')
        new_text = new_text.replace('вашего ключа', 'вашей подписки')
        new_text = new_text.replace('%дней% дней', '%дней%')
        new_text = new_text.replace('%имяключа%', '%имяподписки%')
        
        if new_text != old_text:
            cursor.execute(
                "UPDATE settings SET value = ? WHERE key = 'notification_text'",
                (new_text,)
            )
            conn.commit()
            logger.info("✅ Текст уведомления обновлен (строковый формат)")
            logger.info(f"Новый текст: {new_text}")
        else:
            logger.info("Текст уже актуальный, обновление не требуется")
    
    conn.close()

if __name__ == '__main__':
    update_notification_text()
    print("\n✅ Готово! Перезапусти бота: systemctl restart arcvpn-bot")
