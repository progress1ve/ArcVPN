#!/usr/bin/env python3
"""
Скрипт для сброса флага used_trial для конкретного пользователя.
Используется для тестирования пробного периода.

Использование:
    python reset_trial_for_user.py <telegram_id>
    
Пример:
    python reset_trial_for_user.py 123456789
"""

import sys
import sqlite3

def reset_trial(telegram_id: int):
    """Сбрасывает флаг used_trial для пользователя."""
    try:
        conn = sqlite3.connect('database/vpn_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем существование пользователя
        cursor.execute("SELECT id, telegram_id, username, used_trial FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Пользователь с telegram_id={telegram_id} не найден в базе данных")
            return False
        
        print(f"✅ Найден пользователь:")
        print(f"   ID: {user['id']}")
        print(f"   Telegram ID: {user['telegram_id']}")
        print(f"   Username: {user['username']}")
        print(f"   used_trial (до): {user['used_trial']}")
        
        # Сбрасываем флаг
        cursor.execute("UPDATE users SET used_trial = 0 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT used_trial FROM users WHERE telegram_id = ?", (telegram_id,))
        updated_user = cursor.fetchone()
        
        print(f"   used_trial (после): {updated_user['used_trial']}")
        print(f"\n✅ Флаг used_trial успешно сброшен для пользователя {telegram_id}")
        print(f"   Теперь пользователь может активировать пробный период")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python reset_trial_for_user.py <telegram_id>")
        print("Пример: python reset_trial_for_user.py 123456789")
        sys.exit(1)
    
    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        print("❌ Ошибка: telegram_id должен быть числом")
        sys.exit(1)
    
    success = reset_trial(telegram_id)
    sys.exit(0 if success else 1)
