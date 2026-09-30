# Admin traffic today: ordinary and LTE — 2026-09-30

Goal: make `/admin/traffic-usage` show real same-day ordinary and LTE usage, so the owner can see whether LTE identities were used today.

Scope: a read-only admin API backed by Remnawave's date-range internal-squad usage, the existing React admin traffic page and focused tests. No routing, quotas, subscriptions, tariff logic or node configuration changes. Do not reinterpret the existing cumulative per-user table as period traffic.

Current evidence: production Remnawave has distinct `ArcVPN Staging` (ordinary) and `ArcVPN LTE` squads. Read-only `GET /api/bandwidth-stats/internal-squads/{uuid}/usage?start=YYYY-MM-DD&end=YYYY-MM-DD` returns cursor-paginated `{users:[{id,totalBytes}],nextCursor,hasMore}`. A 2026-09-30 UTC probe found activity in both groups and zero shared user IDs. The squads have overlapping physical node inbounds, so these are product/identity totals, not non-overlapping physical-server totals.

Visible contract: show two prominent cards, "Обычные профили" and "LTE-обход", each with actual used bytes and count of active identities for the current Remnawave UTC calendar day. Show UTC date, update time, and a clear unavailable/error state instead of false zero. Keep the existing user table and filters below unchanged. The cards are independent of its period selector, which currently displays cumulative counters and must not be called a real daily series.

Acceptance: both values come from complete paginated live API results, not mocks or monthly counters; 0 only after a successful empty response; authenticated read-only endpoint; UTC date/caching explicit; partial pages/errors produce unavailable, not partial totals; desktop/mobile layout and loading/error states verified; focused backend tests and admin build pass. Check real production response after deployment without exposing user IDs.

Risks: squad names may be renamed; Remnawave may be unreachable or pagination may change; 2-minute panel flush delay; UTC day differs from Moscow near midnight. Resolve squads by exact name and fail closed on missing/duplicate; cap/validate pagination and cache briefly; label UTC explicitly. Rollback: revert feature commit, redeploy only subscription service and admin bundle. No secret data in logs or Git.

Evidence: focused pagination/auth/error tests passed (4); `npm run build` passed (TypeScript and Vite), including rebuild after merging concurrent React node-operations work. Read-only live Remnawave probe confirmed nonzero usage for both squads on 2026-09-30 UTC. Commit `ffdcfd3` was pushed and pulled fast-forward on Poland; `arcvpn-subscription.service` is active. Authenticated production browser displayed 44.62 GB ordinary (18 active identities) and 1.6 GB LTE (12 active identities) for the UTC day, at 16:46 UTC. These are point-in-time values and will change. Browser layout was checked at current desktop viewport; narrow viewport remains unverified.
