# ArcVPN current handoff

Updated: 2026-08-24. This file is current state, not a diary.

## Authority and topology

- Production/control plane: Poland `217.60.33.38`.
- Remnawave owns active subscription delivery; preserve existing URLs and UUIDs.
- Main DHost nodes: Germany and Netherlands. LTE profiles are separate, traffic multiplier 10.
- Canada was dropped. Vyrex canary was cancelled. Finland was retired from public delivery on 2026-08-24 and must not be reintroduced implicitly.

## Current product state

- Admin panel is not visually accepted. Support has known responsive/layout defects; Schemes is gated and must not be treated as production routing control.
- Frontend changes require live browser inspection at four viewport classes, not only code/tests.
- Node configuration facts live in `.codex/references/node-config-contract.md`.
- Non-secret server topology lives in `.codex/server-inventory.toml`; active Poland/Germany/Netherlands credentials are local DPAPI entries managed by `scripts/ops/server-vault.ps1`.
- Use `$arcvpn-node-ops` for node, Remnawave, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, or certificate work.

## Next recommended stage

Start the next bounded product stage. For UI, run a browser-first admin-panel audit beginning with Support. Do not imitate proprietary Axottle source; reproduce required behavior with the ArcVPN design system and original implementation. Build success alone is insufficient: resolve responsive defects, interaction states, accessibility warnings, and visual acceptance at the required viewports.

## Starting a new chat

Read `AGENTS.md`, this file, `.codex/project-index.md`, and `.codex/orchestrator.toml`. Use the stage skill for non-trivial work. Search `AI_CONTEXT.md` only when a named historical fact is missing.
