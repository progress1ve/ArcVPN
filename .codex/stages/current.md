# Admin broadcasts MVP — 2026-09-29

Status: MVP implemented, checked locally and deployed to Poland. Authenticated
production UI acceptance passed; owner's review and real Telegram test are
pending the owner's choice between two configured admins. No customer sending
or bonus grant is authorized. Work uses the managed isolated admin-broadcasts
checkout; primary owner files and Finland notes are untouched. Existing React
admin and customer Svelte app are preserved.

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
- db_admin_broadcasts + migrations 67/68: durable drafts/revisions/frozen recipients,
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
existing fixed header. Final authenticated deployed browser recheck passed at all four sizes.

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

Owner chooses the Telegram test destination; send the saved compensation draft
only to that admin. Customer start requires separate approval after test review.

## Final deployment and acceptance

- Runtime commits: `48b006f` (MVP), `7e634ed` (campaign order reservations),
  `e2d3892` (named admin destinations); all pushed and production ff-only pulled.
- Restricted SQLite backup completed before pull; migration 67/68 ready.
  Existing key UUIDs and subscription identifiers unchanged against the backup.
- Affected bot/API services restarted and active. Public/admin routes 200;
  unauthenticated campaign API 403; real authenticated options/save API passed.
- Authenticated production browser QA: all four prescribed sizes passed;
  screenshots `production-*-top.png` and `production-*-launch.png`. No customer
  identities captured in those screenshots (search hid the recipient listing).
- Follow-up promo guards: 38 campaign/promocode checks + 2 payment-storage checks
  passed. Existing reserved orders may complete after promo expiry; new order
  reservations are blocked when expired, duplicated or capacity exhausted.
- Compensation draft is saved: 63 recipients, 0 without subscription; status
  draft, tested=0, 63 pending reward rows. Customer deliveries/grants are 0.
- Manual review and real Telegram test are deferred until the owner identifies
  one of the two configured admin destinations. Test must precede separate mass
  approval. No start/queue/bonus action has been performed.
- Code rollback has not been needed. Retain additive tables and ledgers if
  reverting runtime; known pre-MVP DB backup is mode 0600.
- All temporary credential files were removed locally and remotely without
  displaying credentials. Local DNS issue was handled with a per-command GitHub
  address resolved on the server; TLS verification remained enabled.
- Next: owner chooses test destination, reviews the test and the MVP, then
  explicitly authorizes any compensation campaign start.
