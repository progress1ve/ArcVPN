# Локальная очистка ArcVPN: инвентаризация

Дата: 2026-08-20. Владелец разрешил удаление классифицированных локальных кандидатов.

## Изменённые tracked

| Путь | Класс | Решение |
|---|---|---|
| `vless_test_20260708_113659.txt` | diagnostic/obsolete | Удалён после подтверждения владельца |

## Untracked

| Путь | Класс | Решение |
|---|---|---|
| `.arcshots/background-reference.mp4` | generated/reference asset | Сохранить локально, игнорировать Git |
| `.arcshots/*.log` | generated/diagnostic | Сохранить локально, игнорировать Git |
| `.arcshots/pydeps/`, `.arcshots/video-bg/` | generated | Сохранить локально, игнорировать Git |
| `.codex-worktrees/` | generated/tool state | Сохранить локально, игнорировать Git |
| `__diag.py` | secret + diagnostic | Не коммитить; после ротации секрета удалить только с подтверждением владельца |
| `gift.png`, `support.png` | obsolete source assets | Не использовались source; удалены после подтверждения |
| `opencode.json` | user tooling config | Удалён после подтверждения |
| `support_message_2.md` | diagnostic/operator draft | Удалён после подтверждения |
| `webapp/public/assets/arc-flow/*-chroma.png` | generated/intermediate asset | Удалены после проверки source references |
| `webapp/public/assets/arc-flow/referral-gift.png` | obsolete asset | Удалён; runtime использует `referral-gift-v2.png` |
| `webapp/public/assets/arc-flow/support-agent.png` | obsolete asset | Удалён; runtime использует `support-agent-v2.png` |

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

Неоднозначные локальные кандидаты подтверждены и удалены. Следующий security gate:

1. проверить реальные ссылки через `rg`;
2. санитизировать tracked документацию и ротировать обнаруженные credentials;
3. проверить production backup inventory отдельным read-only аудитом;
4. прогнать Python tests, WebApp build, bot import/startup smoke и subscription API smoke.
