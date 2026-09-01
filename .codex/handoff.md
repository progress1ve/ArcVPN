# ArcVPN current handoff

Updated: 2026-09-01. This file is current state, not a diary.

## Authority and topology

- Production/control plane: Poland `217.60.33.38`.
- Remnawave owns active subscription delivery; preserve existing URLs and UUIDs.
- Main DHost nodes: Germany and Netherlands. Product LTE allowance is now modeled
  independently (0/45/115 GB on the user's shared calendar-month anniversary); do not restore the old customer
  `x10` model.
- Canada was dropped. Vyrex canary was cancelled. Finland was retired from public delivery on 2026-08-24 and must not be reintroduced implicitly.

## Current product state

- **Whitenode-style five-profile fallback is deployed at `28e5635`.** Estonia has an x1 Remnawave XHTTP inbound on
  loopback port 10001, active in the existing LTE squad, plus nginx origin
  proxying `/api-test`; the connected node and LTE squad each report three
  inbounds. The existing `cdn-de.arccnet.space` Yandex resource may keep its
  historical domain while using Estonia as active origin and Netherlands as
  Yandex-level backup. The separate `cdn-nd.arccnet.space` Netherlands CDN is
  still in service. Two owner-only manual XHTTP links were exported to the
  gitignored local `.secrets/owner-xhttp-cdn-links.txt`; never paste their UUIDs
  into chat or docs.
- Happ catalog order fix is deployed at `d3c3983` and owner-controlled: Auto, YouTube, Estonia,
  Netherlands, Germany, then five bypass rows. Subscription-wide
  `lowestdelay` autoconnect and ping-on-open metadata must remain absent because
  Happ otherwise reorders visible locations by latency. Internal Xray
  `leastLoad` inside Auto/bypass profiles remains required. The first bypass
  display label is exactly `🇪🇺 Лучший обход`.
- The earlier one-row subscription draft is rejected and must not be restored.
  The deployed implementation preserves five visible bypass
  rows, rename only `Обход глушилок #1` to `🇪🇺 Лучший обход`, give that row an
  Estonia-primary/Netherlands-reserve XHTTP fallback, and make the other rows
  follow the accepted Whitenode behavior. Happ/Xray measures latency client-side
  and does not directly know Remnawave active-user counts; do not invent a second
  server-side weighting algorithm.
- The owner then selected the public `vozduh443/Whitenode-balancer` behavior as
  the exact model for **all five** visible bypass profiles: Burst Observatory
  probes both ordinary and hidden CDN outbounds, `leastLoad` selects a healthy
  ordinary outbound, `fallbackTag` moves traffic to hidden CDN only when the
  ordinary set is unavailable, and recovery returns traffic to ordinary
  infrastructure. The production focused tests pass, the subscription service is
  active, credential-safe public verification passes, and Xray Core 26.3.27
  accepts all 13 generated configs. A controlled real-client censorship outage
  and recovery observation remains open. Independently implement the small routing contract; do not
  copy unrelated DNS/domain lists from the external example and do not claim it
  accounts for Remnawave user counts. The repository exposes no license in its
  root, so treat it as a behavior reference, not a code dependency.
- Censorship-resistant subscription refresh through CDN is explicitly deferred
  by the owner on 2026-09-01. Preserve every existing
  `https://sub.arccnet.space/sub/...` URL and current public DNS. The prepared
  EE/NL nginx `/sub/` origin routes may remain dormant, but do not add the Yandex
  hostname, change its certificate/cache policy, cut DNS, or create another CDN
  resource until the owner resumes this stage. The prepared design places the
  hostname behind the existing Yandex CDN resource; EE and NL nginx origins proxy
  `/sub/` directly to the Poland IP using verified TLS/SNI, avoiding a DNS loop.
  If resumed, dynamic responses must remain uncached and the origin/CDN/revocation/
  Happ-refresh gates must be repeated. Two-user direct/EE/NL byte and header
  parity was already verified, but it is only retained evidence for the deferred
  stage.

- Agent workflow contracts now treat public URLs, topology, pricing, callbacks,
  and visible UI as zero-assumption contracts. Node/CDN stages require an accepted
  route table before mutation and real tunnel evidence after it. Active node
  references now consistently specify x1 CDN/XHTTP accounting. Use
  `$arcvpn-repo-hygiene` for classified cleanup; never delete or restore the
  owner's dirty files. `.codex/stages/current.md` is currently oversized with
  completed history and should be compacted only as a separately approved cleanup.

- Russia-safe Telegram entry and the mobile admin dock are deployed at
  `c542d5e`. The standalone login no longer depends on Telegram's iframe: ArcVPN
  renders its own full-width button and receives the destination from public
  config as `https://t.me/<bot>?start=site_login`. The existing generic `/start`
  handler clears stale bot state and renders canonical onboarding/cabinet; Mini
  App and email auth are unchanged. Telegram may still show its own mandatory
  first-time Start confirmation. The direct Telegram HMAC backend remains in
  place but is no longer exposed by the UI. On admin widths up to 560px the dock
  now has fixed border-box geometry, safe-area spacing, reserved content space
  and non-distorting horizontal navigation. Local evidence is 151 tests and a
  Vite build; production serves the new bundle/config, focused tests are 7/7,
  the subscription service is active and its post-restart error journal is
  empty.

- Renewal tariff Back destination is corrected at `24ca0d6`: it now calls the
  canonical `start` handler and returns to the full bot personal cabinet with its
  cover, subscription status and primary actions, not the text-only `Моя
  подписка` view. The shared purchase keyboard keeps `Создать свой тариф`
  immediately before Back. Local result is 146 tests; production focused result
  is 6 tests, bot active and the warning journal empty.

- Renewal Back active-subscription rendering is repaired at `0944546`. The first
  fix exposed a second production NameError in `_subscription_urls()`, which read
  a bare `SUBSCRIPTION_URL` despite importing `config`; it now uses the configured
  value. Regression coverage executes both empty and active subscription renders.
  Local result is 146 tests; production focused result is 6 tests, bot active and
  the post-restart warning journal empty.

- Bot product selection navigation is deployed at `5b6f869`. After Economy,
  Standard and Family it shows `Создать свой тариф`, opening the configured
  WebApp directly at `/app?screen=custom-tariff`; the query boots into the custom
  builder. Local evidence is 145 tests plus Vite build and a
  direct authenticated deep-link browser check; production has both services
  active, 5 focused tests passing, current public bundle/health and empty warning
  journals.

- Custom tariff purchase/renewal and compact connection artwork are deployed
  through `4cd3f45` (`eeed783` pricing base). Site and Telegram WebApp expose `Создать свой тариф` below the
  fixed product selector; the dedicated builder offers 1-10 devices, 0/15/30/45/
  75/115 GB bypass allowance and 1/3/6/12 months. Server pricing is derived from
  the live Economy/Standard/Family anchors per period. Exact Economy, Standard
  and Family entitlement matches keep the catalog price; other combinations use
  an internal flexibility premium, and any custom option with bypass traffic has
  a 100 RUB-per-purchased-month floor. Thus 1 device/15 GB/3 months is 300 RUB
  and Standard 3/45/3 months is 399 RUB. No markup wording is customer-visible.
  Multi-month custom quotes show their saving against the equivalent one-month
  price multiplied by the selected period. Out-of-range choices are rejected and
  paid requested entitlements are stored.
  Payment and promo quotes share the same authoritative server calculator.
  Happ/INCY phone silhouettes are 138 px on mobile, fit entirely inside their
  cards and do not overlap labels. Cold standalone visits show a neutral session
  check instead of flashing the cabinet; successful automatic email verification
  refreshes the authenticated state immediately. Mobile standalone subpages have
  Back, while Telegram mobile keeps its native control. Notification preferences
  appear only in Telegram WebApp and use true 46x26 capsule switches. Full
  evidence: `142 passed`, Vite build, four responsive viewports without overflow,
  payment-sheet transition, production health/bundle/live-catalog quote and empty
  warning journal. No subscription URL, UUID or existing entitlement was changed.

- Referral and in-page VPN setup corrections are deployed at `1e9df54`. Referral
  has the plain section heading, direct +5/+15-day terms, site/Telegram link
  choice, counters, copy and QR controls, and the supplied gift composition with
  real alpha. Setup offers only iPhone/iPad, Android, Windows and Linux, then
  larger Happ/INCY choices with exact install destinations and direct Happ or
  official encoded INCY import. FAQ contains four entries. Local evidence is a
  successful Vite build, `131 passed`, an INCY round-trip, alpha inspection and
  four responsive viewports; production service/health/bundle/asset passed.

- A credential-safe 2026-08-31 investigation of two Happ refresh/ND-ping reports
  found no subscription or node outage. One user recovered after deleting and
  reimporting the subscription. For the other, the ArcVPN key and Remnawave user
  are active/aligned, public delivery returns 200, the published structure matches
  the recovered user's profile, active nodes are connected, and a real tunneled
  HTTP canary using that user's published Hysteria profile returned 204. Preserve
  the UUID/URL; ask the client to delete the stale Happ profile and reimport before
  considering account mutation.

- Customer-feedback and referral UX is deployed at `6ef14e3`. The day-one trial
  prompt now records actionable categories (connection, speed, service, setup,
  other, or working well) plus optional details; Overview shows the distribution
  and recent answers while legacy numeric replies remain readable. Active main
  usage is reconciled from the Poland Remnawave authority and failed lookups do
  not overwrite cached counters; production currently has 20 of 24 active key
  rows with non-zero main usage. Standalone email uses one neutral passwordless
  code flow that resolves login versus registration server-side. Support FAQ,
  notification copy/pills, referral artwork, real QR and copy toast are current.
  Local evidence: `131 passed`, Vite build, four responsive viewports without
  horizontal overflow; production services/health/asset/public login passed.

- Standalone email registration and the paid-trial funnel are deployed through
  `2fa9072` on Poland with schema v60. Email-only accounts receive no free trial;
  an eligible account is offered one server-priced 10 RUB Standard trial for
  7 days with unlimited main traffic, 5 GiB LTE and 3 devices. An atomic per-user
  claim blocks concurrent provider checkouts before YooKassa and is released only
  after cancellation/failure. Admin exposes the paid-trial cohort and subscription
  mutations render their returned snapshot immediately. Local evidence is
  `119 passed` plus a successful Vite build. Real delivery/payment/saved-method
  acceptance remains pending and must not be claimed as passed.
- Onboarding/billing/quota/WebApp runtime is deployed through `83c3298` on Poland.
  Production schema is v57; 20 users have calendar anchors, the due-reset preview
  was zero at deployment, and the old first-of-month reset is disabled.
- Growth/billing/LTE runtime is deployed through `f6b3156`: Economy, Standard and
  Family have 1/3/6/12-month products; trials are durable Standard entitlements;
  campaign attribution, configurable bonuses, promo activation, independent LTE,
  two-step bot purchase UI, and the WebApp family/period flow are implemented.
- Production schema is v56. Thirteen active keys were migrated to Standard without
  changing UUIDs/public subscription URLs. The explicitly authorized inactive
  never-paid cleanup deleted 135 users after dry-run and separate backups; both
  post-operation previews returned zero.
- Subscription assembly is hybrid by design: Remnawave is the authoritative
  share-link source while ArcVPN remains the stable URL/device/announce/Happ
  compatibility gateway. Legacy generation is an observable fallback and must
  remain until production source metrics demonstrate a zero-fallback soak.
- Trial provisioning now creates/reuses one unlimited-main Standard Remnawave
  identity plus a separate 5-GiB LTE identity. Exact
  production backfill provisioned 2 missing trials after a separate backup;
  repeated preview is zero. Protected Remnawave config has the explicit
  `production` write gate; secrets remain outside Git.
- `/` and `/app` are the standalone customer login/cabinet; `/admin` is the
  separate noindex admin surface. Promo validation/revalidation, one-time email
  code consumption, calendar reset fields, legal-consent versioning, full LTE
  announce, favicon and manifest are deployed. Crypto and Stars are absent from
  customer payment UI/routers.
- Login/branding/tariff follow-up is deployed at `33fad1e`: the supplied white
  Arc mark is used by the app/manifest, standalone login offers Telegram plus
  email with centered composition, tariff copy explicitly states LTE allowance
  and device count without emoji, the promo input no longer draws a rectangular
  focus highlight, and admin password cookies persist for 30 days.
- LTE identity isolation is deployed through `36db815` (runtime layout commit
  `662e8bb`) with schema v58. Fourteen active main identities are unlimited and
  remain on the four-inbound main squad; fourteen separate LTE identities are
  limited to the two reviewed XHTTP inbounds and 0/45/115 GiB entitlement.
  Scheduler reconciliation mirrors LTE Remnawave usage into WebApp/header state.
  Public URLs and main UUIDs are unchanged.
- Customer/LTE layout is deployed through `ffc0915`. Happ delivery is exactly:
  AutoSelect, YouTube without ads, Netherlands VLESS/Hysteria2, Germany
  VLESS/Hysteria2, then five `🇪🇺 Обход глушилок #1..#5` rows. The primary and all
  five bypass rows are main least-load profiles with hidden LTE XHTTP fallback;
  no customer row is a direct XHTTP profile. Burst observatory returns new
  connections to main after recovery; a real Happ outage/recovery canary remains
  the behavioral gate. Main/LTE credential crossover is rejected and covered by
  credential-safe production verification. Finland is
  hidden from subscriptions and admin surfaces; disconnected Remnawave records
  remain intentionally undeleted.
- TikTok forced routing is deployed through `07bf9a2`/`c595bd6`. Explicit
  TikTok/ByteDance domains are proxied before `geoip:ru` and other direct rules
  in legacy routing and every Happ JSON row, including all five bypass profiles;
  their existing main-to-LTE fallback remains unchanged. Production recursive
  verification reports `tiktok_routing_ok=true`. A real affected-device TikTok
  canary during throttling is still required.
- Estonia 1chost is admitted as an active normal Remnawave node through
  `20e050a`/`4ca2ac6`. `ee.arccnet.space` publishes one TCP Reality and one
  Hysteria2 row immediately before the Netherlands pair (`2f32b94`); both are in the main
  squad and AutoSelect. Real tunneled HTTP returned 204 on both transports,
  production shows 13 Happ rows with two Estonia AutoSelect outbounds, and LTE
  identity isolation remains intact. Inventory alias is `ee-1chost`; node control
  port is restricted to Poland.
- Happ node-setting hardening is deployed through `b8308c7`: `hide-settings: 1`
  remains in HTTP and plain/base64 metadata, and every browser/device-scoped Happ
  import now carries the configured eight-character Provider ID in the official
  URL fragment. Public transport verification and 124 local tests pass, but the
  owner's real client still exposed settings before this follow-up. Behaviour is
  not accepted until the same ID is confirmed in the Happ provider dashboard
  with `sub.arccnet.space`, then the subscription is deleted/reimported in a
  current client. Production has no explicit provider-ID environment override
  and uses the repository value. Even when accepted this is client UI/export
  hardening, not cryptographic secrecy against modified/rooted clients.
- Three active legacy trials were reconciled after a separate backup: all now
  have unlimited main traffic, exactly 5 GiB LTE and a separate LTE identity.
  DNS v2 is enabled only for Telegram ID `2075630349`; the global profile remains
  legacy pending the owner's short Wi-Fi/LTE canary.
- Purchase UI now defaults to SBP, vertically centers the wide flow, and all tariff
  descriptions/customer cabinet surfaces state unlimited main traffic plus a
  separate LTE allowance. `panel.arccnet.space` serves admin only (`/app` is 404).
  `arccnet.space` now resolves to Poland, has a valid Let's Encrypt certificate,
  serves the customer cabinet at `/` and `/app`, and is the Telegram Mini App
  origin through `WEBAPP_URL`. Stable subscriptions remain on `sub.arccnet.space`.
- LTE scheduler reconciliation is fixed in `ec6620c`: the environment-backed
  Remnawave authority now has a stable cache identity. For the owner's account,
  Remnawave usage, local LTE usage and the public subscription header matched
  byte-for-byte after production deployment. Sync runs every minute.
- Self-hosted SMTP on Poland remains infeasible: no MTA is installed, outbound
  25/465/587 are blocked, PTR is provider-owned and mail-auth DNS is absent. SMTP
  relay port 2525 is reachable for Mailjet and Brevo. Prefer Mailjet Free after the
  owner creates/verifies the account/domain and supplies credentials outside Git.
- Mailjet domain validation bootstrap is deployed through `b9d7829`. SPF and
  DKIM are confirmed, and the exact empty verification URL returns HTTP 200, but
  Mailjet still shows the domain as Pending and transferred the ticket to a
  specialist group. The domain label is display-only and does not affect this
  validation. A
  local global Codex MCP entry named `mailjet` points to a DPAPI-aware launcher;
  the Mailjet API key/secret has not yet been generated/stored, so the integration
  is configured but intentionally unauthenticated. Store it using
  `C:\Users\babay\.codex\mcp\mailjet-credential.ps1 -Action Set`, then start a
  new Codex task/session and verify a read-only Mailjet tool before sending mail.
- Resend replaced Mailjet for OTP delivery. The verified `arccnet.space` sender
  uses STARTTLS on port 2587; production SMTP authentication and an acceptance
  delivery passed. The secret is in the encrypted local vault and a root-only
  production environment file, never Git. Run one real user OTP inbox check.
- Production subscription audit for Telegram ID 2075630349 found identical DNS
  JSON across all eleven Happ profiles and two intentional routing families.
  Germany Reality #1 now publishes `de.arccnet.space` from both the authoritative
  Remnawave Host and ArcVPN fallback metadata (`0ce2d47`); the domain resolves to
  the same active node and all non-address Host fields were preserved. Fresh
  plain/base64/Happ JSON contain no former literal connection endpoint. A real
  Germany Reality client tunnel remains the final canary.
- Whole-admin operations redesign base was deployed at runtime commit `9c77b67831f163605678c9b476d5c3b72741e349`; its original production evidence is recorded in `.codex/stages/current.md`.
- Tariff-transition/admin telemetry follow-up is deployed on Poland at `8fb6077`.
  Active cross-plan renewal preserves remaining days and applies the new local
  and Remnawave LTE quota/device/enablement contract; Economy disables LTE.
  Admin Users now exposes per-user main/LTE usage with top sorts/filters and
  updates expiry immediately after a verified mutation. Password login issues a
  30-day Lax/Secure/HttpOnly cookie and renders owner access immediately. Health
  displays real Poland uptime. Hysteria customer labels contain no lightning.
  Local result: 114 tests and Vite build pass; production services are active.
  Owner login/reload, one designated safe manual days mutation and fresh touched-
  view mobile/tablet/wide captures remain final external acceptance gates.
- Real Overview/Health/catalog/SEO follow-up is deployed at `a4e6890` on Poland.
  Overview now exposes real D/W/M joins, paid orders/revenue, acquisition source,
  product mix and current-cycle main/LTE usage. Health uses active Remnawave nodes
  plus Poland memory/load/disk/service signals. Panel root redirects visibly to
  `/admin`; the public apex has ArcVPN/Арк ВПН metadata, robots and sitemap.
  Catalog and freshly generated subscriptions agree on AutoSelect, NL/DE pairs,
  YouTube without ads and five EU LTE profiles. Ten stale overrides were backed
  up then cleared; stable user URLs/UUIDs were unchanged. Local result: 110 tests
  and warning-free Vite build.
- All 11 owner sections passed authenticated production composition/overflow checks at mobile, tablet, desktop, and wide viewports. Capability-aware navigation/RBAC, honest state machines, role management, truthful Schemes/Nodes/Backups language, and immediate verified subscription-panel synchronization are implemented.
- Trial feedback follow-up is deployed through `d27d11e`. The bot sends one
  rating prompt no earlier than 24 hours after `trial_entitlements.activated_at`,
  excludes both current and legacy rating events, and still accepts old buttons.
  Admin Overview exposes sent/answered totals, response rate, average,
  distribution and recent respondents. Bot Settings links to the existing email
  verification screen, and renewal Back returns to the subscription list. Local
  result: 128 tests and Vite build pass; production emitted 9 eligible prompts,
  both services are active and journals contain no errors.
- The stage remains **in progress**, not closed: a real keyboard-only activation pass, one explicitly authorized production Support reply, and a designated safe disabled Remnawave identity for live revoke confirmation are still pending. Do not infer permission to mutate a real user or send a Support message.
- The non-operational Schemes editor and its graph dependency were removed in `d111e11efa5f86738e54fc6e464fabe3e2dc9bb6`. Axottle-only infrastructure features without ArcVPN backend contracts remain explicitly deferred/rejected in the current stage matrix.
- Frontend changes require live browser inspection at four viewport classes, not only code/tests.
- Node configuration facts live in `.codex/references/node-config-contract.md`.
- Non-secret server topology lives in `.codex/server-inventory.toml`; active Poland/Germany/Netherlands credentials are local DPAPI entries managed by `scripts/ops/server-vault.ps1`.
- Use `$arcvpn-node-ops` for node, Remnawave, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, or certificate work.

## Next recommended stage

Wait for Mailjet's specialist review of the already public and SPF/DKIM-confirmed
sending domain, publish an initial DMARC policy, provide production SMTP credentials outside Git, then run
a real linked-email delivery/login and authenticated promo/payment pass. Execute
the DNS v2 client canary on Wi-Fi/mobile and at least two Happ platforms before
enabling `ARCVPN_DNS_PROFILE=v2`. Reconcile one real user's local/Remnawave/WebApp
normal and LTE usage at their anniversary, run a real Standard-user LTE
exhaustion/main-survival canary, and complete keyboard-only production acceptance.
Do not claim the stage complete while these gates remain open.

## Starting a new chat

Read `AGENTS.md`, this file, `.codex/project-index.md`, and `.codex/orchestrator.toml`. Use the stage skill for non-trivial work. Search `AI_CONTEXT.md` only when a named historical fact is missing.
