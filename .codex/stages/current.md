# Paid subscription trial-state repair — 2026-09-21

## Previous stage

The referral activation, RU gateway and bot artwork stage is complete in
commit `f28662f`; its detailed evidence remains in Git history.

## Goal

Stop successfully fulfilled subscription purchases from remaining classified as
trial, repair existing affected rows, and expose the current VPS in the compact
mobile admin user row.

## Contract

- A confirmed `new`, `renew`, or `upgrade` purchase completes an active trial
  entitlement idempotently after its paid limits are durably applied.
- Paid trial offers, top-ups, add-ons, pending/failed payments and unfulfilled
  orders do not complete the trial entitlement.
- Existing active trial rows are repaired only when a confirmed commercial
  subscription payment has `addons_applied_at` evidence.
- LTE usage is preserved. `5 / 75 GB` means 5 GB used from a 75 GB allowance.
- At 390 px an online user displays the current VPS name when the API supplies
  it, with a device-count fallback; desktop behavior remains unchanged.

## Acceptance

- Focused lifecycle and migration tests cover conversion, idempotency and
  exclusions.
- Backend tests and admin type-check/build pass.
- Browser evidence at 390 px shows the VPS in the compact row.
- Production migrates safely, affected services remain active, the reported
  account is no longer classified as trial, and its 75 GB LTE quota/usage are
  unchanged.

## Risks and rollback

- The schema migration rebuilds only `trial_entitlements`, preserving its rows
  and indexes. Rollback is a Git revert; completed rows remain harmless because
  old readers select only `active`.
- The backfill requires a successful subscription operation with applied
  entitlement evidence and
  excludes trial offers and non-subscription operations.
- No UUID, subscription URL, payment amount or traffic counter is changed.
