# ArcVPN agent contract

Before non-trivial work, read `.codex/handoff.md`, `.codex/project-index.md`, and `.codex/orchestrator.toml`. Search `AI_CONTEXT.md` only with `rg`; do not read it end to end.

## Invariants

- Production/control-plane authority is Poland `217.60.33.38`; the old Germany control plane is retired.
- Preserve existing subscription URLs, user UUIDs, and active-user access during migrations.
- Never print or commit passwords, tokens, Reality private keys, or subscription IDs.
- Do not delete unknown/user files. Classify first; delete only an explicitly authorized class.
- For node/protocol/CDN work, use `$arcvpn-node-ops` and follow `.codex/references/node-config-contract.md`.
- For deployments, service management, logs, health checks, or general server
  work, use `$arcvpn-server-ops`; automatically prefer the private `arcvpn-ops`
  MCP when its tools are available.
- For frontend work, use `$arcvpn-frontend-qa`; browser evidence is part of acceptance.
- For substantial UI work, separate planning from implementation: agree on the
  content/interaction contract first, then build and verify it. Preserve the
  existing Svelte stack unless the owner explicitly approves a migration.

## Routing

- Simple, low-risk, isolated task: work directly and record evidence.
- Medium/complex task: use `$arcvpn-stage`, create/update `.codex/stages/current.md`, define acceptance before implementation, and split independent work only when the user explicitly authorizes subagents.
- Finish with `$arcvpn-closeout`.

## Production workflow

After runtime code changes: local checks -> inspect staged diff -> commit -> push -> production `git pull --ff-only` -> restart only affected services -> verify service state and public behavior. Services include `arcvpn-bot.service` and `arcvpn-subscription.service`. Documentation-only changes require push and production pull, but no restart unless runtime files changed.
