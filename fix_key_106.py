#!/usr/bin/env python3
"""
Скрипт для исправления ключа 106 - назначение сервера и создание на панели.
"""
import asyncio
import logging
import sys
import uuid

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def fix_key_106():
    """Исправляет ключ 106 - создает ключи на ВСЕХ активных серверах."""
    from database.requests import (
        get_vpn_key_by_id, get_active_servers, update_vpn_key_config,
        get_user_by_id, create_vpn_key_admin
    )
    from bot.services.vpn_api import get_client
    
    key_id = 106
    
    # Получаем ключ из БД
    key = get_vpn_key_by_id(key_id)
    if not key:
        logger.error(f"Ключ {key_id} не найден в БД")
        return False
    
    logger.info(f"Найден ключ {key_id}: user_id={key['user_id']}, tariff_id={key['tariff_id']}, expires_at={key['expires_at']}")
    
    # Получаем активные серверы
    servers = get_active_servers()
    if not servers:
        logger.error("Нет доступных серверов")
        return False
    
    logger.info(f"Найдено {len(servers)} активных серверов")
    
    # Получаем данные пользователя
    user = get_user_by_id(key['user_id'])
    telegram_id = user['telegram_id']
    username = user.get('username')
    
    # Рассчитываем оставшиеся дни
    from datetime import datetime, timezone
    expires_at = key.get('expires_at')
    if expires_at:
        dt_str = str(expires_at).replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        remaining_days = max(1, (dt - now_utc).days)
    else:
        remaining_days = 30  # По умолчанию
    
    # Получаем лимит трафика
    traffic_limit_gb = (key.get('traffic_limit', 0) or 0) / (1024**3)
    
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
                logger.error(f"На сервере {server_name} нет доступных протоколов")
                continue
            
            # Берем первый inbound
            inbound = inbounds[0]
            inbound_id = inbound['id']
            
            logger.info(f"Выбран inbound: {inbound.get('remark', 'N/A')} (ID: {inbound_id}, protocol: {inbound.get('protocol', 'N/A')})")
            
            # Генерируем уникальный email для панели
            base = f"user_{username}" if username else f"user_{telegram_id}"
            suffix = uuid.uuid4().hex[:5]
            panel_email = f'{base}_{suffix}'
            
            # Получаем flow для inbound
            flow = await client.get_inbound_flow(inbound_id)
            
            logger.info(f"Создаем клиента на панели: email={panel_email}, limit={traffic_limit_gb:.1f}GB, days={remaining_days}")
            
            # Создаем клиента на панели
            res = await client.add_client(
                inbound_id=inbound_id,
                email=panel_email,
                total_gb=int(traffic_limit_gb),
                expire_days=remaining_days,
                limit_ip=1,
                enable=True,
                tg_id=str(telegram_id),
                flow=flow
            )
            
            client_uuid = res['uuid']
            
            logger.info(f"Клиент создан на панели: uuid={client_uuid}")
            
            # Для первого сервера обновляем существующий ключ 106
            if idx == 0:
                update_vpn_key_config(
                    key_id=key_id,
                    server_id=server_id,
                    panel_inbound_id=inbound_id,
                    panel_email=panel_email,
                    client_uuid=client_uuid
                )
                created_keys.append(key_id)
                logger.info(f"✅ Основной ключ {key_id} настроен на {server_name}")
            else:
                # Для остальных серверов создаем новые ключи
                new_key_id = create_vpn_key_admin(
                    user_id=key['user_id'],
                    server_id=server_id,
                    tariff_id=key['tariff_id'],
                    panel_inbound_id=inbound_id,
                    panel_email=panel_email,
                    client_uuid=client_uuid,
                    days=remaining_days,
                    traffic_limit=key.get('traffic_limit', 0) or 0
                )
                created_keys.append(new_key_id)
                logger.info(f"✅ Дополнительный ключ {new_key_id} создан на {server_name}")
            
        except Exception as e:
            logger.error(f"Ошибка при настройке на сервере {server.get('name')}: {e}", exc_info=True)
            continue
    
    if created_keys:
        logger.info(f"")
        logger.info(f"🎉 УСПЕШНО! Создано {len(created_keys)} ключей на {len(created_keys)} серверах:")
        for kid in created_keys:
            k = get_vpn_key_by_id(kid)
            if k:
                logger.info(f"   - Ключ {kid}: {k.get('server_name')} (sub_id: {k.get('sub_id')})")
        logger.info(f"")
        logger.info(f"Subscription URL: https://arcc.mooo.com:2053/sub/{key.get('sub_id')}")
        return True
    else:
        logger.error("❌ Не удалось создать ни одного ключа")
        return False

if __name__ == '__main__':
    success = asyncio.run(fix_key_106())
    sys.exit(0 if success else 1)
