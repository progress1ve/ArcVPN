# ArcVPN current handoff

Updated: 2026-08-24. This file is current state, not a diary.

## Authority and topology

- Production/control plane: Poland `217.60.33.38`.
- Remnawave owns active subscription delivery; preserve existing URLs and UUIDs.
- Main DHost nodes: Germany and Netherlands. LTE profiles are separate, traffic multiplier 10.
- Canada was dropped. Vyrex canary was cancelled. Finland was retired from public delivery on 2026-08-24 and must not be reintroduced implicitly.

## Current product state

- Whole-admin operations redesign is deployed at runtime commit `9c77b67831f163605678c9b476d5c3b72741e349`; production evidence is recorded in `.codex/stages/current.md` and its docs follow-up `b0458b95b8bde59deae4fd093afff5d54f07605f`.
- All 11 owner sections passed authenticated production composition/overflow checks at mobile, tablet, desktop, and wide viewports. Capability-aware navigation/RBAC, honest state machines, role management, truthful Schemes/Nodes/Backups language, and immediate verified subscription-panel synchronization are implemented.
- The stage remains **in progress**, not closed: a real keyboard-only activation pass, one explicitly authorized production Support reply, and a designated safe disabled Remnawave identity for live revoke confirmation are still pending. Do not infer permission to mutate a real user or send a Support message.
- The non-operational Schemes editor and its graph dependency were removed in `d111e11efa5f86738e54fc6e464fabe3e2dc9bb6`. Axottle-only infrastructure features without ArcVPN backend contracts remain explicitly deferred/rejected in the current stage matrix.
- Frontend changes require live browser inspection at four viewport classes, not only code/tests.
- Node configuration facts live in `.codex/references/node-config-contract.md`.
- Non-secret server topology lives in `.codex/server-inventory.toml`; active Poland/Germany/Netherlands credentials are local DPAPI entries managed by `scripts/ops/server-vault.ps1`.
- Use `$arcvpn-node-ops` for node, Remnawave, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, or certificate work.

## Next recommended stage

Close the three remaining acceptance gates in `.codex/stages/current.md`. Use a user-authorized non-sensitive Support reply and a designated already-disabled test identity only; verify persistence/delivery and authoritative Remnawave `DISABLED` state without changing the UUID or subscription URL. Complete a real keyboard-only pass across navigation, Support, and representative forms. Then use `$arcvpn-closeout`; do not repeat the completed whole-panel audit.

## Starting a new chat

Read `AGENTS.md`, this file, `.codex/project-index.md`, and `.codex/orchestrator.toml`. Use the stage skill for non-trivial work. Search `AI_CONTEXT.md` only when a named historical fact is missing.
