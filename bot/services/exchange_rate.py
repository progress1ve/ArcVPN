"""
Сервис курсов валют.

Получение курса USD/RUB от ЦБ РФ с fallback в БД.
"""
import logging
import aiohttp

from database.requests import get_exchange_rate, update_exchange_rate

logger = logging.getLogger(__name__)


async def get_usd_rub_rate() -> int:
    """
    Получить курс USD/RUB в копейках.
    Сначала пробует ЦБ РФ, при ошибке берёт из БД (fallback).
    
    Returns:
        Курс USD/RUB в копейках (например, 9500 = 95.00 руб)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://www.cbr-xml-daily.ru/daily_json.js',
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                data = await resp.json(content_type=None)
                rate = data['Valute']['USD']['Value']
                rate_cents = int(rate * 100)
                update_exchange_rate('USD_RUB', rate_cents)
                return rate_cents
    except Exception as e:
        logger.error(f"Failed to get exchange rate from CB: {e}")
        return get_exchange_rate('USD_RUB') or 9500
