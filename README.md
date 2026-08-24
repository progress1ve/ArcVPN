# ArcVPN

ArcVPN is a Telegram sales bot, a Remnawave-backed subscription API, and an operator console for managing users, payments, nodes, support, and service health. Existing public subscription URLs and user UUIDs are compatibility contracts.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

On Windows activate with `.venv\Scripts\Activate.ps1`. The Svelte admin WebApp is built separately:

```bash
cd webapp
npm ci
npm run build
```

Copy `.env.example` to an untracked `.env` and fill it from the owner credential source. Never put production secrets in documentation, commits, screenshots, or command output.

## Production

Production runs from `/root/ArcVPN` using `arcvpn-bot.service` and `arcvpn-subscription.service`. Units tracked under `deploy/systemd/` are the canonical install sources. A runtime change is complete only after local checks, commit, push, production `git pull --ff-only`, the affected service restart, and public verification.

```bash
sudo systemctl restart arcvpn-bot.service arcvpn-subscription.service
curl --fail http://127.0.0.1:8080/health
```

## Структура

- `bot/` — Telegram-бот и административная панель.
- `webapp/` — пользовательский WebApp.
- `subscription_api.py` — публичная выдача подписок.
- `scripts/maintenance/` — ручные операции обслуживания.
- `deploy/systemd/` и `monitoring/` — production units и мониторинг.
- `docs/roadmaps/` — актуальные планы; `docs/archive/` — исторические документы.
- `.codex/` — актуальный handoff, контракты и non-secret inventory для рабочих агентов.

Локальные секреты находятся только в `.secrets/` и никогда не коммитятся.
