#!/usr/bin/env python3
"""
Диагностический скрипт для поиска причины проблемы с автоматическим созданием ключей.
Проверяет все возможные точки отказа.
"""
import asyncio
import logging
import sys
from database.connection import get_db
from database.requests import get_active_servers, get_user_by_id
from bot.services.vpn_api import get_client

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_payment_system():
    """Диагностирует систему оплаты и создания ключей."""
    
    print("="*70)
    print("  ДИАГНОСТИКА СИСТЕМЫ АВТОМАТИЧЕСКОГО СОЗДАНИЯ КЛЮЧЕЙ")
    print("="*70)
    print()
    
    # 1. Проверка активных серверов
    print("1️⃣  ПРОВЕРКА АКТИВНЫХ СЕРВЕРОВ")
    print("-" * 70)
    
    servers = get_active_servers()
    if not servers:
        print("❌ НЕТ АКТИВНЫХ СЕРВЕРОВ!")
        print("   Решение: Добавьте серверы через админ-панель бота")
        return False
    
    print(f"✅ Найдено {len(servers)} активных серверов:")
    for server in servers:
        print(f"   • ID: {server['id']}, Название: {server['name']}, Host: {server['host']}")
    print()
    
    # 2. Проверка подключения к каждому серверу
    print("2️⃣  ПРОВЕРКА ПОДКЛЮЧЕНИЯ К ПАНЕЛЯМ")
    print("-" * 70)
    
    working_servers = []
    failed_servers = []
    
    for server in servers:
        server_id = server['id']
        server_name = server['name']
        
        try:
            print(f"Подключение к {server_name}...", end=" ")
            client = await get_client(server_id)
            print("✅ OK")
            
            # Проверяем inbounds
            print(f"  Получение inbounds...", end=" ")
            inbounds = await client.get_inbounds()
            
            if not inbounds:
                print("❌ НЕТ INBOUNDS!")
                failed_servers.append({
                    'server': server_name,
                    'reason': 'Нет доступных inbounds'
                })
                continue
            
            print(f"✅ OK ({len(inbounds)} inbound(s))")
            
            # Показываем inbounds
            for inbound in inbounds:
                print(f"     - ID: {inbound.get('id')}, "
                      f"Remark: {inbound.get('remark', 'N/A')}, "
                      f"Protocol: {inbound.get('protocol', 'N/A')}")
            
            working_servers.append(server_name)
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            failed_servers.append({
                'server': server_name,
                'reason': str(e)
            })
    
    print()
    
    if not working_servers:
        print("❌ НИ ОДИН СЕРВЕР НЕ ДОСТУПЕН!")
        print()
        print("Причины:")
        for fail in failed_servers:
            print(f"   • {fail['server']}: {fail['reason']}")
        return False
    
    print(f"✅ Работающих серверов: {len(working_servers)}/{len(servers)}")
    if failed_servers:
        print(f"⚠️  Недоступных серверов: {len(failed_servers)}")
        for fail in failed_servers:
            print(f"   • {fail['server']}: {fail['reason']}")
    print()
    
    # 3. Проверка последних платежей
    print("3️⃣  ПРОВЕРКА ПОСЛЕДНИХ ПЛАТЕЖЕЙ")
    print("-" * 70)
    
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                p.id, p.order_id, p.user_id, p.tariff_id, p.vpn_key_id,
                p.payment_type, p.status, p.paid_at,
                vk.server_id, vk.panel_email,
                u.telegram_id, u.username
            FROM payments p
            LEFT JOIN vpn_keys vk ON p.vpn_key_id = vk.id
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.status = 'paid' AND p.payment_type != 'trial'
            ORDER BY p.paid_at DESC
            LIMIT 5
        """)
        
        payments = cursor.fetchall()
        
        if not payments:
            print("⚠️  Нет платежей в системе")
            print()
            return True
        
        print(f"Последние {len(payments)} платежей:")
        print()
        
        for p in payments:
            payment = dict(p)
            print(f"📦 Payment ID: {payment['id']}")
            print(f"   Order ID: {payment['order_id']}")
            print(f"   User: {payment['telegram_id']} (@{payment.get('username', 'N/A')})")
            print(f"   Tariff ID: {payment['tariff_id']}")
            print(f"   VPN Key ID: {payment['vpn_key_id']}")
            print(f"   Payment Type: {payment['payment_type']}")
            print(f"   Paid At: {payment['paid_at']}")
            
            # Проверяем настроен ли ключ
            if payment['vpn_key_id']:
                if payment['server_id'] and payment['panel_email']:
                    print(f"   ✅ Ключ настроен: server_id={payment['server_id']}, email={payment['panel_email']}")
                else:
                    print(f"   ❌ КЛЮЧ НЕ НАСТРОЕН: server_id={payment['server_id']}, email={payment['panel_email']}")
                    print(f"   ⚠️  ПРОБЛЕМА НАЙДЕНА!")
            else:
                print(f"   ⚠️  Нет привязанного ключа")
            
            print()
    
    # 4. Проверка логики создания ключей
    print("4️⃣  ПРОВЕРКА ЛОГИКИ СОЗДАНИЯ КЛЮЧЕЙ")
    print("-" * 70)
    
    # Проверяем что функции импортируются
    try:
        from database.requests import create_vpn_key_admin, update_vpn_key_config
        print("✅ Функции create_vpn_key_admin и update_vpn_key_config импортируются")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    
    # Проверяем что get_client работает
    try:
        from bot.services.vpn_api import get_client
        print("✅ Функция get_client импортируется")
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    
    print()
    
    # 5. Тестовое создание клиента
    print("5️⃣  ТЕСТОВОЕ СОЗДАНИЕ КЛИЕНТА НА ПАНЕЛИ")
    print("-" * 70)
    
    if not working_servers:
        print("⚠️  Пропущено (нет доступных серверов)")
        print()
        return True
    
    # Берем первый рабочий сервер
    test_server = servers[0]
    print(f"Тестовый сервер: {test_server['name']}")
    
    try:
        client = await get_client(test_server['id'])
        inbounds = await client.get_inbounds()
        
        if not inbounds:
            print("❌ Нет inbounds для теста")
            return True
        
        inbound = inbounds[0]
        inbound_id = inbound['id']
        
        print(f"Тестовый inbound: {inbound.get('remark', 'N/A')} (ID: {inbound_id})")
        
        # Получаем flow
        flow = await client.get_inbound_flow(inbound_id)
        print(f"Flow: {flow}")
        
        # Генерируем тестовый email
        import uuid
        test_email = f"test_diagnostic_{uuid.uuid4().hex[:8]}"
        
        print(f"Создание тестового клиента: {test_email}...", end=" ")
        
        result = await client.add_client(
            inbound_id=inbound_id,
            email=test_email,
            total_gb=1,
            expire_days=1,
            limit_ip=1,
            enable=True,
            tg_id="0",
            flow=flow
        )
        
        print(f"✅ OK (UUID: {result['uuid']})")
        
        # Удаляем тестового клиента
        print(f"Удаление тестового клиента...", end=" ")
        await client.delete_client(inbound_id, result['uuid'])
        print("✅ OK")
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        logger.exception("Детали ошибки:")
        return False
    
    print()
    
    # Итоги
    print("="*70)
    print("  ИТОГИ ДИАГНОСТИКИ")
    print("="*70)
    print()
    
    if working_servers and len(working_servers) == len(servers):
        print("✅ ВСЕ СИСТЕМЫ РАБОТАЮТ НОРМАЛЬНО")
        print()
        print("Возможные причины проблемы:")
        print("1. Ошибка возникает только при определенных условиях")
        print("2. Проблема была временной (сервер был недоступен)")
        print("3. Ошибка в логике обработки конкретного способа оплаты")
        print()
        print("Рекомендации:")
        print("• Проверьте логи бота во время следующей оплаты")
        print("• Используйте fix_key_subscription.py для исправления сломанных ключей")
    else:
        print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
        print()
        if failed_servers:
            print("Недоступные серверы:")
            for fail in failed_servers:
                print(f"   • {fail['server']}: {fail['reason']}")
        print()
        print("Рекомендации:")
        print("• Проверьте настройки серверов в админ-панели")
        print("• Убедитесь что панели 3X-UI доступны")
        print("• Проверьте учетные данные для подключения")
    
    return True

if __name__ == '__main__':
    try:
        asyncio.run(diagnose_payment_system())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        logger.exception("Критическая ошибка:")
        sys.exit(1)
