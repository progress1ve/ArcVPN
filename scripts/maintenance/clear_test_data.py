"""
Скрипт для удаления ТОЛЬКО тестовых данных.

Удаляет:
- Тестовые ключи (с названием "Тестовый ключ")
- Платежи за тестовые ключи
- Пользователей без активных подписок и платежей

Более безопасный вариант, чем полное обнуление.
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'database/vpn_bot.db'


def clear_test_data():
    """Удаляет только тестовые данные."""
    
    print("=" * 60)
    print("Очистка тестовых данных")
    print("=" * 60)
    print("\nБудут удалены:")
    print("  - Тестовые VPN-ключи (с названием 'Тестовый ключ')")
    print("  - Связанные платежи")
    print("  - Пользователи без активных подписок и платежей")
    print("=" * 60)
    
    confirm = input("\nПродолжить? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Отменено.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Находим тестовые ключи
        cursor.execute("""
            SELECT id FROM vpn_keys 
            WHERE custom_name LIKE '%Тестовый ключ%' 
            OR custom_name LIKE '%Test%'
            OR custom_name LIKE '%тест%'
        """)
        test_key_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Найдено тестовых ключей: {len(test_key_ids)}")
        
        if test_key_ids:
            # 2. Удаляем уведомления для тестовых ключей
            test_key_ids_placeholder = ','.join('?' * len(test_key_ids))
            cursor.execute(f"DELETE FROM notification_log WHERE vpn_key_id IN ({test_key_ids_placeholder})", test_key_ids)
            deleted_notifications = cursor.rowcount
            logger.info(f"Удалено уведомлений: {deleted_notifications}")
            
            # 3. Удаляем платежи за тестовые ключи
            cursor.execute(f"DELETE FROM payments WHERE vpn_key_id IN ({test_key_ids_placeholder})", test_key_ids)
            deleted_payments = cursor.rowcount
            logger.info(f"Удалено платежей: {deleted_payments}")
            
            # 4. Удаляем тестовые ключи
            cursor.execute(f"DELETE FROM vpn_keys WHERE id IN ({test_key_ids_placeholder})", test_key_ids)
            deleted_keys = cursor.rowcount
            logger.info(f"Удалено тестовых ключей: {deleted_keys}")
        
        # 5. Удаляем пользователей без ключей и платежей
        cursor.execute("""
            DELETE FROM users 
            WHERE id NOT IN (SELECT DISTINCT user_id FROM vpn_keys)
            AND id NOT IN (SELECT DISTINCT user_id FROM payments WHERE status = 'paid')
        """)
        deleted_users = cursor.rowcount
        logger.info(f"Удалено пользователей без активности: {deleted_users}")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Тестовые данные успешно удалены!")
        print("=" * 60)
        print(f"\nУдалено:")
        if test_key_ids:
            print(f"  - Тестовых ключей: {deleted_keys}")
            print(f"  - Платежей: {deleted_payments}")
            print(f"  - Уведомлений: {deleted_notifications}")
        print(f"  - Пользователей без активности: {deleted_users}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Ошибка при очистке тестовых данных: {e}")
        print(f"\n❌ Ошибка: {e}")


if __name__ == '__main__':
    clear_test_data()
