# ArcVPN

Telegram бот для управления VPN подписками.

## Subscription система

Для работы subscription системы нужно запустить `subscription_api.py`:

```bash
# Установить Flask
pip3 install flask

# Запустить API
nohup python3 subscription_api.py > subscription.log 2>&1 &

# Проверить
curl http://localhost:8080/health
```

Пользователи получают subscription URL через кнопку "🔗 Subscription ссылка" в боте.

## Структура

- `bot/` — Telegram-бот и административная панель.
- `webapp/` — пользовательский WebApp.
- `subscription_api.py` — публичная выдача подписок.
- `scripts/maintenance/` — ручные операции обслуживания.
- `scripts/legacy/3xui/` — архивные инструменты старого 3x-ui контура.
- `deploy/systemd/` и `monitoring/` — production units и мониторинг.
- `docs/roadmaps/` — актуальные планы; `docs/archive/` — исторические документы.
- `.codex/` — актуальный handoff, контракты и non-secret inventory для рабочих агентов.

Локальные секреты находятся только в `.secrets/` и никогда не коммитятся.
