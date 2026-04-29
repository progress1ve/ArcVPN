"""
Утилиты для работы с датами и временем.

Конвертация UTC времени из БД в локальное время согласно настройкам.
"""
from datetime import datetime
from typing import Optional
import pytz
from config import TIMEZONE

# Кэшируем объекты timezone
UTC = pytz.UTC
LOCAL_TZ = pytz.timezone(TIMEZONE)


def utc_to_local(utc_dt: datetime) -> datetime:
    """
    Конвертирует UTC datetime в локальное время.
    
    Args:
        utc_dt: datetime объект в UTC (naive или aware)
        
    Returns:
        datetime объект в локальном часовом поясе
    """
    # Если datetime naive (без timezone), считаем что это UTC
    if utc_dt.tzinfo is None:
        utc_dt = UTC.localize(utc_dt)
    
    # Конвертируем в локальное время
    return utc_dt.astimezone(LOCAL_TZ)


def format_datetime(dt_string: Optional[str], format_str: str = '%d-%m-%Y %H:%M') -> str:
    """
    Форматирует строку datetime из БД в локальное время.
    
    Args:
        dt_string: Строка datetime из БД (ISO format, UTC)
        format_str: Формат вывода (по умолчанию 'ДД-ММ-ГГГГ ЧЧ:ММ')
        
    Returns:
        Отформатированная строка в локальном времени
    """
    if not dt_string:
        return '—'
    
    try:
        # Парсим ISO формат из БД
        utc_dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        
        # Конвертируем в локальное время
        local_dt = utc_to_local(utc_dt)
        
        # Форматируем
        return local_dt.strftime(format_str)
    except (ValueError, AttributeError) as e:
        return dt_string  # Возвращаем как есть если не удалось распарсить


def format_date(dt_string: Optional[str]) -> str:
    """
    Форматирует дату без времени (ДД-ММ-ГГГГ).
    
    Args:
        dt_string: Строка datetime из БД
        
    Returns:
        Дата в формате ДД-ММ-ГГГГ
    """
    return format_datetime(dt_string, '%d-%m-%Y')


def format_datetime_full(dt_string: Optional[str]) -> str:
    """
    Форматирует дату и время полностью (ДД-ММ-ГГГГ ЧЧ:ММ:СС).
    
    Args:
        dt_string: Строка datetime из БД
        
    Returns:
        Дата и время в формате ДД-ММ-ГГГГ ЧЧ:ММ:СС
    """
    return format_datetime(dt_string, '%d-%m-%Y %H:%M:%S')
