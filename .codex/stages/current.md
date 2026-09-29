# Admin broadcasts MVP — 2026-09-29

Status: owner accepted the proposed MVP in voice; implementation and local QA
passed, production deployment pending. Production baseline verified a63df20 on
Poland. Work uses managed isolated admin-broadcasts checkout; primary owner files
and Finland notes are untouched. Preserve the existing deployed React admin;
customer Svelte app is unchanged.

## Accepted contract

See `.codex/stages/broadcast-proposal.md`. Owner requested a reviewable MVP,
then an outage notice with +3 days: test to owner first, mass delivery only after
separate explicit owner confirmation. No customer campaign is authorized yet.
UI: Рассылки -> compose -> audience -> bonus/discount -> save -> Telegram test ->
confirm recipient count -> start -> progress/stop/history. Photo, up to three
HTTPS buttons; six audience segments, tariff intersection, search, exclusions.
Days extend one canonical subscription from max(now, expiry), preserve IDs/quota;
no-subscription recipients get an explicit no-grant variant. Promo choices are
existing shared, new shared, or private single-use percent/ruble code.

## Components and acceptance evidence

- ArcAdminRoot/ArcBroadcasts: owner navigation and real API form with sanitized
  preview, loading/error/disabled states and separate confirmation.
- admin_broadcast_api: owner-only, same-origin mutation checks; configured admins
  only for tests; test never starts queue or grants.
- db_admin_broadcasts + migration 67: durable drafts/revisions/frozen recipients,
  atomic reward ledger, stopped-job sync, private promo binding/order guards.
- admin_broadcast_worker + main: sync before benefit notification; Telegram
  rate-limit retry; blocked vs failed vs uncertain; restart never re-sends a
  potentially delivered message. Existing bot broadcasts remain compatible.
- db_promocodes: shared bot/web validation enforces private recipient/order.

Local gates passed: 257 Python tests; after final backend changes, 29 focused
broadcast tests passed (two extra tests added after the full suite). Admin build
and type-check passed. Biome checks on changed frontend passed without findings.
Browser QA: message -> test -> edit invalidation -> retest -> confirmation.
390x844, 768x1024, 1280x900 and 1600x900 show no horizontal overflow. Screenshots
in `.codex/evidence/broadcasts/*-top.png` and `*-launch.png` (local demo accounts;
no production customer data). A sticky panel offset was corrected to clear the
existing fixed header. Final deployed browser recheck pending.

## Risks / rollback

Additive SQLite tables/triggers; restricted DB backup before production pull.
Revert scoped runtime commit and restart bot/subscription; preserve campaign
ledger and granted benefits. Stop before rollback. Network-ambiguous Telegram
results are marked uncertain for manual review; exactly-once remote messaging
cannot be promised. Test media upload sends a clearly-labelled photo to the
configured admin. Personal code is reserved by an active order until that order
is cancelled or completed; shared promo payment semantics otherwise unchanged.
No email/scheduling/new-subscription provisioning in this MVP.

## Next step

Review staged diff, commit/push/ff-only production pull, restart affected
services, inspect deployed form and send only the owner's outage-preview test.
Do not start the customer campaign before a separate owner approval.
