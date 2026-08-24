# Repository layout and root classification

The repository root is reserved for runtime entrypoints and project-level configuration.

| Root path | Class | Reason |
|---|---|---|
| `.agents/` | agent tooling | Project-specific reusable skills; one-off scripts are not allowed here. |
| `.codex/` | agent context | Current handoff, contracts, stage evidence, and non-secret inventory. |
| `bot/` | source | Telegram bot and admin backend/frontend. |
| `database/` | source/schema | Database package and migrations; live SQLite files are ignored. |
| `deploy/` | production asset | Installable systemd/deployment material. |
| `docs/` | documentation | Roadmaps, operations, design references, and explicitly marked archive. |
| `monitoring/` | production asset | Fleet health and telemetry units/scripts. |
| `scripts/` | operations/source | Maintained automation, maintenance, legacy tools, and secret-vault helper. |
| `tests/` | source | Automated verification. |
| `webapp/` | source | User WebApp. |
| `webapp_dist/` | production asset | Tracked deployable WebApp build output. |
| `.env.example` | configuration | Non-secret environment schema. |
| `.gitignore` | configuration | Local/generated/secret exclusions. |
| `AGENTS.md` | agent contract | Small mandatory policy router. |
| `AI_CONTEXT.md` | durable history | Search with `rg`; do not read end to end. |
| `arcLOGOsvg.svg` | runtime asset | Loaded directly by `subscription_api.py`. |
| `main.py` | runtime entrypoint | Bot service entrypoint. |
| `NEXT_CHAT_HANDOFF.md` | compatibility pointer | Redirects old workflows to `.codex/handoff.md`. |
| `README.md` | documentation | Human entrypoint. |
| `skills-lock.json` | configuration | Skill dependency lock. |
| `subscription_api.py` | runtime entrypoint | Public subscription/API service. |
| `subscription_pages.py` | source | Imported by subscription API. |
| `xui_health_guard.py` | runtime entrypoint | Legacy guard still referenced by its systemd unit. |

Local-only retained paths are `.secrets/` (encrypted credentials), `config.py` (deployment configuration), `.codex-worktrees/`, and editor/tool state. They must remain ignored.

## Cleanup classification (2026-08-24)

- Deleted as obsolete: unused root device SVGs, a report screenshot, `subscription_api.py.backup`, stale chat/support notes, 75 one-off `.agents/*.py` diagnostics/mutators, old video reference, and extracted video dependencies.
- Deleted as generated: root `__pycache__`, empty logs, and Vite logs.
- Moved as documentation: roadmaps to `docs/roadmaps/`; old 3x-ui plans/problems to `docs/archive/`; UI references to `docs/design-previews/`.
- Moved as operations: systemd units to `deploy/systemd/`, maintenance scripts to `scripts/maintenance/`, and old 3x-ui tools to `scripts/legacy/3xui/`.
