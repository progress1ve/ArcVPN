# ArcVPN project index

- Bot runtime: `bot/`
- Admin web/API: `subscription_api.py`, `admin_webapp/src/arcvpn/ArcAdminRoot.tsx` (current dedicated React admin); `webapp/src/views/AdminConsole.svelte` remains legacy Svelte.
- Partner cabinet/accounting: `partner_api.py`, `database/db_partners.py`, `admin_webapp/src/arcvpn/ArcPartnerCabinet.tsx`, `admin_webapp/src/arcvpn/ArcPartners.tsx`; operator guide `docs/operations/partner-cabinet.md`.
- Subscription delivery: `subscription_api.py`
- Remnawave integration: search `bot/services/` and `scripts/` for `remnawave`
- Tests: `tests/`
- Operations/deploy: `scripts/`, `deploy/systemd/`, systemd service names in `AGENTS.md`
- Roadmaps: `docs/roadmaps/`; operations: `docs/operations/`; research: `docs/research/`; superseded 3x-ui material: `docs/archive/`
- Non-secret server topology: `.codex/server-inventory.toml`
- Local encrypted credentials: `.secrets/server-credentials/` via `scripts/ops/server-vault.ps1`
- Stable history: `AI_CONTEXT.md` (targeted `rg` only)
- Active stage/evidence: `.codex/stages/current.md`
- Node contract: `.codex/references/node-config-contract.md`
- Node/CDN workflow: `.agents/skills/arcvpn-node-ops/`
- Full node onboarding: `.agents/skills/arcvpn-add-node/`; node speed/IP tests: `.agents/skills/arcvpn-benchmark-nodes/`
- Dated active node/CDN route snapshot: `docs/operations/node-topology-current.md` (verify live before writes)
- Owner benchmark method: `docs/operations/server-benchmark-method.md` (Multitest);
  latest results: `docs/operations/multitest-2026-09-29.md`.

- Partner admin-derived UI: shared AdminNavSection/ShellHeader; admin_webapp/src/arcvpn/PartnerNetwork.tsx adapts opaque scoped nodes to existing admin NetworkGraph; backend db_partners.report handles descriptions/cohort conversion/daily series.
