# Audit: admin Paid counter — 2026-11-08

Read-only audit requested by owner. No billing/user data or UI changed.

Source chain: AdminPanel.tsx statsPaid uses subscriptions.paid; arc-local API
adapter maps backend get_subscriptions_stats paid. Backend computes active
vpn_keys count minus DISTINCT active trial_entitlements users, with NO payment
existence check. Thus this is an active non-trial-key bucket, not lifetime unique
buyers. Renewals do not directly add to this bucket when extending the same key.
Badge +N uses business.payments.day.orders, COUNT successful non-trial orders in
rolling24h, not first purchases and not Moscow calendar today. Addons/demo are
not excluded by this particular order query.

Initial live result matched screenshot:34active keys/14trials/20paid bucket;
19active nontrial users had successful commercial subscription records. During
read-only audit another active key appeared concurrently. Consistent final
SQLite read transaction at2026-11-08 16:00:15MSK:35active keys/35users,
14active trials,21nontrial bucket,19with successful commercial subscription
records,2without. Successful commercial definition: paid/succeeded, operation
new/renew/upgrade, payment_type neither trial nor demo, excludeemail_paid_trial.
No monetary settlement outside the application database was audited.

Last24h badge source:2paidrenew orders byYooKassaQR. For2026-11-07 Moscow date,
these were2orders/2people; only1ofthose people has their first recorded
commercial subscription payment on that date. Both operation labels are renew,
so operation_type=new is NOT a sufficient first-buyer criterion. Historical
missing/imported data can also affect first-recorded-payment attribution.
Nov8Moscow calendar successful payments/first subscribers:0 at audit.
Lifetime distinct commercial subscription payers:27 (includes expired users).

Conclusion: screenshot20 is not reliable count of paying customers; badge+2
is not two new buyers. Proposed separate definitions: active commercial
subscribers, lifetime unique commercial subscribers, first-recorded subscribers
per Moscow calendar day, and renewals separately. Do not silently choose whether
card should show active versus lifetime population; user currently requested
verification only. First purchase should derive MIN paid_at per user across all
qualifying subscription operations, excluding topups/addons/trials/demo, with
calendarMSK boundaries. Keep success-only paid-record provenance explicit.


## Accepted fix — 2026-11-08

Owner selected active paid users for the main card and first buyers today for
the badge, preserving the layout. Runtime 908e95b8 published and FF-pulled
on Poland; subscription service restarted, bot remained active, health HTTP200.
Main count is DISTINCT active user IDs with a positive successful commercial
subscription payment; active trial-linked keys are excluded. Badge uses the
first qualifying paid_at per user and calendar UTC+3 boundaries. Renewals do
not duplicate people; a first payment marked renew after a trial still counts.
Financial order metrics elsewhere are unchanged. No payment/user data writes.
Live snapshot after deployment: active keys34, active trials13, unique paid19,
first buyers today0. Historical missing/imported payment records remain a
limitation: first means first recorded qualifying payment, not independently
verified bank settlement.
