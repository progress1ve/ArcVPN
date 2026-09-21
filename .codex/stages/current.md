# Admin payments, sales statistics and retired-node correction — 2026-09-21

## Goal
Restore the Admin payment registry and sales statistics, prevent implausible
underpayments from being treated as revenue, and retire Albania/Netherlands
from the visible node list without breaking active subscriptions.

## Confirmed findings
- `/api/admin/payments` and `/api/admin/sales-stats` return HTTP 500 because
  their date SQL references nonexistent `payments.created_at`; production has
  `paid_at` only.
- Two succeeded linked YooKassa QR orders for 90/180-day tariffs are stored as
  478/596 kopecks even though their configured tariff prices are 399/499 RUB.
  They must not count as normal subscription revenue.

## Contract
- Use `paid_at` as the payment business timestamp; pending rows use no fabricated
  date and remain visible in the payment registry.
- Provider-confirmed YooKassa amounts are persisted in kopecks. Correct only
  rows whose provider status is succeeded and whose live provider amount
  differs from the stored amount; take a database backup first.
- New YooKassa order preparation stores RUB tariff price in kopecks, after a
  persisted discount, before it can be sent to the provider.
- Hide Albania and Netherlands from the administrative operational node list.
  Do not change the client catalog, Remnawave topology or user access in this
  reporting repair.

## Acceptance
- Payment and sales endpoints return 200 for 24h/period queries and expose only
  financially valid revenue totals.
- Existing and newly-created tariff order calculations use expected kopecks.
- Admin node overview no longer shows Albania or Netherlands.
- Production API checks, focused tests and browser/admin evidence pass.

## Risks and rollback
- Historical amount corrections are restricted to provider-confirmed mismatches
  and protected by a fresh SQLite backup.
- Node filtering is presentation-only. No customer UUID, subscription URL or
  connection route changes.

## Evidence
- Runtime commit `95062cb` was pushed to `main` and pulled fast-forward on the
  Poland production control plane.
- Python compilation, diff validation and 14 focused admin/payment tests passed.
- A fresh SQLite backup was created. All 28 linked succeeded YooKassa payments
  were checked against the provider; exactly two mismatched rows were corrected.
- Production payment registry and 7-day sales endpoints return HTTP 200. The
  verified seven-day revenue is 644 RUB (499 + 145), not 3590.96 RUB.
- Admin overview exposes Estonia, Germany and Moscow Bridge; Albania and
  Netherlands are absent. Subscription URLs and topology were not changed.
- `arcvpn-subscription.service` and `arcvpn-bot.service` are active after the
  restart; current logs show normal startup and no payment API exception.
