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
        dt: datetime объект (naive или aware)
        
    Returns:
        datetime в МСК timezone
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Если naive, считаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(MSK)


def format_datetime_msk(dt: datetime, format_str: str = "%d.%m.%Y %H:%M:%S") -> str:
    """
    Форматирует datetime в строку с конвертацией в МСК.
    
    Args:
        dt: datetime объект
        format_str: Формат строки
        
    Returns:
        Отформатированная строка
    """
    if dt is None:
        return "Неизвестно"
    
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
