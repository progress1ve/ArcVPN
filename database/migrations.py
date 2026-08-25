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
LATEST_VERSION = 56


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
        ('support_channel_link', 'https://t.me/Turan11627'),
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
        "Нажмите кнопку ниже, чтобы активировать пробный доступ прямо сейчас\\!\n\n"
        "_Пробный период предоставляется один раз на аккаунт\\._"
    )

    # Настройки пробной подписки
    trial_settings = [
        ('trial_enabled', '1'),          # Включено по умолчанию
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
        "⚠️ *Ваша VPN-подписка %имяподписки% скоро истекает!*\n\n"
        "Через %дней% закончится срок действия вашей подписки.\n\n"
        "Продлите подписку, чтобы сохранить доступ к VPN без перерыва!"
    )
    html_notification = (
        "⚠️ <b>Ваша VPN-подписка %имяподписки% скоро истекает!</b>\n\n"
        "Через %дней% закончится срок действия вашей подписки.\n\n"
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
        "Нажмите кнопку ниже, чтобы активировать пробный доступ прямо сейчас\\!\n\n"
        "_Пробный период предоставляется один раз на аккаунт\\._"
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
    https://arcc.mooo.com:2053/sub/{sub_id}
    
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


def migration_18(conn: sqlite3.Connection) -> None:
    """
    Миграция v18: Система промокодов.
    
    Изменения:
    - Новая таблица promocodes (промокоды)
    - Новая таблица promocode_usage (использование промокодов)
    """
    logger.info("Применение миграции v18 (Промокоды)...")
    
    # Таблица промокодов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            discount_rub INTEGER NOT NULL,
            max_uses INTEGER NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            discount_type TEXT NOT NULL DEFAULT 'fixed',
            discount_percent INTEGER NOT NULL DEFAULT 0
        )
    """)
    # Обратная совместимость для БД, созданных до появления процентных промокодов
    _promo_cols = [r[1] for r in conn.execute("PRAGMA table_info(promocodes)")]
    if 'discount_type' not in _promo_cols:
        conn.execute("ALTER TABLE promocodes ADD COLUMN discount_type TEXT NOT NULL DEFAULT 'fixed'")
    if 'discount_percent' not in _promo_cols:
        conn.execute("ALTER TABLE promocodes ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_promocodes_code ON promocodes(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_promocodes_expires_at ON promocodes(expires_at)")
    
    # Таблица использования промокодов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS promocode_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promocode_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (promocode_id) REFERENCES promocodes(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(promocode_id, user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_promocode_usage_promocode ON promocode_usage(promocode_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_promocode_usage_user ON promocode_usage(user_id)")
    
    logger.info("Миграция v18 применена")


def migration_19(conn: sqlite3.Connection) -> None:
    """
    Миграция v19: Добавление поддержки промокодов в платежи.
    
    Изменения:
    - Добавляет колонку promocode_id в таблицу payments
    - Добавляет колонку discount_rub в таблицу payments
    """
    logger.info("Применение миграции v19 (Промокоды в платежах)...")
    
    # Добавляем колонку promocode_id
    try:
        conn.execute("ALTER TABLE payments ADD COLUMN promocode_id INTEGER")
        logger.info("Колонка promocode_id добавлена в таблицу payments")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка promocode_id уже существует")
        else:
            raise
    
    # Добавляем колонку discount_rub
    try:
        conn.execute("ALTER TABLE payments ADD COLUMN discount_rub INTEGER DEFAULT 0")
        logger.info("Колонка discount_rub добавлена в таблицу payments")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Колонка discount_rub уже существует")
        else:
            raise
    
    # Создаем индекс для promocode_id
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_promocode ON payments(promocode_id)")
    
    logger.info("Миграция v19 применена")


def migration_20(conn: sqlite3.Connection) -> None:
    """
    Миграция v20: Изменение логики уведомлений - отправка раз в 7 дней вместо раз в день.
    
    Изменения:
    - Удаляет уникальный индекс idx_notification_log_unique (vpn_key_id, sent_at)
    - Теперь можно записывать несколько уведомлений для одного ключа в разные дни
    - Логика проверки изменена: is_notification_sent_today проверяет последние 7 дней
    """
    logger.info("Применение миграции v20 (Уведомления раз в 7 дней)...")
    
    try:
        # Удаляем уникальный индекс, который мешает записывать несколько уведомлений
        conn.execute("DROP INDEX IF EXISTS idx_notification_log_unique")
        logger.info("Уникальный индекс idx_notification_log_unique удалён")
        
        # Оставляем обычный индекс для быстрого поиска по vpn_key_id
        # (он уже существует: idx_notification_log_vpn_key)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении индекса: {e}")
        raise
    
    logger.info("Миграция v20 применена")


def migration_21(conn: sqlite3.Connection) -> None:
    """
    Миграция v21: Lifecycle-поля ордера.

    Изменения:
    - payments.operation_type: new / renew / upgrade / topup / trial_start
    - payments.target_tariff_id: целевой тариф доменной операции
    - payments.fulfillment_status: pending / applied / failed / manual_review
    - payments.fulfilled_at: время успешного исполнения
    - payments.fulfillment_error: последняя ошибка исполнения
    - payments.attempt_count: количество попыток post-payment исполнения
    """
    logger.info("Применение миграции v21 (Lifecycle ордера)...")

    _add_column(conn, "payments", "operation_type TEXT")
    _add_column(conn, "payments", "target_tariff_id INTEGER")
    _add_column(conn, "payments", "fulfillment_status TEXT DEFAULT 'pending'")
    _add_column(conn, "payments", "fulfilled_at DATETIME")
    _add_column(conn, "payments", "fulfillment_error TEXT")
    _add_column(conn, "payments", "attempt_count INTEGER DEFAULT 0")

    # Backfill operation_type и target_tariff_id для существующих заказов.
    conn.execute("""
        UPDATE payments
        SET operation_type = CASE
            WHEN payment_type = 'trial' THEN 'trial_start'
            WHEN tariff_id IS NULL AND vpn_key_id IS NULL THEN 'topup'
            WHEN vpn_key_id IS NOT NULL THEN 'renew'
            ELSE 'new'
        END
        WHERE operation_type IS NULL
    """)
    conn.execute("""
        UPDATE payments
        SET target_tariff_id = tariff_id
        WHERE target_tariff_id IS NULL
    """)
    conn.execute("""
        UPDATE payments
        SET fulfillment_status = CASE
            WHEN status = 'paid' THEN 'applied'
            ELSE COALESCE(fulfillment_status, 'pending')
        END
        WHERE fulfillment_status IS NULL OR fulfillment_status = ''
    """)
    conn.execute("""
        UPDATE payments
        SET fulfilled_at = paid_at
        WHERE status = 'paid' AND paid_at IS NOT NULL AND fulfilled_at IS NULL
    """)
    conn.execute("""
        UPDATE payments
        SET attempt_count = 1
        WHERE status = 'paid' AND (attempt_count IS NULL OR attempt_count = 0)
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_operation_type ON payments(operation_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_fulfillment_status ON payments(fulfillment_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_target_tariff_id ON payments(target_tariff_id)")

    logger.info("Миграция v21 применена")


def migration_22(conn: sqlite3.Connection) -> None:
    """
    Миграция v22: Резервные (бэкап) серверы.

    Изменения:
    - Добавляет колонку is_reserve в таблицу servers.
    - Все существующие серверы по умолчанию НЕ резервные (is_reserve = 0).

    Резервный сервер используется для аварийного Telegram-доступа, когда
    подписка истекла или исчерпан трафик: пользователь сохраняет доступ
    к Telegram (через резервный конфиг), чтобы продлить подписку.
    """
    logger.info("Применение миграции v22 (Резервные серверы)...")

    _add_column(conn, "servers", "is_reserve INTEGER DEFAULT 0")

    logger.info("Миграция v22 применена")


def migration_23(conn: sqlite3.Connection) -> None:
    """
    Миграция v23: Учёт подключённых устройств.

    Изменения в vpn_keys:
    - connect_notified INTEGER DEFAULT 0 — отправлено ли уведомление «подписка
      подключена» (чтобы слать его один раз при первом реальном подключении);
    - online_devices INTEGER DEFAULT 0 — последнее известное число онлайн-устройств
      (по числу онлайн-IP с панели 3X-UI).
    """
    logger.info("Применение миграции v23 (Учёт устройств)...")

    _add_column(conn, "vpn_keys", "connect_notified INTEGER DEFAULT 0")
    _add_column(conn, "vpn_keys", "online_devices INTEGER DEFAULT 0")

    logger.info("Миграция v23 применена")


def migration_24(conn: sqlite3.Connection) -> None:
    """
    Миграция v24: Реферальная модель «3 + 5» в днях подписки.

    Раньше реферал получал фиксированные 50₽ на баланс за оплату приглашённого.
    Новая модель — бонусные ДНИ подписки:
    - +3 дня рефереру, когда приглашённый друг впервые запускает бота (авто-триал);
    - +5 дней рефереру И +5 дней самому другу при первой покупке друга.
    Каждый бонус начисляется один раз на друга (флаги идемпотентности).

    Изменения referral_stats:
    - bonus_trial_granted INTEGER DEFAULT 0 — выдан ли бонус за запуск друга;
    - bonus_purchase_granted INTEGER DEFAULT 0 — выдан ли бонус за первую покупку.
    Накопленные дни складываем в существующую колонку total_reward_days.
    """
    logger.info("Применение миграции v24 (Реферальные бонус-дни 3+5)...")

    _add_column(conn, "referral_stats", "bonus_trial_granted INTEGER DEFAULT 0")
    _add_column(conn, "referral_stats", "bonus_purchase_granted INTEGER DEFAULT 0")

    # Настройки размера бонусов (дни) — редактируемы из админки при желании.
    referral_bonus_settings = [
        ('referral_trial_bonus_days', '3'),
        ('referral_purchase_bonus_days', '5'),
        ('referral_reward_type', 'days'),
    ]
    for key, value in referral_bonus_settings:
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    logger.info("Миграция v24 применена")


def migration_25(conn: sqlite3.Connection) -> None:
    """
    Трекинг реальной активности VPN: когда ключ последний раз был онлайн.

    Планировщик каждые 5 минут опрашивает панель (`get_online_emails`) и
    штампует `last_online_at = CURRENT_TIMESTAMP` для онлайн-ключей. На этом
    строится статистика «кто сейчас онлайн» и «сколько человек включали VPN
    за 3 дня / неделю / месяц». Данные копятся с момента деплоя.
    """
    logger.info("Применение миграции v25 (трекинг онлайна last_online_at)...")
    _add_column(conn, "vpn_keys", "last_online_at DATETIME")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vpn_keys_last_online ON vpn_keys(last_online_at)")
    logger.info("Миграция v25 применена")


def migration_26(conn: sqlite3.Connection) -> None:
    """Реферальная программа: по 15 дней обоим за первую покупку друга."""
    logger.info("Применение миграции v26 (реферальная награда 15+15)...")
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('referral_trial_bonus_days', '0') "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('referral_purchase_bonus_days', '15') "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
    )
    logger.info("Миграция v26 применена")


def migration_27(conn: sqlite3.Connection) -> None:
    """WebApp: устройства, email-вход и персональные уведомления."""
    logger.info("Применение миграции v27 (WebApp account и devices)...")

    _add_column(conn, "users", "email TEXT")
    _add_column(conn, "users", "email_verified_at DATETIME")
    _add_column(conn, "users", "notify_expiry INTEGER DEFAULT 1")
    _add_column(conn, "users", "notify_traffic INTEGER DEFAULT 1")
    _add_column(conn, "users", "notify_connection INTEGER DEFAULT 1")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique "
        "ON users(LOWER(email)) WHERE email IS NOT NULL"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            vpn_key_id INTEGER REFERENCES vpn_keys(id) ON DELETE SET NULL,
            device_token_hash TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'unknown',
            model TEXT,
            display_name TEXT NOT NULL,
            browser TEXT,
            screen_size TEXT,
            first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            imported_at DATETIME,
            UNIQUE(user_id, device_token_hash)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_devices_user ON user_devices(user_id, last_seen_at DESC)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            purpose TEXT NOT NULL CHECK(purpose IN ('link', 'login')),
            code_hash TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, purpose)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS web_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_user ON web_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_web_sessions_expiry ON web_sessions(expires_at)")
    logger.info("Миграция v27 применена")


def migration_28(conn: sqlite3.Connection) -> None:
    """Диалоги поддержки WebApp с ответами администратора через Telegram."""
    logger.info("Применение миграции v28 (WebApp support chat)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS support_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'open',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
            sender TEXT NOT NULL CHECK(sender IN ('user', 'admin')),
            sender_telegram_id INTEGER,
            body TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            read_at DATETIME
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_support_messages_thread ON support_messages(thread_id, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_support_threads_updated ON support_threads(updated_at)")
    logger.info("Миграция v28 применена")


def migration_29(conn: sqlite3.Connection) -> None:
    """Фиксированная коммерческая сетка ArcVPN: 1/3/6/12 месяцев."""
    logger.info("Применение миграции v29 (новая тарифная сетка)...")

    plans = (
        ("1 месяц", 30, 125, 10),
        ("3 месяца", 90, 300, 20),
        ("6 месяцев", 180, 540, 30),
        ("12 месяцев", 365, 960, 40),
    )
    regular = conn.execute(
        """
        SELECT traffic_limit_gb, group_id
        FROM tariffs
        WHERE is_active = 1 AND name != 'Admin Tariff'
        ORDER BY display_order, id
        LIMIT 1
        """
    ).fetchone()
    traffic_limit_gb = int(regular["traffic_limit_gb"] or 0) if regular else 1024
    group_id = int(regular["group_id"] or 1) if regular else 1

    for name, days, price_rub, display_order in plans:
        lower = days - (2 if days < 365 else 1)
        upper = days + (2 if days < 365 else 1)
        rows = conn.execute(
            """
            SELECT id FROM tariffs
            WHERE is_active = 1
              AND name != 'Admin Tariff'
              AND duration_days BETWEEN ? AND ?
            """,
            (lower, upper),
        ).fetchall()
        if rows:
            conn.execute(
                """
                UPDATE tariffs
                SET name = ?, duration_days = ?, price_rub = ?, display_order = ?
                WHERE is_active = 1
                  AND name != 'Admin Tariff'
                  AND duration_days BETWEEN ? AND ?
                """,
                (name, days, price_rub, display_order, lower, upper),
            )
        else:
            conn.execute(
                """
                INSERT INTO tariffs (
                    name, duration_days, price_cents, price_stars, price_rub,
                    external_id, display_order, is_active, traffic_limit_gb, group_id
                ) VALUES (?, ?, 0, 0, ?, NULL, ?, 1, ?, ?)
                """,
                (name, days, price_rub, display_order, traffic_limit_gb, group_id),
            )

    logger.info("Миграция v29 применена")


def migration_30(conn: sqlite3.Connection) -> None:
    """Persistent WebApp entitlements and requested payment add-ons."""
    logger.info("Применение миграции v30 (лимиты WebApp и add-ons платежа)...")

    _add_column(conn, "users", "device_limit INTEGER NOT NULL DEFAULT 2")
    _add_column(conn, "users", "lte_quota_gb INTEGER NOT NULL DEFAULT 20")
    _add_column(conn, "users", "lte_used_bytes INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "users", "entitlements_updated_at DATETIME")

    _add_column(conn, "payments", "requested_device_limit INTEGER")
    _add_column(conn, "payments", "requested_lte_quota_gb INTEGER")
    _add_column(conn, "payments", "addons_applied_at DATETIME")

    conn.execute(
        "UPDATE users SET device_limit = 2 "
        "WHERE device_limit IS NULL OR device_limit < 2"
    )
    conn.execute(
        "UPDATE users SET lte_quota_gb = 20 "
        "WHERE lte_quota_gb IS NULL OR lte_quota_gb < 20"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_addons_pending "
        "ON payments(status, addons_applied_at) "
        "WHERE requested_device_limit IS NOT NULL OR requested_lte_quota_gb IS NOT NULL"
    )
    logger.info("Миграция v30 применена")


def migration_31(conn: sqlite3.Connection) -> None:
    """Raw counters for the approved 500 GB weighted traffic model."""
    logger.info("Применение миграции v31 (weighted traffic 500 GB, LTE x10)...")
    _add_column(conn, "users", "traffic_monthly_limit_gb INTEGER NOT NULL DEFAULT 500")
    _add_column(conn, "users", "normal_used_bytes INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "users", "traffic_cycle_started_at DATETIME")
    _add_column(conn, "users", "traffic_cycle_reset_at DATETIME")

    conn.execute(
        "UPDATE users SET traffic_monthly_limit_gb = 500 "
        "WHERE traffic_monthly_limit_gb IS NULL OR traffic_monthly_limit_gb <= 0"
    )
    conn.execute(
        "UPDATE users SET normal_used_bytes = 0 "
        "WHERE normal_used_bytes IS NULL OR normal_used_bytes < 0"
    )
    logger.info("Миграция v31 применена")


def migration_32(conn: sqlite3.Connection) -> None:
    """Revocable and renameable WebApp device slots."""
    logger.info("Применение миграции v32 (управление слотами устройств)...")
    _add_column(conn, "user_devices", "is_active INTEGER NOT NULL DEFAULT 1")
    _add_column(conn, "user_devices", "revoked_at DATETIME")
    conn.execute(
        "UPDATE user_devices SET is_active = 1 WHERE is_active IS NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_devices_active "
        "ON user_devices(user_id, is_active, first_seen_at)"
    )
    logger.info("Миграция v32 применена")


def migration_33(conn: sqlite3.Connection) -> None:
    """Give the referrer five days when an invited friend activates the trial."""
    logger.info("Применение миграции v33 (реферальный бонус за первый вход)...")
    conn.execute(
        """INSERT INTO settings (key, value) VALUES ('referral_trial_bonus_days', '5')
           ON CONFLICT(key) DO UPDATE SET value = '5'"""
    )
    logger.info("Миграция v33 применена")


def migration_34(conn: sqlite3.Connection) -> None:
    """Idempotent lifecycle messages and answers for retention campaigns."""
    logger.info("Применение миграции v34 (lifecycle-коммуникации)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_key TEXT NOT NULL,
            answer TEXT,
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            answered_at DATETIME,
            UNIQUE(user_id, event_key),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_events_key ON lifecycle_events(event_key, sent_at)")
    logger.info("Миграция v34 применена")


def migration_35(conn: sqlite3.Connection) -> None:
    """Lifecycle campaigns apply only to users who join after rollout."""
    logger.info("Применение миграции v35 (граница lifecycle-аудитории)...")
    conn.execute("""
        INSERT OR IGNORE INTO settings(key, value)
        VALUES ('lifecycle_eligible_after', datetime('now'))
    """)
    logger.info("Миграция v35 применена")


def migration_36(conn: sqlite3.Connection) -> None:
    """Make 500 GiB the single monthly allowance for paid subscriptions."""
    logger.info("Применение миграции v36 (единый лимит 500 ГБ)...")
    limit_bytes = 500 * 1024 * 1024 * 1024
    conn.execute("UPDATE tariffs SET traffic_limit_gb = 500 WHERE COALESCE(traffic_limit_gb, 0) != 500")
    conn.execute(
        """UPDATE vpn_keys SET traffic_limit = ?
           WHERE tariff_id IS NOT NULL AND COALESCE(traffic_limit, 0) != ?""",
        (limit_bytes, limit_bytes),
    )
    conn.execute(
        "UPDATE users SET traffic_monthly_limit_gb = 500 WHERE COALESCE(traffic_monthly_limit_gb, 0) != 500"
    )
    logger.info("Миграция v36 применена")


def migration_37(conn: sqlite3.Connection) -> None:
    """Stored YooKassa methods with self-service recurring cancellation."""
    logger.info("Применение миграции v37 (управление автопродлением)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recurring_payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL DEFAULT 'yookassa',
            payment_method_id TEXT NOT NULL,
            method_type TEXT NOT NULL DEFAULT 'bank_card',
            display_title TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            consent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            disabled_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, payment_method_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recurring_user_active ON recurring_payment_methods(user_id, active)")
    _add_column(conn, "payments", "auto_renew_requested INTEGER NOT NULL DEFAULT 0")
    logger.info("Миграция v37 применена")


def migration_38(conn: sqlite3.Connection) -> None:
    """Remember completed panel expiry actions to avoid retrying them every minute."""
    logger.info("Применение миграции v38 (идемпотентное отключение истёкших ключей)...")
    _add_column(conn, "vpn_keys", "panel_disabled_at DATETIME")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_vpn_keys_panel_disable ON vpn_keys(expires_at, panel_disabled_at)"
    )
    logger.info("Миграция v38 применена")


def migration_39(conn: sqlite3.Connection) -> None:
    """Enforce path-bound subscriptions after a device has been released."""
    logger.info("Applying migration v39 (device-bound subscription paths)...")
    _add_column(conn, "users", "enforce_device_tokens INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """UPDATE users SET enforce_device_tokens = 1
           WHERE id IN (
               SELECT DISTINCT user_id FROM user_devices
               WHERE COALESCE(is_active, 1) = 0
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_device_enforcement "
        "ON users(enforce_device_tokens)"
    )
    logger.info("Migration v39 applied")


def migration_40(conn: sqlite3.Connection) -> None:
    """Give every imported device a standalone one-segment subscription id."""
    logger.info("Applying migration v40 (per-device subscription ids)...")
    _add_column(conn, "user_devices", "device_sub_id TEXT")
    conn.execute(
        "UPDATE user_devices SET device_sub_id=lower(hex(randomblob(16))) "
        "WHERE device_sub_id IS NULL OR device_sub_id=''"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_devices_sub_id "
        "ON user_devices(device_sub_id)"
    )
    logger.info("Migration v40 applied")


def migration_41(conn: sqlite3.Connection) -> None:
    """Store server inventory and time-series health samples for Business Console."""
    logger.info("Applying migration v41 (server inventory and health history)...")
    _add_column(conn, "servers", "provider TEXT")
    _add_column(conn, "servers", "location TEXT")
    _add_column(conn, "servers", "monthly_cost_rub INTEGER")
    _add_column(conn, "servers", "capacity_mbps INTEGER")
    _add_column(conn, "servers", "lifecycle_state TEXT NOT NULL DEFAULT 'unknown'")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_health_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            host TEXT NOT NULL,
            sampled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            state TEXT NOT NULL,
            online_count INTEGER,
            clients_count INTEGER,
            latency_ms REAL,
            cpu_pct REAL,
            mem_pct REAL,
            inbound_count INTEGER,
            xray_state TEXT,
            telemetry_available INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE SET NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_server_health_host_time "
        "ON server_health_samples(host, sampled_at DESC)"
    )
    conn.execute("""
        UPDATE servers SET
          provider=CASE host WHEN '2.26.84.210' THEN 'Play2Go'
                             WHEN '195.226.92.37' THEN 'rdp-onedash.ru'
                             ELSE provider END,
          location=CASE host WHEN '2.26.84.210' THEN 'Германия'
                             WHEN '195.226.92.37' THEN 'Финляндия'
                             ELSE location END,
          monthly_cost_rub=CASE host WHEN '2.26.84.210' THEN 340
                                     WHEN '195.226.92.37' THEN 365
                                     ELSE monthly_cost_rub END,
          capacity_mbps=COALESCE(capacity_mbps, 1000)
        WHERE host IN ('2.26.84.210', '195.226.92.37')
    """)
    logger.info("Migration v41 applied")


def migration_42(conn: sqlite3.Connection) -> None:
    """Independent node-agent metrics, separate from 3x-ui telemetry."""
    logger.info("Applying migration v42 (independent node agent metrics)...")
    _add_column(conn, "server_health_samples", "source TEXT NOT NULL DEFAULT 'panel'")
    _add_column(conn, "server_health_samples", "load_1m REAL")
    _add_column(conn, "server_health_samples", "disk_used_pct REAL")
    _add_column(conn, "server_health_samples", "net_rx_bps REAL")
    _add_column(conn, "server_health_samples", "net_tx_bps REAL")
    _add_column(conn, "server_health_samples", "tcp_established INTEGER")
    _add_column(conn, "server_health_samples", "uptime_seconds INTEGER")
    _add_column(conn, "server_health_samples", "xui_active INTEGER")
    _add_column(conn, "server_health_samples", "hysteria_active INTEGER")
    _add_column(conn, "server_health_samples", "boot_id TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_server_health_source_time "
        "ON server_health_samples(source, sampled_at DESC)"
    )
    logger.info("Migration v42 applied")


def migration_43(conn: sqlite3.Connection) -> None:
    """Track hypervisor CPU contention on inexpensive VPS nodes."""
    logger.info("Applying migration v43 (CPU steal telemetry)...")
    _add_column(conn, "server_health_samples", "cpu_steal_pct REAL")
    logger.info("Migration v43 applied")


def migration_44(conn: sqlite3.Connection) -> None:
    """Recurring-card renewal schedule with idempotent billing cycles."""
    logger.info("Applying migration v44 (recurring renewal cycles)...")
    for name, ddl in (
        ("vpn_key_id", "INTEGER"), ("tariff_id", "INTEGER"),
        ("amount_cents", "INTEGER"), ("period_days", "INTEGER"),
        ("next_charge_at", "DATETIME"), ("last_charge_at", "DATETIME"),
        ("failure_count", "INTEGER NOT NULL DEFAULT 0"), ("last_error", "TEXT"),
    ):
        _add_column(conn, "recurring_payment_methods", f"{name} {ddl}")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recurring_charge_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recurring_method_id INTEGER NOT NULL,
            vpn_key_id INTEGER NOT NULL,
            due_key TEXT NOT NULL,
            order_id TEXT,
            yookassa_payment_id TEXT,
            status TEXT NOT NULL DEFAULT 'claimed',
            error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(recurring_method_id, vpn_key_id, due_key),
            FOREIGN KEY(recurring_method_id) REFERENCES recurring_payment_methods(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recurring_cycle_status ON recurring_charge_cycles(status, created_at)")
    logger.info("Migration v44 applied")


def migration_45(conn: sqlite3.Connection) -> None:
    """Provider-quality probes for objective node and hosting comparisons."""
    logger.info("Applying migration v45 (network quality probes)...")
    for name, ddl in (
        ("packet_loss_pct", "REAL"), ("jitter_ms", "REAL"),
        ("dns_ms", "REAL"), ("https_ms", "REAL"),
        ("download_mbps", "REAL"), ("probed_at", "INTEGER"),
    ):
        _add_column(conn, "server_health_samples", f"{name} {ddl}")
    logger.info("Migration v45 applied")


def migration_46(conn: sqlite3.Connection) -> None:
    """Panel-neutral server metadata used by the Remnawave migration layer."""
    logger.info("Applying migration v46 (panel abstraction and Remnawave staging)...")
    for column in (
        "panel_type TEXT NOT NULL DEFAULT 'xui'",
        "panel_api_url TEXT",
        "panel_api_token TEXT",
        "panel_node_uuid TEXT",
        "panel_squad_uuid TEXT",
        "panel_shadow_enabled INTEGER NOT NULL DEFAULT 0",
        "panel_write_mode TEXT NOT NULL DEFAULT 'disabled'",
    ):
        _add_column(conn, "servers", column)
    logger.info("Migration v46 applied")


def migration_47(conn: sqlite3.Connection) -> None:
    """Deduplicate expiry notifications per meaningful lifecycle stage."""
    logger.info("Applying migration v47 (typed expiry notifications)...")
    _add_column(conn, "notification_log", "notification_type TEXT NOT NULL DEFAULT 'legacy'")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_log_type "
        "ON notification_log(vpn_key_id, notification_type, sent_at)"
    )
    conn.execute(
        """INSERT INTO settings(key,value) VALUES('notification_text',?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
        ("⏳ <b>ArcVPN скоро закончится</b>\n\n"
         "Осталось: <b>%дней%</b>. Продлите заранее, чтобы VPN продолжил работать без перерыва.\n\n"
         "Настройки и устройства сохранятся, повторно импортировать подписку не потребуется.",),
    )
    conn.execute(
        """INSERT INTO settings(key,value) VALUES('expired_notification_text',?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
        ("🔒 <b>Подписка ArcVPN закончилась</b>\n\n"
         "VPN больше не подключается, но ваши настройки и устройства сохранены.\n\n"
         "Продлите подписку — доступ восстановится автоматически, заново настраивать Happ не нужно.",),
    )
    logger.info("Migration v47 applied")


def migration_48(conn: sqlite3.Connection) -> None:
    """Persist bounded manual infrastructure diagnostics."""
    conn.execute("""CREATE TABLE IF NOT EXISTS node_diagnostic_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host TEXT NOT NULL,
        result_json TEXT NOT NULL,
        ok INTEGER NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_node_diagnostics_host ON node_diagnostic_runs(host, created_at)")
    logger.info("Migration v48 applied")


def migration_49(conn: sqlite3.Connection) -> None:
    """Append-only security audit for privileged Business Console actions."""
    conn.execute("""CREATE TABLE IF NOT EXISTS admin_audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_type TEXT NOT NULL,
        actor_id TEXT,
        action TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        outcome TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_events(created_at DESC)")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS admin_audit_no_update
        BEFORE UPDATE ON admin_audit_events BEGIN
        SELECT RAISE(ABORT, 'admin_audit_events is append-only'); END""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS admin_audit_no_delete
        BEFORE DELETE ON admin_audit_events BEGIN
        SELECT RAISE(ABORT, 'admin_audit_events is append-only'); END""")
    logger.info("Migration v49 applied")


def migration_50(conn: sqlite3.Connection) -> None:
    """Role assignments for server-side Business Console authorization."""
    conn.execute("""CREATE TABLE IF NOT EXISTS admin_role_assignments (
        telegram_id INTEGER PRIMARY KEY,
        role TEXT NOT NULL CHECK(role IN ('owner','operator','support','finance','viewer')),
        assigned_by INTEGER,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    logger.info("Migration v50 applied")


def migration_51(conn: sqlite3.Connection) -> None:
    """Durable broadcast queue which survives bot restarts."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS broadcast_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by INTEGER NOT NULL,
            filter_type TEXT NOT NULL,
            message_text TEXT NOT NULL,
            photo_file_id TEXT,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK(status IN ('queued','running','completed','failed','cancelled')),
            total_count INTEGER NOT NULL DEFAULT 0,
            sent_count INTEGER NOT NULL DEFAULT 0,
            blocked_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            completed_at DATETIME,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS broadcast_job_recipients (
            job_id INTEGER NOT NULL REFERENCES broadcast_jobs(id) ON DELETE CASCADE,
            telegram_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','sent','blocked','failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            sent_at DATETIME,
            PRIMARY KEY(job_id, telegram_id)
        );
        CREATE INDEX IF NOT EXISTS idx_broadcast_jobs_status
            ON broadcast_jobs(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_broadcast_recipients_pending
            ON broadcast_job_recipients(job_id, status, telegram_id);
        UPDATE settings SET value = '0' WHERE key = 'broadcast_in_progress';
    """)
    logger.info("Migration v51 applied")


def migration_52(conn: sqlite3.Connection) -> None:
    """Admin-managed subscription catalog and operating expenses."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscription_profile_overrides (
            source_name TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 100,
            enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS service_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'other',
            amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
            incurred_on DATE NOT NULL,
            recurring_monthly INTEGER NOT NULL DEFAULT 0 CHECK(recurring_monthly IN (0,1)),
            note TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_service_expenses_date
            ON service_expenses(incurred_on DESC, id DESC);
    """)
    logger.info("Migration v52 applied")


def migration_53(conn: sqlite3.Connection) -> None:
    """Separate standalone visibility from synthetic-balancer membership."""
    columns = {row[1] for row in conn.execute(
        "PRAGMA table_info(subscription_profile_overrides)"
    )}
    if "include_in_auto" not in columns:
        conn.execute(
            "ALTER TABLE subscription_profile_overrides "
            "ADD COLUMN include_in_auto INTEGER NOT NULL DEFAULT 1 "
            "CHECK(include_in_auto IN (0,1))"
        )
    logger.info("Migration v53 applied")


def migration_54(conn: sqlite3.Connection) -> None:
    """Durable, idempotent lifecycle for one Standard trial per user."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trial_entitlements (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            tariff_id INTEGER NOT NULL REFERENCES tariffs(id),
            status TEXT NOT NULL DEFAULT 'provisioning'
                CHECK(status IN ('provisioning','active','failed')),
            vpn_key_id INTEGER REFERENCES vpn_keys(id) ON DELETE SET NULL,
            attempt_count INTEGER NOT NULL DEFAULT 1,
            last_error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            activated_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_trial_entitlements_status
            ON trial_entitlements(status, updated_at);
    """)
    logger.info("Migration v54 applied")


def migration_55(conn: sqlite3.Connection) -> None:
    """Product families and independent renewable LTE allowances.

    Existing tariff rows and references are retained. Legacy commercial rows
    are hidden from new sales, never rewritten or deleted.
    """
    _add_column(conn, "tariffs", "product_code TEXT")
    _add_column(conn, "tariffs", "period_months INTEGER")
    _add_column(conn, "tariffs", "device_limit INTEGER")
    _add_column(conn, "tariffs", "lte_quota_gb INTEGER")
    _add_column(conn, "tariffs", "lte_cycle_days INTEGER NOT NULL DEFAULT 30")
    _add_column(conn, "users", "lte_cycle_started_at DATETIME")
    _add_column(conn, "users", "lte_cycle_reset_at DATETIME")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_tariffs_product_period
        ON tariffs(product_code, period_months)
        WHERE product_code IS NOT NULL AND period_months IS NOT NULL""")

    regular = conn.execute("""SELECT group_id FROM tariffs
        WHERE name != 'Admin Tariff' AND COALESCE(group_id, 0) > 0
        ORDER BY is_active DESC, display_order, id LIMIT 1""").fetchone()
    group_id = int(regular["group_id"] or 1) if regular else 1
    products = (
        ("economy", "Эконом", 500, 0, 2, (93, 259, 499, 931)),
        ("standard", "Стандарт", 1024, 45, 3, (145, 399, 759, 1469)),
        ("family", "Семейный", 0, 115, 10, (345, 939, 1789, 3389)),
    )
    periods = ((1, 30), (3, 90), (6, 180), (12, 365))
    for product_order, (code, title, traffic_gb, lte_gb, devices, prices) in enumerate(products, 1):
        for period_order, ((months, days), price_rub) in enumerate(zip(periods, prices), 1):
            existing = conn.execute(
                "SELECT id FROM tariffs WHERE product_code=? AND period_months=?",
                (code, months),
            ).fetchone()
            values = (
                f"{title} · {months} мес.", days, price_rub,
                product_order * 100 + period_order * 10, traffic_gb, group_id,
                code, months, devices, lte_gb,
            )
            if existing:
                conn.execute("""UPDATE tariffs SET
                    name=?, duration_days=?, price_rub=?, display_order=?,
                    traffic_limit_gb=?, group_id=?, product_code=?, period_months=?,
                    device_limit=?, lte_quota_gb=?, lte_cycle_days=30, is_active=1
                    WHERE id=?""", values + (existing["id"],))
            else:
                conn.execute("""INSERT INTO tariffs (
                    name, duration_days, price_cents, price_stars, price_rub,
                    external_id, display_order, is_active, traffic_limit_gb,
                    group_id, product_code, period_months, device_limit,
                    lte_quota_gb, lte_cycle_days
                ) VALUES (?, ?, 0, 0, ?, NULL, ?, 1, ?, ?, ?, ?, ?, ?, 30)""", values)

    conn.execute("""UPDATE tariffs SET is_active = 0
        WHERE name != 'Admin Tariff' AND product_code IS NULL""")
    conn.execute("""UPDATE users SET
        lte_cycle_started_at=COALESCE(lte_cycle_started_at, CURRENT_TIMESTAMP),
        lte_cycle_reset_at=COALESCE(lte_cycle_reset_at, datetime('now', '+30 days'))
        WHERE COALESCE(lte_quota_gb, 0) > 0""")
    logger.info("Migration v55 applied")


def migration_56(conn: sqlite3.Connection) -> None:
    """First-touch advertising attribution and disable-safe promo management."""
    _add_column(conn, "promocodes", "is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
            entry_bonus_days INTEGER NOT NULL DEFAULT 0 CHECK(entry_bonus_days BETWEEN 0 AND 365),
            payment_bonus_days INTEGER NOT NULL DEFAULT 0 CHECK(payment_bonus_days BETWEEN 0 AND 365),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_campaign_attribution (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            campaign_id INTEGER NOT NULL REFERENCES ad_campaigns(id) ON DELETE RESTRICT,
            attributed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_campaign_attribution_campaign
            ON user_campaign_attribution(campaign_id, attributed_at);
        CREATE INDEX IF NOT EXISTS idx_campaign_attribution_date
            ON user_campaign_attribution(attributed_at);
        CREATE TABLE IF NOT EXISTS campaign_bonus_grants (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            campaign_id INTEGER NOT NULL REFERENCES ad_campaigns(id) ON DELETE RESTRICT,
            kind TEXT NOT NULL CHECK(kind IN ('entry','payment')),
            days INTEGER NOT NULL CHECK(days BETWEEN 1 AND 365),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','applied','failed')),
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            applied_at DATETIME,
            PRIMARY KEY(user_id,kind)
        );
        CREATE INDEX IF NOT EXISTS idx_campaign_bonus_status
            ON campaign_bonus_grants(status,updated_at);
    """)
    logger.info("Migration v56 applied")


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
    18: migration_18,
    19: migration_19,
    20: migration_20,
    21: migration_21,
    22: migration_22,
    23: migration_23,
    24: migration_24,
    25: migration_25,
    26: migration_26,
    27: migration_27,
    28: migration_28,
    29: migration_29,
    30: migration_30,
    31: migration_31,
    32: migration_32,
    33: migration_33,
    34: migration_34,
    35: migration_35,
    36: migration_36,
    37: migration_37,
    38: migration_38,
    39: migration_39,
    40: migration_40,
    41: migration_41,
    42: migration_42,
    43: migration_43,
    44: migration_44,
    45: migration_45,
    46: migration_46,
    47: migration_47,
    48: migration_48,
    49: migration_49,
    50: migration_50,
    51: migration_51,
    52: migration_52,
    53: migration_53,
    54: migration_54,
    55: migration_55,
    56: migration_56,
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
