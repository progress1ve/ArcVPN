# ArcVPN: безопасный staging Remnawave

## Фактическое состояние стенда на 2026-08-09

- [x] Панель установлена на временном control-plane `195.226.92.37` и доступна
  по `https://remna.arccnet.space` с Let's Encrypt и автоматическим продлением.
- [x] PostgreSQL, Redis и Remnawave Backend 3.2.1 healthy; API отвечает через
  HTTPS. Метрики не опубликованы наружу.
- [x] Созданы отдельный администратор и API-токен `ArcVPN Staging Adapter`.
  Секреты хранятся только на серверах в файлах `0600`, не в Git.
- [x] Создан профиль wCloud с TCP Reality `20140` и Hysteria2 `20141`.
- [x] Создана нода `wCloud France Staging`, `fr2.sfxu.ru:20139`, профиль
  привязан к обоим inbound.
- [x] ArcVPN staging adapter успешно читает панель: `ready=true`,
  `panel=true`; production XUI и реальные пользователи не затронуты.
- [ ] Вставить сгенерированный `SECRET_KEY` в wCloud Console. До этого
  `node_online=false` и `ECONNREFUSED` являются ожидаемым состоянием.
- [ ] После подключения ноды создать staging host/internal squad, выполнить
  synthetic lifecycle, клиентские тесты и начать 72-часовой мониторинг.
- [ ] Перед production заменить тестовый Reality private key и перенести
  control-plane с перегруженной Финляндии на отдельный VPS 4 vCPU / 4 GiB.


## Статус подготовки на 2026-08-09

- [x] единая фабрика панелей: существующие записи без `panel_type` остаются на XUI;
- [x] миграция БД v46 для URL/token/node/squad и режима записи Remnawave;
- [x] официальный Bearer API-клиент Remnawave для users, nodes, traffic, expiry и device limit;
- [x] fail-closed запись: `disabled` по умолчанию, `shadow` только для `arc-staging-*`;
- [x] автоматическая проверка `scripts/remnawave_staging_check.py`;
- [x] контрактные тесты фабрики и защитного режима;
- [ ] получить staging Panel URL, API token, internal squad UUID и RemnaNode UUID;
- [ ] прогнать синтетический lifecycle и 72-часовой тест ноды;
- [ ] canary 2–5 добровольцев; production cutover запрещён до прохождения критериев ниже.

Откат до canary — оставить `panel_type=xui`. Во время canary — вернуть выбранным
записям `panel_type=xui` и очистить кэш клиентов; публичные URL ArcVPN при этом не меняются.

## Главный контракт миграции

Пользователь не должен повторно импортировать подписку. Публичный адрес
`https://sub.arccnet.space/sub/<sub_id>` обслуживает ArcVPN Subscription API и не меняется при
смене панели. До переключения сохраняются UUID клиентов, Reality public/private key, short ID,
SNI, домены, порты и параметры транспортов. Remnawave не становится публичной subscription
страницей ArcVPN.

## Что готовим до получения RemnaNode

1. Отдельная staging-панель и отдельная база без доступа к production SQLite.
2. Два синтетических пользователя и отдельные UUID, которых нет у клиентов.
3. Профили XHTTP Reality и TCP Reality с теми же параметрами, что у production.
4. Адаптер ArcVPN для чтения пользователей, трафика, статуса нод и конфигураций через API.
5. Shadow-sync: запись тестового пользователя одновременно в 3x-ui и Remnawave, но выдача
   пользователю остаётся только из 3x-ui.
6. Автоматический отчёт `monitoring/compare_node_quality.py` и независимый node-agent.
7. Rollback одним флагом источника панели, без изменения URL подписки.

## Трёхдневный тест без production

RemnaNode подключается только к staging Panel. На ней нет реальных пользователей. Проверяются:

- запуск/перезапуск Node и Xray, восстановление после reboot и потери связи с Panel;
- XHTTP Reality и TCP Reality на тестовых портах и доменах;
- импорт отдельной тестовой подписки в Happ на Android, iOS и Windows;
- сохранение порядка и remark подключений;
- packet loss, jitter, DNS, HTTPS, CPU steal и контрольная скорость каждые 10 минут;
- однопоточная и многопоточная загрузка, YouTube/Instagram в часы пик;
- учёт обычного трафика ×1 и LTE ×10;
- выключение пользователя, продление, сброс трафика и превышение лимита;
- недоступность Panel: уже выданный VPN продолжает работать;
- возврат на staging 3x-ui без повторного импорта.

## Критерии допуска к canary

- минимум 95% ожидаемых проб за 72 часа;
- packet loss p95 не выше 1%, jitter p95 не выше 20 мс;
- CPU steal p95 не выше 5%;
- контрольная загрузка p10 не ниже 100 Мбит/с и без длительных вечерних провалов;
- все операции пользователя идемпотентны;
- существующий ArcVPN URL выдаёт эквивалентный набор подключений;
- учебный rollback выполнен успешно.

После этого Remnawave можно показать 2–5 добровольным canary-пользователям. Переход выполняется
ступенями 5% → 25% → 50% → 100%; 3x-ui не удаляется до двух недель стабильной работы.

## Стоп-факторы текущего кода

- `subscription_api.py` напрямую создаёт `XUIClient`;
- `vpn_api.test_server_connection()` всегда создаёт `XUIClient`, игнорируя `panel_type`;
- scheduler напрямую правит `/etc/x-ui/x-ui.db` для восстановления `enable`;
- Hysteria2 не входит в Xray/Remnawave и должен остаться отдельным управляемым сервисом;
- LTE ×10 нужно сверить по фактическим счётчикам, а не только по UI коэффициента.

Эти зависимости устраняются до подключения реальных пользователей, но не требуют аренды Node.
