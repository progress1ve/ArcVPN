"""
Система миграций базы данных.

Миграции применяются автоматически при запуске бота.
Каждая миграция имеет уникальный номер версии.
"""
import sqlite3
import logging
from .connection import get_db
import secrets
import string

logger = logging.getLogger(__name__)


def _add_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    """
    Добавляет колонку в таблицу, игнорируя ошибку если колонка уже существует.
    Используется в миграциях для идемпотентного добавления колонок.
    """
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info(f"Колонка {column_def.split()[0]} уже существует в {table} — пропускаем")
        else:
            raise


# Текущая версия схемы БД
LATEST_VERSION = 17


def get_current_version() -> int:
    """
    Получает текущую версию схемы БД.
    
    Returns:
        int: Номер версии (0 если таблица версий не существует)
    """
    with get_db() as conn:
        # Проверяем существование таблицы schema_version
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if not cursor.fetchone():
            return 0
        
        cursor = conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        return row["version"] if row else 0


def set_version(conn: sqlite3.Connection, version: int) -> None:
    """
    Устанавливает версию схемы БД.
    
    Args:
        conn: Соединение с БД
        version: Номер версии
    """
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


def migration_1(conn: sqlite3.Connection) -> None:
    """
    Миграция v1: Полная структура БД.
    
    Создаёт таблицы:
    - schema_version: версия схемы
    - settings: глобальные настройки бота
    - users: пользователи Telegram
    - tariffs: тарифные планы
    - servers: VPN-серверы (3X-UI)
    - vpn_keys: ключи/подписки пользователей
    - payments: история оплат
    - notification_log: лог уведомлений
    """
    logger.info("Применение миграции v1...")

    # Таблица версий схемы
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL  -- Номер версии схемы БД
        )
    """)
    
    # Глобальные настройки бота
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,  -- Уникальное название настройки
            value TEXT             -- Значение
        )
    """)

    # Дефолтные настройки
    default_settings = [
        ('broadcast_filter', 'all'),  # Фильтр по умолчанию: все пользователи
        ('broadcast_in_progress', '0'),  # Флаг активной рассылки
        ('notification_days', '3'),  # За сколько дней уведомлять
        ('notification_text', '''⚠️ **Ваш VPN-ключ скоро истекает!**

Через {days} дней закончится срок действия вашего ключа.

Продлите подписку, чтобы сохранить доступ к VPN без перерыва!'''),
        ('main_page_text', (
            "🔐 *Добро пожаловать в ArcVPN\\!*\n"
            "Быстрый, безопасный и анонимный доступ к интернету\\.\n"
            "Без логов, без ограничений, без проблем\\! 🚀\n"
        )),
        ('help_page_text', (
            "🔐 Этот бот предоставляет доступ к VPN\\-сервису\\.\n\n"
            "*Как это работает:*\n"
            "1\\. Купите ключ через раздел «Купить ключ»\n\n"
            "2\\. Установите VPN\\-клиент для вашего устройства:\n\n"
            "Hiddify или v2rayNG или V2Box\n"
            "Подробная инструкция по настройке VPN👇 https://telegra\\.ph/Kak\\-nastroit\\-VPN\\-Gajd\\-za\\-2\\-minuty\\-01\\-23\n\n"
            "3\\. Импортируйте ключ в приложение\n\n"
            "4\\. Подключайтесь и наслаждайтесь\\! 🚀"
        )),
        ('news_channel_link', 'https://t.me/ArcVPN'),
        ('support_channel_link', 'https://t.me/ArcVPN_support'),
    ]
    for key, value in default_settings:
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    
    # Пользователи Telegram
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            is_banned INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
    
    # Тарифные планы
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            price_cents INTEGER NOT NULL,
            price_stars INTEGER NOT NULL,
            external_id INTEGER,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # Создаём скрытый тариф для админских ключей
    conn.execute("""
        INSERT INTO tariffs (name, duration_days, price_cents, price_stars, external_id, display_order, is_active)
        SELECT 'Admin Tariff', 365, 0, 0, 0, 999, 0
        WHERE NOT EXISTS (SELECT 1 FROM tariffs WHERE name = 'Admin Tariff')
    """)

    # VPN-серверы
    conn.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            web_base_path TEXT NOT NULL,
            login TEXT NOT NULL,
            password TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # VPN-ключи
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vpn_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER,
            tariff_id INTEGER NOT NULL,
            panel_inbound_id INTEGER,
            client_uuid TEXT,
            panel_email TEXT,
            custom_name TEXT,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (server_id) REFERENCES servers(id),
            FOREIGN KEY (tariff_id) REFERENCES tariffs(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vpn_keys_user_id ON vpn_keys(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vpn_keys_expires_at ON vpn_keys(expires_at)")
    
    # История оплат
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vpn_key_id INTEGER,
            user_id INTEGER NOT NULL,
            tariff_id INTEGER NOT NULL,
            order_id TEXT NOT NULL UNIQUE,
            payment_type TEXT NOT NULL,
            amount_cents INTEGER,
            amount_stars INTEGER,
            period_days INTEGER NOT NULL,
            status TEXT DEFAULT 'paid',
            paid_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vpn_key_id) REFERENCES vpn_keys(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tariff_id) REFERENCES tariffs(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments(paid_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)")

    # Лог уведомлений
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vpn_key_id INTEGER NOT NULL,
            sent_at DATE NOT NULL,
            FOREIGN KEY (vpn_key_id) REFERENCES vpn_keys(id)
        )
    """)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_log_unique ON notification_log(vpn_key_id, sent_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notification_log_vpn_key ON notification_log(vpn_key_id)")
    
    logger.info("Миграция v1 применена")


def migration_2(conn: sqlite3.Connection) -> None:
    """
    Миграция v2: Разрешаем NULL в таблице payments для tariff_id, period_days и payment_type.
    
    Это необходимо, чтобы не фиксировать тариф и тип оплаты при создании pending-ордера,
    так как пользователь выбирает их непосредственно при оплате.
    """
    logger.info("Применение миграции v2 (Make payments fields nullable)...")
    
    # 1. Создаём новую таблицу (tariff_id, period_days, payment_type теперь без NOT NULL)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vpn_key_id INTEGER,
            user_id INTEGER NOT NULL,
            tariff_id INTEGER,  -- Теперь NULLABLE
            order_id TEXT NOT NULL UNIQUE,
            payment_type TEXT,  -- Теперь NULLABLE
            amount_cents INTEGER,
            amount_stars INTEGER,
            period_days INTEGER, -- Теперь NULLABLE
            status TEXT DEFAULT 'paid',
            paid_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vpn_key_id) REFERENCES vpn_keys(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tariff_id) REFERENCES tariffs(id)
        )
    """)
    
    # 2. Копируем данные
    conn.execute("""
        INSERT INTO payments_new (id, vpn_key_id, user_id, tariff_id, order_id, payment_type, 
                                 amount_cents, amount_stars, period_days, status, paid_at)
        SELECT id, vpn_key_id, user_id, tariff_id, order_id, payment_type, 
               amount_cents, amount_stars, period_days, status, paid_at
        FROM payments
    """)
    
    # 3. Удаляем старую таблицу
    conn.execute("DROP TABLE payments")
    
    # 4. Переименовываем новую таблицу
    conn.execute("ALTER TABLE payments_new RENAME TO payments")
    
    # 5. Пересоздаём индексы
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments(paid_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)")
    
    logger.info("Миграция v2 применена")


def migration_3(conn: sqlite3.Connection) -> None:
    """
    Миграция v3: Функция «Пробная подписка».

    Изменения:
    - Добавляет колонку used_trial в таблицу users (флаг использования пробного периода)
    - Добавляет настройки trial_enabled, trial_tariff_id, trial_page_text в settings
    """
    logger.info("Применение миграции v3 (Пробная подписка)...")

    # Добавляем колонку used_trial в таблицу users (если не существует)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN used_trial INTEGER DEFAULT 0")
        logger.info("Колонка used_trial добавлена в таблицу users")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка used_trial уже существует")
        else:
            # Если ошибка другая — пробрасываем её
            raise
    except Exception as e:
        logger.error(f"Ошибка миграции v3: {e}")
        raise

    # Дефолтный текст для страницы пробной подписки (MarkdownV2)
    trial_page_text_default = (
        "🎁 *Пробная подписка*\n\n"
        "Хотите попробовать наш VPN бесплатно?\n\n"
        "Мы предлагаем пробный период, чтобы вы могли убедиться в качестве "
        "и скорости нашего сервиса\\.\n\n"
        "*Что входит в пробный доступ:*\n"
        "• Полный доступ к VPN без ограничений по сайтам\n"
        "• Высокая скорость соединения\n"
        "• Несколько протоколов на выбор\n\n"
        "Нажмите кнопку ниже, чтобы активировать пробный доступ прямо сейчас\!\n\n"
        "_Пробный период предоставляется один раз на аккаунт\._"
    )

    # Настройки пробной подписки
    trial_settings = [
        ('trial_enabled', '0'),          # Выключено по умолчанию
        ('trial_tariff_id', ''),          # Тариф не задан
        ('trial_page_text', trial_page_text_default),  # Текст по умолчанию
    ]
    for key, value in trial_settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    logger.info("Миграция v3 применена")


def migration_4(conn: sqlite3.Connection) -> None:
    """
    Миграция v4: Оплата российскими картами.
    
    - Добавляет поле price_rub (цена в рублях) в таблицу tariffs
    - Добавляет настройки cards_enabled и cards_provider_token
    """
    logger.info("Применение миграции v4...")

    # Добавляем price_rub в tariffs (если его еще нет)
    try:
        conn.execute("ALTER TABLE tariffs ADD COLUMN price_rub INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Игнорируем ошибку, если колонка уже существует

    # Добавляем новые настройки
    card_settings = [
        ('cards_enabled', '0'),          # Выключено по умолчанию
        ('cards_provider_token', ''),    # Токен провайдера пустой
    ]
    for key, value in card_settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    logger.info("Миграция v4 применена")


def migration_5(conn: sqlite3.Connection) -> None:
    """
    Миграция v5: Добавление протокола подключения к панели (HTTP/HTTPS).
    
    Изменения:
    - Добавляет колонку protocol в таблицу servers
    """
    logger.info("Применение миграции v5 (Протоколы панели)...")

    try:
        conn.execute("ALTER TABLE servers ADD COLUMN protocol TEXT DEFAULT 'https'")
        logger.info("Колонка protocol добавлена в таблицу servers")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка protocol уже существует")
        else:
            raise
    except Exception as e:
        logger.error(f"Ошибка миграции v5: {e}")
        raise

    logger.info("Миграция v5 применена")


def migration_6(conn: sqlite3.Connection) -> None:
    """
    Миграция v6: Прямая QR-оплата через ЮКассу (без Telegram Payments API).

    Изменения:
    - Добавляет в settings настройки: yookassa_qr_enabled, yookassa_shop_id, yookassa_secret_key
    - Добавляет в payments колонку yookassa_payment_id для хранения ID платежа на стороне ЮКассы
    """
    logger.info("Применение миграции v6 (ЮКасса QR-оплата)...")

    # Добавляем колонку yookassa_payment_id в payments
    try:
        conn.execute("ALTER TABLE payments ADD COLUMN yookassa_payment_id TEXT")
        logger.info("Колонка yookassa_payment_id добавлена в таблицу payments")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка yookassa_payment_id уже существует")
        else:
            raise

    # Добавляем настройки QR-оплаты
    qr_settings = [
        ('yookassa_qr_enabled', '0'),   # Выключено по умолчанию
        ('yookassa_shop_id', ''),        # Shop ID магазина ЮКассы
        ('yookassa_secret_key', ''),    # Секретный ключ ЮКассы
    ]
    for key, value in qr_settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    logger.info("Миграция v6 применена")


def migration_7(conn: sqlite3.Connection) -> None:
    """
    Миграция v7: Режим интеграции с криптопроцессингом (Ya.Seller).
    
    Добавляет настройку `crypto_integration_mode` (simple / standard).
    Если крипта уже была настроена, то ставим standard, иначе - simple (по умолчанию для новых).
    """
    logger.info("Применение миграции v7 (Режим интеграции крипты)...")

    # Проверяем, была ли настроена крипта (наличие URL или ключа)
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'crypto_item_url'")
    row = cursor.fetchone()
    
    has_old_crypto = False
    if row and row['value']:
        has_old_crypto = True
        
    mode = "standard" if has_old_crypto else "simple"

    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ('crypto_integration_mode', mode)
    )

    logger.info(f"Миграция v7 применена (установлен режим: {mode})")


def migration_8(conn: sqlite3.Connection) -> None:
    """
    Миграция v8: Замена старого текста уведомления об истечении ключа на новый с {keyname}.
    """
    logger.info("Применение миграции v8 (Обновление текста уведомления с {keyname})...")
    
    current_text = None
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'notification_text'")
    row = cursor.fetchone()
    
    if row and row['value']:
        current_text = row['value']
        if "⚠️ *Ваш VPN-ключ скоро истекает!*" in current_text:
            new_text = current_text.replace(
                "⚠️ *Ваш VPN-ключ скоро истекает!*",
                "⚠️ *Ваш VPN-ключ {keyname} скоро истекает!*"
            )
            
            conn.execute(
                "UPDATE settings SET value = ? WHERE key = 'notification_text'",
                (new_text,)
            )

    logger.info("Миграция v8 применена")

def migration_9(conn: sqlite3.Connection) -> None:
    """
    Миграция v9: Отключение автопродления (сброса трафика и дней) для всех существующих ключей.
    
    Вызывает API-метод панели X-UI для каждого сервера и устанавливает reset = 0 
    для всех клиентов, у которых он был не равен 0.
    Сама БД при этом не меняется, но механизм миграций используется для
    однократного выполнения этого действия на всех серверах при обновлении.
    """
    logger.info("Применение миграции v9 (Отключение автопродления ключей на серверах)...")
    
    # Для выполнения асинхронных HTTP-запросов из синхронного кода миграций
    import asyncio
    
    # Получаем все активные серверы синхронно, пока соединение открыто
    cursor = conn.execute("SELECT * FROM servers WHERE is_active = 1")
    servers = [dict(row) for row in cursor.fetchall()]
    
    if not servers:
        logger.info("Нет активных серверов для отключения автопродления.")
        return
    
    async def process_servers(servers_list):
        from bot.services.vpn_api import XUIClient
        
        total_updated = 0
        for server in servers_list:
            logger.info(f"Подключение к серверу {server['name']} для отключения автопродления...")
            client = None
            try:
                client = XUIClient(server)
                # Логинимся
                await client.login()
                
                # Запускаем отключение
                updated = await client.disable_reset_for_all_clients()
                total_updated += updated
                
                logger.info(f"На сервере {server['name']} отключено автопродление для {updated} клиентов.")
            except Exception as e:
                logger.error(f"Ошибка при работе с сервером {server['name']}: {e}")
            finally:
                if client and client.session:
                    await client.session.close()
                    
        logger.info(f"Всего отключено автопродление для {total_updated} клиентов на всех серверах.")

    # Создаем новый event loop или используем текущий
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если мы уже в event loop, создаем задачу
            loop.create_task(process_servers(servers))
        else:
            loop.run_until_complete(process_servers(servers))
    except RuntimeError:
        # Если event loop не существует, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_servers(servers))
        loop.close()

    logger.info("Миграция v9 применена")


def migration_10(conn: sqlite3.Connection) -> None:
    """
    Миграция v10: Текст перед оплатой (отказ от ответственности).
    
    Добавляет настройку prepayment_text для хранения текста,
    который показывается пользователю перед выбором способа оплаты.
    Текст хранится в формате MarkdownV2 с экранированием.
    """
    logger.info("Применение миграции v10 (Текст перед оплатой)...")
    
    default_prepayment_text = (
        "💳 *Купить ключ*\n\n"
        "🔐 *Что вы получаете:*\n"
        "• Доступ к нескольким серверам и протоколам\n"
        "• 1 ключ \\= 1 устройство \\(одновременное подключение\\)\n"
        "• Лимит трафика: до 1 ТБ в месяц \\(сброс каждые 30 дней\\)\n\n"
        "⚠️ *Важно знать:*\n"
        "• Средства не возвращаются — услуга считается оказанной в момент получения ключа\n"
        "• Мы не даём никаких гарантий бесперебойной работы сервиса в будущем\n"
        "• Мы не можем гарантировать, что данная технология останется рабочей\n\n"
        "_Приобретая ключ, вы соглашаетесь с этими условиями\\._"
    )

    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ('prepayment_text', default_prepayment_text)
    )
    
    logger.info("Миграция v10 применена")




def migration_11(conn: sqlite3.Connection) -> None:
    """
    Миграция v11: Реферальная система.
    
    Изменения:
    - Новые поля в users: referral_code, referred_by, personal_balance, referral_coefficient
    - Новая таблица referral_levels (до 3 уровней с процентами)
    - Новая таблица referral_stats (статистика по рефералам)
    - Новая таблица exchange_rates (курсы валют)
    - Новые настройки: referral_enabled, referral_reward_type, referral_conditions_text
    - Генерация реферальных кодов для существующих пользователей
    """
    logger.info("Применение миграции v11 (Реферальная система)...")
    
    try:
        conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
        logger.info("Колонка referral_code добавлена в таблицу users")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка referral_code уже существует")
        else:
            raise
    
    try:
        conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER REFERENCES users(id)")
        logger.info("Колонка referred_by добавлена в таблицу users")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка referred_by уже существует")
        else:
            raise
    
    try:
        conn.execute("ALTER TABLE users ADD COLUMN personal_balance INTEGER DEFAULT 0")
        logger.info("Колонка personal_balance добавлена в таблицу users")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка personal_balance уже существует")
        else:
            raise
    
    try:
        conn.execute("ALTER TABLE users ADD COLUMN referral_coefficient REAL DEFAULT 1.0")
        logger.info("Колонка referral_coefficient добавлена в таблицу users")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка referral_coefficient уже существует")
        else:
            raise
    
    conn.commit()
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referral_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level_number INTEGER NOT NULL UNIQUE,
            percent INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1
        )
    """)
    
    conn.execute(
        "INSERT OR IGNORE INTO referral_levels (level_number, percent, enabled) VALUES (1, 10, 1)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO referral_levels (level_number, percent, enabled) VALUES (2, 5, 0)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO referral_levels (level_number, percent, enabled) VALUES (3, 2, 0)"
    )
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referral_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referral_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            total_payments_count INTEGER DEFAULT 0,
            total_reward_cents INTEGER DEFAULT 0,
            total_reward_days INTEGER DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referral_id) REFERENCES users(id),
            UNIQUE (referrer_id, referral_id, level)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_pair TEXT NOT NULL UNIQUE,
            rate INTEGER NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute(
        "INSERT OR IGNORE INTO exchange_rates (currency_pair, rate) VALUES ('USD_RUB', 9500)"
    )
    
    referral_settings = [
        ('referral_enabled', '0'),
        ('referral_reward_type', 'days'),
        ('referral_conditions_text', ''),
    ]
    for key, value in referral_settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    cursor = conn.execute("SELECT id FROM users WHERE referral_code IS NULL")
    users_without_code = [row['id'] for row in cursor.fetchall()]
    
    alphabet = string.ascii_letters + string.digits
    for user_id in users_without_code:
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        attempts = 0
        while attempts < 100:
            cursor = conn.execute("SELECT 1 FROM users WHERE referral_code = ?", (code,))
            if not cursor.fetchone():
                break
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            attempts += 1
        
        conn.execute("UPDATE users SET referral_code = ? WHERE id = ?", (code, user_id))
    
    logger.info(f"Сгенерированы реферальные коды для {len(users_without_code)} пользователей")
    logger.info("Миграция v11 применена")


def migration_12(conn: sqlite3.Connection) -> None:
    """
    Миграция v12: Настройки кнопок-ссылок в справке.
    
    Добавляет настройки для:
    - news_hidden: скрыта ли кнопка "Новости"
    - support_hidden: скрыта ли кнопка "Поддержка"
    - news_button_name: кастомное название кнопки "Новости"
    - support_button_name: кастомное название кнопки "Поддержка"
    """
    logger.info("Применение миграции v12 (Настройки кнопок-ссылок)...")
    
    link_button_settings = [
        ('news_hidden', '0'),
        ('support_hidden', '0'),
        ('news_button_name', 'Новости'),
        ('support_button_name', 'Поддержка'),
    ]
    for key, value in link_button_settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    logger.info("Миграция v12 применена")


def migration_13(conn: sqlite3.Connection) -> None:
    """
    Миграция v13: Система управления трафиком + Группы тарифов (объединённая).
    
    Трафик:
    - tariffs.traffic_limit_gb: лимит трафика для тарифа (0 = безлимит)
    - vpn_keys.traffic_used: кешированный израсходованный трафик (байты)
    - vpn_keys.traffic_limit: лимит трафика ключа (байты, копируется из тарифа)
    - vpn_keys.traffic_updated_at: время последнего обновления кеша трафика
    - vpn_keys.traffic_notified_pct: последний порог уведомления (100 = не уведомляли)
    - settings.traffic_notification_text: шаблон уведомления о трафике
    - settings.monthly_traffic_reset_enabled: ежемесячный автосброс (0/1)
    
    Группы тарифов:
    - tariff_groups: таблица групп (id, name, sort_order, created_at)
    - Запись "Основная" (id=1, sort_order=1) — группа по умолчанию
    - tariffs.group_id: привязка тарифа к группе (один тариф → одна группа)
    - server_groups: таблица связи серверов и групп (many-to-many)
      Один сервер может входить в любое количество групп.
    
    Ключи не получают отдельного поля group_id — группа ключа определяется
    через привязанный тариф (vpn_keys.tariff_id → tariffs.group_id).
    """
    logger.info("Применение миграции v13 (Трафик + Группы тарифов)...")

    # ── Трафик ─────────────────────────────────────────────────────────────────

    # Лимит трафика в тарифах (0 = безлимит)
    _add_column(conn, "tariffs", "traffic_limit_gb INTEGER DEFAULT 0")

    # Заполняем существующие тарифы значением из конфига (1 TB = 1024 ГБ)
    conn.execute("UPDATE tariffs SET traffic_limit_gb = 1024 WHERE traffic_limit_gb = 0")

    # Кеш трафика в ключах
    _add_column(conn, "vpn_keys", "traffic_used INTEGER DEFAULT 0")
    _add_column(conn, "vpn_keys", "traffic_limit INTEGER DEFAULT 0")
    _add_column(conn, "vpn_keys", "traffic_updated_at DATETIME")

    # Заполняем traffic_limit для существующих ключей из их тарифов
    conn.execute("""
        UPDATE vpn_keys SET traffic_limit = (
            SELECT COALESCE(t.traffic_limit_gb, 0) * 1024 * 1024 * 1024
            FROM tariffs t WHERE t.id = vpn_keys.tariff_id
        )
        WHERE tariff_id IS NOT NULL AND traffic_limit = 0
    """)

    # Последний порог уведомления о трафике (100 = ещё не уведомляли)
    _add_column(conn, "vpn_keys", "traffic_notified_pct INTEGER DEFAULT 100")

    # Шаблон уведомления о трафике
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ('traffic_notification_text',
         '⚠️ По ключу *{keyname}* осталось {percent}% трафика ({used} из {limit})')
    )

    # Настройка ежемесячного автосброса трафика
    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ('monthly_traffic_reset_enabled', '0')
    )

    # ── Группы тарифов ─────────────────────────────────────────────────────────

    # Таблица групп тарифов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tariff_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,              -- Название группы (видно пользователю)
            sort_order INTEGER DEFAULT 1,    -- Порядок сортировки (1-99)
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создаём группу «Основная» по умолчанию (id=1)
    conn.execute("""
        INSERT OR IGNORE INTO tariff_groups (id, name, sort_order)
        VALUES (1, 'Основная', 1)
    """)

    # Привязка тарифов к группе (один тариф → одна группа)
    _add_column(conn, "tariffs", "group_id INTEGER DEFAULT 1")
    conn.execute("UPDATE tariffs SET group_id = 1 WHERE group_id IS NULL")
    logger.info("Колонка group_id проверена в таблице tariffs")

    # Таблица связи серверов с группами (many-to-many)
    # Один сервер может входить в любое количество групп.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_groups (
            server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
            group_id  INTEGER NOT NULL REFERENCES tariff_groups(id) ON DELETE CASCADE,
            PRIMARY KEY (server_id, group_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_server_groups_group ON server_groups(group_id)")

    # Все существующие серверы добавляем в группу «Основная» (id=1)
    conn.execute("""
        INSERT OR IGNORE INTO server_groups (server_id, group_id)
        SELECT id, 1 FROM servers
    """)
    logger.info("Таблица server_groups создана, все серверы добавлены в группу 'Основная'")

    logger.info("Миграция v13 применена")


def migration_14(conn: sqlite3.Connection) -> None:
    """
    Миграция v14:
    - Замена тегов {days} на %дней% и {keyname} на %имяключа% в notification_text
    - Добавление key_delivery_text для кастомизации сообщения с ключом
    """
    import json
    logger.info("Применение миграции v14 (Теги уведомлений и текст выдачи ключа)...")

    # 1. Замена тегов в notification_text
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'notification_text'")
    row = cursor.fetchone()
    
    if row and row['value']:
        current_val = row['value']
        # Может быть JSON или обычная строка
        try:
            data = json.loads(current_val)
            if isinstance(data, dict) and 'text' in data:
                # Это JSON
                data['text'] = data['text'].replace('{days}', '%дней%').replace('{keyname}', '%имяключа%')
                new_val = json.dumps(data, ensure_ascii=False)
            else:
                # JSON но не тот формат
                new_val = current_val.replace('{days}', '%дней%').replace('{keyname}', '%имяключа%')
        except (json.JSONDecodeError, TypeError):
            # Это строка
            new_val = current_val.replace('{days}', '%дней%').replace('{keyname}', '%имяключа%')
            
        conn.execute(
            "UPDATE settings SET value = ? WHERE key = 'notification_text'",
            (new_val,)
        )
        logger.info("Теги в notification_text обновлены")

    # 2. Добавление текста выдачи ключа по умолчанию (MarkdownV2-формат)
    default_key_delivery = (
        "✅ *Ваш VPN\\-ключ\\!*\n\n"
        "%ключ%\n"
        "☝️ Нажмите, чтобы скопировать\\.\n\n"
        "📱 *Инструкция:*\n"
        "1\\. Скопируйте ссылку или отсканируйте QR\\-код\\.\n"
        "2\\. Импортируйте в свой клиент\\. Какие именно клиент подходит смотри в инструкции по кнопке ниже\\.\n"
        "3\\. Нажмите подключиться\\!"
    )
    
    # Форматируем как JSON для нового message_editor
    key_delivery_json = json.dumps({
        'text': default_key_delivery,
        'photo_file_id': None,
        'video_file_id': None,
        'animation_file_id': None
    }, ensure_ascii=False)

    conn.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ('key_delivery_text', key_delivery_json)
    )
    logger.info("Добавлен текст key_delivery_text по умолчанию")
    
    logger.info("Миграция v14 применена")


def _convert_md_to_html(text: str) -> str:
    """Конвертирует MarkdownV2 текст в HTML."""
    import re
    
    # 1. Убираем экранирование спецсимволов MD2 (\. \! \( \) \- \= \| \{ \} \# \+ \> \~ \`)
    text = re.sub(r'\\([_*\[\]()~`>#+\-=|{}.!\\])', r'\1', text)
    
    # 2. Конвертируем форматирование (в правильном порядке: сначала bold+italic)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)  # ***bold italic***
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)              # **bold**  
    text = re.sub(r'\*(.+?)\*', r'<b>\1</b>', text)                   # *bold*
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)                     # _italic_
    text = re.sub(r'~(.+?)~', r'<s>\1</s>', text)                     # ~strikethrough~
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)                   # __underline__
    
    # 3. Inline code: `code` → <code>code</code>
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # 4. Code blocks: ```\ncode\n``` → <pre>code</pre>
    text = re.sub(r'```\n?(.*?)\n?```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    
    # 5. Ссылки: [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    return text


def _is_default_text(text: str, md_default: str) -> bool:
    """Проверяет, совпадает ли текст с дефолтным (с допуском на пробелы)."""
    return text.strip() == md_default.strip()


def _migrate_setting_text(conn, key: str, md_default: str, html_default: str) -> str:
    """Мигрирует одну настройку из MD в HTML."""
    import json as _json
    
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    if not row or not row['value']:
        # Нет значения → ставим HTML-дефолт
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, html_default))
        return 'default_set'
    
    current_val = row['value']
    
    # Пробуем распарсить JSON
    try:
        data = _json.loads(current_val)
        if isinstance(data, dict) and 'text' in data:
            text = data['text']
            if _is_default_text(text, md_default):
                data['text'] = html_default
            else:
                data['text'] = _convert_md_to_html(text)
            new_val = _json.dumps(data, ensure_ascii=False)
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, key))
            return 'json_converted'
    except (_json.JSONDecodeError, TypeError):
        pass
    
    # Обычная строка
    if _is_default_text(current_val, md_default):
        conn.execute("UPDATE settings SET value = ? WHERE key = ?", (html_default, key))
        return 'default_replaced'
    else:
        new_val = _convert_md_to_html(current_val)
        conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, key))
        return 'converted'


def migration_15(conn: sqlite3.Connection) -> None:
    """
    Миграция v15: Конвертация всех текстов из MarkdownV2 в HTML.
    
    Для каждого текстового ключа:
    1. Если текст совпадает с дефолтным MarkdownV2 → заменяем на чистый HTML-дефолт
    2. Если текст НЕ совпадает (пользователь изменил) → конвертируем MD → HTML автоматически
    
    Обрабатывает оба формата хранения: обычная строка и JSON {text, photo_file_id, ...}.
    """
    import json as _json
    logger.info("Применение миграции v15 (MarkdownV2 → HTML)...")
    
    # ── 1. main_page_text ─────────────────────────────────────────────────────
    md_main = (
        "🔐 *Добро пожаловать в ArcVPN\\!*\n"
        "Быстрый, безопасный и анонимный доступ к интернету\\.\n"
        "Без логов, без ограничений, без проблем\\! 🚀\n"
    )
    html_main = (
        "🔐 <b>Добро пожаловать в ArcVPN!</b>\n\n"
        "Быстрый, безопасный и анонимный доступ к интернету.\n"
        "Без логов, без ограничений, без проблем! 🚀"
    )
    result = _migrate_setting_text(conn, 'main_page_text', md_main, html_main)
    logger.info(f"main_page_text: {result}")
    
    # ── 2. help_page_text ─────────────────────────────────────────────────────
    md_help = (
        "🔐 Этот бот предоставляет доступ к VPN\\-сервису\\.\n\n"
        "*Как это работает:*\n"
        "1\\. Купите ключ через раздел «Купить ключ»\n\n"
        "2\\. Установите VPN\\-клиент для вашего устройства:\n\n"
        "Hiddify или v2rayNG или V2Box\n"
        "Подробная инструкция по настройке VPN👇 https://telegra\\.ph/Kak\\-nastroit\\-VPN\\-Gajd\\-za\\-2\\-minuty\\-01\\-23\n\n"
        "3\\. Импортируйте ключ в приложение\n\n"
        "4\\. Подключайтесь и наслаждайтесь\\! 🚀"
    )
    html_help = (
        "🔐 Этот бот предоставляет доступ к VPN-сервису.\n\n"
        "<b>Как это работает:</b>\n"
        "1. Купите ключ через раздел «Купить ключ»\n\n"
        "2. Установите VPN-клиент для вашего устройства:\n\n"
        "Hiddify или v2rayNG или V2Box\n"
        "Подробная инструкция по настройке VPN👇 https://telegra.ph/Kak-nastroit-VPN-Gajd-za-2-minuty-01-23\n\n"
        "3. Импортируйте ключ в приложение\n\n"
        "4. Подключайтесь и наслаждайтесь! 🚀"
    )
    result = _migrate_setting_text(conn, 'help_page_text', md_help, html_help)
    logger.info(f"help_page_text: {result}")
    
    # ── 3. notification_text ──────────────────────────────────────────────────
    # Может содержать старые теги {days}/{keyname} или новые %дней%/%имяключа%
    md_notification = (
        "⚠️ *Ваш VPN-ключ %имяключа% скоро истекает!*\n\n"
        "Через %дней% дней закончится срок действия вашего ключа.\n\n"
        "Продлите подписку, чтобы сохранить доступ к VPN без перерыва!"
    )
    html_notification = (
        "⚠️ <b>Ваш VPN-ключ %имяключа% скоро истекает!</b>\n\n"
        "Через %дней% дней закончится срок действия вашего ключа.\n\n"
        "Продлите подписку, чтобы сохранить доступ к VPN без перерыва!"
    )
    result = _migrate_setting_text(conn, 'notification_text', md_notification, html_notification)
    logger.info(f"notification_text: {result}")
    
    # ── 4. trial_page_text ────────────────────────────────────────────────────
    md_trial = (
        "🎁 *Пробная подписка*\n\n"
        "Хотите попробовать наш VPN бесплатно?\n\n"
        "Мы предлагаем пробный период, чтобы вы могли убедиться в качестве "
        "и скорости нашего сервиса\\.\n\n"
        "*Что входит в пробный доступ:*\n"
        "• Полный доступ к VPN без ограничений по сайтам\n"
        "• Высокая скорость соединения\n"
        "• Несколько протоколов на выбор\n\n"
        "Нажмите кнопку ниже, чтобы активировать пробный доступ прямо сейчас\!\n\n"
        "_Пробный период предоставляется один раз на аккаунт\._"
    )
    html_trial = (
        "🎁 <b>Пробная подписка</b>\n\n"
        "Хотите попробовать наш VPN бесплатно?\n\n"
        "Мы предлагаем пробный период, чтобы вы могли убедиться в качестве "
        "и скорости нашего сервиса.\n\n"
        "<b>Что входит в пробный доступ:</b>\n"
        "• Полный доступ к VPN без ограничений по сайтам\n"
        "• Высокая скорость соединения\n"
        "• Несколько протоколов на выбор\n\n"
        "Нажмите кнопку ниже, чтобы активировать пробный доступ прямо сейчас!\n\n"
        "<i>Пробный период предоставляется один раз на аккаунт.</i>"
    )
    result = _migrate_setting_text(conn, 'trial_page_text', md_trial, html_trial)
    logger.info(f"trial_page_text: {result}")
    
    # ── 5. prepayment_text ────────────────────────────────────────────────────
    md_prepayment = (
        "💳 *Купить ключ*\n\n"
        "🔐 *Что вы получаете:*\n"
        "• Доступ к нескольким серверам и протоколам\n"
        "• 1 ключ \\= 1 устройство \\(одновременное подключение\\)\n"
        "• Лимит трафика: до 1 ТБ в месяц \\(сброс каждые 30 дней\\)\n\n"
        "⚠️ *Важно знать:*\n"
        "• Средства не возвращаются — услуга считается оказанной в момент получения ключа\n"
        "• Мы не даём никаких гарантий бесперебойной работы сервиса в будущем\n"
        "• Мы не можем гарантировать, что данная технология останется рабочей\n\n"
        "_Приобретая ключ, вы соглашаетесь с этими условиями\\._"
    )
    html_prepayment = (
        "💳 <b>Купить ключ</b>\n\n"
        "🔐 <b>Что вы получаете:</b>\n"
        "• Доступ к нескольким серверам и протоколам\n"
        "• 1 ключ = 1 устройство (одновременное подключение)\n"
        "• Лимит трафика: до 1 ТБ в месяц (сброс каждые 30 дней)\n\n"
        "⚠️ <b>Важно знать:</b>\n"
        "• Средства не возвращаются — услуга считается оказанной в момент получения ключа\n"
        "• Мы не даём никаких гарантий бесперебойной работы сервиса в будущем\n"
        "• Мы не можем гарантировать, что данная технология останется рабочей\n\n"
        "<i>Приобретая ключ, вы соглашаетесь с этими условиями.</i>"
    )
    result = _migrate_setting_text(conn, 'prepayment_text', md_prepayment, html_prepayment)
    logger.info(f"prepayment_text: {result}")
    
    # ── 6. key_delivery_text ──────────────────────────────────────────────────
    md_key_delivery = (
        "✅ *Ваш VPN\\-ключ\\!*\n\n"
        "%ключ%\n"
        "☝️ Нажмите, чтобы скопировать\\.\n\n"
        "📱 *Инструкция:*\n"
        "1\\. Скопируйте ссылку или отсканируйте QR\\-код\\.\n"
        "2\\. Импортируйте в свой клиент\\. Какие именно клиент подходит смотри в инструкции по кнопке ниже\\.\n"
        "3\\. Нажмите подключиться\\!"
    )
    html_key_delivery = (
        "✅ <b>Ваш VPN-ключ!</b>\n\n"
        "%ключ%\n"
        "☝️ Нажмите, чтобы скопировать.\n\n"
        "📱 <b>Инструкция:</b>\n"
        "1. Скопируйте ссылку или отсканируйте QR-код.\n"
        "2. Импортируйте в свой клиент. Какие именно клиент подходит смотри в инструкции по кнопке ниже.\n"
        "3. Нажмите подключиться!"
    )
    result = _migrate_setting_text(conn, 'key_delivery_text', md_key_delivery, html_key_delivery)
    logger.info(f"key_delivery_text: {result}")
    
    # ── 7. traffic_notification_text ──────────────────────────────────────────
    md_traffic = '⚠️ По ключу *{keyname}* осталось {percent}% трафика ({used} из {limit})'
    html_traffic = '⚠️ По ключу <b>{keyname}</b> осталось {percent}% трафика ({used} из {limit})'
    result = _migrate_setting_text(conn, 'traffic_notification_text', md_traffic, html_traffic)
    logger.info(f"traffic_notification_text: {result}")
    
    # ── 8. referral_conditions_text ───────────────────────────────────────────
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'referral_conditions_text'")
    row = cursor.fetchone()
    if row and row['value'] and row['value'].strip():
        current_val = row['value']
        try:
            data = _json.loads(current_val)
            if isinstance(data, dict) and 'text' in data and data['text']:
                data['text'] = _convert_md_to_html(data['text'])
                new_val = _json.dumps(data, ensure_ascii=False)
                conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, 'referral_conditions_text'))
                logger.info("referral_conditions_text: json_converted")
            else:
                logger.info("referral_conditions_text: пустой JSON, пропуск")
        except (_json.JSONDecodeError, TypeError):
            new_val = _convert_md_to_html(current_val)
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, 'referral_conditions_text'))
            logger.info("referral_conditions_text: converted")
    else:
        logger.info("referral_conditions_text: пустой, пропуск")
    
    # ── 9. broadcast_message ──────────────────────────────────────────────────
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'broadcast_message'")
    row = cursor.fetchone()
    if row and row['value'] and row['value'].strip():
        current_val = row['value']
        try:
            data = _json.loads(current_val)
            if isinstance(data, dict) and 'text' in data and data['text']:
                data['text'] = _convert_md_to_html(data['text'])
                new_val = _json.dumps(data, ensure_ascii=False)
                conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, 'broadcast_message'))
                logger.info("broadcast_message: json_converted")
            else:
                logger.info("broadcast_message: пустой JSON, пропуск")
        except (_json.JSONDecodeError, TypeError):
            new_val = _convert_md_to_html(current_val)
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (new_val, 'broadcast_message'))
            logger.info("broadcast_message: converted")
    else:
        logger.info("broadcast_message: пустой, пропуск")
    
    logger.info("Миграция v15 применена")


def migration_16(conn: sqlite3.Connection) -> None:
    """
    Миграция v16: Добавляет поле first_name в таблицу users.
    """
    logger.info("Применение миграции v16...")
    
    # Добавляем поле first_name для хранения имени пользователя
    _add_column(conn, 'users', 'first_name TEXT')
    
    logger.info("Миграция v16 применена")


def migration_17(conn: sqlite3.Connection) -> None:
    """
    Миграция v17: Индивидуальные subscription ссылки для каждого ключа.
    
    Добавляет поле sub_id (уникальный идентификатор подписки) в таблицу vpn_keys.
    Каждый ключ получает свою уникальную subscription ссылку вида:
    https://sub.arcvpn.mooo.com:8443/sub/{sub_id}
    
    Это позволяет пользователям покупать несколько ключей с разными сроками
    и использовать их независимо на разных устройствах.
    """
    logger.info("Применение миграции v17 (Индивидуальные subscription ссылки)...")
    
    # Добавляем поле sub_id (без UNIQUE в ALTER TABLE - добавим индекс отдельно)
    _add_column(conn, 'vpn_keys', 'sub_id TEXT')
    
    # Создаем уникальный индекс для sub_id
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vpn_keys_sub_id ON vpn_keys(sub_id)")
    except sqlite3.OperationalError as e:
        if "already exists" not in str(e):
            raise
    
    # Генерируем уникальные sub_id для существующих ключей
    cursor = conn.execute("SELECT id FROM vpn_keys WHERE sub_id IS NULL")
    keys_without_sub_id = [row['id'] for row in cursor.fetchall()]
    
    import uuid
    for key_id in keys_without_sub_id:
        # Генерируем уникальный sub_id (используем UUID без дефисов)
        sub_id = uuid.uuid4().hex
        
        # Проверяем уникальность (на всякий случай)
        attempts = 0
        while attempts < 100:
            cursor = conn.execute("SELECT 1 FROM vpn_keys WHERE sub_id = ?", (sub_id,))
            if not cursor.fetchone():
                break
            sub_id = uuid.uuid4().hex
            attempts += 1
        
        conn.execute("UPDATE vpn_keys SET sub_id = ? WHERE id = ?", (sub_id, key_id))
    
    logger.info(f"Сгенерированы sub_id для {len(keys_without_sub_id)} существующих ключей")
    logger.info("Миграция v17 применена")


MIGRATIONS = {
    1: migration_1,
    2: migration_2,
    3: migration_3,
    4: migration_4,
    5: migration_5,
    6: migration_6,
    7: migration_7,
    8: migration_8,
    9: migration_9,
    10: migration_10,
    11: migration_11,
    12: migration_12,
    13: migration_13,
    14: migration_14,
    15: migration_15,
    16: migration_16,
    17: migration_17,
}


def run_migrations() -> None:
    """
    Запускает все необходимые миграции.
    
    Проверяет текущую версию и применяет все миграции от текущей до LATEST_VERSION.
    """
    try:
        current = get_current_version()
        
        if current >= LATEST_VERSION:
            logger.info(f"✅ БД соответствует версии {LATEST_VERSION}. Миграция не требуется.")
            return
        
        logger.info(f"🔄 Требуется миграция БД с версии {current} до {LATEST_VERSION}")
        
        with get_db() as conn:
            for version in range(current + 1, LATEST_VERSION + 1):
                if version in MIGRATIONS:
                    logger.info(f"🚀 Применяю миграцию v{version}...")
                    MIGRATIONS[version](conn)
                    set_version(conn, version)
        
        logger.info(f"✅ Миграция успешная : БД обновлена до версии {LATEST_VERSION}")
        
    except Exception as e:
        logger.error(f"❌ Неуспешная миграция: {e}")
        raise
