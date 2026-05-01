"""
Сервис биллинга — обработка платежей.

Проверка подписей, создание/продление ключей после оплаты.
Создание QR-платежей через ЮКасса REST API.
Реферальные начисления.
"""
import hmac
import hashlib
import logging
import uuid
import base64
import aiohttp
import qrcode
import io
import math
from typing import Optional, Dict, Any, Tuple

from database.requests import (
    find_order_by_order_id, complete_order, is_order_already_paid,
    get_vpn_key_by_id, extend_vpn_key, get_setting,
    get_yookassa_credentials,
    is_referral_enabled, get_referral_reward_type, get_active_referral_levels,
    get_user_referrer, get_user_referral_coefficient, get_user_balance,
    add_to_balance, deduct_from_balance, add_days_to_first_active_key,
    update_referral_stat, get_user_by_id
)
from bot.services.exchange_rate import get_usd_rub_rate

logger = logging.getLogger(__name__)

STAR_TO_USD = 0.013
USDT_TO_USD = 1.0

YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"

# Алфавит для Base62 кодирования
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"




def encode_base62(data: bytes) -> str:
    """
    Кодирует бинарные данные в Base62.
    
    Используется для формирования подписи callback от Ya.Seller.
    
    Args:
        data: Бинарные данные
        
    Returns:
        Строка в формате Base62
    """
    if not data:
        return ""
    
    num = int.from_bytes(data, 'big')
    if num == 0:
        return "0"
    
    res = []
    while num > 0:
        num, rem = divmod(num, 62)
        res.append(ALPHABET[rem])
    
    return "".join(reversed(res))


def verify_crypto_signature(data_part: str, received_signature: str, secret_key: str) -> bool:
    """
    Проверяет подпись callback от криптопроцессинга Ya.Seller.
    
    Подпись = Base62(HMAC-SHA256(data_part, secret_key)[:11]).
    
    Алгоритм согласно документации https://yadreno.ru/seller/integration.php:
    1. Вычисляем HMAC-SHA256 от data_part с секретным ключом
    2. Берем первые 11 байт бинарного результата
    3. Кодируем в Base62
    
    Args:
        data_part: Все сегменты кроме последнего (например bill1-aZ1-bY-1-_-1000)
        received_signature: Полученная подпись (последний сегмент)
        secret_key: Секретный ключ продавца
        
    Returns:
        True если подпись валидна
    """
    # Вычисляем HMAC-SHA256
    h = hmac.new(
        secret_key.encode('utf-8'),
        data_part.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Берем первые 11 байт и кодируем в Base62
    truncated = h[:11]
    expected = encode_base62(truncated)
    
    # Сравниваем подписи
    is_valid = hmac.compare_digest(expected, received_signature)
    
    if not is_valid:
        logger.warning(f"Неверная подпись! expected={expected}, received={received_signature}")
    
    return is_valid


def parse_crypto_callback(start_param: str) -> Optional[Dict[str, Any]]:
    """
    Парсит параметр start из callback криптопроцессинга.
    
    Формат: bill1-ORDER_ID-ITEM_ID-TARIFF-PROMO-PRICE-SIGNATURE
    
    Args:
        start_param: Значение параметра start из deep link
        
    Returns:
        Словарь с полями: order_id, item_id, tariff, promo, price, signature, data_part
        или None если формат неверный
    """
    if not start_param or not start_param.startswith('bill'):
        return None
    
    parts = start_param.split('-')
    
    # Минимум: bill1-ORDER_ID-ITEM_ID-TARIFF-PROMO-PRICE-SIGNATURE (7 частей)
    if len(parts) < 7:
        logger.warning(f"Неверный формат callback: {start_param} (частей: {len(parts)})")
        return None
    
    try:
        # Последняя часть — подпись
        signature = parts[-1]
        # Остальное — данные для проверки подписи
        data_part = start_param.rsplit('-', 1)[0]
        
        return {
            'prefix': parts[0],        # bill1 или bill0
            'order_id': parts[1],      # наш invoice_id
            'item_id': parts[2],       # ID товара в Ya.Seller
            'tariff': parts[3],        # номер тарифа (1-9) или '_'
            'promo': parts[4],         # промокод или '_'
            'price': int(parts[5]) if parts[5] != '_' else 0,  # цена в центах
            'signature': signature,
            'data_part': data_part
        }
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback: {e}")
        return None


async def process_payment_order(order_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Универсальная обработка успешного ордера (Crypto или Stars).
    Закрывает ордер, продлевает ключ или создаёт черновик.
    Также обрабатывает пополнение баланса (когда tariff_id=None и vpn_key_id=None).
    
    Returns:
        (success, message_text, order_data)
    """
    from database.requests import (
        is_order_already_paid, find_order_by_order_id, complete_order, 
        extend_vpn_key, create_initial_vpn_key, update_payment_key_id,
        add_to_balance, get_user_balance
    )
    from bot.services.user_locks import user_locks
    
    # 1. Проверка на дубликат (на всякий случай, если вызывающий не проверил)
    if is_order_already_paid(order_id):
        # Получаем ордер чтобы вернуть контекст
        order = find_order_by_order_id(order_id)
        return True, "✅ Этот платёж уже был обработан ранее.", order

    # 2. Поиск ордера
    order = find_order_by_order_id(order_id)
    if not order:
        logger.warning(f"Ордер не найден: {order_id}")
        return False, "⚠️ Ордер не найден. Обратитесь в поддержку.", None
    
    # 3. Проверяем, это пополнение баланса или покупка подписки
    if order.get('tariff_id') is None and order.get('vpn_key_id') is None:
        # Это пополнение баланса
        logger.info(f"Обработка пополнения баланса: order_id={order_id}")
        
        user_internal_id = order['user_id']
        amount_cents = order.get('amount_cents', 0)
        
        # Пополняем баланс
        async with user_locks[user_internal_id]:
            add_to_balance(user_internal_id, amount_cents)
        
        # Закрываем заказ
        if not complete_order(order_id):
            if order['status'] == 'paid':
                pass
            else:
                return False, "❌ Ошибка обновления статуса платежа.", order
        
        logger.info(f"Баланс пополнен на {amount_cents} коп для user {user_internal_id} (order {order_id})")
        
        return True, f"✅ Баланс успешно пополнен на {amount_cents // 100} ₽!", order
    
    # 4. Закрываем ордер (для покупки подписки)
    if not complete_order(order_id):
        # Если статус уже paid, process_payment_order вызван повторно - обрабатываем как успех
        if order['status'] == 'paid':
             pass
        else:
             return False, "❌ Ошибка обновления статуса платежа.", order
    
    logger.info(f"Order {order_id} processed (paid)")

    user_internal_id = order['user_id']
    days = order.get('period_days') or order.get('duration_days') or 30

    if order['vpn_key_id']:
        if days and extend_vpn_key(order['vpn_key_id'], days):
            logger.info(f"Ключ {order['vpn_key_id']} продлён на {days} дней (order={order_id})")
            
            from bot.services.vpn_api import push_key_to_panel, restore_traffic_limit_in_db
            # Восстанавливаем лимит трафика в БД (без обращения к панели)
            restore_traffic_limit_in_db(order['vpn_key_id'])
            # Пушим ВСЕ данные из БД на панель одним вызовом (сброс up/down + обновление)
            await push_key_to_panel(order['vpn_key_id'], reset_traffic=True)
            
            if order.get('payment_type') == 'crypto':
                await process_referral_reward(user_internal_id, days, order.get('amount_cents', 0), 'crypto')
            
            return True, f"✅ Оплата прошла успешно!\n\nВаш ключ продлён на {days} дней.", order
        else:
            logger.error(f"Не удалось продлить ключ {order['vpn_key_id']} после оплаты!")
            return True, "✅ Оплата принята!\n\n⚠️ Возникла проблема с продлением. Мы разберёмся.", order
    else:
        if not order.get('tariff_id'):
            logger.error(f"Ордер {order_id}: тариф не найден или неактивен в БД (received tariff_id could not be resolved).")
            from bot.errors import TariffNotFoundError
            raise TariffNotFoundError()
        
        try:
            days = order.get('period_days') or order.get('duration_days') or 30
            # Получаем лимит трафика из тарифа
            from database.requests import get_tariff_by_id as _get_tariff
            _tariff = _get_tariff(order['tariff_id'])
            traffic_limit_bytes = (_tariff.get('traffic_limit_gb', 0) or 0) * (1024**3) if _tariff else 0
            key_id = create_initial_vpn_key(order['user_id'], order['tariff_id'], days, traffic_limit=traffic_limit_bytes)
            
            update_payment_key_id(order_id, key_id)
            order['vpn_key_id'] = key_id
            
            logger.info(f"Создан черновик ключа {key_id} для заказа {order_id}")
            
            if order.get('payment_type') == 'crypto':
                await process_referral_reward(user_internal_id, days, order.get('amount_cents', 0), 'crypto')
            
            return True, "✅ Оплата прошла успешно!", order
            
        except Exception as e:
            logger.error(f"Ошибка создания черновика ключа: {e}")
            return True, "✅ Оплата принята, но произошла ошибка при создании ключа. Обратитесь в поддержку.", order


async def process_crypto_payment(start_param: str, user_id: Optional[int] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Обрабатывает платёж от криптопроцессинга (parse + verify + confirm).
    """
    # Парсим callback
    parsed = parse_crypto_callback(start_param)
    if not parsed:
        return False, "❌ Неверный формат платёжных данных", None
    
    # Получаем секретный ключ
    secret_key = get_setting('crypto_secret_key')
    if not secret_key:
        logger.error("Секретный ключ криптопроцессинга не настроен!")
        return False, "❌ Ошибка конфигурации. Обратитесь в поддержку.", None
    
    # Проверяем подпись
    if not verify_crypto_signature(parsed['data_part'], parsed['signature'], secret_key):
        return False, "❌ Неверная подпись платежа. Попробуйте снова.", None
    
    order_id = parsed['order_id']
    
    # --- ЛОГИКА ОБРАБОТКИ ОРДЕРОВ (Внешние/Внутренние) ---
    is_internal_order = order_id.startswith("00")
    order = find_order_by_order_id(order_id)
    
    from database.requests import get_crypto_integration_mode
    crypto_mode = get_crypto_integration_mode()
    
    if order and crypto_mode == 'simple':
        # Простая интеграция: строго сверяем сумму, переданную в Ya.Seller с тарифом
        from database.requests import get_tariff_by_id
        order_tariff = get_tariff_by_id(order['tariff_id'])
        if order_tariff:
            expected_cents = order_tariff['price_cents']
            received_cents = parsed.get('price', 0)
            if received_cents < expected_cents:
                logger.error(f"Ордер {order_id}: Сумма платежа недостаточна. Ожидалось {expected_cents}, получено {received_cents}")
                return False, "❌ Сумма платежа не совпадает с тарифом.", None
    
    # Если это внутренний ордер (и стандартный режим), но пользователь оплатил другой тариф (выбрал в UI процессинга)
    elif order and parsed.get('tariff') and parsed['tariff'] != '_':
        try:
            tariff_ext_id = int(parsed['tariff'])
            from database.requests import get_tariff_by_external_id, update_order_tariff
            real_tariff = get_tariff_by_external_id(tariff_ext_id)
            
            # Если тариф найден и он отличается от того, что в ордере (или тарифа нет)
            if real_tariff and (real_tariff['id'] != order['tariff_id'] or order.get('payment_type') != 'crypto'):
                logger.info(f"Обновление тарифа ордера {order_id}: {order['tariff_id']} -> {real_tariff['id']} (из callback)")
                if update_order_tariff(order_id, real_tariff['id'], payment_type='crypto'):
                    # Перезагружаем ордер из базы, чтобы получить обновленные данные
                    order = find_order_by_order_id(order_id)
                    logger.info(f"Ордер {order_id} перезагружен: tariff_id={order['tariff_id']}, period_days={order.get('period_days')}")
        except Exception as e:
            logger.error(f"Не удалось обновить тариф из callback: {e}")
    
    if not order:
        if is_internal_order:
             return False, "❌ Ордер не найден в системе.", None
        
        # Внешний ордер -> Создаем PAID order в базе ПЕРЕД обработкой
        if not user_id:
             return False, "⚠️ Ошибка обработки внешнего заказа (нет user_id).", None
        
        logger.info(f"Новый внешний ордер: {order_id}")
        
        # Нам нужен тариф для создания ордера
        tariff_id = None
        amount_cents = 0
        amount_stars = 0
        period_days = 30 # Default
        
        if parsed.get('tariff') and parsed['tariff'] != '_':
            try:
                tariff_external_id = int(parsed['tariff'])
                from database.requests import get_tariff_by_external_id
                tariff = get_tariff_by_external_id(tariff_external_id)
                if tariff:
                    tariff_id = tariff['id']
                    amount_cents = tariff['price_cents']
                    amount_stars = tariff['price_stars']
                    period_days = tariff['duration_days']
            except Exception as e:
                logger.error(f"Ошибка получения тарифа для внешнего ордера: {e}")
        
        # Если тариф не определен, мы не можем создать ордер корректно
        if not tariff_id:
             logger.error(f"Внешний ордер {order_id} без валидного тарифа!")
             from bot.errors import TariffNotFoundError
             raise TariffNotFoundError()
             
        # Используем цену из callback если она там есть (PRICE)
        if parsed.get('price') and parsed['price'] > 0:
            amount_cents = parsed['price']
            
        from database.requests import create_paid_order_external
        
        success = create_paid_order_external(
            order_id=order_id,
            user_id=user_id,
            tariff_id=tariff_id,
            payment_type='crypto',
            amount_cents=amount_cents,
            amount_stars=amount_stars,
            period_days=period_days
        )
        
        if not success:
             return False, "❌ Ошибка сохранения внешнего заказа.", None
    
    # Delegate to unified logic
    return await process_payment_order(order_id)


def build_crypto_payment_url(
    item_id: str,
    invoice_id: str,
    tariff_external_id: Optional[int] = None,
    price_cents: Optional[int] = None
) -> str:
    """
    Формирует ссылку на криптопроцессинг с нашим invoice.
    
    Формат: https://t.me/Ya_SellerBot?start=item-{item_id}-{ref}-{promo}-{invoice}-{price}
    
    Args:
        item_id: ID товара в Ya.Seller (из настроек)
        invoice_id: Наш уникальный invoice (макс 8 символов)
        tariff_external_id: Номер тарифа (1-9) для фиксации цены
        price_cents: Цена в центах (если нужно переопределить)
        
    Returns:
        URL для перехода в криптопроцессинг
    """
    # Формат: item-{item_id}-{ref_code}-{promo}-{invoice}-{price}
    # Пустые параметры заменяем прочерками
    
    ref_code = ""  # Реффералку не используем
    promo = ""     # Промокод не используем
    
    parts = [
        "item",
        item_id,
        ref_code,
        promo,
        invoice_id
    ]
    
    # Добавляем цену если нужно зафиксировать
    if price_cents:
        parts.append(str(price_cents))
    
    start_param = "-".join(parts)
    
    return f"https://t.me/Ya_SellerBot?start={start_param}"


def extract_item_id_from_url(crypto_item_url: str) -> Optional[str]:
    """
    Извлекает item_id из ссылки на товар в Ya.Seller.
    
    Формат ссылки: https://t.me/Ya_SellerBot?start=item-{item_id}...
    
    Args:
        crypto_item_url: Полная ссылка на товар
        
    Returns:
        item_id или None
    """
    if not crypto_item_url:
        return None
    
    # Ищем start= параметр
    if '?start=' in crypto_item_url:
        start_param = crypto_item_url.split('?start=')[1]
        parts = start_param.split('-')
        if len(parts) >= 2 and parts[0] == 'item':
            return parts[1]
    
    return None


# ============================================================================
# ЮКАССА QR-ОПЛАТА (прямой REST API без Telegram Payments)
# ============================================================================

async def create_yookassa_qr_payment(
    amount_rub: float,
    order_id: str,
    description: str,
    bot_name: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Создаёт платёж в ЮКасса REST API с подтверждением через QR-код.

    Возвращает изображение QR-кода (PNG) по ссылке, которую можно
    отправить пользователю прямо в Telegram как фото.

    Args:
        amount_rub: Сумма в рублях (например, 299.00)
        order_id: Наш внутренний ордер (для metadata)
        description: Описание платежа (показывается в форме оплаты)
        metadata: Дополнительные метаданные (необязательно)

    Returns:
        Словарь с ключами:
            - yookassa_payment_id: ID платежа в системе ЮКасса
            - qr_image_url: URL изображения QR-кода (PNG)
            - qr_url: Ссылка, зашитая в QR (для открытия в браузере)

    Raises:
        ValueError: Если учётные данные не настроены
        aiohttp.ClientError: Если API недоступен
        RuntimeError: Если API вернул ошибку
    """
    shop_id, secret_key = get_yookassa_credentials()
    if not shop_id or not secret_key:
        raise ValueError("ЮКасса: не настроены shop_id или secret_key")

    # Заголовок Basic Auth: base64(shop_id:secret_key)
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()

    # Ключ идемпотентности — уникальный для этого ордера
    idempotence_key = f"qr-{order_id}-{uuid.uuid4().hex[:8]}"

    payload = {
        "amount": {
            "value": f"{amount_rub:.2f}",
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me"
        },
        "description": description,
        "receipt": {
            "customer": {
                "email": f"user_{order_id}@t.me"
            },
            "items": [
                {
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount_rub:.2f}",
                        "currency": "RUB"
                    },
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "service"
                }
            ]
        },
        "metadata": {
            "order_id": order_id,
            **(metadata or {})
        }
    }

    headers = {
        "Authorization": f"Basic {credentials}",
        "Idempotence-Key": idempotence_key,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            YOOKASSA_API_URL,
            json=payload,
            headers=headers
        ) as response:
            data = await response.json()

            if response.status not in (200, 201):
                error_desc = data.get('description', 'Неизвестная ошибка')
                logger.error(f"ЮКасса API ошибка {response.status}: {error_desc} | payload={payload}")
                raise RuntimeError(f"ЮКасса API ошибка: {error_desc}")

            confirmation = data.get('confirmation', {})
            qr_url = confirmation.get('confirmation_url', '')
            
            if not qr_url:
                logger.error(f"ЮКасса API не вернул confirmation_url: {data}")
                raise RuntimeError("ЮКасса API не вернул данные для QR-кода")

            # Генерируем QR-код из строки оплаты через локальную библиотеку qrcode
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            bio = io.BytesIO()
            img.save(bio, format="PNG")
            qr_image_data = bio.getvalue()

            logger.info(
                f"ЮКасса QR создан: payment_id={data['id']}, order_id={order_id}, "
                f"amount={amount_rub} RUB"
            )

            return {
                'yookassa_payment_id': data['id'],
                'qr_image_data': qr_image_data,
                'qr_url': qr_url,
                'status': data.get('status', 'pending')
            }


async def check_yookassa_payment_status(yookassa_payment_id: str) -> str:
    """
    Проверяет статус платежа в ЮКасса REST API.

    Args:
        yookassa_payment_id: ID платежа в системе ЮКасса

    Returns:
        Строка статуса: 'pending', 'waiting_for_capture', 'succeeded', 'canceled'

    Raises:
        ValueError: Если учётные данные не настроены
        aiohttp.ClientError: Если API недоступен
        RuntimeError: Если API вернул ошибку
    """
    shop_id, secret_key = get_yookassa_credentials()
    if not shop_id or not secret_key:
        raise ValueError("ЮКасса: не настроены shop_id или secret_key")

    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json"
    }

    url = f"{YOOKASSA_API_URL}/{yookassa_payment_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()

            if response.status != 200:
                error_desc = data.get('description', 'Неизвестная ошибка')
                logger.error(f"ЮКасса статус ошибка {response.status}: {error_desc}")
                raise RuntimeError(f"ЮКасса API ошибка: {error_desc}")

            status = data.get('status', 'pending')
            logger.debug(f"ЮКасса payment {yookassa_payment_id}: status={status}")
            return status


def convert_to_rub_cents(amount_raw: int, payment_type: str, usd_rub_rate: int) -> int:
    """
    Конвертировать сырую сумму в копейки рублей.
    
    Args:
        amount_raw: сырая сумма (звёзды/центы USDT/копейки рублей)
        payment_type: тип платежа ('stars', 'crypto', 'cards', 'yookassa_qr')
        usd_rub_rate: курс USD/RUB в копейках
    
    Returns:
        Сумма в копейках рублей
    """
    if payment_type == 'stars':
        usd_cents = int(amount_raw * STAR_TO_USD * 100)
        return usd_cents * usd_rub_rate // 100
    elif payment_type == 'crypto':
        usd_cents = amount_raw
        return usd_cents * usd_rub_rate // 100
    else:
        return amount_raw


async def process_referral_reward(
    payer_id: int,
    period_days: int,
    amount_raw: int,
    payment_type: str
) -> None:
    """
    Обработка реферального вознаграждения при оплате.
    Вызывается ПОСЛЕ успешной обработки платежа.
    
    Начисляет фиксированные 50₽ (5000 копеек) на баланс реферера
    за каждую покупку приглашенного пользователя.
    
    Args:
        payer_id: Внутренний ID пользователя, который оплатил
        period_days: Сколько дней купил реферал (не используется)
        amount_raw: СЫРАЯ сумма (не используется)
        payment_type: Тип платежа (не используется)
    
    Note:
        При оплате балансом реферальные вознаграждения НЕ начисляются,
        поэтому эта функция не вызывается для платежей балансом.
    """
    logger.info(f"process_referral_reward вызвана: payer_id={payer_id}, payment_type={payment_type}")
    
    if not is_referral_enabled():
        logger.warning(f"Реферальная система отключена, вознаграждение не начислено для payer_id={payer_id}")
        return
    
    # Получаем прямого реферера (уровень 1)
    referrer_id = get_user_referrer(payer_id)
    logger.info(f"Реферер для payer_id={payer_id}: referrer_id={referrer_id}")
    
    if not referrer_id:
        logger.info(f"У пользователя {payer_id} нет реферера, вознаграждение не начислено")
        return
    
    # Фиксированное вознаграждение: 50₽ = 5000 копеек
    FIXED_REWARD_CENTS = 5000
    
    from bot.services.user_locks import user_locks
    
    # Начисляем фиксированную сумму на баланс реферера
    async with user_locks[referrer_id]:
        add_to_balance(referrer_id, FIXED_REWARD_CENTS)
    
    # Обновляем статистику
    update_referral_stat(
        referrer_id, payer_id, 1,  # level=1 (только прямые рефералы)
        FIXED_REWARD_CENTS, 0  # reward_cents=5000, reward_days=0
    )
    
    logger.info(f"Начислено {FIXED_REWARD_CENTS} коп реферу {referrer_id} за покупку реферала {payer_id}")
    
    # Отправляем уведомление рефереру
    await send_referral_reward_notification(referrer_id, payer_id, FIXED_REWARD_CENTS)


async def send_referral_reward_notification(referrer_id: int, payer_id: int, reward_cents: int) -> None:
    """
    Отправляет уведомление рефереру о начислении бонуса.
    
    Args:
        referrer_id: Внутренний ID реферера
        payer_id: Внутренний ID того, кто оплатил
        reward_cents: Сумма вознаграждения в копейках
    """
    logger.info(f"send_referral_reward_notification: referrer_id={referrer_id}, payer_id={payer_id}, reward={reward_cents}")
    
    try:
        from aiogram import Bot
        from config import BOT_TOKEN
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        # Получаем данные реферера и плательщика
        referrer = get_user_by_id(referrer_id)
        payer = get_user_by_id(payer_id)
        
        logger.info(f"Данные реферера: {referrer}")
        logger.info(f"Данные плательщика: {payer}")
        
        if not referrer:
            logger.warning(f"Реферер {referrer_id} не найден для отправки уведомления")
            return
        
        referrer_telegram_id = referrer['telegram_id']
        payer_username = payer.get('username', 'пользователь') if payer else 'пользователь'
        
        # Форматируем сумму
        reward_rub = reward_cents / 100
        reward_str = f"{reward_rub:.0f} ₽" if reward_rub >= 10 else f"{reward_rub:.2f} ₽"
        
        # Получаем текущий баланс
        current_balance = get_user_balance(referrer_id)
        balance_rub = current_balance / 100
        balance_str = f"{balance_rub:.0f} ₽" if balance_rub >= 10 else f"{balance_rub:.2f} ₽"
        
        # Формируем текст уведомления
        text = (
            f"🎉 <b>Реферальное вознаграждение!</b>\n\n"
            f"Ваш реферал @{payer_username} оплатил подписку.\n\n"
            f"💰 <b>Начислено:</b> {reward_str}\n"
            f"💎 <b>Ваш баланс:</b> {balance_str}\n\n"
            f"Используйте баланс для оплаты подписок!"
        )
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💎 Мой баланс", callback_data="referral_system"))
        builder.row(InlineKeyboardButton(text="🏠 На главную", callback_data="start"))
        
        # Отправляем уведомление
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=referrer_telegram_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
        await bot.session.close()
        
        logger.info(f"Отправлено уведомление о реферальном бонусе рефереру {referrer_telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о реферальном бонусе: {e}")


def calculate_balance_discount(user_id: int, tariff_price_cents: int) -> tuple[int, int]:
    """
    Рассчитать скидку с баланса. БЕЗ списания!
    
    Args:
        user_id: Внутренний ID пользователя
        tariff_price_cents: Цена тарифа в копейках
    
    Returns:
        Кортеж (remaining_to_pay_cents, to_deduct_cents):
        - remaining_to_pay_cents: сколько нужно оплатить внешним способом
        - to_deduct_cents: сколько будет списано с баланса ПРИ УСПЕШНОЙ оплате
    """
    balance = get_user_balance(user_id)
    
    if balance >= tariff_price_cents:
        return 0, tariff_price_cents
    else:
        return tariff_price_cents - balance, balance


async def complete_payment_flow(
    order_id: str,
    message,
    state,
    telegram_id: int,
    payment_type: str,
    referral_amount: int
) -> None:
    """
    Единый post-payment поток после подтверждения оплаты.
    
    Выполняет:
    1. Обработку ордера (process_payment_order)
    2. Списание баланса (если частичная оплата)
    3. Начисление реферального вознаграждения
    4. Финализацию UI (выдача ключа / показ результата)
    
    Вызывается из:
    - successful_payment_handler (Stars/Cards) — base.py
    - check_yookassa_payment (QR/СБП) — yookassa.py
    
    Args:
        order_id: ID ордера
        message: Сообщение для ответа пользователю
        state: FSM-контекст (для баланса и очистки)
        telegram_id: Telegram ID пользователя
        payment_type: Тип платежа ('stars', 'cards', 'yookassa_qr')
        referral_amount: Сырая сумма для реферального вознаграждения:
            - 'stars': количество звёзд
            - 'cards': копейки рублей
            - 'yookassa_qr': копейки рублей
    """
    from bot.handlers.user.payments.base import finalize_payment_ui
    from bot.keyboards.admin import home_only_kb
    from bot.services.user_locks import user_locks
    
    state_data = await state.get_data()
    balance_to_deduct = state_data.get('balance_to_deduct', 0)
    
    try:
        (success, text, order) = await process_payment_order(order_id)
        
        if success and order:
            user_internal_id = order['user_id']
            days = order.get('period_days') or order.get('duration_days') or 30
            
            # Списание баланса при частичной оплате
            if balance_to_deduct > 0:
                async with user_locks[user_internal_id]:
                    current_balance = get_user_balance(user_internal_id)
                    actual_deduct = min(balance_to_deduct, current_balance)
                    if actual_deduct > 0:
                        deduct_from_balance(user_internal_id, actual_deduct)
                        logger.info(
                            f'Списано {actual_deduct} коп с баланса user '
                            f'{user_internal_id} при частичной оплате ({payment_type})'
                        )
            
            # Очистка FSM данных о балансе
            await state.update_data(balance_to_deduct=0, remaining_cents=0)
            
            # Реферальное вознаграждение
            await process_referral_reward(user_internal_id, days, referral_amount, payment_type)
            
            # Финализация UI
            await finalize_payment_ui(message, state, text, order, user_id=telegram_id)
        else:
            await message.answer(text, reply_markup=home_only_kb(), parse_mode='HTML')
    
    except Exception as e:
        from bot.errors import TariffNotFoundError
        if isinstance(e, TariffNotFoundError):
            from bot.keyboards.user import support_kb
            support_link = get_setting('support_channel_link', 'https://t.me/ArcVPN_support')
            await message.answer(str(e), reply_markup=support_kb(support_link), parse_mode='HTML')
        else:
            logger.exception(f'Ошибка обработки {payment_type} платежа: {e}')
            await message.answer('❌ Произошла ошибка при обработке платежа.', parse_mode='HTML')
