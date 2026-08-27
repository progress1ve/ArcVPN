# ArcVPN: добавление нод и профилей из админ-панели

Цель следующего инфраструктурного этапа — безопасно создавать ноду и публиковать
её профиль без ручной правки `subscription_api.py`. Текущая панель редактирует
только продуктовый порядок уже известных профилей и не притворяется системой
provisioning.

## Поток оператора

1. Создать черновик ноды: страна, провайдер, публичный адрес, роль main/LTE,
   желаемые протоколы и лимиты.
2. Панель выдаёт одноразовую короткоживущую команду enrolment. Постоянные ключи и
   токены в UI не показываются.
3. Агент сообщает ОС, ресурсы, сеть и занятые порты. Preflight проверяет DNS,
   TLS, firewall, время, Docker и доступность панели.
4. Оператор видит dry-run: какие Remnawave Node/Host/inbound/squad и локальные
   сервисы будут созданы. Применение требует отдельного подтверждения.
5. После установки выполняются реальные TCP/UDP/tunnel probes и canary на одном
   тестовом пользователе. Только успешный canary разрешает Publish.
6. Публикация добавляет профиль в единый versioned catalog; plain, base64 и Happ
   строятся из одного snapshot. UUID и URL существующих пользователей не меняются.

## Контракт данных и API

- `managed_nodes`: desired state, фактическое состояние, версия агента,
  heartbeat и последняя ошибка без секретов.
- `managed_profiles`: node, Remnawave host/inbound UUID, protocol, transport,
  product role, display label, order, enabled и canary status.
- `POST /api/admin/nodes/preflight`, `/enrolment`, `/apply`, `/canary`, `/publish`;
  mutation endpoints идемпотентны и пишут audit event.
- Каталог получает server-generated revision и optimistic lock: нельзя затереть
  параллельное изменение устаревшей формой.

## Обязательные защиты

- Раздельные permissions для просмотра, provisioning и публикации.
- Secret vault, короткоживущие enrolment tokens, allowlist панели и ротация.
- Нельзя удалить последнюю рабочую main-ноду или опубликовать непроверенный
  протокол. Retire — отдельный drain-процесс с preview активных пользователей.
- Rollback возвращает предыдущий catalog revision и desired state, но не вращает
  пользовательские UUID и subscription URL.
