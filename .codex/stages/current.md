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

Deployed runtime: ee7c079, production ff-only pull, both affected services active.
Server render preserves authored text; public admin HTTP 200. One previously
successful day-draft test invalidated; both campaigns remain drafts, untested,
no deliveries. Authenticated browser: duplicate absent and no overflow at
390/768/1280/1600 widths. Evidence: .codex/evidence/broadcasts/copy-fix-*.png.
Owner's draft “Проблема с серверами решена” targets 24 active subscribers; earlier
compensation draft targets 63. Audience and copy unchanged. Next: owner reloads
admin and repeats Telegram test, then separately confirms any actual send.
