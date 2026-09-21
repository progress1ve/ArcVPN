# LTE monthly traffic-cycle repair — 2026-09-21

## Goal

Restore per-user monthly reset dates for censorship-bypass traffic and ensure
new trial users always enter the authoritative reset scheduler.

## Confirmed production cause

- 16 active users currently have LTE entitlement.
- 6 have no traffic-cycle anchor or reset boundary, so the scheduler never
  selects them.
- The other 10 share one synthetic migration anchor and one reset date instead
  of their individual activation anniversaries.
- No reset attempts exist because the affected rows are not yet considered due.

## Components

- `database/migrations.py`: one-time repair for missing and duplicated synthetic
  anchors, based on the earliest key creation timestamp.
- `bot/handlers/user/trial.py`: start the cycle immediately after successful
  trial activation.
- `database/db_traffic_cycles.py` and `bot/services/scheduler.py`: unchanged
  authoritative reset path (Remnawave first, local counters second).

## Non-goals

- No changes to quotas, prices, subscriptions, nodes, CDN, DNS or user UUIDs.
- Do not blindly zero local counters. A due cycle is cleared only after the
  corresponding Remnawave main/LTE resets succeed.
- Do not change users whose existing anchor is unique and therefore may reflect
  a legitimate lapsed-subscription reactivation.

## Acceptance

- Every active LTE user has an anchor and reset boundary.
- Duplicated migration anchors are replaced by each user's earliest key date.
- A boundary that has already passed remains due so the scheduler performs an
  authoritative reset; successful users show 0 used from the new allowance.
- New trial activation initializes its own cycle.
- Focused cycle and migration tests pass; production backup, migration, bot
  restart and aggregate post-checks pass without exposing user identifiers.

## Risks and rollback

- Risk: a panel reset fails for one identity. The existing retry table keeps
  that user due and does not zero local data.
- Before deployment, create a SQLite backup. Rollback code by reverting the
  release; restore only affected cycle columns from that backup if the migration
  selects an unexpected cohort.

## Result and evidence

- Focused cycle/trial suite: 10 passed; compilation and diff checks passed.
- A production database backup was created before deployment.
- Runtime `441ebc8` was pulled fast-forward on Poland; only
  `arcvpn-bot.service` was restarted and it remains active.
- Schema v64 repaired 53 historical cycle rows. All 16 active LTE users now
  have anchors and boundaries; 9 overdue cycles were applied successfully.
- No active due cycle, missing cycle, or failed reset remained at verification.
- One 45 GB cycle reaches its exact anniversary later on 2026-09-21; one 5 GB
  trial is legitimately exhausted until 2026-10-11. Neither was reset early.
