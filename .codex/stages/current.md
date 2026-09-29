# Broadcast day-bonus copy correction — 2026-09-29

Accepted: owner writes the day-bonus copy; remove the automatic successful-day
sentence from preview and Telegram rendering. Keep atomic grants, test gate,
promo-code rendering and the no-subscription exception notice intact.
Components: ArcBroadcasts.tsx, db_admin_broadcasts.render, focused regression.
Acceptance: authored HTML is unchanged for recipients with a subscription;
preview has no appended gift sentence; existing day idempotency tests pass;
admin build passes and deployed browser verifies the correction at four sizes.
Risk: existing successful tests previewed old copy. Invalidate day-campaign tests
on deployment, without changing audience or starting any campaign.
Rollback: revert this scoped commit; retain reward ledger. No mass send authorized.

Latest-main generic-device repair is preserved (83976e6); its separate evidence
is in `.codex/stages/device-generic-fix.md`.
Local: 31 campaign checks passed; admin TypeScript/Vite build passed.
