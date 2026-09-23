# Trial feedback, conversion and client usage — 2026-09-23

## Goal

Add a standalone admin feedback overview with response statistics and user drill-down.
Correct trial-response semantics, implement the approved targeted win-back offer,
and investigate LTE usage plus ambiguous client devices before changing accounting.

## Visible contract

| Surface | Required behavior |
| --- | --- |
| Admin feedback | Separate «Ответы» button in the Users group opens a dashboard of sent/answered counts, answer categories, trial-to-paid status and a filtered list linking to users. The per-user answer tab remains available for drill-down. |
| Meaning | `speed` means the user selected «Низкая скорость» when asked what to improve. A later purchase does not change the historical answer. |
| Win-back | Target only connected, expired trial users without a successful commercial payment; offer a one-use 20% reduction on a 3-month first purchase for 48 hours, with one follow-up at most and immediate stop after payment. Existing lifecycle exclusions and eligibility date apply. |
| LTE | Compare local and panel usage, effective allowance, add-on balance and provisioning; correct only a demonstrated mismatch with regression coverage. |
| Add-on and custom tariff | Disclose that purchased bypass GB expire at the next traffic reset. Permit 175 and 225 GB custom bypass tiers consistently in the public builder, WebApp, server quote and payment validation. |
| Devices | Do not label an unidentified client as Happ. Show INCY only when an actual client identifier proves it; ambiguous `generic` entries remain clearly unidentified and HEAD checks do not create slots. A real direct GET can still reserve a recovery slot by design. |

## Components

- Admin API and React dashboard/routes/navigation.
- Lifecycle scheduler, callback and payment quote/promo integration.
- LTE identity/sync/purchase path and device registration/subscription fetch path.
- Focused tests, type-check/build, production service and HTTP checks. Browser
  verification is delegated to the owner per instruction.

## Acceptance

- Aggregate feedback totals match underlying events and filters; categories
  separate praise from complaints and paid status from historical response.
- Admin links work from overview to the selected user.
- Win-back discount cannot be reused, cannot apply to paid users, and respects
  its expiry; no duplicate Telegram messages from scheduler retries.
- LTE fix is based on an observed source-of-truth discrepancy and does not reset
  existing purchased traffic.
- Unknown client remains unknown; known INCY renders as INCY; HEAD creates no slot.
- Relevant tests, TypeScript and build pass. Production rollout follows the
  repository pull/restart/HTTP checks without browser automation.
- 175/225 GB quote prices remain monotonic, and the add-on expiry note appears beside the GB choices.

## Risks and rollback

- Billing and quota logic is high impact: preserve user entitlements and
  compare against the panel before any data correction.
- Bot offer delivery must be idempotent. The existing 3-day feedback gift must
  not combine into repeated discount offers.
- Roll back runtime via Git revert and affected-service restart; retain event
  and payment records for audit.

## Verification matrix

| Area | Local | Production |
| --- | --- | --- |
| Feedback | API/filter test, React type-check/build | Auth gate and aggregate/API smoke |
| Win-back | eligibility, discount and idempotency tests | Bot status and bounded journal |
| LTE/devices | regression tests and read-only accounting audit | Panel/local consistency and service health |
