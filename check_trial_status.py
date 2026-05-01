#!/usr/bin/env python3
"""
Скрипт для проверки статуса пробного периода.

Использование:
    python check_trial_status.py [telegram_id]
    
Если telegram_id не указан, показывает всех пользователей с used_trial=1
"""

import sys
import sqlite3

def check_trial_status(telegram_id: int = None):
    """Проверяет статус пробного периода."""
    try:
        conn = sqlite3.connect('database/vpn_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if telegram_id:
            # Проверяем конкретного пользователя
            cursor.execute("""
                SELECT id, telegram_id, username, used_trial, created_at 
                FROM users 
                WHERE telegram_id = ?
            """, (telegram_id,))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ Пользователь с telegram_id={telegram_id} не найден")
                return False
            
            print(f"\n📊 Статус пользователя {telegram_id}:")
            print(f"   ID: {user['id']}")
            print(f"   Username: @{user['username'] or 'не указан'}")
            print(f"   used_trial: {user['used_trial']} {'✅ (использовал)' if user['used_trial'] else '❌ (не использовал)'}")
            print(f"   Создан: {user['created_at']}")
            
            # Проверяем наличие ключей
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM vpn_keys 
                WHERE user_id = ?
            """, (user['id'],))
            keys_count = cursor.fetchone()['count']
            print(f"   Ключей: {keys_count}")
            
            # Проверяем платежи с типом 'trial'
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM payments 
                WHERE user_id = ? AND payment_type = 'trial'
            """, (user['id'],))
            trial_payments = cursor.fetchone()['count']
            print(f"   Пробных активаций: {trial_payments}")
            
        else:
            # Показываем всех пользователей с used_trial=1
            cursor.execute("""
                SELECT id, telegram_id, username, used_trial, created_at 
                FROM users 
                WHERE used_trial = 1
                ORDER BY created_at DESC
                LIMIT 20
            """)
            users = cursor.fetchall()
            
            if not users:
                print("✅ Нет пользователей, использовавших пробный период")
                return True
            
            print(f"\n📊 Пользователи, использовавшие пробный период (последние 20):\n")
            print(f"{'ID':<8} {'Telegram ID':<15} {'Username':<20} {'Создан':<20}")
            print("-" * 70)
            
            for user in users:
                username = f"@{user['username']}" if user['username'] else "—"
                print(f"{user['id']:<8} {user['telegram_id']:<15} {username:<20} {user['created_at']:<20}")
        
        # Показываем общую статистику
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as used FROM users WHERE used_trial = 1")
        used_trial = cursor.fetchone()['used']
        
        print(f"\n📈 Общая статистика:")
        print(f"   Всего пользователей: {total_users}")
        print(f"   Использовали пробный период: {used_trial} ({used_trial/total_users*100:.1f}%)")
        print(f"   Не использовали: {total_users - used_trial} ({(total_users-used_trial)/total_users*100:.1f}%)")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


if __name__ == "__main__":
    telegram_id = None
    
    if len(sys.argv) > 1:
        try:
            telegram_id = int(sys.argv[1])
        except ValueError:
            print("❌ Ошибка: telegram_id должен быть числом")
            sys.exit(1)
    
    success = check_trial_status(telegram_id)
    sys.exit(0 if success else 1)
