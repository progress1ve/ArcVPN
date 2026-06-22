# План переезда `xui.py` на 3x-ui v3.0.0

> Документ-план (без реализации). Цель — портировать `bot/services/panels/xui.py`
> под API 3x-ui **v3.0.0**, сохранив обратную совместимость с **v2.9.x** на время
> переезда. Текущий прод стоит на v2.9.4; код уже работает с ним.

## 0. Контекст и почему это нужно

Сейчас `xui.py` написан под v2.x API (`/panel/api/inbounds/*`). В v3.0.0 client-API
переехал и получил **нативную мульти-inbound** модель (`InboundIds`), что напрямую
упрощает нашу фичу «одна подписка = все inbound» (см. `MIGRATION_AND_SCALING.md` и
реализованный зеркалирующий провижининг в `provision_client_all_inbounds`). После
переезда зеркалирование вручную станет не нужно — клиент создаётся сразу в списке
inbound одним вызовом.

## 1. Ключевые отличия v2.9.x → v3.0.0

| Область | v2.9.x (сейчас) | v3.0.0 |
|---|---|---|
| CSRF | Только на `/login` (уже реализовано: `_fetch_csrf_token`) | CSRF-токен **на всех** изменяющих запросах (`x-csrf-token`) |
| `settings`/`streamSettings` | JSON-строка | Уже **dict** (распарсено). У нас закрыто `_as_obj()` |
| Создание клиента | `POST /panel/api/inbounds/addClient` (тело: `{id, settings:"{clients:[...]}"}`) | `POST /panel/api/clients/*` с `ClientCreatePayload` и **`InboundIds: [..]`** (множественное) |
| Обновление клиента | `POST /panel/api/inbounds/updateClient/{id}` | client-эндпоинты `/panel/api/clients/*` |
| Удаление | `POST /panel/api/inbounds/{ib}/delClient/{id}` | client-эндпоинт |
| Список inbound | `GET /panel/api/inbounds/list` | вероятно тот же (проверить) |
| onlines / clientIps | `POST /panel/api/inbounds/onlines`, `.../clientIps/{email}` | проверить путь |

> ⚠️ Точные схемы `ClientCreatePayload` и пути `/panel/api/clients/*` **нужно
> сверить с исходниками** установленной версии (`web/controller`, `web/service`)
> или Swagger панели перед реализацией — таблица выше составлена по обсуждению и
> подлежит верификации.

## 2. Стратегия совместимости (v2 и v3 одновременно)

Не делать «большой разрыв». Поддержать обе версии в одном клиенте:

1. **Детект версии** при `login()` / первом запросе:
   - `GET /panel/api/server/status` или специальный `version`-эндпоинт; либо
     эвристика: пробный вызов нового client-эндпоинта → при 404 считаем v2.
   - Кэшировать `self._api_version` ("v2"|"v3") на время сессии.
2. **Тонкий слой эндпоинтов**: вынести пути и форму тела в методы-адаптеры,
   например `self._ep_add_client(...)`, `self._ep_update_client(...)`,
   `self._ep_del_client(...)`, которые внутри ветвятся по `self._api_version`.
   Бизнес-логика (`provision_client_all_inbounds`, `update_client_full`, ...) их
   вызывает, не зная про версию.
3. **CSRF**: текущий `_request` уже добавляет `x-csrf-token`, если токен получен.
   Для v3 убедиться, что токен получается на каждой сессии и обновляется при 403
   (ветка 403 в `_request` уже есть).

## 3. Маппинг методов `xui.py` (что трогаем)

| Метод | Действие при переезде |
|---|---|
| `login` / `_fetch_csrf_token` | Оставить; проверить, что токен принимается на write-эндпоинтах v3 |
| `get_inbounds` | Сверить путь; `_as_obj` уже снимает разницу dict/str |
| `provision_client_all_inbounds` | **Главный выигрыш**: для v3 — один вызов `addClient` с `InboundIds=[все поддерживаемые]`. Для v2 — текущий цикл по inbound. Спрятать в `_ep_add_client` |
| `add_client` | Перевести на `_ep_add_client` (один inbound = `InboundIds:[id]`) |
| `update_client_full` / `update_client_limit` / `extend_client_expiry` | Перевести на `_ep_update_client`; в v3 обновление по client-id может затрагивать все его inbound нативно (проверить) — тогда фан-аут не нужен |
| `delete_client` | Перевести на `_ep_del_client` |
| `reset_client_traffic` | Сверить путь reset в v3 |
| `get_all_client_configs` / `_build_client_config` | Логика та же (читаем inbounds + clients). Проверить, что `clients`/`settings` структура совпадает |
| `get_online_emails` / `get_client_ips` / `get_online_clients_count` | Сверить пути onlines/clientIps |
| `get_database_backup` | Сверить эндпоинт getDb |

## 4. Влияние на остальной код

- `bot/services/vpn_api.py` (`push_key_to_panel`, `disable_key_on_panel`,
  `restore_key_traffic_limit`, `extend_key_on_server`) — **без изменений**: они
  ходят через методы `XUIClient`, версия скрыта внутри.
- `subscription_api.py` — без изменений (использует `get_all_client_configs`).
- Создатели ключей (`billing.py`, `trial.py`, `users_keys.py`, миграционные
  скрипты) — без изменений (используют `provision_client_all_inbounds`).
- Генератор ссылок `key_generator.py` — без изменений.

## 5. Порядок работ

1. Поднять тестовый стенд 3x-ui v3.0.0 (отдельный VPS/порт), создать VLESS +
   Hysteria2 inbound.
2. Снять с исходников/Swagger точные пути и схемы `/panel/api/clients/*`,
   `ClientCreatePayload`, формат `InboundIds`, reset/onlines/clientIps.
3. Реализовать детект версии + адаптеры `_ep_*` (ветвление v2/v3).
4. Прогнать сценарии (раздел 6) на тестовом стенде, затем на копии прод-данных.
5. Выкатить; первое время держать v2-ветку как фолбэк, пока все ноды не на v3.

## 6. Тест-план (на тестовом стенде v3)

1. `login` + получение CSRF; повторный запрос после 403 (протух токен) восстанавливается.
2. `provision_client_all_inbounds` → клиент создан сразу во всех inbound одним вызовом (`InboundIds`), один uuid/email.
3. Подписка `/sub/<sub_id>?format=plain` отдаёт VLESS + Hysteria2 строки, имена из remark.
4. Продление (`push_key_to_panel`) меняет срок во всех inbound; отключение истёкшего — во всех.
5. `delete_client` удаляет клиента из всех inbound.
6. `get_online_emails`/`get_client_ips` — детект устройств работает.
7. Бэкап БД панели скачивается.
8. Регресс на ноде, оставшейся на v2.9.x: всё то же самое через v2-ветку адаптеров.

## 7. Откат

- Версия определяется per-session; если v3-ветка падает — временно форсировать
  v2-пути через env/конфиг-флаг (`XUI_FORCE_API_VERSION`), не откатывая код.
- Полный откат — `git revert` коммита переезда; методы `XUIClient` и их сигнатуры
  не меняются, поэтому остальной код не затрагивается.

## 8. Риски

- Точные схемы v3 не подтверждены документально — обязательна сверка с исходниками
  до реализации (раздел 1 помечен ⚠️).
- В v3 обновление/удаление может быть «по client-id глобально», а не по inbound —
  если так, наш ручной фан-аут (`update_client_full`) для v3 надо отключить, иначе
  лишние запросы. Решается внутри адаптеров.
- Hysteria2 в v3 может иметь иную форму клиента — проверить на стенде.
