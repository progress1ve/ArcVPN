#!/usr/bin/env python3
"""
Скрипт для проверки совпадения UUID при создании ключа.
Проверяет:
1. UUID который мы отправляем в панель
2. UUID который панель реально сохранила
3. UUID который мы сохраняем в БД
"""
import asyncio
import logging
import sys
import json
import uuid as uuid_module

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_uuid_matching():
    """Проверяет совпадение UUID при создании клиента."""
    
    from database.requests import get_active_servers
    from bot.services.vpn_api import get_client
    
    print("="*70)
    print("  ПРОВЕРКА СОВПАДЕНИЯ UUID ПРИ СОЗДАНИИ КЛИЕНТА")
    print("="*70)
    print()
    
    servers = get_active_servers()
    if not servers:
        print("❌ Нет активных серверов")
        return
    
    test_server = servers[0]
    print(f"Тестовый сервер: {test_server['name']} (ID: {test_server['id']})")
    print()
    
    client = await get_client(test_server['id'])
    inbounds = await client.get_inbounds()
    
    if not inbounds:
        print("❌ Нет inbounds")
        return
    
    inbound = inbounds[0]
    inbound_id = inbound['id']
    protocol = inbound.get('protocol', 'unknown')
    
    print(f"Inbound: {inbound.get('remark', 'N/A')}")
    print(f"  ID: {inbound_id}")
    print(f"  Protocol: {protocol}")
    print()
    
    # Генерируем тестовый email
    test_email = f"test_uuid_check_{uuid_module.uuid4().hex[:8]}"
    
    # ===== ШАГ 1: Создаем клиента =====
    print("📝 ШАГ 1: Создание клиента на панели")
    print("-" * 70)
    
    # Получаем flow
    flow = await client.get_inbound_flow(inbound_id)
    print(f"Flow: {flow}")
    
    print(f"Email: {test_email}")
    
    # Создаем клиента
    result = await client.add_client(
        inbound_id=inbound_id,
        email=test_email,
        total_gb=1,
        expire_days=1,
        limit_ip=1,
        enable=True,
        tg_id="test_123",
        flow=flow
    )
    
    returned_uuid = result['uuid']
    print(f"✅ Клиент создан")
    print(f"   UUID возвращенный add_client: {returned_uuid}")
    print()
    
    # ===== ШАГ 2: Проверяем клиента в панели =====
    print("🔍 ШАГ 2: Проверка клиента в панели")
    print("-" * 70)
    
    # Получаем inbounds снова чтобы найти клиента
    inbounds_after = await client.get_inbounds()
    
    found_client = None
    for ib in inbounds_after:
        if ib['id'] == inbound_id:
            settings_raw = ib.get('settings', '{}')
            if isinstance(settings_raw, str):
                settings = json.loads(settings_raw)
            else:
                settings = settings_raw
            
            clients_list = settings.get('clients', [])
            for c in clients_list:
                if c.get('email') == test_email:
                    found_client = c
                    break
    
    if not found_client:
        print("❌ Клиент не найден в inbound!")
        print("   Возможно панель использует другую структуру данных")
    else:
        print(f"✅ Клиент найден в панели")
        
        # Определяем поле UUID в зависимости от протокола
        if protocol == 'trojan':
            actual_uuid = found_client.get('password', 'N/A')
            uuid_field = 'password'
        elif protocol == 'shadowsocks':
            actual_uuid = found_client.get('password', 'N/A')
            uuid_field = 'password'
        else:
            actual_uuid = found_client.get('id', 'N/A')
            uuid_field = 'id'
        
        print(f"   UUID в панели (поле '{uuid_field}'): {actual_uuid}")
        print(f"   Email: {found_client.get('email')}")
        print(f"   Enable: {found_client.get('enable')}")
        print(f"   Limit IP: {found_client.get('limitIp')}")
        print(f"   TG ID: {found_client.get('tgId')}")
        print()
        
        # ===== ШАГ 3: Сравниваем UUID =====
        print("🎯 ШАГ 3: Сравнение UUID")
        print("-" * 70)
        
        print(f"UUID возвращенный add_client: {returned_uuid}")
        print(f"UUID реально в панели:       {actual_uuid}")
        print()
        
        if returned_uuid == actual_uuid:
            print("✅ UUID СОВПАДАЮТ!")
            print("   Проблема НЕ в функции add_client")
        else:
            print("❌ UUID НЕ СОВПАДАЮТ!")
            print("   ЭТО КОРНЕВАЯ ПРИЧИНА ПРОБЛЕМЫ!")
            print()
            print("   Возможные причины:")
            print("   1. Панель игнорирует переданный UUID и генерирует свой")
            print("   2. Ошибка в парсинге ответа панели")
            print("   3. Панель использует другой формат UUID")
    
    print()
    
    # ===== ШАГ 4: Проверяем get_client_config =====
    print("🔍 ШАГ 4: Проверка get_client_config")
    print("-" * 70)
    
    try:
        config = await client.get_client_config(test_email)
        if config:
            print(f"✅ Конфиг получен")
            print(f"   UUID в конфиге: {config.get('uuid', 'N/A')}")
        else:
            print("⚠️ Конфиг не получен")
    except Exception as e:
        print(f"❌ Ошибка получения конфига: {e}")
    
    print()
    
    # ===== Очистка =====
    print("🧹 Очистка: Удаление тестового клиента")
    print("-" * 70)
    
    try:
        # Пробуем удалить по UUID который вернул add_client
        deleted = await client.delete_client(inbound_id, returned_uuid)
        if deleted:
            print(f"✅ Клиент удален (по UUID: {returned_uuid})")
        else:
            # Если не удалился, пробуем по фактическому UUID
            if found_client and actual_uuid != returned_uuid:
                deleted2 = await client.delete_client(inbound_id, actual_uuid)
                if deleted2:
                    print(f"✅ Клиент удален (по UUID: {actual_uuid})")
                else:
                    print("⚠️ Не удалось удалить клиента")
            else:
                print("⚠️ Не удалось удалить клиента")
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
    
    print()
    print("="*70)
    print("  ТЕСТ ЗАВЕРШЕН")
    print("="*70)

if __name__ == '__main__':
    try:
        asyncio.run(test_uuid_matching())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        logger.exception("Критическая ошибка:")
        sys.exit(1)
