# Stage: MCP workflow and repository hygiene

## Goal

Make ArcVPN server operations automatically prefer the private `arcvpn-ops` MCP,
improve task routing, and remove only proven reproducible cache files.

## Non-goals

- Do not change production runtime or topology.
- Do not modify the owner's current `Connect.svelte` edit or deleted landing prompt.
- Do not remove secrets, database state, dependencies, worktrees, previews, legacy
  sources, or any unknown/untracked file.
- Do not install a frontend framework or UI library during this stage.

## Components

- `AGENTS.md`
- `.agents/skills/arcvpn-server-ops/`
- `.agents/skills/arcvpn-node-ops/`
- `.agents/skills/arcvpn-frontend-qa/`
- reproducible Python and pytest cache directories

## Acceptance

- Generic server work automatically routes to `arcvpn-server-ops`.
- Node/protocol work uses high-level `arcvpn-ops` MCP tools when available and
  safely falls back to the existing DPAPI SSH path.
- MCP use never expands authorization or weakens production gates.
- Only classified reproducible caches are deleted.
- Existing owner changes remain byte-for-byte untouched.
- Changed skills pass the skill validator and the final Git diff is reviewed.

## Risks and rollback

- Tool unavailable in the current task: fall back to the established vault and
  host-key-verified SSH helper.
- Broad terminal access: prefer bounded read-only MCP tools, require the same
  explicit scope for mutations, and preserve deployment verification.
- Rollback: revert the workflow commit; caches regenerate automatically.

## Verification

- Passed: new and changed skills validate with `quick_validate.py`.
- Passed: cleanup removed 19 reproducible Python/pytest cache directories only.
- Passed: `.secrets`, database, config, virtual environment, `node_modules`,
  worktrees, previews, legacy sources, and unknown files remain present.
- Passed: owner changes to `Connect.svelte` and the deleted landing prompt remain
  unstaged and untouched.
- Passed: reviewed commit `e519584`, pushed to `main`, and production
  fast-forwarded to the same commit. Documentation/skills changed only, so no
  service restart was performed.

## Closeout

- Runtime impact: none; no production service restart is required.
- Rollback: revert the documentation/skill commit. Deleted caches regenerate.
- Residual: Impeccable and shadcn were evaluated but not installed. Official
  shadcn/ui is React-oriented and does not match the current Svelte stack.
- Residual: the production checkout contains older untracked backups and runtime
  artifacts. They were outside the requested local-cleanup scope and remain
  untouched pending a separate classified production cleanup.
- Next: use the new landing-planning prompt in a fresh task, then implement only
  after its public content and interaction contract is accepted.
