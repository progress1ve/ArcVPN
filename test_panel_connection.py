#!/usr/bin/env python3
"""
Простой тест подключения к панели 3X-UI.
"""
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection():
    """Тестирует подключение к панели."""
    
    print("="*70)
    print("  ТЕСТ ПОДКЛЮЧЕНИЯ К ПАНЕЛИ 3X-UI")
    print("="*70)
    print()
    
    # Получаем сервер из БД
    from database.requests import get_active_servers
    
    servers = get_active_servers()
    
    if not servers:
        print("❌ Нет активных серверов в БД")
        return False
    
    server = servers[0]
    print(f"Сервер: {server['name']}")
    print(f"Host: {server['host']}")
    print(f"Port: {server['port']}")
    print(f"Protocol: {server['protocol']}")
    print()
    
    # Пытаемся подключиться
    print("Попытка подключения...")
    print()
    
    try:
        from bot.services.vpn_api import get_client
        
        client = await get_client(server['id'])
        
        print("✅ Подключение успешно!")
        print()
        
        # Получаем inbounds
        print("Получение списка inbounds...")
        inbounds = await client.get_inbounds()
        
        if not inbounds:
            print("⚠️  Нет inbounds на сервере")
            return False
        
        print(f"✅ Получено {len(inbounds)} inbound(s):")
        print()
        
        for inbound in inbounds:
            print(f"  • ID: {inbound.get('id')}")
            print(f"    Remark: {inbound.get('remark', 'N/A')}")
            print(f"    Protocol: {inbound.get('protocol', 'N/A')}")
            print(f"    Port: {inbound.get('port', 'N/A')}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        print()
        logger.exception("Детали ошибки:")
        return False

if __name__ == '__main__':
    try:
        success = asyncio.run(test_connection())
        
        if success:
            print("="*70)
            print("✅ ВСЕ РАБОТАЕТ!")
            print("="*70)
        else:
            print("="*70)
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
            print("="*70)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        logger.exception("Критическая ошибка:")
        sys.exit(1)
