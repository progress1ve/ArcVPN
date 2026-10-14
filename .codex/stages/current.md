# ArcVPN current stages — 2026-10-14

## Completed: LTE paid addon recovery — 2026-10-14

Runtime `a76f09eee9814ee6192e1633e0f681bb954897f5` published/Poland FFpulled, bot+API active; Moscow same static release, prior de6af44f retained. User5138461362 restored50GB (5base+45paid until22Oct23:07MSK), usage/3 devices/expiry/identifiers preserved. All payment history and82 LTE profiles audited:1 paid addon repaired,3 pending excluded,0 remaining quota/missing/UUID discrepancies. Paid grants now last a calendar month from activation, survive base reset and reconcile from receipts; renewal avoids base duplication, parallel callbacks idempotent, rejected panel writes retry/readback verified.83 focused tests/Svelte build, staged tree verification, authenticated profile and copy4 widths pass; public routes/assets/Google200, unauth403. No messages/charges/refunds/migrations/topology/identity changes. Exact evidence/acceptance/rollback in `lte-addon-recovery.md`; primary evidence `evidence/lte-addon-20261014/`. Residual: panel expiry sync on existing60s worker/outage retries; actual22Oct expiry is future. Next: owner admin review. Economy; no subagents.

## Completed: bot notification formatting — 2026-10-13

Evidence/acceptance/rollback: notification-html.md. Production7cda75fc FFpulled; bot and subscription API restarted/sharedbilling, active; WebApp200. Feedback payload uses plain caption + two native bold entities.80 selected cases pass across runs (one initial local empty-schema failure repaired with offline fixture initialization). Missing admin modes/dynamic report escaping fixed, shared fallback covers nested media. HostUp12h/150GB preserved. No live unsolicited messages, DB migrations, campaign replay or rollback. Natural next Telegram render remains external. Economy, no subagents; primary/remote owner changes preserved.

## Completed: admin user workflows — 2026-10-13

Documentation closeout recorded2026-10-14; runtime and live acceptance completed2026-10-13.

Owner's content contract, exact acceptance/rollback/evidence: `admin-user-workflows.md`. Runtime `787398d231c0e973dffb723f639be9d4d04032d0` deployed on Poland after initial `5aca069`/`264349e`; subscription API active, bot unchanged/active. Profile heading/contrast/grouping fixed, answers/tickets BackIcon and no Refresh, ticket waiting/unread/newest queue, honest ordinary/LTE traffic, source-based user history and hardened read-only server preflight.89 backend/11 frontend tests, TS/build and live360/768/1280/1600 on all5 pages plus ticket dialog passed. Primary evidence `evidence/admin-20261013/acceptance-final.public.json` and public screenshots. No migrations/identity/billing/routing changes; older admin snapshots/chunks retained. Full automatic node installation deferred; next stage requires its installation/routing contract. Economy; no subagents. Existing notification-stage evidence retained.
