#!/usr/bin/env python3
"""
Тестовый скрипт для проверки реферальной системы
"""
import sys
sys.path.insert(0, '/root/ArcVPN')

from database.requests import (
    get_user_by_id,
    get_user_referrer,
    is_referral_enabled,
    get_user_balance,
)

def test_referral_system():
    print("=" * 60)
    print("ТЕСТ РЕФЕРАЛЬНОЙ СИСТЕМЫ")
    print("=" * 60)
    
    # Проверяем настройки
    print("\n1. Проверка настроек:")
    enabled = is_referral_enabled()
    print(f"   Реферальная система включена: {enabled}")
    
    # Проверяем пользователя 9 (друг)
    print("\n2. Проверка пользователя 9 (друг):")
    user9 = get_user_by_id(9)
    if user9:
        print(f"   ID: {user9['id']}")
        print(f"   Telegram ID: {user9['telegram_id']}")
        print(f"   Username: {user9.get('username', 'N/A')}")
        print(f"   Referred by: {user9.get('referred_by', 'N/A')}")
        print(f"   Balance: {user9.get('personal_balance', 0)} копеек")
    else:
        print("   ❌ Пользователь 9 не найден!")
        return
    
    # Проверяем реферера
    print("\n3. Проверка реферера:")
    referrer_id = get_user_referrer(9)
    print(f"   Referrer ID для user_id=9: {referrer_id}")
    
    if referrer_id:
        referrer = get_user_by_id(referrer_id)
        if referrer:
            print(f"   Реферер ID: {referrer['id']}")
            print(f"   Реферер Telegram ID: {referrer['telegram_id']}")
            print(f"   Реферер Username: {referrer.get('username', 'N/A')}")
            print(f"   Реферер Balance: {referrer.get('personal_balance', 0)} копеек")
        else:
            print(f"   ❌ Реферер с ID {referrer_id} не найден!")
    else:
        print("   ❌ У пользователя 9 нет реферера!")
    
    # Проверяем пользователя 1 (вы)
    print("\n4. Проверка пользователя 1 (вы):")
    user1 = get_user_by_id(1)
    if user1:
        print(f"   ID: {user1['id']}")
        print(f"   Telegram ID: {user1['telegram_id']}")
        print(f"   Username: {user1.get('username', 'N/A')}")
        print(f"   Balance: {user1.get('personal_balance', 0)} копеек")
    else:
        print("   ❌ Пользователь 1 не найден!")
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ:")
    if enabled and referrer_id == 1:
        print("✅ Все настроено правильно!")
        print("   - Реферальная система включена")
        print("   - У пользователя 9 есть реферер (ID=1)")
        print("   - При оплате должно начисляться 5000 копеек")
    else:
        print("❌ Есть проблемы:")
        if not enabled:
            print("   - Реферальная система ОТКЛЮЧЕНА")
        if referrer_id != 1:
            print(f"   - Неправильный реферер: {referrer_id} (ожидается 1)")
    print("=" * 60)

if __name__ == "__main__":
    test_referral_system()
