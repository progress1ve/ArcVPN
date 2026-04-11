"""
Утилиты для работы с группами тарифов в пользовательской части.
"""
from database.requests import (
    get_all_groups,
    get_groups_count,
    get_tariffs_by_group,
    get_active_servers_by_group,
    get_tariff_group_id,
    get_all_tariffs,
    get_active_servers
)


def build_groups_data_for_tariffs():
    """
    Формирует данные для группированного отображения тарифов.
    
    Группа показывается ТОЛЬКО если в ней есть И активные тарифы И активные серверы (К1).
    При 1 группе — возвращает None (без группировки).
    
    Returns:
        list[dict] или None: Список словарей {'group': {...}, 'tariffs': [...]}
                             или None если группировка не нужна
    """
    groups_count = get_groups_count()
    if groups_count <= 1:
        return None
    
    groups = get_all_groups()
    groups_data = []
    
    for group in groups:
        tariffs = get_tariffs_by_group(group['id'])
        servers = get_active_servers_by_group(group['id'])
        
        # К1: группа видна только если есть И тарифы И серверы
        if tariffs and servers:
            groups_data.append({
                'group': group,
                'tariffs': tariffs
            })
    
    # Если осталась только 1 видимая группа — не показываем заголовки
    if len(groups_data) <= 1:
        return None
    
    return groups_data


def get_tariffs_for_renewal(key_tariff_id: int):
    """
    Получает тарифы, доступные для продления ключа.
    При >1 группе — только тарифы из группы текущего ключа.
    При 1 группе — все активные тарифы.
    
    Args:
        key_tariff_id: ID тарифа текущего ключа
        
    Returns:
        Список тарифов для продления
    """
    groups_count = get_groups_count()
    
    if groups_count <= 1:
        return get_all_tariffs(include_hidden=False)
    
    # Фильтруем по группе ключа
    group_id = get_tariff_group_id(key_tariff_id)
    return get_tariffs_by_group(group_id)


def get_servers_for_key(key_tariff_id: int):
    """
    Получает серверы, доступные для ключа (замена или создание).
    При >1 группе — только серверы из группы тарифа.
    При 1 группе — все активные серверы.
    
    Args:
        key_tariff_id: ID тарифа ключа
        
    Returns:
        Список серверов
    """
    groups_count = get_groups_count()
    
    if groups_count <= 1:
        return get_active_servers()
    
    # Фильтруем по группе тарифа
    group_id = get_tariff_group_id(key_tariff_id)
    return get_active_servers_by_group(group_id)
