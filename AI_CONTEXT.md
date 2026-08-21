# AI_CONTEXT.md — рабочая память проекта ArcVPN

> **Инцидент 2026-07-31:** на немецком master-узле повторно повредилась SQLite
> база 3x-ui (`database disk image is malformed`, затем `disk I/O error`). Это
> проблема хранилища состояния панели, а не блокировка VPN-протокола. База
> восстановлена из проверенного снимка; `xui_health_guard.py` должен при таком
> повреждении сохранять forensic-копию, атомарно возвращать `last-known-good.db`
> и заново синхронизировать клиентов из основной БД ArcVPN. Нельзя заменять
> живую x-ui.db обычным `cp` при работающей панели.
>
> План бизнес-админки: `docs/ADMIN_PANEL_PLAN.md`. Чек-лист действий владельца
> для полной готовности: `docs/SERVICE_READINESS_GUIDE.md`.
>
> **Business Console, этап 1:** `/admin`, UI в
> `webapp/src/views/AdminConsole.svelte`, read-only API
> `GET /api/admin/overview`. API принимает только подписанный Telegram initData
> пользователя из `config.ADMIN_IDS`; анонимный запрос обязан возвращать 403.
> На проде проверено: авторизованный запрос 200, x-ui `quick_check=ok`, 8 inbound.
> Пункты YooKassa 1.1–1.3 и Telegram-раздел чек-листа владелец выполнил.

> **Для AI-модели:** Это локальная, некоммитимая рабочая память проекта. Не записывай сюда токены, пароли, приватные ключи, полные URL с секретными путями и персональные данные без прямого указания владельца.
> Общайся с владельцем **только по-русски** (он — Камиль). Прод живой, пользователи реальные, деньги — реальные.

## Как экономить контекст

1. Для обычной задачи сначала прочитай разделы **1**, **3** и раздел, соответствующий задаче ниже. Не загружай весь файл автоматически.
2. Перед изменением конкретного кода найди символ через `rg`, затем прочитай только нужный файл и его непосредственные вызовы.
3. Полностью читать этот файл нужно только для архитектурного изменения, прод-инцидента с неясной причиной или передачи проекта новому агенту.
4. После существенной работы обновляй этот файл только устойчивыми фактами: архитектура, контракты, риски, проверенные команды, решения и актуальные TODO. Временный прогресс и незавершённые гипотезы записывай в `WORKING_NOTES.md`.

| Тип задачи | Читать сначала |
|---|---|
| Бот, ключи, триал, рефералы | 1, 3, 4, 9, 10, 12, 13 |
| Платежи, промокоды, тарифы | 1, 3, 4, 9, 13 |
| Подписки, x-ui, инбаунды, ноды | 1, 2, 5–8, 13 |
| Mini App | 1, 3, 11 |
| Деплой, миграции, инцидент | 1, 2, 4, 13, 14 |

**Быстрый поиск:** `rg -n '^## |нужный_символ' AI_CONTEXT.md bot database subscription_api.py`.

---

## 1. БЫСТРЫЙ СТАРТ — что нужно знать в первую очередь

| Важность | Факт |
|----------|------|
| 🔴 КРИТИЧНО | `config.py` и `database/vpn_bot.db` в `.gitignore` — `git pull` их НЕ обновляет |
| 🔴 КРИТИЧНО | Любые новые константы читать через `getattr(config, "NAME", default)` |
| 🔴 КРИТИЧНО | После изменения схемы БД — сначала рестартить бота (он делает миграции), потом subscription |
| 🟡 ВАЖНО | Никогда не пересоздавать инбаунды — меняются Reality-ключи, ломаются все подписки |
| 🟡 ВАЖНО | Не тестировать VPN через ipify/ifconfig.me — они в блок-листе x-ui (ложный фейл) |
| 🟡 ВАЖНО | SSH на Финляндию с Windows банится — только через веб-панель или с Германии |
| 🟢 НОРМ | Все тексты UI/комментарии в коде — по-русски, в тон существующим |

### Стандартный деплой
```bash
cd /root/ArcVPN && git pull
systemctl restart arcvpn-bot arcvpn-subscription
```

### Диагностика сервисов
```bash
systemctl is-active arcvpn-bot.service arcvpn-subscription.service
journalctl -u arcvpn-subscription -n 60 --no-pager
journalctl -u arcvpn-bot -n 60 --no-pager
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/health
```

---

## 2. ИНФРАСТРУКТУРА

### Серверы

| ID | Роль | IP | OS | Панель |
|----|------|-----|-----|--------|
| 10 | Мастер (Германия) | `2.26.84.210` | Linux | 3x-ui v3.3.1 |
| 11 | Нода (Финляндия) | `195.226.92.37` | Linux | 3x-ui v3.3.1 (нода) |

### SSH-доступы

| Сервер | Команда / адрес | Доступ |
|--------|-----------------|--------|
| Германия | `ssh root@2.26.84.210` | Только локальное защищённое хранилище / `.env` |
| Финляндия | `195.226.92.37`, SSH-порт `22` | Только локальное защищённое хранилище / `.env` |

### Доступы к панелям 3x-ui

| Сервер | URL | Учётные данные |
|--------|-----|----------------|
| Германия (мастер) | `https://2.26.84.210:2082/` | Хранятся только в локальном защищённом хранилище / `.env` |
| Финляндия (нода) | `http://195.226.92.37:2082/` | Хранятся только в локальном защищённом хранилище / `.env` |

SSH Финляндия: порт `22`; доступы не хранить в репозитории. Проверено прямое подключение с Windows 2026-07-24.

### Сервисы на Германии

```
arcvpn-bot.service
  → python3 main.py
  → Бот aiogram, запускает миграции БД при старте

arcvpn-subscription.service
  → python3 subscription_api.py
  → Flask API на 127.0.0.1:8080
  → nginx проксирует :2053 → :8080 и :8443 → :8080

x-ui.service
  → Панель 3x-ui, HTTPS на :2082
  → Генерирует /usr/local/x-ui/bin/config.json из x-ui.db при старте
```

### Базы данных

| Файл | Где | Назначение |
|------|-----|-----------|
| `database/vpn_bot.db` | `/root/ArcVPN/database/vpn_bot.db` | Бот (gitignored!) |
| `x-ui.db` | `/etc/x-ui/x-ui.db` | Панель x-ui |

### Домены и сети

| Домен | Куда | Назначение |
|-------|------|-----------|
| `sub.arccnet.space:2053` | `2.26.84.210` | Подписки (новый, основной) |
| `arcc.mooo.com:2053` | `2.26.84.210` | Подписки (старый, НЕ отключать) |
| `cdn.arccnet.space:443` | Яндекс CDN → `2.26.84.210:80` | Белые списки (CDN) |
| `arccnet.space` | DNS: Reg.ru (ns1/ns2.reg.ru) | Основной домен |

---

## 3. КАРТА ПРОЕКТА

### Полная структура файлов

```
/root/ArcVPN/
│
├── main.py                         # Точка входа бота: регистрирует роутеры,
│                                   # middleware, запускает планировщики, polling
│
├── config.py                       # GITIGNORED! Шаблон есть в репо для примера
│                                   # На сервере правится вручную
│
├── subscription_api.py             # Flask API (63 KB!) — подписки, Mini App,
│                                   # Happ routing, CDN-инбаунд, health
│
├── subscription_pages.py           # HTML шаблоны страниц (инструкции для
│                                   # iOS/Android/Windows — data-driven)
│
├── bot/
│   ├── handlers/
│   │   ├── admin/
│   │   │   ├── __init__.py         # admin_router — регистрирует все admin-хендлеры
│   │   │   ├── broadcast.py        # Рассылка пользователям
│   │   │   ├── groups.py           # Управление группами
│   │   │   ├── main.py             # Главное меню админки
│   │   │   ├── message_editor.py   # Редактор текстов бота
│   │   │   ├── payments.py         # Просмотр платежей
│   │   │   ├── promocodes.py       # Управление промокодами (fixed/percent)
│   │   │   ├── referral.py         # Настройки реферальной программы
│   │   │   ├── servers.py          # Управление VPN-серверами
│   │   │   ├── statistics.py       # Сводка-дашборд статистики
│   │   │   ├── system.py           # Системные настройки, автообновление
│   │   │   ├── tariffs.py          # Управление тарифами
│   │   │   ├── trial.py            # Настройки триала
│   │   │   ├── users_keys.py       # Управление ключами пользователей
│   │   │   ├── users_keys_deleted.py # Удалённые ключи
│   │   │   ├── users_list.py       # Список пользователей
│   │   │   └── users_manage.py     # Блокировка, бан, управление юзерами
│   │   │
│   │   └── user/
│   │       ├── __init__.py         # user_router — строгий порядок включения
│   │       ├── start.py            # /start, главное меню, авто-триал, deeplink buy_<id>
│   │       ├── keys.py             # Управление ключами (продление, просмотр, смена)
│   │       ├── trial.py            # provision_trial_for_user() — ядро триала
│   │       ├── tariffs.py          # Выбор тарифа (покупка)
│   │       ├── referral.py         # Реферальная программа UI
│   │       ├── promocode.py        # Ввод и применение промокода
│   │       ├── topup.py            # Пополнение баланса (dead, НЕ удалять)
│   │       └── payments/
│   │           ├── __init__.py     # Экспорт payment роутеров
│   │           ├── base.py         # show_payment_method_selection_screen(),
│   │           │                   # renew_invoice_cancel_handler
│   │           ├── yookassa.py     # ЮКасса QR/redirect (СБП+карты),
│   │           │                   # _yookassa_post с retry (4 попытки)
│   │           ├── stars.py        # Telegram Stars оплата
│   │           ├── crypto.py       # Крипта оплата
│   │           ├── balance.py      # Баланс оплата (dead UI, НЕ удалять)
│   │           ├── demo.py         # Demo-оплата (тест без реальных денег)
│   │           └── keys_config.py  # Выбор конфига ключа
│   │
│   ├── keyboards/
│   │   ├── __init__.py             # Все клавиатуры (user + admin)
│   │   ├── user.py                 # Пользовательские клавиатуры (48 KB!)
│   │   ├── admin.py                # Базовые admin-клавиатуры
│   │   ├── admin_broadcast.py      # Клавиатуры рассылки
│   │   ├── admin_groups.py         # Клавиатуры групп
│   │   ├── admin_misc.py           # Разные admin-клавиатуры
│   │   ├── admin_payments.py       # Клавиатуры платежей
│   │   ├── admin_servers.py        # Клавиатуры серверов
│   │   ├── admin_settings.py       # Клавиатуры настроек
│   │   ├── admin_tariffs.py        # Клавиатуры тарифов
│   │   └── admin_users.py          # Клавиатуры пользователей
│   │
│   ├── middlewares/
│   │   ├── subscription_check.py   # Проверка подписки на канал
│   │   ├── debug_logging.py        # Логирование callback_query (первым!)
│   │   └── parse_mode_fallback.py  # SafeParseSession — fallback при MarkdownV2 ошибках
│   │
│   ├── services/
│   │   ├── billing.py              # apply_paid_order(), infer_order_operation_type(),
│   │   │                           # _apply_new_order(), _apply_renew_order() (48 KB!)
│   │   ├── vpn_api.py              # Высокоуровневые VPN-операции:
│   │   │                           # get_client(), push_key_to_panel(), disable_key_on_panel()
│   │   ├── scheduler.py            # Планировщики: run_daily_tasks(),
│   │   │                           # run_traffic_sync_scheduler() (каждые 5 мин),
│   │   │                           # run_update_check_scheduler() (49 KB!)
│   │   ├── notifications.py        # send_to_user(), notify_admins(), render_template()
│   │   ├── reserve.py              # ensure_reserve_client(), get_reserve_client_info()
│   │   ├── exchange_rate.py        # Курс ЦБ (cbr-xml-daily.ru)
│   │   ├── user_locks.py           # Блокировки per-user (asyncio.Lock)
│   │   └── panels/
│   │       ├── base.py             # Базовый класс панели
│   │       ├── xui.py              # XUIClient — 3x-ui API v2/v3 адаптер (103 KB!)
│   │       │                       # provision_client_all_inbounds(), фан-аут write-ops
│   │       └── marzban.py          # Marzban клиент (не основной)
│   │
│   ├── utils/
│   │   ├── key_generator.py        # generate_vless_link(), generate_hysteria2_link()
│   │   │                           # extra=URL-enc JSON для XHTTP CDN-инбаунда
│   │   ├── payment_flow_ui.py      # show_payment_method_selection_screen() — единый UI
│   │   │                           # show_tariff_selection_screen()
│   │   ├── key_sender.py           # Отправка ключа пользователю
│   │   ├── telegram_webapp.py      # get_telegram_id() — HMAC-валидация initData
│   │   ├── git_utils.py            # Утилиты автообновления через git (18 KB)
│   │   ├── datetime_utils.py       # format_date() — МСК timezone
│   │   ├── message_editor.py       # Редактирование сообщений
│   │   ├── subscription.py         # Вспомогательные функции подписки
│   │   ├── text.py                 # Текстовые утилиты
│   │   └── groups.py               # Утилиты для групп
│   │
│   ├── states/                     # FSM States (aiogram)
│   ├── errors.py                   # Кастомные ошибки
│   └── messages.py                 # Общие тексты
│
├── database/
│   ├── connection.py               # get_db() — SQLite connection (row_factory)
│   ├── migrations.py               # run_migrations(), LATEST_VERSION=29
│   ├── db_keys.py                  # Операции с vpn_keys (30 KB)
│   ├── db_payments.py              # prepare_payment_order(), apply_paid_order() (38 KB)
│   ├── db_tariffs.py               # _recompute_prices() — динамич. Stars/крипта (16 KB)
│   ├── db_users.py                 # Операции с users (22 KB)
│   ├── db_statistics.py            # get_usage_activity_stats(), get_revenue_stats() (25 KB)
│   ├── db_payments.py              # Платежи, ордера (38 KB)
│   ├── db_servers.py               # Серверы (8 KB)
│   ├── db_settings.py              # Настройки бота из settings таблицы (8 KB)
│   ├── db_groups.py                # Группы (11 KB)
│   ├── db_stats.py                 # Ежедневная статистика (10 KB)
│   ├── db_promocodes.py            # Промокоды (8 KB)
│   ├── requests.py                 # Импорт всех db_* модулей
│   └── vpn_bot.db                  # SQLite БД (GITIGNORED!)
│
├── webapp/                         # Svelte Mini App (исходники, НЕ на сервере)
│   └── src/
│       ├── App.svelte              # Главный компонент, роутинг вкладок, темы
│       ├── app.css                 # Дизайн-токены, глобальные стили
│       ├── main.js                 # Точка входа Vite
│       ├── views/
│       │   ├── Home.svelte         # Главная: hero-карточка, статус, тарифы
│       │   ├── Connect.svelte      # Подключение: Happ guide iOS/Android/Windows
│       │   ├── Referral.svelte     # Рефералы: N дней получено
│       │   └── Profile.svelte      # Профиль: TG ID, трафик, устройства, тема
│       ├── components/
│       │   ├── Logo.svelte         # Инлайн SVG лого (arcLOGOsvg.svg, currentColor)
│       │   ├── DeviceIcon.svelte   # Бренд SVG: Apple/Android/Windows
│       │   ├── TabBar.svelte       # Плавающая навигация (стекло)
│       │   ├── Button.svelte       # Кнопки
│       │   ├── Toast.svelte        # Тосты
│       │   ├── Gauge.svelte        # Индикатор трафика
│       │   ├── Icon.svelte         # Иконки
│       │   ├── Row.svelte          # Строка-элемент
│       │   ├── RouteArc.svelte     # Дуга маршрута (декоративная)
│       │   └── Segmented.svelte    # Сегментированный контрол
│       └── lib/
│           ├── api.js              # fetch к /api/*, DEV-моки под import.meta.env.DEV
│           └── theme.js            # Управление темой (localStorage, ?theme=light|dark)
│
├── webapp_dist/                    # Собранный фронтенд (КОММИТИТСЯ в git!)
│                                   # На сервере Node.js не нужен
│
├── database/vpn_bot.db             # SQLite БД бота (GITIGNORED!)
│
├── logs/                           # Логи бота (RotatingFileHandler, 3 × 1MB)
│
├── # --- Утилиты-скрипты ---
├── backfill_all_inbounds.py        # Добавить клиентов в новые инбаунды (dry-run по умолч.)
├── cleanup_expired_trials.py       # Удалить истёкшие неоплаченные триалы (--apply)
├── rebuild_inbound_from_botdb.py   # Восстановить инбаунд из БД бота
├── migrate_keys_to_new_server.py   # Миграция ключей на другой сервер
├── check_trial_status.py           # Проверка статуса триалов
├── clear_test_data.py              # Очистка тестовых данных
├── reset_statistics.py             # Сброс статистики
├── reset_trial_for_user.py         # Сброс триала для конкретного юзера
├── __diag.py                       # Диагностика
│
├── # --- Системные файлы ---
├── arcvpn-bot.service              # systemd unit для бота
├── arcvpn-subscription.service     # systemd unit для Flask API
├── arcvpn.service                  # (назначение уточнить)
│
├── # --- AI/Документация ---
├── AI_CONTEXT.md                   # ← ЭТОТ ФАЙЛ
├── WORKING_NOTES.md                # gitignored заметки между чатами
├── V3_MIGRATION_PLAN.md            # Переезд на 3x-ui v3 (ВЫПОЛНЕНО)
├── ARCHITECTURE_NEXT_CHAT_BRIEF.md # История архитектурных изменений
├── MIGRATION_AND_SCALING.md        # Миграция и масштабирование
├── AGENTS.md                       # Правила для AI-агентов
└── opencode.json                   # Конфиг opencode (Moon AI: Fable5/Opus4.8)
```

---

## 4. СХЕМА БАЗЫ ДАННЫХ

### Таблицы (LATEST_VERSION = 29)

```sql
-- Основные таблицы (v1)
users           telegram_id, username, is_banned, created_at,
                used_trial(v3), referral_code(v11), referred_by(v11),
                personal_balance(v11), referral_coefficient(v11),
                is_active(v?), last_seen_at(v?)

tariffs         name, duration_days, price_rub(v4), price_cents, price_stars,
                external_id, display_order, is_active
                -- price_stars/price_cents НЕ читаются напрямую!
                -- Пересчитываются в db_tariffs._recompute_prices()

servers         name, host, port, protocol(v5), web_base_path, login, password,
                is_active, is_reserve(v22)

vpn_keys        user_id, server_id, tariff_id(NULL=триал), panel_inbound_id,
                client_uuid, panel_email, custom_name, expires_at, created_at,
                sub_id(v?), connect_notified(v23), online_devices(v23),
                last_online_at(v25)

payments        vpn_key_id, user_id, tariff_id, order_id UNIQUE, payment_type,
                amount_cents, amount_stars, period_days, status, paid_at,
                yookassa_payment_id(v6), promocode_id(v?), discount_rub(v?),
                operation_type(v21), target_tariff_id(v21),
                fulfillment_status(v21), fulfilled_at(v21), fulfillment_error(v21),
                attempt_count(v21)

-- Реферальная система (v11)
referral_stats  user_id, referrer_id, total_referrals, total_reward_days,
                bonus_trial_granted(v24), bonus_purchase_granted(v24)

referral_levels level, percent

-- Биллинг
exchange_rates  currency, rate_kopecks, updated_at  (курс ЦБ)
promocodes      code, discount_type, discount_rub, discount_percent,
                max_uses, used_count, is_active

-- Системные
settings        key, value  (глобальные настройки бота через settings-таблицу)
schema_version  version
notification_log vpn_key_id, sent_at
```

### Ключевые паттерны работы с БД

```python
# Триал = tariff_id IS NULL
# НЕ использовать tariffs.is_trial — этой колонки нет в проде

# Основной ключ пользователя
get_user_primary_key(user_id)  # в db_keys.py

# Динамический пересчёт цен (ОБЯЗАТЕЛЕН при чтении тарифов)
db_tariffs.get_all_tariffs()           # вызывает _recompute_prices() внутри
db_tariffs.get_tariff_by_id(id)        # тоже
db_tariffs.get_tariff_by_external_id() # тоже

# Платёжный lifecycle
prepare_payment_order(...)   # создать/обновить pending-ордер
apply_paid_order(order_id)   # применить оплату, выдать доступ
```

---

## 5. СОСТОЯНИЕ VPN-ИНБАУНДОВ (2026-07-22)

| # | Порт | Протокол | Название в Happ | SNI | fp | Статус |
|---|------|----------|-----------------|-----|----|--------|
| 1 | :12631 | VLESS XHTTP Reality | Финляндия / Германия (Основной) | `avito.ru` | firefox | ✅ mode=auto |
| 2 | :2087 | VLESS TCP Reality | Германия (Запасной) | `ozon.ru` | chrome | ✅ (был :443) |
| 3 | :10001 | VLESS XHTTP none | Белые списки (LTE/CDN) | — | — | ✅ через CDN |

### Reality-ключи (НЕ МЕНЯТЬ без необходимости)

| Инбаунд | pubkey |
|---------|--------|
| :12631 XHTTP | `7ze0wY82bNHFG4FIt0oI0PDX-RNvpleuUoh8K1BP3jk` |
| :2087 TCP | `EeLv4vGqklDzYrCXQq1k3gr-3elWZawjRTnTTcl_OlE` |

### Имена и порядок в подписке
- Имя каждой ссылки берётся из `remark` соответствующего inbound в 3x-ui.
- Порядок ссылок повторяет порядок, который возвращает панель 3x-ui; для изменения порядка и названий редактировать inbound в панели.
- VLESS-first сохраняется только для одиночного QR/ключа, а не для списка подписки.
- Имя профиля: `ArcVPN ✨`. Информационный текст: «❗ Не работает VPN? Жми кнопку - 🔁 обновить подписку.», затем «🔥РФ сервисы РАБОТАЮТ с VPN», ⚡ скорость, ⭐ надёжность, LTE — обход глушилок (белые списки). Флаг 🇷🇺 не использовать: он некорректно отображается в клиентах.
- Для кастомного `subscription_api.py` (не встроенного subscription-сервера 3x-ui) текст выдаётся заголовком `announce: base64:<UTF-8>` и дублируется строкой `#announce:` для совместимости. Имя профиля выдаётся через `profile-title`.

### api-inbound (ОБЯЗАТЕЛЕН для статистики трафика)
```json
{"tag":"api","listen":"127.0.0.1","port":62789,"protocol":"dokodemo-door","settings":{"address":"127.0.0.1"}}
```
Должен быть в `xrayTemplateConfig` (settings x-ui.db). Без него gRPC StatsService падает, трафик замирает.
Диагностика: `xray api statsquery` — если "failed to dial" → нет api-inbound → `systemctl restart x-ui`

### Padding на инбаундах XHTTP
| Поле | :12631 | :10001 (CDN) |
|------|--------|--------------|
| xPaddingKey | `_t` | `dc` |
| xPaddingHeader | `X-CSRFToken` | `X-Cache` |
| mode | `tokenish` / `queryInHeader` | `tokenish` / `queryInHeader` |

---

## 6. API 3x-UI: V2 vs V3

3x-ui v3 перенёс клиент-API. Старые `/panel/api/inbounds/*Client` → **404**.

| Операция | v2 (form-data) | v3 (JSON) |
|----------|---------------|-----------|
| создать | `POST inbounds/addClient` | `POST clients/add` |
| обновить | `POST inbounds/updateClient/{id}` | `POST clients/update/{email}` |
| удалить | `POST inbounds/{ib}/delClient/{id}` | `POST clients/del/{email}` |
| сброс трафика | `POST inbounds/{ib}/resetClientTraffic/{email}` | `POST clients/resetTraffic/{email}` |
| онлайны | `POST inbounds/onlines` | `POST clients/onlines` |
| IP клиента | `POST inbounds/clientIps/{email}` | `POST clients/ips/{email}` |
| читать | (из inbounds/list) | `GET clients/get/{email}` |
| читать всё | `GET inbounds/list` | без изменений |
| детект v3 | — | `GET inbounds/list/slim` (v2 → 404) |

**Реализация:** `bot/services/panels/xui.py` — автодетект `_ensure_api_version()` + ветки v2/v3.
Override: `XUI_FORCE_API_VERSION = "v3"` в config.py.

**Модель клиента v3:** единая запись, `inboundIds:[..]`, `uuid` (VLESS) + `password` (Hysteria2), `tgId` = int.

---

## 7. ФИНЛЯНДИЯ — АРХИТЕКТУРА МАСТЕР+НОДА

**Схема:** встроенная Мастер+Нода 3x-ui 3.3.1. Бот работает ТОЛЬКО с Германией.

- Мастер (Германия) синхронизирует клиентов и инбаунды на ноду автоматически
- В `database/vpn_bot.db` сервер `id=11`, `is_active=0` — бот не ходит туда напрямую
- Инбаунд Финляндии = `id=7` на мастере, `node_id=1`, `share_addr_strategy=node`, порт 12631

**Фикс host (сделан в xui.py):**
- `_fetch_node_addresses()` — GET /panel/api/nodes/list, кэш `{node_id: address}`
- `_build_client_config` берёт host из node_addrs по nodeId/node_id, а не всегда мастера

**Сортировка:** `_link_sort_key` по URL-флагу 🇫🇮 → Финляндия первой

**Ноды-инбаунды НЕЛЬЗЯ менять через remark в x-ui.db** — рестарт откатит

**TODO:**
- [ ] Поддомен `fi.arccnet.space` → Let's Encrypt → HTTPS для ноды
- [ ] 2-й инбаунд Финляндии VLESS/TCP/Reality (проверить, работает ли TCP из FI)

---

## 8. CDN YANDEX — ОБХОД БЕЛЫХ СПИСКОВ

Яндекс CDN режет POST (405), но пропускает OPTIONS.

**Решение (работает, подтверждено E2E):**
```
Клиент: uplinkHTTPMethod=OPTIONS, alpn=["h2","http/1.1"], padding (dc/X-Cache)
  ↓
Яндекс CDN edge (cdn.arccnet.space:443)
  ↓
nginx origin (:80): map $request_method $m { default $request_method; OPTIONS POST; }
                    proxy_method $m; proxy_buffering off; proxy_request_buffering off;
  ↓
xray :10001 (VLESS XHTTP none, mode=packet-up)
```

CDN resource-id: `bc8rbymkgjkroz3gf3ru`
**Нестабильность:** ~70% (session-affinity — разные edge-ноды Яндекса). Рассматривать как best-effort.

Код: `extra` (URL-encoded JSON) в `key_generator.py` → CDN-override в `subscription_api.py ~строки 961-1005`

---

## 9. ПЛАТЁЖНАЯ СИСТЕМА

### Провайдеры

| Провайдер | Метод | Статус |
|-----------|-------|--------|
| ЮKassa (shop 1325666) | СБП + карты (redirect-форма) | ✅ Активен |
| Telegram Stars | Stars | ✅ Активен |
| Крипта (внешний сервис) | Крипта | ✅ Активен |
| Баланс | Баланс | 🔴 Dead code, UI убран, НЕ удалять |
| Demo | Тест без денег | ✅ Только для тестов |

### Тарифы (актуально 2026-07)

| Период | Цена RUB | Stars (динамически) |
|--------|----------|---------------------|
| 1 мес | 100₽ | ceil(100/usd_rub/0.015) |
| 3 мес | 270₽ | ceil(270/usd_rub/0.015) |
| 6 мес | 480₽ | ceil(480/usd_rub/0.015) |
| 12 мес | 840₽ | ceil(840/usd_rub/0.015) |

**Триал:** 7 дней / 100 ГБ (settings: `trial_days`, `trial_traffic_gb`)

### Lifecycle платёжного ордера

```
1. prepare_payment_order(user_id, tariff_id, ...)  → order_id (pending)
2. [Пользователь оплачивает через провайдера]
3. apply_paid_order(order_id)                       → fulfillment
   → infer_order_operation_type()                  → 'new' | 'renew' | 'topup'
   → _apply_new_order() или _apply_renew_order()
   → fulfillment_status = 'applied'
```

**Важно:** `paid` ≠ `выдан доступ`. Есть отдельный `fulfillment_status`.
**ЮKassa retry:** `_yookassa_post`/`_yookassa_get` — timeout(connect=7, total=25) + 4 ретрая с одним Idempotence-Key.

### Промокоды
- `discount_type`: `fixed` (рубли) или `percent` (проценты)
- `compute_discount_rub(promo, price_rub)` — в db_promocodes.py

---

## 10. РЕФЕРАЛЬНАЯ ПРОГРАММА

**Модель «3+5 дней» (переделано 2026-06-27):**

| Событие | Кому | Сколько | Функция |
|---------|------|---------|---------|
| Друг запустил бота | Рефереру | +3 дня | `process_referral_trial_reward` |
| Друг купил тариф | Рефереру | +5 дней | `process_referral_reward` |
| Друг купил тариф | Самому другу | +5 дней | `process_referral_reward` |

- Идемпотентность: флаги `bonus_trial_granted`/`bonus_purchase_granted` в `referral_stats`
- `grant_bonus_days(user, days)` → продлевает ключ через `extend_vpn_key` → `push_key_to_panel`
- Авто-триал при /start: `provision_trial_for_user(user)` в `bot/handlers/user/trial.py`
- Триал = `tariff_id IS NULL`

---

## 11. TELEGRAM MINI APP

**Стек:** Svelte 4 + Vite 5. Только мобильные.

| Что | Где |
|-----|-----|
| Исходники | `webapp/` (локально, не деплоится) |
| Сборка | `npm run build` в `webapp/` → `webapp_dist/` |
| Деплой | Коммит `webapp_dist/` в git → `git pull` на сервере |
| На сервере | Node.js не нужен, Flask раздаёт статику |

**Flask эндпоинты:**
- `/app`, `/app/<path>` — SPA (index.html fallback)
- `/api/status` — статус подписки, трафик, устройства
- `/api/tariffs` — тарифы с ценами
- `/api/referral` — earned_days, bonus_days
- Auth: header `X-Telegram-Init-Data` → HMAC-валидация через `telegram_webapp.get_telegram_id()`

**Deeplink из Mini App:** `?start=buy_<tariff_id>` → обрабатывается в `start.py::cmd_start`
→ `show_payment_method_selection_screen` или `show_tariff_selection_screen`

**Дизайн-токены (webapp/src/app.css):**
```css
--bg: #07090f               /* холодный почти-чёрный */
--brand: #7c82f5            /* голубой (НЕ фиолетовый!) */
--radius-lg: 28px
--radius: 20px
```
Шрифты: **Manrope** (display/body) + **JetBrains Mono** (числа/ID/цены)
Блоки — плотные панели (НЕ стекло). Стекло только на `.ghost`-кнопках и `TabBar`

---

## 12. ТРЕКИНГ ОНЛАЙНА И СТАТИСТИКА

- `vpn_keys.last_online_at` — timestamp (миграция v25, UTC)
- Планировщик `sync_traffic_stats` каждые 5 мин: `get_online_emails()` → `mark_keys_online()`
- `online_now` = за последние 10 мин (2 цикла)

**Статфункции в db_statistics.py:**
- `get_usage_activity_stats()` → online_now, d3, week, month (DISTINCT user_id)
- `get_recently_online_users(minutes=10)` → конкретные юзеры онлайн
- `get_revenue_stats()` — yookassa + yookassa_qr + cards (payment_type != 'trial')

---

## 13. ИЗВЕСТНЫЕ ГРАБЛИ И РЕШЕНИЯ

### 502 Bad Gateway при деплое
```
Причина:  новая константа from config import NAME, старый config.py → ImportError
Решение:  getattr(config, "NAME", default) ВЕЗДЕ
Пример:   getattr(config, "DEFAULT_LIMIT_IP", 2)
```

### x-ui "Obtain (disk I/O error)" + подписка 503
```
Причина:  x-ui.db заменили на живой панели → мёртвые WAL-дескрипторы
Диагноз:  ls -l /proc/$(pgrep -x x-ui)/fd/ | grep -iE "x-ui.db|deleted"
Фикс:     systemctl restart x-ui   (файл цел, просто переоткроет дескрипторы)
```

### Статистика трафика заморожена (трафик=0, онлайн не обновляется)
```
Причина:  удалён api-inbound из xrayTemplateConfig (кто-то "оптимизировал")
Диагноз:  xray api statsquery → "failed to dial 127.0.0.1:..."
Фикс:     вернуть api-inbound в шаблон + systemctl restart x-ui
```

### Reality не работает на мобильном РФ (пинг есть, трафик нет)
```
Причина:  fp=chrome палится ТСПУ
Решение:  всегда fp=firefox на новых инбаундах
```

### Порт 443 режется РФ к иностранному IP
```
Решение:  перенести инбаунд на :2087 (проверено рабочим)
```

### Подписка отдаёт старый Reality-ключ
```
Причина:  пересоздание инбаунда меняет ключи → старые импорты не коннектятся
Вывод:    НИКОГДА не пересоздавать инбаунды без крайней нужды
```

### "unexpected status 400" при XHTTP
```
Причина:  padding-параметры клиента не совпадают с сервером
Правило:  клиент должен слать padding точь-в-точь как настроен инбаунд
```

### Статистика ЮKassa зависает (QR не создаётся)
```
Причина:  api.yookassa.ru → 2 A-записи, одна периодически таймаутит
Решение:  реализованы retry с Idempotence-Key в billing.py
          (_yookassa_post: timeout(7,25) + 4 попытки)
```

---

## 14. config.py — СТРУКТУРА (шаблон репо, gitignored на сервере)

```python
BOT_TOKEN = "..."
ADMIN_IDS = [2075630349, 5592399539]
TIMEZONE = 'Europe/Moscow'

ENABLE_SPLIT_TUNNELING = True
SPLIT_TUNNELING_MODE = "speed"       # "speed" | "compatibility"
SPLIT_TUNNELING_DIRECT_SITES = ["geosite:category-ru", "geosite:yandex", ...]
SPLIT_TUNNELING_DIRECT_IP = ["geoip:ru", "geoip:private"]

# ВАЖНО: в репо стоит старый Cloudflare — на сервере заменить на Google!
SPLIT_TUNNELING_REMOTE_DNS_DOMAIN = "https://dns.google/dns-query"  # ← должно быть на сервере
SPLIT_TUNNELING_REMOTE_DNS_IP = "8.8.8.8"                           # ← должно быть на сервере

SUBSCRIPTION_URL = "https://sub.arccnet.space"   # без trailing slash, без порта
XUI_DB_PATH = "/etc/x-ui/x-ui.db"

RESERVE_ACCESS_ENABLED = True         # резервный доступ (только Telegram) для истёкших
RESERVE_CLIENT_EMAIL = "reserve_shared_fallback"
RESERVE_PROXY_SITES = ["geosite:telegram"]
RESERVE_PROXY_IP = ["geoip:telegram", ...]

GITHUB_REPO_URL = "https://github.com/progress1ve/ArcVPN.git"

DEFAULT_LIMIT_IP = 2                  # лимит устройств на подписку
DEFAULT_TOTAL_GB = 1024^4             # 1 TB в байтах (лимит трафика)
TRAFFIC_THRESHOLD_FOR_KEY_CHANGE = 20 # % трафика до которого можно сменить ключ

RATE_LIMITS = {"commands_per_minute": 30, "critical_operations_per_minute": 5}
RETRY_CONFIG = {"max_attempts": 3, "delays": [1, 3, 9]}

# Серверные опции (через getattr в коде):
# XUI_FORCE_API_VERSION = "v3"
# HYSTERIA2_ENABLED, HYSTERIA2_SERVER_IDS, HYSTERIA2_HOST, HYSTERIA2_PORT,
# HYSTERIA2_OBFS_PASSWORD (= пароль obfs в /etc/hysteria/config.yaml)
```

---

## 15. ДРУГИЕ AI-АГЕНТЫ В ПРОЕКТЕ

| Файл | Назначение |
|------|-----------|
| `opencode.json` | opencode.ai конфиг: Moon AI (Fable5/Opus4.8), используется через opencode CLI |
| `AGENTS.md` | Правила для AI-агентов |
| `.agents/` | Конфигурация Antigravity AI агента |
| `C:\Users\babay\.claude\projects\...\memory\` | 21 memory-файл Claude (все собраны в этот AI_CONTEXT.md) |

---

## 16. КАК РАБОТАТЬ С ВЛАДЕЛЬЦЕМ (Камиль)

1. **Язык:** только русский. Комментарии/UI-тексты в коде тоже русские, в тон существующим.
2. **Срочность прод-инцидентов:** немедленно — гипотеза → команда диагностики → точечный фикс.
3. **Команды:** владелец сам выполняет на сервере и присылает вывод → давать готовые copy-paste блоки.
   - Bash: heredoc или прямые команды
   - nano: указывать Ctrl+O → Enter → Ctrl+X
4. **Проактивность:** помимо задачи — находить и чинить логические/UI баги попутно.
5. **Проверка:** после изменений `python3 -m py_compile <файл>`, желательно мини-тест.
6. **WORKING_NOTES.md** — gitignored файл в корне репо, для заметок между чатами. Обновлять при значимых изменениях.

---

## 17. ТЕКУЩИЕ TODO

### Высокий приоритет
- [ ] **fi.arccnet.space** — поддомен + LE cert + HTTPS для ноды Финляндия
- [ ] **Финляндия #2** — 2-й инбаунд VLESS/TCP/Reality для Финляндии

### Средний приоритет
- [ ] RU VPS (Timeweb/Selectel) для инбаунда с whitelisted IP → обход шатдауна
- [ ] Hysteria2: отдельный тестовый inbound и замер на мобильных сетях перед включением в подписку.

### Принятое решение по протоколам (2026-07-24)
- TCP Reality не восстанавливать и не добавлять: на текущей инфраструктуре он не работает стабильно.
- VLESS gRPC Reality не добавлять: лишняя сложность и нет подтверждённой пользы для проекта.
- Следующий экспериментальный протокол — только Hysteria2, после отдельного теста качества и скорости.

### Поведение подписок и трафика
- HTTP-заголовок `profile-update-interval` по умолчанию равен 1 часу; допустим override `PROFILE_UPDATE_INTERVAL_HOURS` в `config.py`.
- Ежемесячный сброс лимитного трафика выполняется 1-го числа; настройка БД `monthly_traffic_reset_enabled = 1` включена на проде 2026-07-24.

### Целевые названия инбаундов
- XHTTP (применено на проде 2026-07-24): `🇫🇮 Финляндия ⭐⚡ [АВТОВЫБОР]` (id=7, нода), `🇩🇪 Германия ⭐ [АВТОВЫБОР]` (id=3). Флаг 🇷🇺 запрещён только в информационном тексте подписки.
- TCP Reality (исследовать блокировку до включения): `Финляндия #1`, `Германия #1`.
- Hysteria2 после теста: `Финляндия #2⚡`, `Германия #2⚡`.
- CDN/LTE: существующий через Германию переименован в `Обход глушилок (LTE) #2` (id=5); для #1 через Финляндию требуется отдельный CDN resource и origin на финский IP.
  `cdn-fi.arccnet.space` создан в Yandex Cloud; сертификат применён и проверен по HTTPS 2026-07-24. На финской ноде nginx на `:80` проксирует XHTTP в `127.0.0.1:10001`, а `/.well-known/acme-challenge/` остаётся доступен для продления сертификата. LTE #1 создан через master (master id=13, physical node id=6), имеет 109 клиентских привязок и `xhttpSettings.host=cdn-fi.arccnet.space`. В подписке LTE #1 обязательно должен быть `cdn-fi.arccnet.space:443`, TLS/SNI `cdn-fi.arccnet.space` и XHTTP OPTIONS; LTE #2 — `cdn.arccnet.space:443`. Оба remark начинаются с `🇷🇺`; флаг РФ не использовать только в info-тексте.
  Встроенная подписка/страница 3x-ui (порт 2096) всегда показывает сырой адрес ноды `195.226.92.37:10001` и `security=none`; это ожидаемо и не пригодно для CDN. Пользователям выдавать только кастомный URL ArcVPN `/sub/<sub_id>`: он подменяет LTE #1/#2 на CDN TLS-ссылки.

### Технический долг
- [ ] `migrations.py:320,1050` — SyntaxWarning `\!` `\.` (raw-строки нужны)
- [ ] Перевод subscription на gunicorn (сейчас Flask dev-server с threaded=True)
- [ ] Автообновление подписки у старых клиентов (переход arcc.mooo.com → sub.arccnet.space)

### Не делать (dead code, намеренно оставлен)
- `bot/handlers/user/topup.py` — баланс вне обращения
- `bot/handlers/user/payments/balance.py` — балансовые платежи
- `show_balance_button` ветки — форсированы в False

---

## 18. БЭКАПЫ НА СЕРВЕРЕ

```bash
/root/x-ui.db.bak.*                    # бэкапы x-ui.db (корень)
/root/ArcVPN/*.bak.*                   # бэкапы config.py, subscription_api.py
/etc/x-ui/x-ui.db.bak*                # бэкапы x-ui.db (/etc)
/root/xui_backups/                     # бэкапы от хардненинга инбаундов
/root/ArcVPN/database/vpn_bot.db.bak.* # бэкапы БД бота
```

---

*Создан 2026-07-22 из 21 memory-файла Claude + полного анализа исходников проекта.*
*При значимых изменениях — обновлять этот файл И WORKING_NOTES.md.*

## Arc Flow purchase and UI correction (2026-07-29, local only)

- Визуальный фон: центр экрана остаётся почти чёрным; медленные синие Aurora-сгустки движутся только вдоль левого, правого и нижнего краёв и маскируются от центральной рабочей зоны.
- Заголовки основных секций центрированы, служебные надписи `ARC FRIENDS` / `ARC CARE` / `ARC ACCOUNT` удалены.
- В реферальной секции не показывается длинный список приглашённых. Вместо него — CTA «Полная статистика» на `ref.stats_link`, затем `VITE_REFERRAL_STATS_URL`, с fallback на публичную site-link рефералки.
- Быстрые вопросы поддержки: обход блокировок, подключение к серверу, оплата/подписка, низкая скорость. Аватар менеджера использует фирменный `arc-logo.svg`.

- Major WebApp surfaces use a premium hairline border: `1px solid rgba(214, 233, 255, 0.07)`. The arrow pills inside the Home shortcuts remain explicitly borderless.
- Home shortcut illustrations use only a soft, high-blur blue ambient glow. Do not add hard neon halos.
- Settings category headings are white, compact, and medium weight. Russian subscription-day pluralization is handled by `daysWord()` (`41 день`, `42 дня`, `40 дней`).
- A local purchase/renew screen is available from the Home CTA. It has a full-width clipped horizontal tariff carousel, a device stepper with a minimum of 2 and `+25 RUB/month` for each extra device, and a live estimate.
- The `buy_<tariff_id>` Mini App deep link now preserves the selected tariff for renewals and opens that tariff's payment-method screen directly instead of asking the user to choose the tariff again.
- LTE purchase rule: 20 GB is included free, extra traffic changes in 5 GB steps, and costs 2 RUB/GB/month (10 RUB per step per month). `.env.example` documents `VITE_EXTRA_LTE_GB_MONTHLY_RUB=2`. Do not activate addon billing in production until server-side payment fulfillment/accounting is implemented.
- Support chat groups messages by day, shows the date only once in a separator, and shows only local `HH:MM` beside each message. The `Chat with manager` heading is geometrically centered. Incoming manager messages have an Arc Care avatar; quick questions send immediately.
- Migration 29 sets the regular tariff ladder to: 30 days = 125 RUB, 90 days = 300 RUB, 180 days = 540 RUB, 365 days = 960 RUB. It updates matching active tariffs and creates a missing duration without touching `Admin Tariff`.
- SMTP and legal operator fields are safe placeholders in `.env.example`; real secrets and legal requisites must be supplied only before production release.
- Release rule remains unchanged: Arc Flow is local-only and must not be deployed without explicit owner approval after Telegram iOS/Android fullscreen QA.

---

## WebApp, trial, referrals and device cache (2026-07-24)

- Trial is an automatic first-entry action. Do not show a “get trial” CTA: both `/start` and the mandatory-channel confirmation must call `provision_trial_for_user()` idempotently whenever `has_used_trial()` is false. Do not gate this on `is_new`, because middleware/channel checks can create the DB user before the first normal `/start`.
- Referral business rule: only the first paid tariff of an invited friend earns a reward. Add **15 days to the referrer and 15 days to the friend**; no bonus for merely opening the bot. DB settings: `referral_trial_bonus_days=0`, `referral_purchase_bonus_days=15`. `grant_referral_bonus_once(..., 'purchase', ...)` is the idempotency boundary.
- Telegram WebView cannot navigate to `happ://` and throws `net::ERR_UNKNOWN_URLSCHEME`. In `webapp/src/views/Connect.svelte` use the normal HTTPS `import_url` through `Telegram.WebApp.openLink` (`openExternal`), which opens `/import/<sub_id>` outside the WebView; only that landing page launches `happ://add/<subscription URL>`.
- `online_devices` is a cache in `vpn_keys`, updated by `sync_traffic_stats()` via 3x-ui online emails and `clientIps`. The bot sends the one-time “subscription connected” notification in the same job. Scheduler interval is 60 seconds (first run after 5 seconds), not 5 minutes. A count can only distinguish unique public IPs provided by 3x-ui; two devices behind the same NAT cannot be reliably separated without adding per-client connection telemetry.
- Future product direction: remove legacy bot UI flows in favour of WebApp. Planned WebApp work: redesigned interface, payments inside WebApp, and a richer device inventory (platform/model such as Apple iPhone) rather than only a count. This requires explicit device telemetry/registration; do not fake device names from IP addresses.

### Planned WebApp UX v2 (2026-07-25; planning only)

- User-facing bot is to be minimal: greeting, mandatory channel check, then one primary **«Подключиться»** button opening the WebApp. Keep the current bot admin panel/handlers.
- WebApp navigation has exactly four bottom sections: **Главная**, **Друзья**, **Поддержка**, **Настройки**. Dark theme only; remove the light-theme switch. Use the provided VPNUS screens as a layout reference (large bottom nav, 8-point spacing, clear thumb-zone CTA) but retain ArcVPN branding and original implementation/assets.
- Главная: days left/status, renew subscription, connect VPN, online devices, remaining ordinary traffic and LTE/censorship-bypass traffic, referral entry point, support entry point. Define new/trial/active/expired states before implementation.
- Друзья: referral link, invited/paid counts, clear rule: first paid tariff gives +15 days to referrer and +15 days to the friend. No reward for launch alone.
- Поддержка: FAQ first, then an in-WebApp conversation screen. Messages must be persisted and forwarded to the administrator via the bot; admin replies in bot must be delivered back to the same WebApp conversation. Add read/status/error states.
- Настройки: device management (after reliable telemetry exists), login methods (Telegram always linked; optional email linking with ownership verification, not a separate registration), user agreement. Do not offer a fake device list based on IPs.
- Implement in separate releases: (1) navigation/home, (2) referral/support FAQ/settings shell, (3) support chat backend, (4) secure email linking, (5) reliable device model/telemetry, (6) remove legacy user bot UI after mobile QA.
- Detailed tracked checklist: `WEBAPP_V2_PLAN.md`. Update its checkboxes and journal after each completed unit of work.
- Launch rule: Menu Button uses the HTTPS WebApp URL; the app calls `ready()`, `expand()` fallback, then `requestFullscreen()` on Telegram WebApp API 8.0+, handles fullscreen failure and safe-area insets. Bot inline entry uses a `url` button with Direct Mini App link `https://t.me/<bot>/<app_short_name>?startapp=<route>&mode=fullscreen`, after configuring the Main Mini App short name in BotFather.
- Navigation haptics: use `HapticFeedback.selectionChanged()` only when the active bottom section actually changes; use light impact for primary CTAs and notification feedback for success/error.
- Release rule: do not deploy WebApp v2 or remove the legacy bot UI until local production build, Android/iOS Telegram launch modes, account states and rollback have been tested and the project owner explicitly confirms release.
- Current design comparison: `?design=blue`, `?design=mono`, and the newer `?design=flow`. Owner rejected the overly card-based/all-blue-gradient character of the first Blue draft. `Arc Flow` is the current candidate and includes four working local sections: home, friends/referrals, support/FAQ, and settings. It uses `Manrope`, a locally extracted Microsoft Fluent icon subset (`regular`, with `filled` only for the active navigation item), icon-only bottom navigation, a single filled CTA, outlined connect CTA, compact status pills, short illustration-led cards and four restrained asynchronous CSS lights on a nearly-black background (dark navy → sky-blue, no turquoise). The accepted source logo is `webapp/public/assets/arc-flow/arc-logo.svg`; current shield-free transparent illustrations are `referral-gift-v2.png` and `support-agent-v2.png`, each with a small local CSS glow. The redundant “Подписка активна” label is intentionally absent. Fullscreen behavior uses BotFather Fullscreen launch mode plus `ready()`, `expand()`, Bot API 8.0 `requestFullscreen()` and Telegram content-safe-area CSS variables. All preview routes remain local-only and must not be deployed before explicit approval.
- `Arc Flow` consumes the existing status/tariffs/referral API and implements real renew/buy deep-links, a platform chooser, HTTPS import-page flow for Happ, referral copy/share and Telegram support. The referral API returns both `link` (Telegram) and `site_link`; `/invite/<code>` is the public ArcVPN-domain redirect to the bot deep-link.
- WebApp account foundation added locally on 2026-07-29 (migration 27): verified email linking/login with hashed one-time codes and hashed 30-day sessions; notification preferences for expiry/traffic/first connection; import-time device registry; public user agreement dated 29 July 2026. Email delivery requires production `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` environment values. Never store raw codes/session tokens.
- Device inventory is registered when the HTTPS Happ import page opens and refreshed again at the deep-link click. It gives immediate platform-level visibility independent of 3x-ui IP counting. Exact hardware model is displayed only when User-Agent Client Hints exposes it; iOS normally hides the exact iPhone model, so do not infer or fake it. 3x-ui `online_devices` remains a separate current-activity count.
- Current Arc Flow background is three slow high-blur morphing CSS aurora blobs (navy/blue/soft sky), with `prefers-reduced-motion`. Major cards use a subtle premium hairline plus tonal separation; inner radii are smaller than container radii. Home shortcut art sits over an 11%-opacity radial glow blurred by 46px; arrow pills and the Connect VPN button interior are transparent.
- WebApp support chat added locally in migration 28: one persistent thread per user, ordered user/admin messages, unread timestamps and a six-messages-per-minute limit. `POST /api/support/messages` notifies every `ADMIN_IDS` entry with callback `support_reply:<thread_id>`; the admin FSM stores the reply and sends the user a Telegram notification. The WebApp polls every 5 seconds while the chat is open. Keep the external support URL only as a fallback, not as the primary chat UX.

### Renewal after expiry: 3x-ui v3 incident (2026-07-25)

- Symptom: payment and DB expiry extension succeeded, but every subscription inbound remained unusable for a previously expired client.
- Root cause: `POST /panel/api/clients/update/{email}` expects the client object at the JSON root. Sending `{"client": body}` is rejected with `client email is required`; that wrapper is valid for `clients/add`, not `clients/update`.
- The billing flow also ignored a false result from `push_key_to_panel()` and incorrectly marked fulfillment as `applied`.
- Fix commit: `2950b7b`. All three v3 update call sites now send the root object; renewal becomes `manual_review` instead of `applied` when the panel update fails.
- Recovery procedure for an affected paid key: run `push_key_to_panel(key_id, reset_traffic=True)`, then verify the v3 `clients.enable`, expiry/traffic values and every attached inbound on master and physical nodes.

---

## Проверка Hysteria2 на проде — 2026-07-24

- Нативные Hysteria2 inbound 3x-ui активны: Германия `id=14`, Финляндия на master `id=15` (физический inbound ноды — `id=7`), UDP/443.
- Прямые домены и сертификаты: `de.arccnet.space` → Германия, `fin.arccnet.space` → Финляндия. Для Hysteria нужен именно этот SNI, а не CDN-домены.
- Обе линии проверены официальным Hysteria v2-клиентом: QUIC-соединение, маскировка `salamander`, SOCKS и HTTP-трафик успешно прошли. Серверная часть исправна.
- 3x-ui v3 хранит маскировку в `stream_settings.finalmask.udp` списком объектов `{type: "salamander", settings: {password: ...}}`. Генератор подписки обязан поддерживать этот формат (и старый словарь), иначе клиент получает ссылку без пароля маскировки.
- Кастомная ArcVPN-подписка `/sub/<sub_id>?format=plain` сейчас выдаёт обе Hysteria2-ссылки: прямой IP, порт 443, `sni=de.arccnet.space` / `fin.arccnet.space`, `obfs=salamander` и непустой `obfs-password`.
- Для совместимости с мобильными клиентами в Hysteria2-ссылку также явно передаётся `alpn=h3`; изменение применено на проде и API подписки перезапущен.
- После мобильной диагностики `salamander` временно отключён на обоих Hysteria2 inbound: телефон завершал лишь QUIC-проверку без передачи полезного трафика. Текущая рабочая конфигурация — нативный Hysteria2 + TLS (`sni`) + `alpn=h3`, без obfs. Официальный Hysteria-клиент проверен на Германии и Финляндии с реальным HTTP-трафиком.
- Hysteria2 URI должен использовать TLS-домен также в authority/host (`fin.arccnet.space` или `de.arccnet.space`), а не голый IP с отдельным `sni`: это повышает совместимость мобильных клиентов с проверкой сертификата. Применено на проде 2026-07-24.
- Критический фикс 2026-07-24: в 3x-ui v3 `clients/list` отдаёт общий `password`, а Hysteria2 проверяет inbound-специфичный `settings.clients[].auth`. Генератор кастомной подписки обязан объединять `auth` из записи конкретного inbound; иначе клиент завершает только QUIC handshake, а прокси-аутентификация отклоняется. На проде ссылки подтверждённо используют корректный `auth`.
- Hysteria #2 обслуживается официальным бинарником `hysteria` v2 на UDP/443 (`arcvpn-hysteria.service`) на обеих нодах. Xray inbound Hysteria перенесён на UDP/8443 и оставлен только как источник клиентов для панели/подписки. Авторизация официального сервера выполняется `/usr/local/lib/arcvpn-hy2-auth.py`, который сверяет `auth` в `/etc/x-ui/x-ui.db` и не хранит общий пароль.
- Активные клиенты добавлены в Hysteria #2 2026-07-24 штатным v3 `attach`: 12 клиентов в Германии #2 (master id=14), Финляндии #2 (master id=15) и физической ноде Финляндии (id=7). Для future backfill в v3 использовать attach, а не clients/update: текущая панель отклоняет старую обёртку update с ошибкой `client email is required`.
- Если Hysteria не работает в телефоне после этой проверки — сначала принудительно нажать «Обновить подписку» либо удалить и добавить её заново: вероятнее всего, клиент держит старую ссылку. Если не поможет, собирать точный текст ошибки и оператора/сеть: часть мобильных сетей блокирует или ухудшает UDP/QUIC при полностью рабочем TCP Reality.

---

## Germany panel/client recovery and Arc Flow release (2026-07-29)

- Owner explicitly approved the Arc Flow WebApp production release. `/app` now defaults to Arc Flow; `?design=legacy` remains the rollback view and `?design=blue` / `?design=mono` remain comparison previews. Build the WebApp before deploy and verify `https://sub.arccnet.space/app` returns HTTP 200.
- A support-message regression was fixed in commit `e21e79d`: SMTP email-code creation belongs only in `_send_email_code()`. `_notify_support_admins()` only forwards the message to `ADMIN_IDS`; placing email variables there crashes its background thread with `NameError: purpose` while the user-facing API still returns 200.
- Germany x-ui had a historical SQLite `disk I/O error: no such file or directory` event on 2026-07-28. On the 2026-07-29 check, DB `quick_check` and `integrity_check` were `ok`, `x-ui.service` was active with no restart, and there were no fresh I/O/crash records. Recurring `get` localization warnings are harmless and not a VPN failure.
- Do not use `inbounds.settings` as the client source of truth in 3x-ui v3. Use `GET /panel/api/clients/list` via `XUIClient._v3_list_clients()` and compare the returned `email` values with active `vpn_keys.panel_email`.
- IMPORTANT correction: never recover a missing v3 client with `XUIClient.add_client(..., inbound_id=1)`. That creates a client bound to only one inbound and makes the subscription appear to contain Germany only. Use `provision_client_all_inbounds()` with the existing app UUID, then verify all protected inbound IDs and synchronize `client_uuid` with the panel. Before repair, make a dated copy under `/root/ArcVPN/backup/deploy/`; never edit `/etc/x-ui/x-ui.db` while x-ui is running.

---

## x-ui stability guard and expired-client reconciliation (2026-07-30)

- Incident evidence: the host filesystem and kernel showed no physical storage errors, no read-only remount and sufficient free space. The panel DB passed `quick_check`, but v3 writes failed with `disk I/O error: no such file or directory` while reads still worked. A clean x-ui stop, WAL checkpoint, temporary switch to DELETE journal, removal of stale `-wal`/`-shm`, and restart restored writes. The panel returns to WAL after start; that is normal.
- The 2026-07-28 outage also contained an invalid Xray VLESS inbound (`decryption: "none"` missing), so Xray could not build `in-12631-tcp`. The panel additionally entered login throttling because stale credentials retried repeatedly. There were no kernel/disk hardware errors; the failure was application/SQLite/config state.
- A paid key can remain unusable when ArcVPN DB renewal succeeds but the panel client stays `enable=false` with an old `expiryTime`. The 2026-07-30 case for key `143` was repaired without resetting traffic: enabled, expiry synchronized to 2026-08-15, 1 TiB limit retained, 7.23 GB app usage retained and all protected inbound attachments verified.
- Production protection: `xui_health_guard.py`, `arcvpn-xui-guard.service` and `arcvpn-xui-guard.timer` (commits `9eec62b`, `9094c9a`). The timer runs every two minutes independently of the bot. It checks SQLite integrity, exact inbound topology `{3,5,7,13,14,15,16,17}`, x-ui/Xray/Hysteria runtime state and every active client's presence, attachments, UUID, `enable`, expiry and traffic limit.
- The guard never deletes clients and never resets traffic. It recreates only missing active clients across all supported inbound IDs, repairs missing attachments and synchronization drift, performs a controlled WAL recovery on write I/O failure, and sends admins a Telegram alert only on recovery or failure.
- Резервный пользовательский UI Telegram-бота после кнопки «Продолжить в боте» использует компактный кабинет: актуальный статус, срок и остаток трафика; основная CTA «Открыть ArcVPN»; отдельные действия «Подключить VPN», «Моя подписка», «Продлить/Выбрать тариф», «Пригласить друга» и «Помощь». Экран подключения повторно использует существующий безопасный импорт подписки, а помощь содержит FAQ внутри Telegram и ссылку на оператора. UUID, адреса серверов и другие технические детали на главном экране не показываются. Админская часть не менялась.
- В пользовательском Telegram UI действует модель одной подписки: callback `my_keys` и старые `key:<id>` больше не показывают список ключей и техническую карточку. Они сразу открывают единый экран подписки со статусом, оставшимися днями, остатком трафика, количеством устройств, импортом, продлением и инструкцией. Старые callback сохраняются только ради уже отправленных сообщений. После оплаты тот же экран используется как итоговый. Инструкции Happ сообщают фактическое автообновление раз в 1 час.
- Реферальная модель с миграции 33: реферер получает `+5 дней` один раз, когда приглашённый друг впервые заходит в бот и получает авто-trial; после первой покупки друг и реферер получают ещё по `+15 дней`. Значения идут из `referral_trial_bonus_days=5` и `referral_purchase_bonus_days=15`, выдача идемпотентна через `grant_referral_bonus_once`. Оба бонуса должны одинаково описываться в Telegram UI, WebApp и `/invite/<code>`.
- Новая обложка резервного кабинета создана встроенным ImageGen и хранится в `bot/assets/arc-cabinet-v2.webp`; она отправляется новым пользователям вместе с сообщением об автоматически активированном trial.
- `/root/ArcVPN/backup/xui-guard/last-known-good.db` is atomically refreshed only after a successful full check. A daily consistent SQLite backup is stored alongside it. If inbound topology disappears, the guard restores the last known-good topology and then reconciles active clients from the ArcVPN DB.
- Both Germany and Finland use a systemd override with `Restart=always` and `RestartSec=3s` for x-ui. Official Hysteria already uses the same restart policy. A transient Germany→Finland panel timeout was checked: Finland x-ui/Hysteria/Xray were active, required ports listened, and subsequent cross-node TCP/HTTP probes completed normally.
# WebApp, онбординг и платежи (2026-07-30)

- Telegram Mini App работает в Fullscreen. Верхние и нижние отступы нельзя
  задавать константами: `webapp/src/lib/telegram.js` синхронизирует
  `contentSafeAreaInset` в CSS-переменные `--tg-content-safe-top/bottom`.
- После обязательной подписки на канал пробный доступ создаётся автоматически.
  Новый пользователь видит фирменное приветствие и две кнопки:
  `Подключиться` (WebApp) и `Продолжить в боте` (резервный интерфейс).
- Покупка базового тарифа из WebApp идёт через
  `POST /api/payments/sbp`, проверка — `GET /api/payments/sbp/<order_id>`.
  YooKassa вызывается строго с `payment_method_data.type=sbp`; заказ и
  fulfillment идемпотентны.
- Выбор банковского приложения после перехода — штатная часть СБП/НСПК, а не
  выбор способа оплаты ArcVPN.
- YooKassa имеет два A-адреса, один из них периодически зависает на TLS.
  Платёжные вызовы `AsyncExecutor.run(..., timeout=45)` должны успевать перейти
  на повторную попытку; нельзя возвращать им общий короткий таймаут генерации
  подписки.
- Крестик Telegram переназначить нельзя. Для вложенных экранов используется
  нативная `Telegram.WebApp.BackButton` и событие `backButtonClicked`.
- Desktop WebApp (`min-width: 900px`): вертикальный navigation rail слева,
  широкое скруглённое рабочее полотно и компактная центральная колонка; мобильная
  нижняя навигация сохраняется без изменений.
- Для быстрого первого отображения Telegram SDK подключён с `defer`, удалён
  второй неиспользуемый запрос Google Fonts. Таймаут подключения к YooKassa
  2.5 секунды: при зависшем A-адресе быстро выполняется следующая попытка.
- Доплаты за устройства и LTE пока запрещены сервером (`addons_not_available`):
  не брать деньги до появления постоянного учёта и применения этих лимитов.
- Для YooKassa сумма тарифа берётся из `tariffs.price_rub`; в платёжный order
  записывается `price_rub * 100`. Не использовать старое `price_cents` как
  копейки рублей: в текущей базе это историческая расчётная валютная цена
  (например, 3 месяца: `price_rub=300`, `price_cents=382`).
- Импорт из WebApp в Happ добавляет к subscription URL стабильный анонимный
  параметр `device`. Сначала WebApp регистрирует хеш идентификатора в
  `user_devices`, затем открывает Happ. Первые `DEFAULT_LIMIT_IP` устройств по
  времени первого импорта получают настоящий профиль; последующие получают
  ровно две информационные строки «Превышен лимит устройств» и «Докупите
  устройство в ArcVPN». Старые subscription URL без `device` не блокируются:
  это сохраняет совместимость уже добавленных подписок.
- Реферальная `/invite/<code>` больше не делает автоматический 302 в Telegram.
  Она отдаёт автономную лёгкую landing page без внешних шрифтов и скриптов,
  объясняет бонус +15 дней и только по кнопке открывает bot deep-link.
- Единый план превращения WebApp и пользовательской части бота в полноценный
  продукт ведётся в `PRODUCT_ROADMAP.md`. Рассматривается единый пакет `500 ГБ`
  с расходом LTE `×10`, но до отдельного надёжного учёта usage по inbound
  действующие лимиты пользователей менять нельзя. Для первого стабильного
  релиза технически безопаснее сохранить два прозрачных счётчика.
- Миграция v30 создаёт постоянные entitlement-поля пользователя:
  `device_limit` (default 2), `lte_quota_gb` (default 20), `lte_used_bytes`, а
  также поля запрошенных add-ons в `payments`. API `/api/devices` возвращает
  эти лимиты, а subscription device gate читает `device_limit` пользователя.
  Покупки add-ons пока по-прежнему нельзя принимать до идемпотентного
  fulfillment и синхронизации `limitIp` на панели.
- Владелец утвердил модель трафика: `500 ГБ` на месяц, обычный трафик `×1`,
  inbound обхода глушилок LTE `×10`. Миграция v31 хранит сырой normal/LTE usage
  и границы месячного цикла. Не переключать существующие 1024 ГБ до появления
  проверенного раздельного meter по inbound.
- На поздних этапах обязательно напомнить владельцу: SMTP; юридические
  реквизиты/email; возможные ручные действия YooKassa webhook/чеков;
  утверждение визуального направления картинок; запрос Happ о device ID/модели.
- WebApp add-ons: сервер является источником цены (`+25 ₽/устройство/месяц`,
  `+2 ₽/ГБ LTE/месяц`, шаг LTE 5 ГБ), сохраняет requested limits в payment и
  применяет их один раз после статуса paid. Старые bot-заказы без requested
  значений не сбрасывают entitlement. `push_key_to_panel()` передаёт
  персональный `device_limit` как `limitIp`; новый клиент создаётся с ним сразу.
  LTE entitlement продаётся и хранится, но физическое weighted-списание нельзя
  включать до готовности раздельного meter.
- YooKassa webhook endpoint: `POST /api/payments/yookassa/webhook`. Нельзя
  доверять входящему `object.status`: endpoint находит order по provider ID и
  повторно вызывает YooKassa API, затем идемпотентно выполняет fulfillment.
  После applied отправляет пользователю Telegram-уведомление. Позже напомнить
  владельцу зарегистрировать этот URL в кабинете YooKassa.
- Резервный планировщик в `bot/services/scheduler.py` каждые 2 минуты
  перепроверяет через YooKassa API свежие незавершённые СБП-заказы за 48 часов.
  Поэтому оплаченный заказ применяется и при задержке или недоставке webhook.
- WebApp хранит незавершённый СБП-order в `localStorage`, восстанавливает его
  после возврата из банка/перезапуска и автоматически проверяет статус каждые
  4 секунды. UI различает ожидание, успешную оплату, отмену и сетевую задержку.
- Если деньги получены, но fulfillment перешёл в `manual_review`, API отдаёт
  `review_required=true`: WebApp прекращает polling, предупреждает не платить
  повторно и открывает чат поддержки.
- Миграция v32 добавляет `user_devices.is_active/revoked_at`. В настройках
  WebApp устройство можно переименовать или освободить его слот. Запись не
  удаляется: отозванный device token блокируется при следующем обновлении
  подписки, а явный повторный импорт реактивирует его как новый слот.
- Business Console `/admin` допускает два независимых способа входа: подписанный
  Telegram initData администратора и HttpOnly-сессию после пароля. Пароль
  задаётся только серверной переменной `ADMIN_CONSOLE_PASSWORD`, не хранится в
  Git; cookie подписывается HMAC, живёт 12 часов, включены Secure/SameSite и
  ограничение попыток входа.
- `get_user_primary_key()` обязан возвращать `sub_id`: от него зависят текстовая
  копируемая ссылка и прямой импорт Happ в сообщениях «Моя подписка» и
  «Подключить VPN».
- Миграция v34 добавляет идемпотентные lifecycle-события. После 5 дней активной
  подписки бот один раз просит оценку; спустя 2–10 дней после окончания один раз
  спрашивает причину ухода. Ответ на win-back опрос однократно даёт 3 дня и
  синхронизирует срок на панели. Обложки: `arc-feedback-v1.png` и
  `arc-winback-v1.png`; основная обложка кабинета — `arc-cabinet-v5.png`.
- Lifecycle v35 применяется только к пользователям, зарегистрированным после
  даты включения механики (`settings.lifecycle_eligible_after`). Существующих
  пользователей нельзя включать в автоматическую оценочную/win-back рассылку.
  При причине ухода «другой VPN» бот запрашивает название и свободный отзыв.
- Единый комплект обложек Telegram UI: `arc-welcome-v1.png`,
  `arc-cabinet-v6.png`, `arc-payment-v1.png`, `arc-referral-v1.png` и
  `arc-winback-v1.png`. Стиль: тёмный фирменный фон, логотип слева сверху,
  осмысленная матовая 3D-иллюстрация справа и название слева снизу.
- В Business Console старые платежи с `amount_cents`, записанным до исправления
  рублёвой цены, помечаются как старые ошибочные заказы. По умолчанию платежи
  фильтруются до успешных; пользователи имеют фильтры по сумме оплат, онлайну и
  отсутствию продления, а длинные списки скроллятся внутри панели.

## Обновление UI оплаты и ссылок (2026-07-31)

- Пользовательская ссылка показывается без технических параметров: `https://sub.arccnet.space/sub/<sub_id>`. В Telegram она выводится отдельным тегом `<code>`, поэтому по нажатию её удобно копировать. Параметр `?format=plain` используется только во внутренней ссылке прямого импорта Happ.
- В WebApp перед созданием платежа открывается модальное окно со способами в порядке: СБП, карта, криптовалюта. СБП работает через текущую интеграцию YooKassa; карта и криптовалюта временно передают пользователя в соответствующий платёжный сценарий бота.
- Автопродление показано в интерфейсе, но заблокировано до подключения и проверки рекуррентных платежей YooKassa. Нельзя включать переключатель фиктивно.
- В Telegram-клавиатурах покупки и продления применяется тот же порядок и названия: `⚡ СБП`, `💳 Картой`, `₿ Криптовалютой`.
- Новая обложка `bot/assets/arc-referral-v1.png` не содержит соединяющей телефоны линии.
- В админ-панели фильтры пользователей и платежей закреплены над списком; прокрутка происходит внутри списка, системный scrollbar визуально скрыт.

## Автопродление YooKassa

- `save_payment_method=true` только запрашивает привязку способа оплаты. Полноценное автопродление требует: разрешения автоплатежей для боевого магазина у менеджера YooKassa; сохранения `payment_method.id` после успешного webhook при `payment_method.saved=true`; таблицы согласий и параметров продления; фонового scheduler; повторного платежа с `payment_method_id`; уведомлений об успехе/ошибке и пользовательского отключения.
- Welcome-баннер `bot/assets/arc-welcome-v1.png` имеет обязательный размер 1344×768; внутри телефона отображается читаемый список VPN-серверов.

## Операционная телеметрия и трафик (2026-08-01)

- `servers.active_clients` нельзя трактовать как онлайн: исторически это число активных по сроку ключей из БД. Живой онлайн берётся из 3x-ui `/panel/api/clients/onlines`.
- Master 3x-ui возвращает общий online всех локаций, а `/panel/api/nodes/list` — online каждой внешней ноды. Германия считается как `общий online - сумма online нод`; Финляндия берётся напрямую из node telemetry.
- Business Console показывает отдельно доступность API панели, systemd-служб, нод и реестр inbound. Общая цифра «Сейчас онлайн» должна совпадать с суммой локаций.
- Guard хранит состояние в `/run/arcvpn-xui-health-state.json`; уведомление об аварии отправляется после трёх последовательных ошибок, одиночный сбой авторизации/сети не считается падением VPN.
- Платные тарифы и ключи имеют единый месячный лимит 500 ГБ. LTE-inbound обязательно помечается в подписке как `трафик ×10`.
- В 3x-ui v3 текущая global-client модель дублирует один общий `clientStats` во всех inbound. Поэтому точное индивидуальное списание LTE ×10 нельзя считать по текущему email/UUID: нужен отдельный LTE client identity на пользователя и миграция ссылок. Не включать фиктивный weighted meter по дублированным счётчикам.
- Business Console имеет рабочие разделы инфраструктуры, поддержки и чек-листа готовности сервиса, а не пустые заглушки.
- Callback `start` обязан импортировать `FSInputFile`: без него кнопки «На главную» падают во время выполнения и пользователь остаётся на старом сообщении.
- Финляндия управляется как внешний узел `195.226.92.37` и добавляется в инфраструктурный реестр Business Console без создания второй записи сервера и дублирования ключей.
- Диагностика 2026-08-02: заявленные 10 Гбит/с Финляндии не подтверждены фактической производительностью. Тест одного TCP-потока дал около 70 Мбит/с, параллельный тест около 230 Мбит/с; CPU steal составлял 11–45%, наблюдался высокий джиттер TLS/маршрута. Это признаки перепроданного гипервизора/аплинка и вероятная причина медленной загрузки видео. Германия в тот же момент дала около 466–530 Мбит/с и CPU steal 0–1%. Не считать паспортную скорость тарифа гарантированной; сравнивать ноды по длительным метрикам и клиентским тестам из РФ.
- Business Console получает список support threads, историю сообщений и может отправлять ответ пользователю одновременно в WebApp и Telegram.
# Точный LTE ×10 и стабильность (2026-08-01)

## Remnawave staging: фактическая проверка wCloud (2026-08-09)

- Staging panel: `https://remna.arccnet.space`; production XUI остаётся источником реальных подписок до завершения 72-часового теста и canary.
- Нода `wCloud France Staging` (`fr2.sfxu.ru`, control `20139`) подключена и online. Internal squad: `ArcVPN Staging`; в нём только staging-пользователи.
- Staging hosts: TCP Reality `20140` и Hysteria2 UDP `20141`. Оба включены и выдаются canary-пользователю.
- Проверен полный synthetic lifecycle через `scripts/remnawave_staging_check.py --write-synthetic`: create/read/reset/disable успешно.
- Проверена реальная клиентская передача данных через Xray: VLESS Reality и Hysteria2 валидны, HTTPS проходит через французский IP, Cloudflare POP `CDG`.
- Секреты панели, API token, Reality private key и subscription URL canary хранятся только на серверах в файлах `0600`; в Git их не добавлять.
- Следующий gate: 72 часа телеметрии → canary 2–5 пользователей → поэтапный cutover. Новый импорт публичной ArcVPN-подписки пользователям не должен требоваться.


## Подготовка перехода XUI → Remnawave (2026-08-09)

- Публичный URL подписки ArcVPN не меняется; существующие клиенты не должны импортировать подписки заново.
- Добавлена миграция БД v46 и фабрика панелей. Старые записи без `panel_type` всегда используют `xui`.
- Remnawave подключается Bearer API token через `panel_api_url`; сохраняются VLESS UUID, срок, лимит трафика, лимит устройств и internal squad.
- Запись в Remnawave по умолчанию закрыта (`panel_write_mode=disabled`). Режим `shadow` разрешает только синтетические имена `arc-staging-*`; реальные пользователи доступны лишь после явного `production` cutover.
- Проверка до canary: `scripts/remnawave_staging_check.py`; критерии и откат описаны в `docs/REMNAWAVE_STAGING_PLAN.md`.
- Production XUI остаётся источником конфигураций до успешного 72-часового теста RemnaNode и canary. Ноду нельзя подключать напрямую к реальным пользователям.
- Получена тестовая wCloud RemnaNode `freetest` во Франции: `fr2.sfxu.ru`, control port `20139`, TCP Reality `20140`, Hysteria2 `20141`, аренда 3 дня. До ввода Secret Key control/TCP-порты извне закрыты — это ожидаемое неподключённое состояние.
- Текущий DE production непригоден для Remnawave Panel: 1 vCPU/2 ГБ при официальном минимуме 2 vCPU/2 ГБ и рекомендуемых 4 vCPU/4 ГБ; на нём уже работают XUI/Xray/Hysteria/bot/API/nginx. Panel нужна на отдельном VPS.
- Полученный профиль wCloud содержит TCP Reality и Hysteria2, но не XHTTP и LTE. Reality private key из переданного тестового JSON не переносить в production — сгенерировать новый.

## Целевой каталог подписки и экономика инфраструктуры (2026-08-11)

- Публичный URL `/sub/<sub_id>` сохраняется. Миграция между панелями и добавление нод должны происходить через обычное обновление подписки без повторного импорта пользователями.
- Целевой порядок профилей: `⚡ Автовыбор — самый быстрый`, `🇩🇪 Германия`, `🇫🇮 Финляндия`, дополнительные страны после основных, затем `🇷🇺 Обход глушилок (трафик ×10, LTE)`.
- `Автовыбор` нельзя имитировать переименованным обычным inbound. Для Happ/Xray нужен отдельный JSON-профиль с несколькими outbounds, observatory и balancer `leastPing`; до проверки на мобильном и desktop Happ пользователям его не выдавать.
- В публичной подписке остаётся только финский LTE/CDN origin `cdn-fi.arccnet.space`. Немецкий LTE удаляется. Точное публичное имя финского обхода: `🇷🇺 Обход глушилок (трафик ×10, LTE)`.
- Финляндия временно остаётся рабочим fallback и LTE-origin до отдельной проверенной замены. Нормальные DE/FI-профили нельзя удалять одним релизом вместе с переходом панели.
- Контрольная экономика: Польша control plane $4.83 ≈ 380 ₽/мес; wCloud cloud-2 — 200 ₽/мес за ноду; старая Финляндия — 365 ₽/мес. Минимум Польша+DE+FI ≈ 945 ₽/мес; с production FR cloud-2 ≈ 1 145 ₽/мес. При консервативном среднем вкладе 100 ₽ с платящего пользователя это около 10 и 12 ежемесячно платящих пользователей соответственно.
- Не покупать Канаду/Великобританию только ради количества стран: до 25–30 стабильно платящих пользователей приоритет — DE+FR, независимый FI fallback и наблюдаемость. Не держать все production-ноды у одного провайдера после этапа запуска.
- Business Console должна использовать нормализованные суммы: старые YooKassa-записи хранят RUB в `amount_cents`, новые — копейки. Историю не переписывать; нормализовать на чтении и показывать реальную сумму RUB.
- Germany wCloud cloud-2 подключена к Remnawave как отдельная нода `de2.sfxu.ru`: control `20036`, TCP Reality `20037`, Hysteria2 `20038`. Используется отдельный config profile `wCloud Germany`; внутренние inbound tags обязательно уникальны (`DE_VLESS_TCP`, `DE_HYSTERIA_UDP`). Secret Key хранится только на control plane в `.secret.remnanode-germany` с mode `0600`.
- Чистый ручной каталог без названий протоколов: `Германия #1/#2`, `Франция #1/#2`, `Финляндия #1/#2/#3`, затем будущая Польша, старая Германия с пометкой `(резерв)`, последним финский LTE.
- Настоящий автовыбор Happ реализуется параметрами подписки `subscription-autoconnect: 1` и `subscription-autoconnect-type: lowestdelay`, а не фиктивным inbound. Для применения расширенных параметров Happ нужен восьмизначный Provider ID, привязанный к `sub.arccnet.space`; он задаётся в `config.HAPP_PROVIDER_ID`.
- Инцидент новой Германии 2026-08-11: RemnaNode и порты были доступны, но немецкие inbounds не входили во внутренний squad ArcVPN, поэтому Remnawave генерировала Xray-конфиг с `0 users`. В squad добавлены FR+DE inbounds; конфиг Германии перезапущен с 13 активными клиентами. `scripts/sync_remnawave_users.py` теперь каждые 5 минут восстанавливает декларативный список из `REMNAWAVE_SQUAD_INBOUND_UUIDS` и проверяет его после записи.
- 2026-08-11 wCloud заменил проблемную Германию на новую Францию: control `fr2.sfxu.ru:20085`, TCP Reality `:20086`, Hysteria2 `:20087`, SID `ba5b0807589028e6`, public key `IRmahen2BbN-2-_exw4TNoeJBGAF0bvVSobxdBQ_Bn0`. Старая тестовая Франция отключена от публичной подписки, новая публикуется как `Франция #1/#2`. Целевой порядок: Франция, Финляндия, Германия, LTE; слово `(резерв)` пользователю не показывать.

## Full Remnawave inbound cutover (2026-08-11)

- Публичный каталог больше не строится из inbound 3x-ui. Все обычные подключения управляются Remnawave: Франция — TCP Reality и Hysteria2; Финляндия и Германия — XHTTP Reality, TCP Reality и Hysteria2.
- Порядок и названия без технических протоколов: `Франция #1/#2`, `Финляндия #1/#2/#3`, `Германия #1/#2/#3`, затем `Обход глушилок (трафик ×10, LTE)`. Пометка `(резерв)` для Германии запрещена.
- Finland RemnaNode: control `22200`, public transports `22201` TCP Reality, `22202/udp` Hysteria2, `22203` XHTTP Reality. Germany RemnaNode: control `22100`, public transports `22101` TCP Reality, `22102/udp` Hysteria2, `22103` XHTTP Reality.
- LTE вынесен в отдельную Finland RemnaNode на control `22210`, origin `10001`; Yandex CDN и публичный адрес `cdn-fi.arccnet.space:443` сохранены. На ноде установлен `consumptionMultiplier=10`, поэтому расход LTE точно списывается в десятикратном размере.
- Reality использует проверенный self-steal: Finland — `fin.arccnet.space`, Germany — `sub.arccnet.space`. Canary через настоящий Xray-клиент дал HTTP 204 для TCP Reality, XHTTP Reality и Hysteria2 обеих стран.
- URL подписок и VLESS UUID пользователей сохранены. После обычного обновления подписки клиент получает новый Remnawave-каталог без повторного импорта. Старые 3x-ui данные не удалять немедленно: они остаются только как локальный rollback и не участвуют в выдаче подписки.
- Happ Provider ID `O7YLTHgc` привязан владельцем к `sub.arccnet.space`. Subscription API передаёт его одновременно через HTTP-заголовок `providerid` и комментарий `#providerid`, чтобы Provider-функции сохранялись при добавлении и обновлении подписки.
- Happ-автовыбор реализован официальными subscription meta-параметрами: `subscription-autoconnect=1`, `subscription-autoconnect-type=lowestdelay` и `subscription-ping-onopen-enabled=1`. Это режим всей подписки: Happ пингует список при открытии и подключается к минимальной задержке, но не создаёт отдельную строку-сервер `Автовыбор`. Не подменять его дубликатом конкретной страны.
- По запросу владельца добавлен также отдельный видимый JSON-профиль `⚡ Автовыбор`: это полноценная клиентская Xray-конфигурация с outbound всех обычных Remnawave-подключений, `burstObservatory` и balancer `leastLoad`; LTE в балансировщик не входит. Happ-импорт использует `format=json`, где первым объектом идёт автовыбор, затем самостоятельные серверы.
- Во время релиза `5513ebb` польский control-plane `217.60.33.38` перестал отдавать SSH banner и HTTPS. На Germany fallback `/etc/nginx/sites-enabled/subscription-arccnet` переключён с proxy на Польшу на локальный `127.0.0.1:8080`; `/health` через германский A-запись снова отвечает HTTP 200. Пока Польша не восстановлена, её A-запись создаёт вероятность таймаута и должна быть временно убрана из DNS либо узел должен быть перезапущен у провайдера.
- 2026-08-11 начат полный zero-downtime cutover legacy-нод в Remnawave. На Финляндии RemnaNode слушает control `22200`, TCP Reality `22201`, Hysteria2 `22202`, XHTTP Reality `22203`; node UUID `a6ef8ba9-8f39-437a-be01-b3d23bd78be3`, profile UUID `e783e4bf-6f6d-4059-9fab-888704db2b10`. На старой Германии: control `22100`, TCP `22101`, Hysteria2 `22102`, XHTTP `22103`; node UUID `a59b0c97-267a-40af-95df-ff86ba0d4977`, profile UUID `e2a1bb3f-f5eb-4c61-9505-baf007146867`. Обе ноды работают параллельно с legacy Xray, получили 13 пользователей через squad. При включении `REMNAWAVE_FINLAND_ENABLED`/`REMNAWAVE_GERMANY_ENABLED` обычные legacy-строки этих стран скрываются, но финский LTE остаётся на старом origin до отдельного переноса с коэффициентом ×10.
- Коэффициент трафика Remnawave задаётся для всей Node, а не отдельного inbound. Для строгого LTE ×10 нужна отдельная LTE Node (или отдельный внешний счётчик); смешивать обычный ×1 и LTE ×10 на одной Node нельзя.

- Единый месячный лимит: 500 GiB. Трафик двух inbound «Обход глушилок» должен списываться строго с коэффициентом ×10.
- Текущие глобальные clientStats 3x-ui не позволяют отделить LTE от остальных протоколов: один клиент прикреплён ко всем inbound и имеет общий счётчик.
- Целевая реализация: отдельные внутренние `lte_panel_email` и UUID, прикреплённые только к LTE inbound; обычная идентичность остаётся на XHTTP/TCP/Hysteria. Публичный URL подписки не меняется.
- Миграция выполняется только штатным API attach/detach, партиями, с canary, backup и автоматическим rollback. Прямая правка живой SQLite x-ui запрещена.
- Причины прошлых сбоев разделены: повреждение SQLite/disk I/O; рассинхронизация credentials панели; небезопасная ручная последовательность stop/edit/start.
- Полная схема: `docs/STABILITY_AND_LTE_ACCOUNTING.md`.

# Автопродление YooKassa (2026-08-01)

- Магазин `1325666`: рекуррентные платежи пока не подключены. YooKassa требует сначала согласовать автоплатежи по банковским картам; после этого отдельно запрашиваются СБП и другие способы.
- Обновление 2026-08-08: ЮKassa включила привязку банковских карт для магазина `1325666`. Реализованы отдельная карточная оплата с `save_payment_method=true`, хранение только подтверждённого `payment_method.saved=true`, идемпотентные циклы повторного списания и самостоятельное отключение. Для СБП код поддерживает тот же сценарий, но флаг `yookassa_sbp_recurring_enabled` нельзя включать до отдельного подтверждения ЮKassa. При сохранении СБП список банков может быть уже обычного: ЮKassa показывает только участников СБП, поддерживающих автоплатежи.
- Обязательное условие YooKassa реализовано: WebApp → Настройки → Автопродление показывает сохранённый способ и позволяет самостоятельно отключить автосписания и удалить локальный payment method без обращения в поддержку.
- Первый платёж с согласием создаётся с `save_payment_method=true`. Сохранять `payment_method.id` разрешено только после ответа YooKassa `payment_method.saved=true`.
- Пока YooKassa не согласовала опцию, настройка `yookassa_recurring_enabled` остаётся `0`, а UI показывает ожидание подключения. После письменного подтверждения установить её в `1` и включить scheduler повторных списаний.

## Telegram bot: `/start` и автопродление (2026-08-01)

### YooKassa и мониторинг (2026-08-08)

- YooKassa письменно подтвердила подключение рекуррентных платежей через СБП для магазина.
  Прод-настройка `yookassa_sbp_recurring_enabled` должна быть `1`; карточные и СБП-рекурренты
  управляются раздельно. Способ сохраняется только при `payment_method.saved=true`.
- Схема v45 хранит независимые сетевые пробы нод: packet loss, jitter, DNS, HTTPS и контрольную
  скорость загрузки. Агент запускает тяжёлую часть раз в 10 минут, обычную телеметрию — раз в минуту.
- Бесплатный RemnaNode wCloud на три дня рассматривается только как staging/canary для проверки
  Remnawave и сети. Миграция с 3x-ui выполняется параллельно и поэтапно, без замены живых UUID.
- До получения RemnaNode обязателен `docs/REMNAWAVE_STAGING_PLAN.md`. Публичные ArcVPN subscription
  URL не меняются при смене панели; повторный импорт пользователями является стоп-фактором миграции.
- `monitoring/compare_node_quality.py` формирует 72-часовой отчёт и решение `canary_ready` по
  покрытию, loss, jitter, CPU steal и p10 контрольной скорости.
- Владелец 2026-08-08 одобрил целевой переход с 3x-ui на Remnawave. Новую RemnaNode запрашиваем
  только после готовности staging Panel, panel-adapter, синтетических пользователей, shadow-sync
  и автоматического rollback; production-подписки и UUID до canary не переключаются.
- Сетевой нюанс YooKassa: из Play2Go один из двух IPv4 edge периодически зависает на TLS, а второй
  отвечает. HTTP-клиент обязан выбирать конкретный IPv4 на каждую попытку, чередовать адреса и
  повторять 429/5xx с неизменным `Idempotence-Key`. Текст пользователю — «Создаём оплату…», без
  внутреннего термина «создание QR».
- Платёжный UX бота с 2026-08-09 не показывает QR по умолчанию и не требует кнопки «Я оплатил»:
  основное действие открывает СБП, QR генерируется только по запросу для второго устройства,
  `payment.succeeded` автоматически применяет заказ и уведомляет пользователя, а reconciliation
  остаётся резервом при задержке webhook. Старый callback ручной проверки сохраняется только для
  ранее отправленных сообщений.

- Причина отказа `/start`: локальный `from aiogram.types import FSInputFile` внутри `cmd_start` сделал имя локальной переменной для всей функции; ветка существующего пользователя обращалась к нему до выполнения импорта и падала с `UnboundLocalError`. `FSInputFile` должен импортироваться только на уровне модуля.
- В резервном UI бота есть раздел `⚙️ Настройки → Автопродление`: он показывает состояние привязанного способа и позволяет самостоятельно отключить его без поддержки.
- При оплате заказ хранит явный выбор пользователя в `payments.auto_renew_requested`. Пока `yookassa_recurring_enabled=0`, включение заблокировано понятным сообщением; после согласования YooKassa тот же UI начнёт передавать `save_payment_method=true`.
- Фоновая сверка YooKassa — только резерв к webhook: не более 10 свежих заказов за цикл; при первом сетевом сбое цикл прекращается, чтобы недоступность YooKassa не забивала обработку Telegram-команд.
- Общая кнопка «Настройки» в резервном UI заменена на понятный раздел «Автопродление». Перед каждой оплатой экран явно показывает режим «без автопродления» или «с автопродлением» и позволяет переключить его до перехода к банку; согласие нельзя включать неявно.
- Все кнопки «Назад» из QR YooKassa возвращают в современный экран выбранного тарифа и способов оплаты. Старый экран `QR-оплата / Ключ / Выберите тариф` оставлен только как совместимый callback, но теперь тоже перенаправляет в новый UI.
- В «Моя подписка» и «Подключить VPN» ссылка выводится отдельным копируемым `<code>` с пустыми строками до и после и подсказкой «Нажмите на ссылку, чтобы скопировать»; URL формируется динамически по `sub_id` пользователя.
- Для согласования рекуррентов с YooKassa у администратора есть закрытый предпросмотр `Автопродление`: на нём видны название ArcVPN, отмеченная привязанная карта и кнопка самостоятельного удаления. Пользователь без прав администратора этот демонстрационный экран открыть не может.
- Уточнённый платёжный UX: переключателя автопродления на общем экране способов оплаты нет. После выбора СБП бот показывает отдельное подтверждение с двумя явными действиями — «Продолжить с автопродлением» и «Отключить и оплатить один раз» — и текстом согласия с регулярными списаниями и Пользовательским соглашением. Пока YooKassa не включила рекурренты, вариант с автопродлением не создаёт фиктивную привязку и предлагает разовый платёж.
- Резервный UI бота снова имеет раздел `⚙️ Настройки`, внутри которого находятся `📱 Устройства` (открывает сразу страницу устройств WebApp) и `🔁 Автопродление`.
- Причина неработавшего освобождения устройства окончательно подтверждена production-трассировкой: Happ удаляет и query `?device=`, и дополнительный сегмент `/sub/<master>/<device>`. Рабочая архитектура с миграции v40 — отдельный одноуровневый `device_sub_id` для каждого устройства: `/sub/<device_sub_id>?format=plain`. Happ такой ID сохраняет без изменений.
- Миграция v39 включает `users.enforce_device_tokens` для аккаунтов, где уже освобождалось устройство. Их старый URL без token возвращает три служебные строки и требует один раз переимпортировать оставшиеся устройства. После этого освобождённое устройство получает профиль «Подписка удалена», превышение лимита — профиль «Превышен лимит устройств».
- Business Console показывает отдельный блок контроля доступа: активные и освобождённые устройства, аккаунты с жёсткой привязкой, превышения лимита и ожидающие повторного импорта.
- Страница `/import/<sub_id>` автоматически пытается открыть `happ://add/...` через 120 мс после запуска фоновой регистрации устройства. Ручная кнопка остаётся только fallback для браузеров, блокирующих custom scheme без пользовательского касания.
- Business Console вынесена на отдельный hostname `https://panel.arccnet.space/` (A → Германия `2.26.84.210`). Для домена выпущен отдельный Let's Encrypt сертификат; Nginx stream SNI направляет `panel.arccnet.space` на HTTPS frontend `2053`, а SPA определяет админку по hostname. Старый `/admin` сохранён как совместимый адрес.
- Глобальная блокировка прокрутки исправлена: `overflow:hidden` на `html/body` включается только пока смонтирован `AdminConsole` через класс `body.admin-console-open`; пользовательский WebApp снова прокручивается независимо от CSS админки.
- HTTPS import bridge теперь отдаёт визуально пустую тёмную страницу без старого интерфейса. Он регистрирует device token и автоматически вызывает Happ; касание пустой страницы повторяет deeplink, если браузер заблокировал первый запуск.
- Happ может объединять или обновлять поверх друг друга разные subscription URL с одинаковым `Profile-Title`. Текущее продуктовое решение — у всех профилей единое название `ArcVPN` без эмодзи; состояние доступа показывается служебными inbound, а не переименованием подписки.
- Master URL нельзя блокировать WebApp-only сценарием: пользователь без работающего VPN может не открыть Telegram/WebApp. При прямом импорте master URL сервер создаёт детерминированный управляемый слот `Устройство Happ` и отдаёт рабочий профиль `ArcVPN`. Слот учитывается в общем лимите; после его освобождения повторный прямой импорт реактивирует слот. Модель телефона при вставке subscription URL неизвестна: Happ не передаёт модель, ОС и устойчивый device ID.
- Для `platform=unknown` WebApp использует отдельную белую векторную иконку Happ, а не fallback Apple/Windows. Инфо-текст подписки сохраняет подсказку обновления и работу РФ-сервисов, а вместо расшифровки ⚡/⭐ показывает реферальную механику: +5 дней за вход друга и +15 дней каждому после продления другом.
- Миграция v38 добавляет `vpn_keys.panel_disabled_at`: отключение истёкшего клиента на панели идемпотентно выполняется один раз. Уже отсутствующий на панели клиент считается достигшим требуемого состояния и больше не обходится каждую минуту.

# Remnawave staging installation (2026-08-09)

- The Remnawave control panel is installed on the existing Finland VPS at
  `https://remna.arccnet.space` (`195.226.92.37`). This is a temporary staging
  placement forced by the available infrastructure; it is not the recommended
  long-term control-plane host.
- Docker services `remnawave`, `remnawave-db`, and `remnawave-redis` are healthy.
  A persistent 4 GiB swapfile and conservative container limits were added.
  Existing `x-ui`, `nginx`, and `arcvpn-hysteria` services stayed active.
- TLS is issued by Let's Encrypt and renews automatically. Host nginx proxies
  only `remna.arccnet.space` to `127.0.0.1:3000`; metrics port 3001 is private.
- Remnawave administrator credentials are stored only on the Finland server at
  `/root/remnawave-admin-credentials` with mode `0600`. Do not commit them.
- The `ArcVPN Staging Adapter` API token is stored only on the Germany server at
  `/root/ArcVPN/.env.remnawave-staging` with mode `0600`. Production XUI remains
  authoritative and no real ArcVPN user is written to Remnawave.
- The wCloud France test node is registered as `wCloud France Staging`, address
  `fr2.sfxu.ru`, control port `20139`, with TCP Reality `20140` and Hysteria2
  `20141`. The panel is reachable through the ArcVPN adapter, but the node will
  remain offline until its generated `SECRET_KEY` is pasted into wCloud.
- The generated wCloud `SECRET_KEY` was copied to the operator clipboard on
  2026-08-09. Never put it in Git or chat logs. Rotate the provided Reality
  private key before any production rollout.
- Staging readiness result before connecting the node:
  `{"ready": true, "panel": true, "node_online": false}`.
- Finland still shows high CPU steal and is unsuitable as the permanent panel
  location. Before production migration, move the control plane to a separate
  4 vCPU / 4 GiB VPS (minimum 2 vCPU / 2 GiB) and restore it from backup.

## Import bridge and node purchasing decision (2026-08-10)

- WebApp import must use the HTTPS `/import/<master_sub_id>` bridge. The bridge
  registers exactly one device, waits for `/api/device/import/<master_sub_id>`,
  and opens the returned one-level `/sub/<device_sub_id>?format=plain` Happ URL.
  Never replace the master subscription path with the browser device token and
  never pre-register the same click inside the Svelte WebApp.
- Chromium's reduced Android Client Hints can report the fake model `K`.
  One-character/generic models are normalized to the platform label `Android`.
- Current paid infrastructure: Germany Play2Go 340 RUB/month and Finland
  rdp-onedash 365 RUB/month (705 RUB/month total). On the last 24-hour window,
  Germany showed p10/p50 download 54.28/78.41 Mbps and CPU steal p95 0.09%;
  Finland showed 20.52/40.06 Mbps and CPU steal p50/p95 23.83/37.35%.
- wCloud cloud-1 staging is a 200 Mbps tier, not evidence for cloud-2. Its first
  15 hours produced p10/p50 download about 30.35/49.19 Mbps and HTTPS p95 about
  792 ms. Do not buy three wCloud nodes from this result or place every node at
  one provider.
- Approved purchase gate: first request a 24-72 hour cloud-2 trial; if refused,
  buy exactly one cloud-2 (200 RUB) as a paid canary. Keep Germany authoritative
  and keep Finland during the test. Promote only after end-to-end client/video
  tests and telemetry pass. A safe near-term target is Germany + two cloud-2
  nodes in distinct locations (740 RUB/month); this costs only +35 RUB/month
  versus today and retains a second provider for rollback.

## Payment UI and Remnawave colocation (2026-08-11)

- The subscription purchase screen presents the approved unified 500 GB quota.
  Do not expose the legacy 20 GB LTE add-on as a purchasable product: LTE usage
  is already part of the unified quota with the x10 weight. Generic traffic
  add-ons remain visibly unavailable until their billing and quota application
  are implemented end to end.
- Payment selection uses one consistent circular checked-state marker, while
  promo code and recurring-payment rows retain readable contrast on the dark
  ArcVPN surface. In Telegram payment keyboards, SBP is the primary/accented
  method; card and crypto buttons are shown only when their providers are
  actually configured.
- Official Remnawave documentation permits installing RemnaNode on the Panel
  server, but explicitly marks this topology as not recommended. It is suitable
  only for a low-load bootstrap or emergency node. Production traffic nodes
  should remain separate so Xray load or a network attack cannot take down the
  control plane, database, bot, and every subscription operation together.

## Poland control-plane migration (2026-08-11)

- The ArcVPN control plane was migrated from Germany/Finland to the dedicated
  Poland VPS `217.60.33.38` (`Omega-Tiger-6K0CCiSO.expresshost.cloud`). Never
  commit its SSH credentials; keep them only in the operator's secret storage.
- Active services on Poland: `arcvpn-bot.service`,
  `arcvpn-subscription.service`, nginx, and the Remnawave/PostgreSQL/Valkey
  Docker stack. The authoritative SQLite database was transferred with an
  integrity-checked final snapshot. Telegram polling and the public Mini App
  now run from Poland.
- Public subscription paths and user UUIDs did not change. Production VPN
  traffic still uses the existing XUI nodes until the separate Remnawave canary
  migration is approved; moving the control plane must never force users to
  re-import subscriptions.
- Germany `2.26.84.210` no longer runs the bot or subscription API. Its nginx
  remains a rollback proxy for `sub.arccnet.space` and `panel.arccnet.space` so
  clients with cached DNS continue reaching Poland.
- The old Remnawave containers on Finland `195.226.92.37` are stopped. Finland
  nginx remains a rollback proxy for `remna.arccnet.space`. The restored Poland
  panel reports the wCloud France staging node online.
- Migration backups are stored with mode `0600` under
  `/root/migration-backups` on Poland and on the source servers. Keep the old
  proxy origins for at least 48 hours after DNS changes, then retain them until
  payment, bot, WebApp, admin, subscription and node telemetry are confirmed.
- Target DNS after validation: `sub.arccnet.space`, `panel.arccnet.space`, and
  `remna.arccnet.space` A records all point to `217.60.33.38`. Certificate
  renewal must be checked after the DNS cutover.

## Zero-downtime Remnawave subscription migration (2026-08-11)

- Production is in a deliberate hybrid migration phase. Poland Remnawave is
  the new identity/control-plane target, while the existing Germany/Finland
  XUI profiles remain in the public subscription as rollback capacity. This is
  required until the replacement Germany RemnaNode and the LTE/CDN topology
  are ready; removing XUI earlier would silently remove working locations.
- Active ArcVPN users are synchronized into Remnawave every five minutes by
  `arcvpn-remnawave-user-sync.timer`. The synchronization preserves each
  existing VLESS UUID, expiry, traffic quota, Telegram ID and device limit, so
  users do not need to re-import their subscription.
- The unchanged public `/sub/<id>` response now appends two profiles served by
  the online wCloud France RemnaNode: `🇫🇷 Франция TCP ⭐` on port `20140` and
  `🇫🇷 Франция #2 ⚡` (Hysteria2) on port `20141`. Existing Germany, Finland and
  LTE profiles remain present. A production canary returned HTTP 200 and the
  expected France profiles after deployment.
- `sub.arccnet.space` and `panel.arccnet.space` were moved toward Poland
  `217.60.33.38`. During DNS propagation both the old Germany IP and Poland IP
  can be returned; Germany deliberately proxies to Poland. After at least 48
  stable hours, remove the old `2.26.84.210` A records so traffic no longer
  takes the compatibility hop.
- `remna.arccnet.space` does not need to be exposed to VPN clients. The old
  Finland nginx proxy currently forwards it to Poland and is sufficient for
  the migration. Before retiring Finland, either point that name directly to
  Poland or replace it with an explicitly private/internal panel endpoint and
  verify certificate renewal.
- Full Remnawave authority is complete only after all required replacement
  nodes and hosts exist, every public profile is generated from Remnawave, and
  XUI is retained through a measured rollback window. Never call the hybrid
  phase a completed XUI retirement.

## Happ auto profile and Remnawave presence (2026-08-13)

- The production subscription service on Poland must run commit `5513ebb` or
  newer. JSON imports contain a visible first profile `⚡ Автовыбор`, built as
  an Xray `burstObservatory` plus a `leastLoad` balancer. Plain subscriptions
  cannot represent this composite profile; users need a JSON import/re-import.
- The auto profile balances only normal Wi-Fi outbounds. LTE/CDN is deliberately
  excluded: latency alone cannot detect a mobile whitelist regime, and silently
  routing ordinary traffic through LTE would consume weighted x10 traffic.
- Remnawave `/api/users` exposes `userTraffic.onlineAt` and
  `lastConnectedNodeUuid`. The business console treats activity within three
  minutes as online and maps the node UUID to its RemnaNode name. Do not add
  Remnawave node counters together: one user can appear on more than one node.
- `194.186.130.21` is an unverified shared edge address suggested in a chat.
  Never hard-code it as the CDN resource address without confirming ownership,
  TLS/SNI behavior and operator-specific reachability. Prefer the CDN-assigned
  CNAME and use fixed edge IP only as a measured, reversible emergency route.

## Fleet monitoring, LTE fallback and notifications (2026-08-13)

- Production runs `arcvpn-fleet-monitor.timer` on Poland every 10 minutes. It
  reads only registered RemnaNodes, checks panel connectivity and TCP-based
  active inbound ports, stores 30 days in `node_diagnostic_runs`, and exposes
  the latest result in Business Console. Hysteria2 is UDP/QUIC and must never
  be declared down by a TCP-connect probe. The console also provides a bounded
  manual deep test for a selected registered node.
- Happ JSON subscriptions use LTE as a costly fallback only: normal outbounds
  participate in `leastLoad`/`burstObservatory`, while `lte_backup` is excluded
  from latency selection and referenced only by `fallbackTag`. The separate
  visible LTE profile remains an explicit emergency option. Existing live Xray
  connections may persist until reconnect; automatic fallback is not an
  instant migration mechanism.
- Subscription lifecycle messages are independent stages: three days left,
  one day left, and expired. Each stage has its own deduplication key, so an
  early warning can no longer suppress the urgent or expired notification.
  Expired wording says saved devices/settings remain and renewal does not
  require re-import.
- Exactly one Telegram polling instance is allowed. On 2026-08-13 the obsolete
  Germany `arcvpn-bot.service` was stopped and disabled after it was found
  competing with Poland (`getUpdates` conflicts). Poland is authoritative for
  bot commands, lifecycle notifications and payment reconciliation.

## Deterministic catalog and France reconnect (2026-08-14)

- `sub.arccnet.space` still resolves to both `2.26.84.210` and
  `217.60.33.38`. This caused the apparent random old/new subscription: two
  independent nginx origins served different deployed revisions. Both origins
  were synchronized to the same commit as an immediate compatibility fix.
  Remove the old Germany A record after DNS propagation so Poland is the only
  subscription authority; do the same for `panel.arccnet.space`.
- An unspecified subscription format now resolves to Happ JSON for both Happ
  and generic/browser clients. Explicit `?format=plain` and `?format=base64`
  remain available for other clients. The verified Happ catalog contains eight
  profiles: AutoSelect, France TCP, Finland TCP/Hysteria, Germany
  TCP/Hysteria, and two selectable LTE profiles.
- France Remnawave profile `f9e9b07f-2b9e-42e8-9b66-16d52642fd4d` now uses
  `vpbggjof6.vpvr4ib84nuv6hdkt.ru:443`, Reality port `20086`, short ID
  `e1609bc5259a2c3f`, and no Hysteria inbound. The control address is
  `vpbggjof6.vpvr4ib84nuv6hdkt.ru:20085`. A new RemnaNode secret was generated
  and stored only on Poland at `/root/ArcVPN/.secret.remnanode-france` (0600);
  it must be pasted into wCloud together with panel IP `217.60.33.38`.

## Single subscription authority and Business Console (2026-08-14)

- Poland (`217.60.33.38`) is the only subscription/database authority. The old
  Germany origin (`2.26.84.210`) must not run its own subscription API: its
  nginx endpoint transparently proxies requests to Poland. This prevents
  alternating device-limit decisions while both DNS A records still exist.
  The old Germany `arcvpn-subscription.service` is disabled.
- A blocked Happ JSON response must always be a JSON array of three complete,
  visibly named profiles. A single object with `remarks: ArcVPN` is invalid for
  this purpose because Happ renders it as one unexplained empty server.
- Business Console uses the ArcVPN dark-blue palette. Health, connection
  schemes, nodes, security, backups and settings are separate views, not
  duplicated copies of one readiness screen. Do not expose dead controls:
  every visible action must navigate, filter, diagnose, reply, refresh, or
  perform a real server-side operation.
- `/api/admin/backups` lists and creates local SQLite backups using the SQLite
  backup API, verifies each new copy with `PRAGMA quick_check`, and stores it in
  `/root/ArcVPN/backups` with mode 0600.
- Happ JSON profiles are standalone Xray configurations. Russian split routing
  must therefore be embedded into every regular profile and AutoSelect profile;
  the legacy `happ://routing` header alone does not affect JSON imports. Direct
  rules include configured RU geo-assets plus explicit `.ru`/`.su`/`.xn--p1ai`
  and major Russian-service domain fallbacks, followed by the proxy rule.

## Remnawave provisioning incident and France Hysteria (2026-08-20)

- New-user provisioning failed because `REMNAWAVE_SQUAD_INBOUND_UUIDS` retained
  UUIDs of removed inbounds. Remnawave returned `Update internal squad error`
  before the sync loop, so new ArcVPN users received syntactically valid links
  but were absent from Remnawave and rejected by every node.
- `scripts/sync_remnawave_users.py` must never let squad-topology reconciliation
  block user provisioning. Squad errors are operator warnings; every user is
  synchronized independently and one bad legacy record cannot stop the batch.
  The production reconciliation timer runs every minute so a new identity is
  not left with valid-looking but unauthorized node links for five minutes.
- Production squad now contains seven live inbounds. A full reconciliation
  selected and verified all 14 active ArcVPN identities, including subscription
  `IhiMk6JyzqhXDedn0-1SI5EcJBtC_xkQ`.
- Production France profile `f9e9b07f-2b9e-42e8-9b66-16d52642fd4d` now exposes
  TCP Reality on `20086` and Hysteria2 on `20087`. Public connection metadata
  must match the current wCloud profile; private Reality keys stay outside Git.

## Next-chat handoff (2026-08-20)

- `NEXT_CHAT_HANDOFF.md` is the concise entry point for the next Codex chat.
  Read it before targeted searches in this file; do not reconstruct the project
  by scanning thousands of files.
- Next priorities: canary and 72-hour evaluation of one Vyrex Netherlands node;
  architecture/security/license audit of the BEDOLAGA Telegram bot and cabinet;

## BEDOLAGA audit and Vyrex preparation (2026-08-20)

- Read-only audit pinned BEDOLAGA bot `49b05d5` (v4.1.0) and cabinet `2192484`.
  Bot is MIT plus Commons Clause, not plain MIT; cabinet is AGPL-3.0. Do not copy code
  into commercial closed ArcVPN without written permission/license review. The approved
  approach is independent implementation of selected patterns; see
  `docs/BEDOLAGA_AUDIT_2026-08-20.md`.
- Highest-value independent adaptations: server-side RBAC, append-only admin audit,
  broadcast job queue, payment health, signed/deduplicated Remnawave webhook inbox,
  backup verification and squad migration preview. Stable ArcVPN subscription URLs,
  UUIDs, device slots and current payment history remain authoritative.
- Vyrex Netherlands must start as an isolated synthetic canary. The 72-hour report now
  includes latency p50/p95, explicit evening metrics and fail-closed missing-metric gates.
  Access/install steps and production/reserve/reject criteria are documented in
  `docs/VYREX_NETHERLANDS_CANARY_RUNBOOK.md`.
- Local cleanup inventory is `docs/LOCAL_CLEANUP_INVENTORY_2026-08-20.md`. Unknown/user
  files were not deleted. A local diagnostic file and older tracked history contain
  credentials; rotate and sanitize them before any cleanup commit that touches secrets.
- Owner cancelled Vyrex on 2026-08-20. A one-day reseller trial at `159.200.230.224`
  was advertised as Hetzner, but live routing identifies AS58212 dataforest GmbH,
  Frankfurt. Baseline hardware is 1 vCPU, 2 GiB RAM and 20 GiB disk. It is telemetry-only:
  no Remnawave profile/squad/user exposure until a hostname and a successful gate exist.
- Owner approved deletion of the classified local obsolete/unknown candidates. Only the
  verified unused root assets, intermediate images, operator draft, tooling config and
  historical VLESS diagnostic were removed; final `*-v2.png` runtime assets remain.
- Dataforest trial node-agent was installed and started on 2026-08-20. Production accepts
  the host through `NODE_INVENTORY`; the first stored agent sample had 0% loss, 0.1 ms
  jitter, 0.96 ms latency, 0% steal and 158.65 Mbps. YouTube/Instagram/Gemini were
  reachable, while Claude returned HTTP 403. The node remains telemetry-only and its
  `degraded` state is expected until a VPN runtime exists. Do not expose it to users yet.
- Owner-only isolated test transports were installed on the Dataforest trial: VLESS TCP
  Reality and Hysteria2 UDP both use port 443 (different transports). Their temporary import links are only
  in ignored local `.secrets/test-node-access.txt`; never commit or paste them into logs.
  Both passed real SOCKS-to-YouTube HTTP 204 tests and returned active after reboot into
  kernel 5.15.0-190. They are not connected to Remnawave or public subscriptions.
- Telegram daily server reports and the admin server drill-down now read authoritative
  live Remnawave nodes/user totals. Historical `servers` rows are not fleet telemetry.
- The obsolete `arcvpn-xui-guard.timer` is disabled on the old Germany proxy. Keep
  `x-ui.service` only as a temporary rollback transport; it must not reconcile users or
  send Telegram notifications.
- BEDOLAGA-inspired admin hardening is implemented independently: migration v49 adds
  append-only `admin_audit_events` with database triggers blocking update/delete. Login,
  logout, node diagnostics, backup creation and support replies create bounded events.
- Happ JSON AutoSelect uses a two-stage Xray balancer: regular `proxy-main-*` leastLoad
  falls back through `LOOPBACK_TO_BACK`/`FROM_LOOPBACK_BACK` into the LTE-only
  `proxy-back-*` leastLoad balancer. LTE remains outside the main selector and is used
  only when normal candidates fail; the second balancer falls back to direct.
- LTE outbounds remain available as explicit manual Happ profiles at the owner's request,
  but are not included in burstObservatory. AutoSelect's LTE fallback uses roundRobin
  without background probes. A manually selected LTE profile always consumes CDN traffic;
  AutoSelect consumes it only after all observed main candidates fail.
- Business Console RBAC migration v50 supports owner/operator/support/finance/viewer.
  Permission checks are server-side; configured admins default to owner, explicit Telegram
  assignments can downgrade/grant access, and denied actions are appended to audit.
- Broadcast migration v51 replaces the volatile inline send loop with persistent jobs and
  per-recipient delivery state. The bot worker resumes interrupted campaigns after restart
  and sends the initiating admin a final sent/blocked/failed summary.
- The dhost Germany VPS at `193.233.198.184` is registered as `ArcVPN Germany DHost`
  with its own Remnawave profile and Reality keypair. Its public TCP Reality contract was
  changed on 2026-08-20 to port 443 and `google.com` SNI/target while
  preserving the existing private/public keypair and inbound UUID. The previous Germany
  node remains enabled and is customer-labelled `Германия (Резерв)`. The post-reboot
  outage was caused by two control-plane issues: UFW did not allow the current Remnawave
  source to management port 22300, and the node had lost its active config-profile/inbound
  assignment. Both were repaired on 2026-08-20; the node returned connected/enabled,
  loaded 16 users, listened publicly on 443, and a real VLESS Reality tunnel reached
  YouTube with HTTP 204. Keep management port 22300 restricted to control-plane IPs.
  An empty Reality short ID worked with Xray but was replaced with a normal 16-hex short
  ID for Happ compatibility; the native and fallback subscription links must both include
  the same `sid` value.
- On 2026-08-21 the affected Happ builds were confirmed to require `firefox` or `edge`
  fingerprints on the failing mobile routes. Remnawave Hosts for DHost Germany and LTE
  were changed from `chrome` to `firefox`, and native VLESS links are normalized likewise.
  Native Remnawave XHTTP links omit ArcVPN's required `xPadding*` transport extension, so
  the Arc wrapper injects the same `extra` JSON used by the stable legacy generator. The
  dead old-Germany node and its TCP/HY2 Hosts, plus the obsolete German LTE Host, are
  disabled rather than deleted; only the Finland LTE CDN origin remains published.
- The old production host `2.26.84.210` became unreachable on 2026-08-21 (SSH,
  RemnaNode management and VPN transports all time out). The fallback generator now keeps
  its reserve profile disabled by default and publishes only the Finland LTE origin. DNS
  still had a stale `sub.arccnet.space -> 2.26.84.210` A-record beside the live
  `217.60.33.38`; remove the stale Reg.ru record because it makes subscription refreshes
  fail nondeterministically.
- The initial dhost Reality failure was not networking or Happ: the declarative
  `REMNAWAVE_SQUAD_INBOUND_UUIDS` list still had seven entries, so reconciliation removed
  the new inbound from the production squad and no user UUIDs reached the node. Production
  env now declares eight inbounds; a real Xray/SOCKS test through dhost to YouTube returned
  HTTP 204 after reconciliation. Keep the env list updated whenever adding an inbound.
  then a classified, reversible cleanup of the local workspace.
- Existing untracked assets, diagnostics and local files belong to the owner
  until classified. Never mass-delete them or treat `git status` as permission.
- BEDOLAGA-style native Remnawave subscription sourcing was added behind the unchanged
  ArcVPN `/sub/<id>` contract. Device enforcement, headers, Happ JSON/AutoSelect and the
  legacy generator remain local; panel URL/body caches are bounded and every native
  failure fails open to the working generator.
- Production canary on 20 August 2026 found Remnawave's native subscription credentials
  did not initially match the active user's panel VLESS UUID. Root cause: Remnawave had
  no Hosts attached to the user's internal-squad inbounds and returned four dummy
  `0.0.0.0:1` notice links. The Hosts catalog was rebuilt for all eight squad inbounds
  (including two LTE hosts), and one stale DHost inbound UUID in the production env was
  replaced. The squad now has eight valid inbounds; native output has nine real links
  with matching VLESS/Hysteria2 credentials. Keep the credential and real-endpoint gate:
  any topology drift must fail open to the stable ArcVPN generator.
- On 2026-08-21 DHost Germany gained a second inbound, native Hysteria2 on UDP/443,
  without changing the existing TCP Reality inbound or user identities. DHost filters
  inbound ACME HTTP-01 and TLS-ALPN-01, so Hysteria2 uses a long-lived self-signed
  leaf certificate (`CA:FALSE`) with mandatory `pinnedPeerCertSha256` and
  `verifyPeerCertByName=de.arccnet.space`; never replace this with `allowInsecure`.
  The current Xray `26.7.28` includes the certificate-pinning security fix. The new
  inbound is attached to the production squad and declared in
  `REMNAWAVE_SQUAD_INBOUND_UUIDS`; reconciliation verified nine inbounds. A real Xray
  client tunnel through German Hysteria2 reached the public 204 endpoint successfully.
- Target Finland retirement topology: Germany and Netherlands each use one normal
  RemnaNode (`consumptionMultiplier=1`) for TCP Reality plus Hysteria2, and a separate
  LTE RemnaNode (`consumptionMultiplier=10`) for XHTTP `packet-up`. LTE Hosts stay out of
  burstObservatory/main AutoSelect and require distinct CDN resources/hostnames; the
  direct `de.arccnet.space` and `nd.arccnet.space` A-records are not CDN endpoints.
  Netherlands remains canary-only until SSH authentication, node connection, squad/Host
  assignment and real TCP/Hysteria tests pass. Do not retire Finland before both normal
  and LTE replacement gates pass.
- On 2026-08-21 the DHost Netherlands VPS at `193.233.82.42` passed the normal-node
  admission gate. It runs RemnaNode 3.1.1 with TCP Reality and Hysteria2 on TCP/UDP 443;
  management port 22400 is restricted to the Polish control plane. Both unique inbounds
  are attached to the production squad and their Remnawave Hosts are enabled. Real Xray
  client tunnels built from an active user's native subscription reached the public 204
  endpoint through both transports. Planning capacity remains a conservative 1 Gbit/s
  despite the advertised shared 10 Gbit/s uplink. This admits only the normal Netherlands
  node; Netherlands LTE still requires a separate x10 node and CDN hostname before Finland
  can be retired.
