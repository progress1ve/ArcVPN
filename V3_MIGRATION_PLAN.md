# Переезд на 3x-ui v3 — выполнено (адаптер v2/v3 в xui.py)

> Обновлено 2026-06-23 по факту реального апгрейда прод-ноды на v3.

## 0. Что оказалось на самом деле

В v3.x 3x-ui **перенёс операции с клиентами** с `/panel/api/inbounds/*Client`
на новые `/panel/api/clients/*` (подтверждено `strings` по бинарнику панели —
фронт зовёт `clients/add|update|del|...`). Старые write-пути отдают **404**, из-за
чего после апгрейда сломались покупки/продления/бэкфилл. Read-путь
(`inbounds/list`, клиенты внутри `settings.clients`) в v3 **не изменился**.

Решение: в `bot/services/panels/xui.py` добавлен **детект версии + ветка v3**,
с сохранением v2 как фолбэка (мультисервер: ноды могут быть на разных версиях).

## 1. Карта эндпоинтов v2 → v3

| Операция | v2 | v3 |
|---|---|---|
| создать | `POST inbounds/addClient` (form) | `POST clients/add` (**JSON**) |
| обновить | `POST inbounds/updateClient/{id}` (form) | `POST clients/update/{email}` (**JSON**) |
| удалить | `POST inbounds/{ib}/delClient/{id}` | `POST clients/del/{email}` |
| сброс трафика | `POST inbounds/{ib}/resetClientTraffic/{email}` | `POST clients/resetTraffic/{email}` |
| онлайны | `POST inbounds/onlines` | `POST clients/onlines` |
| IP клиента | `POST inbounds/clientIps/{email}` | `POST clients/ips/{email}` |
| читать клиента | (из inbounds/list) | `GET clients/get/{email}` |
| список inbound (+клиенты) | `GET inbounds/list` | без изменений |
| детект версии | — | `GET inbounds/list/slim` (в v2 → 404) |

Модель клиента v3 — единая запись с `inboundIds: [..]` и **двумя секретами**
(`uuid` для VLESS, `password` для Hysteria2/Trojan). Мы кладём один секрет в оба
поля → одна запись обслуживает все inbound (как зеркалирование в v2, но нативно
одним вызовом). `tgId` в v3 — целое.

## 2. Что в коде (xui.py)

- `_ensure_api_version()` — лениво детектит "v2"/"v3" (кэш на жизнь клиента),
  override через `config.XUI_FORCE_API_VERSION`.
- `_request(..., json_body=True)` — JSON-тело для v3 (form для v2).
- Хелперы: `_v3_get_client`, `_v3_client_body`, `_v3_update_fields`,
  `_v3_email_for_secret`, `_v3_provision_all`.
- Ветки v3 в: `provision_client_all_inbounds` (один `clients/add` с inboundIds),
  `add_client`, `update_client_full`, `update_client_limit`,
  `extend_client_expiry`, `delete_client`, `reset_client_traffic`,
  `get_online_emails`, `get_online_clients_count`, `get_client_ips`.
- `vpn_api.disable_key_on_panel` — терпит dict-`settings` (v3).
- Сигнатуры публичных методов не изменились → остальной код не трогаем.

## 3. Деплой и поэтапная проверка (root@ArcVPN)

1. `cd /root/ArcVPN && git pull`
2. Бэкап: `cp database/vpn_bot.db ~/vpn_bot.db.bak.$(date +%F)`
3. `systemctl restart arcvpn-bot arcvpn-subscription`
4. **Дымовой тест ОДНОГО ключа** перед массовым бэкфиллом:
   ```bash
   python3 - <<'PY'
   import asyncio
   from bot.services.vpn_api import get_client, push_key_to_panel, close_all_clients
   async def m():
       c = await get_client(10)                  # id сервера
       print("version:", await c._ensure_api_version())
       await close_all_clients()
   asyncio.run(m())
   PY
   ```
   Затем продлить/обновить один тестовый ключ из бота и убедиться, что 404 ушли.
5. **Бэкфилл** существующих клиентов в Hysteria2 (после успешного п.4):
   ```bash
   python3 backfill_all_inbounds.py --server 10            # dry-run
   python3 backfill_all_inbounds.py --server 10 --apply
   ```
6. Проверить подписку: `curl -s '<SUBSCRIPTION_URL>/sub/<sub_id>?format=plain'`
   → должны прийти и `vless://`, и `hysteria2://`.

## 4. Откат

- Код совместим с обеими версиями. Если что-то идёт не так на v3 — `git revert`
  коммита адаптера вернёт чистый v2-код; саму панель откатывать не обязательно
  (но тогда write-операции снова 404 на v3 — несовместимо). Правильный откат —
  откат панели на v2.9.x из бэкапа x-ui.db.
- Точечный форс версии: `XUI_FORCE_API_VERSION = "v3"` (или `"v2"`) в `config.py`.

## 5. Контрольный список

- [ ] `git pull` + restart bot/subscription.
- [ ] `_ensure_api_version()` → "v3".
- [ ] Продление/покупка тестового ключа без 404.
- [ ] Backfill применён.
- [ ] Подписка отдаёт VLESS + Hysteria2.
