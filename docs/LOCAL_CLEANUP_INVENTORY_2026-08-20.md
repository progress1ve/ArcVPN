# Локальная очистка ArcVPN: инвентаризация

Дата: 2026-08-20. На этом этапе файлы не удалялись и не перемещались.

## Изменённые tracked

| Путь | Класс | Решение |
|---|---|---|
| `vless_test_20260708_113659.txt` | diagnostic/obsolete candidate | Удаление принадлежит пользователю; не включать в коммит без подтверждения |

## Untracked

| Путь | Класс | Решение |
|---|---|---|
| `.arcshots/background-reference.mp4` | generated/reference asset | Сохранить локально, игнорировать Git |
| `.arcshots/*.log` | generated/diagnostic | Сохранить локально, игнорировать Git |
| `.arcshots/pydeps/`, `.arcshots/video-bg/` | generated | Сохранить локально, игнорировать Git |
| `.codex-worktrees/` | generated/tool state | Сохранить локально, игнорировать Git |
| `__diag.py` | secret + diagnostic | Не коммитить; после ротации секрета удалить только с подтверждением владельца |
| `gift.png`, `support.png` | unknown/source asset candidate | Не удалять; сравнить с финальными WebApp assets |
| `opencode.json` | unknown/user tooling config | Не удалять и пока не игнорировать |
| `support_message_2.md` | diagnostic/operator draft | Не удалять; после подтверждения перенести в private incident archive либо удалить |
| `webapp/public/assets/arc-flow/*-chroma.png` | generated/intermediate asset | Не публиковать, пока не подтверждена необходимость runtime |
| `webapp/public/assets/arc-flow/referral-gift.png` | production asset candidate | Сравнить ссылки в source и dimensions/hash |
| `webapp/public/assets/arc-flow/support-agent.png` | production asset candidate | Сравнить ссылки в source и dimensions/hash |
| `webapp/public/assets/arc-flow/referral-v2-chroma.png` | generated/intermediate asset | Не удалять без подтверждения |
| `webapp/public/assets/arc-flow/support-v2-chroma.png` | generated/intermediate asset | Не удалять без подтверждения |

## Tracked-классы

- `bot/`, `database/`, `monitoring/`, `scripts/`, `webapp/src/`: source.
- `webapp/public/assets/`: production assets, кроме явно помеченных intermediate.
- `docs/`, `README.MD`, `NEXT_CHAT_HANDOFF.md`: documentation.
- `deploy/` и systemd units: production assets.
- `tests/`: source/tests.
- `AI_CONTEXT.md`: documentation, но содержит чувствительные исторические данные и должен
  быть санитизирован с ротацией затронутых credentials.
- `*.backup`, root diagnostic dumps и historical test outputs: obsolete/diagnostic candidates;
  удалять только отдельным подтверждённым списком.

## Выполненное безопасное изменение `.gitignore`

Добавлены `.arcshots/`, `.codex-worktrees/`, `*.log` и `__diag.py`. Файлы остаются на
диске. `opencode.json`, пользовательские картинки и markdown draft намеренно не скрыты.

## Следующий destructive gate

До удаления требуется решение владельца по tracked `vless_test_...`, двум корневым PNG,
`support_message_2.md`, `opencode.json` и всем intermediate PNG. После решения:

1. проверить реальные ссылки через `rg`;
2. сравнить hash/dimensions и оставить только runtime assets;
3. санитизировать tracked документацию и ротировать обнаруженные credentials;
4. сделать cleanup отдельным коммитом;
5. прогнать Python tests, WebApp build, bot import/startup smoke и subscription API smoke.
