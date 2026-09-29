# Admin broadcasts — proposed contract, 2026-09-29

Status: planning; owner agreement on interaction/reward semantics pending.

## Goal and source of truth

Add an accessible Рассылки entry to the current production admin and implement
Telegram campaigns with audience selection, mandatory admin test, rewards, and
observable delivery. Primary checkout is dirty and behind origin/main a63df20.
Current main contains admin_webapp (React) and broadcast UI/API client inherited
from its upstream; local legacy Svelte AdminConsole is not the current panel.
Use the existing deployed admin stack, without introducing another migration.
Public /admin/ browser baseline shows the new admin login; authenticated baseline
and production revision are still to be verified. Do not overwrite owner work.

## Proposed interaction contract

1. Рассылки opens history, status and Создать рассылку.
2. Compose a named draft: Telegram text, safe formatting controls, optional photo,
   and supported purchase/cabinet URL buttons. Never submit arbitrary callbacks.
3. Choose audience: all eligible Telegram users; active; expired; never paid;
   expiring within N days; tariff; explicit search/selection and exclusions.
   Combine criteria with AND. Show count and exclusions before testing.
4. Choose message only, gift days, existing/new shared promocode, or personal
   purchase discount. Discount supports percent/rubles, expiry and usage limits.
   Shared code is reusable by any otherwise eligible holder; personal discount
   is bound to selected user, once, without stacking, within expiry.
5. Gift days extend one existing subscription per recipient, preserving tariff,
   UUID, URL and allowances. Active: expiry + N days; expired: now + N days.
   No subscription: explicitly skipped, no invented subscription or quota.
   Resolve canonical subscription selection from current billing implementation.
6. Send test to an owner-authorized configured Telegram admin. Test must use the
   same rendering/buttons as delivery, with no real gift or discount activation.
7. Only after successful test, allow explicit Отправить N пользователям from the
   panel. Any content, reward or audience change invalidates the test. Freeze and
   expose the audience; audience changes require a new test/confirmation.
8. Running campaign shows progress, delivered/blocked/failed, bonus sync status,
   and stop (unsent recipients only). History and draft survive restart.

## Components

- Current admin_webapp navigation, broadcast pages/API client and preview.
- subscription_api.py admin adapter, authorization and audit trail.
- database migrations, campaign/recipient/reward ledger and audience queries.
- bot/services/broadcast_worker.py, supported test delivery and reward sync.
- Existing subscription extension, Remnawave synchronization and payment promo
  validation; tests and generated admin_webapp_dist.

## Acceptance

- Telegram HTML is built from safe structured formatting or strictly validated
  supported markup; malformed tags, entities, links and length fail before send.
- The rendered test is identical to final payload for the same draft revision.
- API rejects untested/changed drafts, unauthorized admins and repeated starts.
- Recipient list is distinct, deterministic, inspectable and frozen; unreachable
  or unlinked Telegram accounts are counted separately and never used as IDs.
- Bonus ledger prevents repeat awards across retries/restarts; external expiry
  sync retries explicitly and never reports an unconfirmed benefit as delivered.
- Handle Telegram rate limits/transient errors separately from blocked accounts.
  An ambiguous accepted-send/network timeout cannot promise exactly-once Telegram
  delivery; preserve uncertain status instead of blindly retrying.
- Discount eligibility is enforced in real bot/web payment paths, including
  recipient binding, expiry, use limits, concurrency and no stacking.
- Stop preserves completed awards and deliveries; rewards activate only during
  confirmed real execution. Test has no customer-side mutations.
- Verify empty/loading/error/focus/disabled states and 390x844, 768x1024,
  1280x900, 1600x900 with browser evidence; API/worker/reward tests and build pass.
- Commit reviewed scoped diff; push; Poland ff-only pull; restart affected
  services; verify panel/API and service state. No real customer campaign is
  launched as part of development acceptance.

## Risks, rollback and exclusions

Persistent job implementation currently distinguishes TelegramBadRequest as
blocked and does not separately handle RetryAfter; gift flow is separate from
durable message queue. Assess on current main before reuse. SQLite and external
panel writes need a durable reconciliation mechanism. Owner files and prior
Finland stage remain untouched. Rollback runtime via scoped revert; keep additive
ledger and campaign records, stop jobs first; never undo granted benefits blindly.
Email, scheduled campaigns and new subscription provisioning are outside this
proposed first release.

## Evidence / next step

Read mandatory local contract/context and relevant skills. Inspected legacy bot
queue/filter/gift implementation and origin/main admin broadcast routes/client.
Public admin login inspected in browser; authenticated view pending. No runtime
edits, sends, bonuses or deployment performed. Next: obtain owner agreement,
then inspect deployed revision and use suitable managed isolated checkout.
