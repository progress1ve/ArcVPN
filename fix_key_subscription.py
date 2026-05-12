#!/usr/bin/env python3
"""
Скрипт для исправления подписки которая не работает.
Проверяет ключ в БД и создает его на панели если нужно.
"""
import asyncio
import logging
import sys
from database.connection import get_db
from database.requests import get_active_servers, update_vpn_key_config, create_vpn_key_admin
from bot.services.vpn_api import get_client
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

async def fix_subscription(sub_id: str):
    """Исправляет подписку по sub_id."""
    
    # Находим ключ по sub_id
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT 
                vk.id, vk.user_id, vk.tariff_id, vk.server_id, vk.panel_email,
                vk.expires_at, vk.traffic_limit, vk.custom_name,
                u.telegram_id, u.username,
                t.name as tariff_name, t.traffic_limit_gb, t.duration_days
            FROM vpn_keys vk
            JOIN users u ON vk.user_id = u.id
            LEFT JOIN tariffs t ON vk.tariff_id = t.id
            WHERE vk.sub_id = ?
        """, (sub_id,))
        
        key = cursor.fetchone()
        
        if not key:
            logger.error(f"❌ Ключ с sub_id={sub_id} не найден в БД")
            return False
        
        key = dict(key)
    
    logger.info(f"Найден ключ {key['id']}: user_id={key['user_id']}, tariff_id={key['tariff_id']}, expires_at={key['expires_at']}")
    
    # Проверяем есть ли server_id и panel_email
    if key['server_id'] and key['panel_email']:
        logger.info(f"✅ Ключ {key['id']} уже настроен на сервере {key['server_id']}")
        logger.info(f"   panel_email: {key['panel_email']}")
        return True
    
    # Ключ не настроен - создаем на всех серверах
    logger.warning(f"⚠️  Ключ {key['id']} НЕ настроен на панели (server_id={key['server_id']}, panel_email={key['panel_email']})")
    
    # Получаем все активные серверы
    servers = get_active_servers()
    if not servers:
        logger.error("❌ Нет активных серверов")
        return False
    
    logger.info(f"Найдено {len(servers)} активных серверов")
    
    # Вычисляем сколько дней осталось
    from datetime import datetime
    expires_at = datetime.fromisoformat(key['expires_at'])
    now = datetime.utcnow()
    days_left = max(1, (expires_at - now).days)
    
    logger.info(f"Дней до истечения: {days_left}")
    
    # Получаем лимит трафика
    traffic_limit_bytes = key['traffic_limit'] or 0
    traffic_limit_gb = traffic_limit_bytes / (1024**3) if traffic_limit_bytes > 0 else 0
    
    logger.info(f"Лимит трафика: {traffic_limit_gb} ГБ")
    
    created_keys = []
    
    # Создаем ключи на ВСЕХ серверах
    for idx, server in enumerate(servers):
        try:
            server_id = server['id']
            server_name = server['name']
            
            logger.info(f"[{idx+1}/{len(servers)}] Настройка на сервере {server_name} (ID: {server_id})")
            
            # Подключаемся к панели
            client = await get_client(server_id)
            inbounds = await client.get_inbounds()
            
            if not inbounds:
                logger.warning(f"На сервере {server_name} нет доступных протоколов, пропускаем")
                continue
            
            # Берем первый inbound
            inbound = inbounds[0]
            inbound_id = inbound['id']
            
            logger.info(f"Выбран inbound: {inbound.get('remark', 'N/A')} (ID: {inbound_id}, protocol: {inbound.get('protocol', 'N/A')})")
            
            # Генерируем уникальный email для панели
            base = f"user_{key['username']}" if key.get('username') else f"user_{key['telegram_id']}"
            suffix = uuid.uuid4().hex[:5]
            panel_email = f'{base}_{suffix}'
            
            # Получаем flow для inbound
            flow = await client.get_inbound_flow(inbound_id)
            
            # Создаем клиента на панели
            logger.info(f"Создаем клиента на панели: email={panel_email}, limit={traffic_limit_gb}GB, days={days_left}")
            
            res = await client.add_client(
                inbound_id=inbound_id,
                email=panel_email,
                total_gb=traffic_limit_gb,
                expire_days=days_left,
                limit_ip=1,
                enable=True,
                tg_id=str(key['telegram_id']),
                flow=flow
            )
            
            client_uuid = res['uuid']
            
            logger.info(f"Клиент создан на панели: uuid={client_uuid}")
            
            # Создаем ключ в БД для этого сервера
            # Для первого сервера используем уже созданный key_id
            if idx == 0:
                update_vpn_key_config(
                    key_id=key['id'],
                    server_id=server_id,
                    panel_inbound_id=inbound_id,
                    panel_email=panel_email,
                    client_uuid=client_uuid
                )
                created_keys.append(key['id'])
                logger.info(f"✅ Основной ключ {key['id']} настроен на {server_name}")
            else:
                # Для остальных серверов создаем новые ключи
                new_key_id = create_vpn_key_admin(
                    user_id=key['user_id'],
                    server_id=server_id,
                    tariff_id=key['tariff_id'],
                    panel_inbound_id=inbound_id,
                    panel_email=panel_email,
                    client_uuid=client_uuid,
                    days=days_left,
                    traffic_limit=traffic_limit_bytes,
                    custom_name=key.get('custom_name')
                )
                created_keys.append(new_key_id)
                logger.info(f"✅ Дополнительный ключ {new_key_id} создан на {server_name}")
        
        except Exception as e:
            logger.error(f"Ошибка настройки на сервере {server.get('name')}: {e}", exc_info=True)
            continue
    
    if created_keys:
        logger.info(f"")
        logger.info(f"🎉 УСПЕШНО! Создано {len(created_keys)} ключей на {len(created_keys)} серверах:")
        logger.info(f"")
        for kid in created_keys:
            logger.info(f"   - Ключ {kid}")
        logger.info(f"")
        logger.info(f"Subscription URL: https://arcc.mooo.com:2053/sub/{sub_id}")
        return True
    else:
        logger.error(f"⚠️  Не удалось создать ни одного ключа на панелях")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 fix_key_subscription.py <sub_id>")
        print("Example: python3 fix_key_subscription.py adcf83297a3f45d78aaaa06caa008831")
        sys.exit(1)
    
    sub_id = sys.argv[1]
    success = asyncio.run(fix_subscription(sub_id))
    
    if success:
        print("\n✅ Готово! Подписка должна работать.")
    else:
        print("\n❌ Не удалось исправить подписку. Проверьте логи выше.")
