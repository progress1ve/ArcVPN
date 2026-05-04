"""
Утилиты для работы с датой и временем.
"""
from datetime import datetime, timezone
import pytz

# Московская временная зона
MSK = pytz.timezone('Europe/Moscow')


def now_msk() -> datetime:
    """Возвращает текущее время в МСК."""
    return datetime.now(MSK)


def utc_to_msk(dt: datetime) -> datetime:
    """
    Конвертирует UTC datetime в МСК.
    
    Args:
        dt: datetime объект (naive или aware) или строка ISO формата
        
    Returns:
        datetime в МСК timezone
    """
    if dt is None:
        return None
    
    # Если передана строка, парсим её
    if isinstance(dt, str):
        dt = parse_db_datetime(dt)
        if dt is None:
            return None
    
    if dt.tzinfo is None:
        # Если naive, считаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(MSK)


def utc_to_local(dt: datetime) -> datetime:
    """
    Конвертирует UTC datetime в локальное время (МСК).
    Алиас для utc_to_msk() для обратной совместимости.
    
    Args:
        dt: datetime объект (naive или aware)
        
    Returns:
        datetime в МСК timezone
    """
    return utc_to_msk(dt)


def format_datetime_msk(dt: datetime, format_str: str = "%d.%m.%Y %H:%M:%S") -> str:
    """
    Форматирует datetime в строку с конвертацией в МСК.
    
    Args:
        dt: datetime объект или строка ISO формата
        format_str: Формат строки
        
    Returns:
        Отформатированная строка
    """
    if dt is None:
        return "Неизвестно"
    
    # Если передана строка, парсим её
    if isinstance(dt, str):
        dt = parse_db_datetime(dt)
        if dt is None:
            return "Неизвестно"
    
    dt_msk = utc_to_msk(dt)
    return dt_msk.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M:%S") -> str:
    """
    Форматирует datetime в строку с конвертацией в МСК.
    Алиас для format_datetime_msk() для обратной совместимости.
    
    Args:
        dt: datetime объект
        format_str: Формат строки
        
    Returns:
        Отформатированная строка
    """
    return format_datetime_msk(dt, format_str)


def format_date(dt: datetime, format_str: str = "%d-%m-%Y") -> str:
    """
    Форматирует datetime в строку даты (без времени) с конвертацией в МСК.
    
    Args:
        dt: datetime объект или строка ISO формата
        format_str: Формат строки (по умолчанию ДД-ММ-ГГГГ)
        
    Returns:
        Отформатированная строка даты
    """
    if dt is None:
        return "—"
    
    # Если передана строка, парсим её
    if isinstance(dt, str):
        dt = parse_db_datetime(dt)
        if dt is None:
            return "—"
    
    dt_msk = utc_to_msk(dt)
    return dt_msk.strftime(format_str)


def parse_db_datetime(dt_str: str) -> datetime:
    """
    Парсит datetime из БД (SQLite хранит в UTC).
    
    Args:
        dt_str: Строка datetime из БД
        
    Returns:
        datetime объект в UTC
    """
    if not dt_str:
        return None
    
    try:
        # SQLite возвращает строку в формате 'YYYY-MM-DD HH:MM:SS'
        dt = datetime.fromisoformat(str(dt_str))
        
        # Помечаем как UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except (ValueError, TypeError):
        return None
