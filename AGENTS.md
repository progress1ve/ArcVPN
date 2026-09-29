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
- For full node onboarding use `$arcvpn-add-node`; for requested node speed/IP diagnostics use `$arcvpn-benchmark-nodes`. Confirm the dated snapshot in `docs/operations/node-topology-current.md` against live state.
- Finish with `$arcvpn-closeout`.

## Working with the owner

- Communicate in concise Russian, lead with the result and the remaining risk. Do not stop after an intermediate check when the authorized task can safely be finished; send progress updates during longer work.
- For a product-topology or live migration choice, present one explicit route/profile table and ask one focused question if approval is needed. Do not repeatedly ask about routine in-scope diagnostic or implementation steps.
- For benchmarks, provide the complete copyable terminal output or a private raw-log location when requested, alongside a short interpretation. Distinguish measured results from assumptions and do not call ping or a single iperf run a complete user-experience test.
- If the owner reverses a production decision, audit the affected routes and subscriptions promptly before restoring anything. Never infer that a returned VPS is available.

## Production workflow

After runtime code changes: local checks -> inspect staged diff -> commit -> push -> production `git pull --ff-only` -> restart only affected services -> verify service state and public behavior. Services include `arcvpn-bot.service` and `arcvpn-subscription.service`. Documentation-only changes require push and production pull, but no restart unless runtime files changed.
