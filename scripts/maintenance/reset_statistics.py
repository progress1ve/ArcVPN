"""
Скрипт для обнуления статистики (удаление тестовых данных).

ВНИМАНИЕ: Этот скрипт удалит:
- Всех пользователей (кроме админов)
- Все VPN-ключи
- Все платежи
- Все уведомления
- Всю статистику рефералов

Используйте с осторожностью!
"""
import sqlite3
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = 'database/vpn_bot.db'


def reset_statistics():
    """Обнуляет статистику, удаляя тестовые данные."""
    
    print("=" * 60)
    print("ВНИМАНИЕ! Этот скрипт удалит все данные из базы!")
    print("=" * 60)
    print("\nБудут удалены:")
    print("  - Все пользователи (кроме админов)")
    print("  - Все VPN-ключи")
    print("  - Все платежи")
    print("  - Все уведомления")
    print("  - Вся статистика рефералов")
    print("\nАдмины (не будут удалены):", ADMIN_IDS)
    print("=" * 60)
    
    confirm = input("\nВы уверены? Введите 'YES' для подтверждения: ")
    
    if confirm != 'YES':
        print("Отменено.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Получаем ID админов в базе
        admin_ids_str = ','.join(str(aid) for aid in ADMIN_IDS)
        cursor.execute(f"SELECT id FROM users WHERE telegram_id IN ({admin_ids_str})")
        admin_user_ids = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Найдено админов в БД: {len(admin_user_ids)}")
        
        # 1. Удаляем уведомления
        cursor.execute("DELETE FROM notification_log")
        deleted_notifications = cursor.rowcount
        logger.info(f"Удалено уведомлений: {deleted_notifications}")
        
        # 2. Удаляем платежи (кроме платежей админов)
        if admin_user_ids:
            admin_ids_placeholder = ','.join('?' * len(admin_user_ids))
            cursor.execute(f"DELETE FROM payments WHERE user_id NOT IN ({admin_ids_placeholder})", admin_user_ids)
        else:
            cursor.execute("DELETE FROM payments")
        deleted_payments = cursor.rowcount
        logger.info(f"Удалено платежей: {deleted_payments}")
        
        # 3. Удаляем VPN-ключи (кроме ключей админов)
        if admin_user_ids:
            admin_ids_placeholder = ','.join('?' * len(admin_user_ids))
            cursor.execute(f"DELETE FROM vpn_keys WHERE user_id NOT IN ({admin_ids_placeholder})", admin_user_ids)
        else:
            cursor.execute("DELETE FROM vpn_keys")
        deleted_keys = cursor.rowcount
        logger.info(f"Удалено VPN-ключей: {deleted_keys}")
        
        # 4. Удаляем статистику рефералов (если таблица существует)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='referral_stats'")
        if cursor.fetchone():
            if admin_user_ids:
                admin_ids_placeholder = ','.join('?' * len(admin_user_ids))
                cursor.execute(f"DELETE FROM referral_stats WHERE referrer_id NOT IN ({admin_ids_placeholder})", admin_user_ids)
            else:
                cursor.execute("DELETE FROM referral_stats")
            deleted_referral_stats = cursor.rowcount
            logger.info(f"Удалено записей статистики рефералов: {deleted_referral_stats}")
        
        # 5. Удаляем пользователей (кроме админов)
        if admin_user_ids:
            admin_ids_placeholder = ','.join('?' * len(admin_user_ids))
            cursor.execute(f"DELETE FROM users WHERE id NOT IN ({admin_ids_placeholder})", admin_user_ids)
        else:
            cursor.execute("DELETE FROM users")
        deleted_users = cursor.rowcount
        logger.info(f"Удалено пользователей: {deleted_users}")
        
        # 6. Сбрасываем автоинкремент для всех таблиц
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'vpn_keys', 'payments', 'notification_log', 'referral_stats')")
        
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Статистика успешно обнулена!")
        print("=" * 60)
        print(f"\nУдалено:")
        print(f"  - Пользователей: {deleted_users}")
        print(f"  - VPN-ключей: {deleted_keys}")
        print(f"  - Платежей: {deleted_payments}")
        print(f"  - Уведомлений: {deleted_notifications}")
        if 'deleted_referral_stats' in locals():
            print(f"  - Статистики рефералов: {deleted_referral_stats}")
        print(f"\nАдмины сохранены: {len(admin_user_ids)}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Ошибка при обнулении статистики: {e}")
        print(f"\n❌ Ошибка: {e}")


if __name__ == '__main__':
    reset_statistics()
