# Repository hygiene audit — 2026-09-01

Read-only audit. No cleanup was applied.

## Highest-risk findings

1. Active node instructions contradicted the current product contract: two files
   still prescribed x10 LTE/CDN accounting. They were corrected to x1.
2. `.codex/stages/current.md` contains 2,138 lines and many completed stages.
   This is a context-quality risk: old rejected requirements can look current.
   Compaction needs a separate owner-approved change; Git history already keeps
   prior revisions.
3. The working tree contains an owner deletion of
   `docs/design/arcvpn-landing-page-prompt.md`. It is excluded from agent commits
   and must not be restored or deleted by cleanup automation.

## Classification

| Class | Candidates | Decision |
|---|---|---|
| Reproducible ignored runtime | `__pycache__/`, `.pytest_cache/`, `.venv/`, `webapp/node_modules/` | Safe cleanup class only after explicit approval; no production value in Git. |
| Sensitive/local runtime | `.secrets/`, `config.py`, `database/vpn_bot.db` | Never include in generic cleanup; secrets and local state are intentional. |
| Empty untracked directories | `.claude/`, `.codex/stages/evidence/admin-before/`, `docs/design-previews/`, `.codex-worktrees/`, `scripts/legacy/3xui/` | Low disk impact; remove only in a separately approved empty-directory class. |
| Tracked delivery output | `webapp_dist/` | Intentional production artifact under the current deployment workflow; not a duplicate-source cleanup target. |
| Tracked generated media | matching assets under `webapp/public/` and `webapp_dist/` | Intentional source/build pairing until deployment changes to build on production. |
| Historical documentation | `docs/archive/` | Intentional archive listed by `.codex/project-index.md`; keep. One archived migration document refers to a now-absent legacy script, which is acceptable only while clearly historical. |
| Owner-owned dirty state | deleted landing prompt | Preserve exactly as-is and exclude from commits. |

## Contract improvements applied

- Zero assumption budget for public contracts that admit multiple implementations.
- Rejected drafts cannot become authority.
- Node/CDN mutation requires an accepted route table covering hostname, CDN,
  origins, Host/SNI, inbound/path, multiplier, public identifier impact, failure
  behavior and rollback.
- Ping, port and generated JSON are insufficient substitutes for a real tunnel.
- Added `$arcvpn-repo-hygiene` for classified, separately authorized cleanup.

## Recommended bounded cleanup

1. After owner approval, reduce `.codex/stages/current.md` to the truly active
   stage and keep completed details in Git history plus concise durable decisions.
2. Remove only the explicitly approved cache/empty-directory classes; never use
   a broad `git clean` against this checkout.
3. Keep runtime changes, node canaries and cleanup in separate commits/stages.
4. Re-run this audit periodically for contradictory active instructions; these
   are more dangerous than harmless cache files.
