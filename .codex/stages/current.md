# Stage: legal-version synchronization and quiet daily backups

## Goal

Make the 10 September 2026 User Agreement and Privacy Policy canonical in every
ArcVPN surface, and stop the bot from sending the daily backup archive to
administrators while preserving local backup creation and cleanup.

## Exact contract

| Surface | Required result |
| --- | --- |
| Public legal page | Remains the canonical full Agreement + Privacy Policy |
| WebApp settings | Shows the current date and opens the canonical full document; no stale embedded summary or placeholders |
| Purchase disclosures | Continue linking to the canonical legal URL |
| Telegram gate | Names both documents and records version `2026-09-10` |
| Production setting | `legal_consent_version` is explicitly `2026-09-10` |
| Daily scheduler | Still creates a local DB backup and removes expired local backups; sends no backup archive/document to admins |
| Other notifications | Daily statistics, expiry notices and failure logging remain unchanged |

## Components

- `webapp/src/views/HomeFlowPreview.svelte` and generated `webapp_dist/`
- `bot/middlewares/subscription_check.py`
- `bot/handlers/user/start.py`
- `bot/services/scheduler.py`
- focused tests and production setting
- closeout context files

## Non-goals

- No change to the legal text, tariffs, payment processing or existing consent history.
- No deletion of local/server backups and no disabling backup creation.
- No removal of daily admin statistics, user expiry alerts, error logging or manually requested admin log exports.
- No Hero or landing-content changes.

## Risks and rollback

- A stale production setting could keep recording the prior consent version; verify it directly after deployment.
- Scheduler refactoring must not accidentally stop local backup retention.
- Roll back with a normal revert and restart only the bot/subscription services affected by the reverted runtime files.

## Verification

| Check | Status | Evidence |
| --- | --- | --- |
| Source inventory | Passed | Stale WebApp dates/summary and bot fallback located |
| Scheduler boundary | Passed | Daily Telegram archive call is separate from local backup work |
| Focused tests | Passed | 7 focused tests; scheduler import verified |
| Vite build | Passed | Production bundle built |
| Public browser | Passed | `/app` and current assets verified |
| Production setting/services | Passed | `2026-09-10`; all affected services active |

## Result

- WebApp settings now show “Соглашение и конфиденциальность”, revision date 10
  September 2026, a concise scope summary and a link to the canonical full
  document. The stale embedded copy, old date and operator placeholders are gone.
- Telegram channel gate names both documents. New recorded consent uses version
  `2026-09-10`; production setting was explicitly written and read back.
- Daily scheduler no longer builds or sends a Telegram backup archive. It still
  runs `save_local_backup()` and `cleanup_old_backups()` at 09:10 UTC. Daily
  statistics, expiry alerts, error logs and manual admin log export remain.

## Verification result

| Check | Status | Evidence |
| --- | --- | --- |
| Source inventory | Passed | No stale 29 July date or 2026-08-26 fallback in scoped surfaces |
| Focused tests | Passed | 7 tests; scheduler import checked separately |
| Vite build | Passed | Production bundle built; only pre-existing unused-selector warnings |
| Public browser | Passed | `/app` loaded the production login surface; current JS asset returns 200 and contains current date/canonical URL only |
| Backup boundary | Passed | Production scheduler has local maintenance and no archive sender |
| Production setting/services | Passed | Version `2026-09-10`; bot, subscription and nginx active/running |

Runtime commits: `9c3c452`, `e989cf3`. Rollback remains a normal revert followed
by bot restart; static WebApp files do not require subscription-service restart.
