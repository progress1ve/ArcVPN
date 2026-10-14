# Bot notification formatting — completed 2026-10-13

## Active: LTE paid addon recovery — 2026-10-14

Owner reports paid45GB lost before a full month (user5138461362). Exact contract, mapped components, acceptance and rollback in `lte-addon-recovery.md`. Audit confirmed calendar reset clears paid bonus early and panel falls to5GB; restore receipt-proven50GB, audit all similar receipts, then fix independent expiry/panel reconciliation/reset/renewal and customer copy. No charges/messages/identity or topology change. Economy; no subagents.
Evidence/acceptance/rollback: notification-html.md. Production7cda75fc FFpulled; bot and subscription API restarted/sharedbilling, active; WebApp200. Feedback payload uses plain caption + two native bold entities.80 selected cases pass across runs (one initial local empty-schema failure repaired with offline fixture initialization). Missing admin modes/dynamic report escaping fixed, shared fallback covers nested media. HostUp12h/150GB preserved. No live unsolicited messages, DB migrations, campaign replay or rollback. Natural next Telegram render remains external. Economy, no subagents; primary/remote owner changes preserved.

## Completed: admin user workflows — 2026-10-13

Documentation closeout recorded2026-10-14; runtime and live acceptance completed2026-10-13.

Owner's content contract, exact acceptance/rollback/evidence: `admin-user-workflows.md`. Runtime `787398d231c0e973dffb723f639be9d4d04032d0` deployed on Poland after initial `5aca069`/`264349e`; subscription API active, bot unchanged/active. Profile heading/contrast/grouping fixed, answers/tickets BackIcon and no Refresh, ticket waiting/unread/newest queue, honest ordinary/LTE traffic, source-based user history and hardened read-only server preflight.89 backend/11 frontend tests, TS/build and live360/768/1280/1600 on all5 pages plus ticket dialog passed. Primary evidence `evidence/admin-20261013/acceptance-final.public.json` and public screenshots. No migrations/identity/billing/routing changes; older admin snapshots/chunks retained. Full automatic node installation deferred; next stage requires its installation/routing contract. Economy; no subagents. Existing notification-stage evidence retained.
