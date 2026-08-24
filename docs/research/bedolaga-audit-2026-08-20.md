# ArcVPN: аудит BEDOLAGA

Дата среза: 2026-08-20.

Проверенные upstream revisions:

- `remnawave-bedolaga-telegram-bot`: `49b05d5ab79dd9bb92f0404bb0066cda8a175649` (v4.1.0);
- `bedolaga-cabinet`: `2192484b011068d8cb75c61a6aeaada1d06115aa`.

Аудит read-only. Исходный код BEDOLAGA в ArcVPN не копировался.

## Итог

BEDOLAGA нельзя использовать как drop-in замену ArcVPN. Bot существенно шире по
продуктовым функциям, но его лицензия — MIT с Commons Clause, запрещающей продажу
сервиса, ценность которого существенно происходит из программы. Cabinet находится
под AGPL-3.0: модифицированная сетевая версия требует предоставления соответствующего
исходного кода пользователям. Для коммерческого закрытого ArcVPN безопасны только
независимая реализация общих идей и API-контрактов либо отдельное письменное разрешение
правообладателя.

Технически разумная стратегия: сохранить ArcVPN как authority над стабильными
subscription URL, UUID, устройствами и платежной историей; адаптировать небольшими
независимыми модулями RBAC, audit log, backup verification, broadcast queue и
Remnawave migration preview.

## Архитектура и актуальность

| Область | BEDOLAGA | ArcVPN | Вывод |
|---|---|---|---|
| Backend | Python 3.13, FastAPI, aiogram 3, SQLAlchemy/Alembic, PostgreSQL/SQLite, Redis | Python, aiogram, Flask subscription API, SQLite | BEDOLAGA лучше масштабируется, но полная миграция слишком рискованна |
| Frontend | React/Vite/TypeScript, отдельный cabinet | Svelte WebApp и Business Console в одном продукте | Не заменять; брать UX-паттерны независимо |
| Releases | Активный v4.1.0, частые релизы и тесты | Небольшой продуктовый репозиторий | Следить за upstream, не автоматически обновлять |
| Deployment | Docker Compose | systemd + Remnawave containers | Текущий ArcVPN проще; контейнеризация не является самоцелью |
| Database | PostgreSQL preferred, Redis для transient state | SQLite authority | PostgreSQL рассматривать при росте, не мигрировать ради аудита |

## Функциональная матрица

| Компонент | Уже есть в ArcVPN | У BEDOLAGA лучше | Решение |
|---|---|---|---|
| Remnawave users | Сохранение UUID, expiry, traffic, device limit; минутный reconciliation | Полный CRUD, auto-sync, несколько auth modes | Адаптировать только health/recommendation UX; authority ArcVPN не менять |
| Nodes/inbounds/squads | Fleet monitor, node agent, declarative squad inbound UUID | Обзор nodes, realtime stats, actions, migration preview, GeoCheck | Взять идею read-only preview и отдельные permissions; destructive actions делать two-step |
| Stable subscriptions | Собственный стабильный URL и device slots | Типовые Remnawave subscription modes | Оставить ArcVPN: это критическое преимущество и контракт миграции |
| Device lifecycle | Управляемые device subscription IDs и release | Более общий device UI/webhook events | Сравнить webhook events, не заменять проверенную модель Happ |
| Payments | YooKassa, Stars, crypto, recurring cycles, idempotent orders | Больше провайдеров, Apple IAP, balance/cart, payment health | Адаптировать payment health и reconciliation dashboard; новые провайдеры только по спросу |
| Statistics | Users, revenue, traffic, presence, node telemetry | Sales funnels, top consumers, detailed traffic filters | Адаптировать агрегаты и фильтры без копирования UI/кода |
| Broadcasts | Targeted broadcasts и admin selection | Persistent queue, progress/cancel, campaigns | Высокий приоритет: независимо реализовать queue + immutable audience snapshot |
| Support | Один thread/user, rate limit, admin reply | Tickets, statuses, assignment, cabinet workflow | Адаптировать ticket state/assignment, сохранив простую Telegram доставку |
| Admin access | Telegram admin session and fixed admin IDs | RBAC permissions throughout cabinet | Высокий приоритет: роли viewer/support/finance/operator/owner и server-side checks |
| Audit | События частично видны в логах/БД | Более развитые admin surfaces, но полноту audit trail надо проверять отдельно | Реализовать append-only audit для destructive/admin/payment действий |
| Backups | Production backups и UI статуса | API create/list/download/upload/restore + background tasks | Взять lifecycle/status, но restore оставить offline/two-person operation |
| Referrals/promos | Реферальные дни, промокоды | Campaigns, coupons, gifts, partner network, wheel | Campaigns/coupons можно адаптировать; wheel и gamification сейчас лишние |
| Notifications | Expiry, payment, traffic, first connection | Remnawave webhook matrix и preferences | Адаптировать подписанные webhook events с deduplication |
| Content/legal | Agreement and policy foundation | News, info pages, recurrent/IAP flows | Legal тексты не заимствовать; CMS нужен только после завершения реквизитов ArcVPN |

## Матрица решений

### Стоит адаптировать независимо

1. RBAC с серверной проверкой каждого permission.
2. Preview/plan перед миграциями squads и массовыми изменениями.
3. Persistent broadcast jobs: snapshot аудитории, progress, cancel, retry и deduplication.
4. Payment health и reconciliation по провайдерам.
5. Ticket states, assignment и SLA timestamps.
6. Backup jobs с checksum, off-host copy и регулярным restore drill.
7. Подписанные Remnawave webhooks с timestamp/replay protection и idempotency key.
8. Read-only top consumers и per-node traffic views.

### Уже достаточно хорошо в ArcVPN

- стабильные публичные URL и UUID при смене панели/нод;
- device-bound импорт Happ и освобождение устройств;
- Remnawave reconciliation с fail-open user sync;
- node-agent, fleet monitoring и отдельные TCP/UDP transport checks;
- staged lifecycle уведомлений;
- LTE как дорогой fallback, исключённый из обычного балансировщика;
- простой rollback на старые origins без повторного импорта.

### Не переносить

- полную БД/ORM модель и миграцию пользователей одним cutover;
- frontend cabinet целиком (AGPL и несовместимый UX/runtime);
- backup upload/restore из обычной admin-сессии без отдельного approval;
- restart-all nodes как однокнопочное действие;
- wheel/gamification, Apple IAP и множество платёжных провайдеров без product need;
- режим физического удаления Remnawave users по умолчанию;
- секреты или subscription endpoints из `.env.example` без собственного threat model.

## Security review

Положительные наблюдения:

- SQLAlchemy и параметризованные запросы уменьшают риск SQL injection;
- bcrypt/JWT и отдельная проверка Telegram init data присутствуют;
- Remnawave webhook поддерживает HMAC-SHA256 shared secret;
- API routes используют security dependencies;
- есть throttling/rate-limit utilities и security policy;
- payment idempotency покрыта тестами;
- backup paths resolve-ятся и проверяются перед доступом.

Риски, требующие проверки перед заимствованием идеи:

1. Проверка пути через строковый `startswith` недостаточна как общий паттерн
   (`/backup-a` имеет префикс `/backup`); нужен `Path.is_relative_to()`.
2. Upload/restore backup — высокорисковая поверхность: нужны лимит размера до чтения
   файла, безопасное извлечение archive members, checksum/signature, CSRF/re-auth,
   отдельное разрешение и audit event.
3. JWT должен фиксировать допустимый algorithm, issuer, audience, expiry и token type;
   frontend route guards не заменяют backend authorization.
4. HMAC webhook должен проверять timestamp и replay window, а event ID — храниться для
   идемпотентности. Одной подписи тела недостаточно против повторной доставки.
5. URL Remnawave, OAuth endpoints и remote assets должны иметь allowlist/blocked private
   ranges, чтобы административные настройки не стали SSRF.
6. Node restart/toggle/restart-all и squad migration требуют step-up auth, preview,
   bounded concurrency и rollback; обычного bearer token недостаточно.
7. Redis throttling должен fail closed для auth/payment/admin endpoints и иметь доверенную
   схему client IP за reverse proxy.
8. Логи и rich error reports не должны содержать API keys, payment payloads, init data,
   subscription URLs или JWT.

## План внедрения идей

1. Append-only `admin_audit_events` и RBAC — сначала read-only roles.
2. Broadcast job queue с тестом на одном admin account.
3. Backup inventory/checksum/off-host verification без remote restore.
4. Remnawave webhook inbox с signature, timestamp и dedupe, сначала shadow mode.
5. Ticket statuses/assignment.
6. Sales/payment health и traffic analytics.

Каждый модуль внедрять отдельным коммитом и feature flag, с миграцией только вперёд,
backup БД, contract tests и проверенным rollback.
