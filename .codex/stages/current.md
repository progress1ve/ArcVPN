# ArcVPN design and website onboarding — 2026-10-10

Mode economy; no subagents (owner contract). Production publication explicitly authorized. Release isolated in codex/design-polish-release; primary owner work preserved and behind production. Poland is runtime authority; Moscow serves public static assets. No DNS, TLS or node/protocol changes.

## Accepted behavior

- Landing top navigation has no backdrop or active underline, per final owner correction. After scrolling, near-black glass with a cold light edge and pill.
- Contextual Back: addons opened from renewal return to the same selected tariff/period; devices return to home or settings according to entry point.
- New verified website email account automatically gets one free day, Standard, three devices, 5 GB bypass, no card or recurring charge. Existing Telegram trial policy preserved. Durable entitlement makes this once per account; failed provisioning is retryable and commercial accounts are ineligible.
- Optional 10 RUB purchase adds seven days on the same free-trial key/URL. Future recurring subscription is ordinary monthly Standard, currently145 RUB/30 days. Checkout verifies displayed price and snapshots consent. Legacy checkouts without that snapshot cannot acquire the higher charge.
- Trial-specific payment pending/canceled/review/success; no normal399 RUB renewal dialog after10 RUB trial. Email can be corrected.
- Groq answers use Happ/INCY instructions, plain text and bounded requests. Automatic admin notices go only to owner2075630349; second admin access stays.

## Evidence before publication

PASS:129 focused backend tests (24.83s), including one-time trial, retries, eligibility, payment race, unchanged key, snapshot/price changes, migration, provider/prompt/timeout and support access. Latest Vite build184 modules/5.11s; mapped customer views have no Svelte warnings. Old hashed assets retained.

PASS: local browser360/768/1280/1600 no horizontal overflow; landing price baselines match across columns at tablet and desktop. Variable Manrope loads. Transparent top and blur24px scrolled navigation observed. Contextual Back preserves six-month/759 RUB selection and both device entry paths.

PASS: DEV email invalid code/change email/correct code leads to1 day,0/3 devices,5 GB. Pending, canceled (still gets free day), review and success use isolated previews. No real email or banking transaction. Real SMTP environment exists.

PASS: real Groq candidate inference0.52/0.58 seconds with correct Happ/INCY instructions. Earlier owner-only controlled outage/recovery notifications delivered. Alerts detect actual inference failures, not an idle periodic provider probe.

Evidence: primary .codex/stages/evidence/design-20261009/: trial-tests.local.log, release-build-trial.local.log, final-responsive.local.json, free-day-mobile.local.jpg, trial-success-mobile.local.jpg, nav-*-final-1600.local.jpg. Old drafts superseded.

## Publication and rollback

Runtime base847d28f992770bcea428ca686acb6e232312080b, schema75. Public static basee0e6b70cbe29d4b6356e812e2599f9b07327ed05. Migration76 adds nullable payment renewal amount/period only. Back up live SQLite before migration; restart bot/API only. Publish committed static build atomically to Moscow; verify public assets, frontend and services. Published runtime/static71e2fd8d692e7ae53ccc49c4bc6212980f7880c1; docs closeout follows separately.

Rollback: revert runtime commit without removing additive columns, switch static symlink to retained e0e6b70 release. Preserve users/UUIDs/subscription URLs. Owner checkout and remote ssh_askpass excluded. Remaining external checks: real new-email delivery, paid checkout/renewal, Telegram keyboard, search recrawl/ranking and owner visual acceptance. Next: publish and record live evidence.


## Live acceptance and closeout

PASS: Poland fast-forward pull to71e2fd8d, SQLite online backup/integrity verified0600, migration76 and nullable consent columns verified, bot/API active after restart. No existing weekly10 RUB recurring configurations were changed. Moscow archive SHA256 b6e9ca3d3d04389aae5b68f589d543288ef420356c613aa82f0896fa3d0ef150 verified, same committed static assets published.

PASS: public /,/app,new JS/CSS/vendor fonts,robots,sitemap,public catalog/config200. Unauthenticated trial APIs401. Public browser four widths360/768/1280/1600 fonts loaded,no overflow; top background transparent/active pseudo-line none; scrolled blur24px/cold glass. Proof nav-top-public-1600.local.jpg,nav-glass-public-1600.local.jpg,public-responsive.local.json. Real postdeploy Groq first-connect answer0.8 seconds/correct Happ/INCY.

Deployment deviation: initial static extraction omitted nginx-required app/ nesting and caused a brief404. Previous symlink restored, app/ nesting corrected, release republished and actual HTTP/browser200 verified. No nginx configuration changed. Required static layout now recorded in handoff.

Residuals DEFERRED: real email delivery/bank purchase/recurring debit, Telegram keyboard, search recrawl and owner visual acceptance. Existing scheduler Telegram delivery warnings for email-only identities/blocked recipients observed. Next: owner tests one fresh website signup and optional bank checkout. Stage implementation and authorized publication complete; no real test charge performed.
