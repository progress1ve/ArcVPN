# Admin traffic period correction — 2026-09-30

Goal: make 1/3/7/14/30-day and custom-date selections control real ordinary/LTE totals in both summary cards and user rows. A 1-day LTE row must not show its all-time LTE counter.

Scope: existing React `/admin/traffic-usage`, a read-only admin API and Remnawave date-range usage adapter. No VPN routing, billing, quotas, UUIDs, subscription URLs or node changes. Preserve the independent node-operations stage in `current.md`.

Visible contract: all presets are inclusive UTC calendar days ending today; custom dates are inclusive UTC. Cards display the selected interval's ordinary and LTE totals. User table lists corresponding period usage only, with `0` for a confirmed zero and an unavailable state if panel data is incomplete. The node selector means ordinary/LTE profile groups here, not individual physical hosts. Keep only period, profile-group selector and CSV export in the filter bar; remove tariff, status, country, threshold and search controls. Sorting, pagination and CSV operate on the same interval values. Existing cumulative counters may not appear as period usage. Label UTC and current as-of time.

Evidence before implementation: production `/api/admin/traffic` ignores `period`, `nodes`, and date args and returns SQLite cumulative `vpn_keys.traffic_used` and `users.lte_used_bytes`. React sends these args but adapts cumulative values into rows, so changing 1d→7d cannot affect them. Production Remnawave date-range internal-squad API yields `{id,totalBytes}` for ordinary and LTE groups; `/api/users` supplies identity mapping. A read-only live check found all currently active period identities mappable to local users through panel ID/UUID/Telegram mapping. Squads may share physical inbounds, so group totals are not physical-node totals.

Acceptance: exact UTC start/end and interval metadata; complete paginated panel usage and identity-list fetch; 1d/7d values differ when history differs; cards/table/export agree; selected group filter changes row totals and columns; incomplete/unavailable data never falls back to cumulative counters; authenticated API; focused tests, TypeScript build, browser desktop/mobile checks and production verification.

Risks: stale identity mappings, panel API latency, high-volume users, UTC vs Moscow day boundary. Fail closed on incomplete pagination, expose unmapped usage rather than silently attributing it, bounded range, short client cache and clear source labels. Rollback: revert feature commit and redeploy subscription service plus admin bundle.

Evidence: six focused tests (period selection, group filtering, rejection/failure, prior daily helper) passed; TypeScript/Vite production build passed. Read-only live panel query confirmed usage payload has `id,totalBytes`, identity payload has `id,vlessUuid,telegramId`, and all currently active ordinary/LTE usage identities map to local users. Production browser verification pending deployment.
