# Current stage: redesign five bypass fallbacks after rejected simplification

## 2026-09-01 repair INCY import from site and WebApp

Goal: make the INCY import button open its encrypted `incy://crypt1` deeplink
inside the original user click on both the website and Telegram WebApp. Show the
same neutral `Поддерживается` badge for Happ and INCY.

Acceptance: the browser-safe synchronous INCY encoder is used; the WebApp opens
an HTTPS bridge on the ArcVPN domain and its blank black page automatically
opens the generated `incy://crypt1/` link; both app cards say `Поддерживается`;
the desktop back button sits inside the centered connection header; production
build and focused regression tests pass. Responsive browser inspection is
excluded by owner request.

Risk and rollback: only the app-choice UI and INCY deeplink generation change.
Revert the frontend commit and rebuild `webapp_dist`; subscription URLs, device
registration, Happ import, server profiles, and VPN services remain untouched.

## 2026-09-01 remove ineffective Happ sort control and show client step

Goal: remove the ineffective advanced `subscriptions-sort-type` metadata now
that ArcVPN intentionally has no Happ Provider ID. Do not add a UI instruction
or require manual client configuration. The dedicated Auto profile remains the
only latency-based selection mechanism.

Acceptance: Provider ID and every sort-control metadata field are absent from
public/import responses; server JSON order remains fixed; no sorting instruction
is added to the UI; build/tests and production/public checks pass.

Non-goals: no Provider ID, paid Happ feature, node/CDN/DNS change, or modification
of internal Auto/Whitenode `leastLoad`. Existing Happ local state cannot be
changed by ArcVPN without the external Provider integration.

Rollback: revert the runtime commit, rebuild `webapp_dist`, deploy, and restart
only `arcvpn-subscription.service`. No identifiers or database rows change.

## 2026-09-01 remove Happ Provider ID and force backend order

Goal: remove the external Happ Provider ID dependency from every import and
refresh path, and explicitly request `subscriptions-sort-type: without` so the
visible catalog follows the backend JSON order. The dedicated first Auto profile
remains the only latency-based customer choice.

Acceptance: no Provider ID exists in import URLs, bodies or response headers;
plain and HTTP metadata both carry `subscriptions-sort-type: without`; JSON order
remains Auto, YouTube, Estonia, Netherlands, Germany and five bypass rows; public
URLs/UUIDs/access remain unchanged; focused/full and public checks pass.

Non-goals: no Happ paid/remote-management integration, no node/CDN/DNS changes,
and no change to internal Whitenode `leastLoad`. CDN subscription refresh remains
deferred. Existing clients may need one delete/reimport because Happ documents
Provider association and app settings as client-side state.

Rollback: revert the runtime commit and restart only
`arcvpn-subscription.service`. No database or identity migration is involved.

Closeout: **passed** at runtime commit `56a2c14`. Local focused/full results are
`13 passed` and `151 passed`; production focused result is `13 passed`.
Credential-safe public verification confirms Provider ID absent from headers,
subscription body and import page; `subscriptions-sort-type=without`; 13 profiles
remain in the accepted order. Service is active and the post-restart journal has
zero error/exception/traceback matches. Public URLs, UUIDs and authorization are
unchanged. Rollback is `git revert 56a2c14`, deploy and restart only the
subscription service. Residual client-side state: an already imported Happ
subscription may require delete/reimport once to discard its former Provider
binding and cached sort choice.

## 2026-09-01 fixed Happ catalog order and CDN-refresh deferral

Goal: display the first bypass profile exactly as `🇪🇺 Лучший обход` and keep the
server-defined Happ catalog order without client-side lowest-delay reordering.

Non-goals: do not change the internal Whitenode `leastLoad` behavior inside the
explicit `Автовыбор`/bypass profiles; do not change nodes, CDN origins, DNS,
certificates, UUIDs or public subscription URLs. Subscription refresh through
CDN is explicitly deferred: keep the public DNS unchanged and do not create or
modify a Yandex CDN resource for it.

Accepted visible order:

1. `Автовыбор | Самый быстрый`
2. `🇷🇺 Ютуб без рекламы`
3. Estonia profiles in protocol order
4. Netherlands profiles in protocol order
5. Germany profiles in protocol order
6. `🇪🇺 Лучший обход`
7. `🇪🇺 Обход глушилок #2` through `#5`

Acceptance: JSON array order matches the list; plain/HTTP subscription metadata
does not request `lowestdelay` autoconnect or ping-on-open; internal fallback
balancers remain unchanged; focused/full tests pass; production service and
credential-safe public order verification pass.

Risk and rollback: existing Happ clients may retain a locally reordered cache
until refresh/reimport. Roll back the runtime commit and restart only
`arcvpn-subscription.service`. Public identifiers and authorization are unchanged.

Topology table: no topology mutation in this stage. All client/CDN/origin/SNI/
inbound paths and x1 multipliers remain byte-equivalent; only visible label/order
metadata changes. CDN subscription-refresh work is deferred with no public cutover.

Closeout: **passed**. Runtime commit `d3c3983` was pushed and fast-forwarded on
Poland; only `arcvpn-subscription.service` restarted. Local focused/full results
are `9 passed` and `152 passed`; production focused result is `9 passed`.
Credential-safe public verification returned 13 profiles in the exact accepted
order, `eu_best=true` and `lowestdelay_headers_absent=true`. Service is active and
the post-restart journal scan reports zero error/exception/traceback matches.
The immediate post-restart verifier initially hit the normal readiness window
with connection refused; the bounded readiness retry and every subsequent public
check passed. Rollback is `git revert d3c3983`, deploy, and restart only the same
service. Residual client risk: Happ may retain its old local ordering until the
subscription is refreshed or reimported. Next step is only a real-device refresh;
subscription refresh through CDN remains deliberately deferred.

## 2026-09-01 corrected contract gate

Status: **runtime deployed; Yandex subscription-host cutover and a controlled
censorship failover canary remain open**. The earlier interpretation (replace all five bypass rows
with one Netherlands-only row) is rejected. Preserve five visible bypass rows;
rename only row #1 to `Лучший обход`. All five profiles must independently
implement the behavior contract demonstrated by `vozduh443/Whitenode-balancer`:
ordinary and hidden CDN outbounds are probed by Burst Observatory, selected with
`leastLoad`, CDN is activated through `fallbackTag` only when ordinary outbounds
are unavailable, and ordinary routing returns after recovery. Do not copy the
reference project's unrelated DNS/domain lists. Its behavior is client-side
health/RTT selection, not a Remnawave active-user counter; do not add a second
load algorithm unless the owner separately requests one after this contract.

Current infrastructure: Estonia has a backed-up x1 XHTTP inbound active in the
LTE squad and nginx origin on port 80; `cdn-de.arccnet.space` can front Estonia
without renaming the existing Yandex resource, while `cdn-nd.arccnet.space`
continues to front Netherlands. Owner-only manual links exist solely in the
gitignored `.secrets` path recorded in the handoff.

Additional deliverable: keep the stable `sub.arccnet.space/sub/...` contract but
serve it through the existing CDN resource so clients can refresh during origin
blocking. Both CDN origins proxy `/sub/` directly to the Poland IP with verified
TLS/SNI, avoiding a DNS loop after the public CNAME cutover. Preserve the complete
request path, query, format and User-Agent behavior, disable all CDN/browser
caching for the personalized response, and preserve response metadata. The DNS cutover is gated
on two-user cache-isolation tests, revoked/expired behavior, direct-origin and
CDN fetch parity, Happ refresh during simulated origin blocking and a documented
TTL rollback. A cached response for one user appearing for another is a hard
security failure.

Implementation evidence: production commit `28e5635` preserves five visible
balancer profiles, renames only row #1 to `Лучший обход`, deduplicates and orders
the hidden CDN outbounds as Estonia (`cdn-de`) then Netherlands (`cdn-nd`), and
uses the Whitenode contract in every clone: Burst Observatory GET/10s/6 samples/
5s over both selector prefixes, one `leastLoad` balancer with 3s max RTT and the
Estonia CDN as `fallbackTag`. CDN telemetry and quota accounting are x1. Local
full suite passed (`151 passed`); production focused tests passed (`4 passed`),
the service is active, credential-safe public verification passed, and Xray Core
26.3.27 accepted all 13 generated configurations. A controlled real-client
censorship failover/recovery observation remains open and is not replaced by the
syntax gate.

No second CDN resource is required for subscription refresh. The existing CDN
origin group can accept `sub.arccnet.space` as an additional hostname. Both EE
and NL nginx origins now proxy only `/sub/` directly to the Poland IP over
verified TLS/SNI, so the later public CNAME cannot create a DNS loop. They force
private/no-store/no-cache headers and do not buffer. Credential-safe checks over
two distinct active subscriptions returned 200 through direct Poland, EE and NL,
with byte-identical bodies, identical Subscription-Userinfo, distinct bodies
between users and no-store on both origins. Yandex hostname/certificate/cache
configuration and DNS cutover remain an external gate; the current public
`sub.arccnet.space` DNS is unchanged.

## 2026-09-01 fallback simplification and stability audit

Goal: make the Happ customer fallback expose one Netherlands CDN route named
`Лучший обход`, remove Germany CDN from that fallback, account all CDN/XHTTP
traffic at the physical 1:1 rate, and determine whether the existing Germany CDN
resource can be safely retargeted to the Estonia origin without creating a new
CDN resource. Diagnose reported Germany/Netherlands connection drops before any
topology mutation.

Non-goals: no subscription URL, UUID, user authorization, tariff, quota,
ordinary Germany/Netherlands transport or Reality material changes; no CDN/DNS/
certificate/origin mutation until the reuse gate is proven.

Affected components: Happ JSON catalog/fallback builder and tests; production
Remnawave/CDN/DNS/node state read-only during the feasibility gate. Target
fallback origin is the existing Netherlands CDN edge. Candidate future origin
is `ee-1chost`; the Germany CDN resource is only a candidate for reuse.

Acceptance:

1. Generated Happ JSON contains one customer row named `Лучший обход`; its
   fallback balancer contains exactly one hidden CDN outbound, the Netherlands
   CDN host, with existing loopback-only activation and no background CDN probe.
2. Germany CDN is absent from customer fallback output; ordinary profiles and
   credentials remain byte-equivalent apart from the intentional catalog row.
3. Plain/base64 compatibility is explicitly checked and public Happ JSON is
   recursively inspected; subscription URL/UUID and user authorization remain
   unchanged.
4. Production NL CDN passes DNS/TLS/edge/origin/XHTTP and a real tunneled request
   before it becomes the sole fallback.
5. Germany/Netherlands instability audit records service uptime, resource/load,
   packet loss or transport evidence and does not equate ping/open ports with a
   working VPN.
6. Remnawave reports a `1.0` consumption multiplier for every delivered CDN/
   XHTTP edge; customer quota remains separate but no physical byte is multiplied.
7. Reuse of the Germany CDN resource for Estonia is approved only if its origin
   group can be changed, Estonia has an isolated x1 XHTTP origin and inbound,
   the chosen public hostname/certificate remains valid or is safely replaced,
   and rollback can restore Germany without rotating user identities. Otherwise
   it remains deferred.

Risks: a single fallback edge removes redundancy; stale Happ imports keep old
profiles until refresh/reimport; CDN retargeting can interrupt existing Germany
LTE traffic. Rollback: revert the subscription commit and restart only the
subscription service; any future CDN move must first remove its Host from public
delivery, preserve the old origin-group values, and restore them on failed gates.

Verification matrix: focused builder tests; full local suite; production source
profile comparison; recursive JSON assertion; NL CDN edge/origin plus real Xray
tunnel; node/service/journal/resource checks; public profile re-fetch after
deployment.

Interim status: **Estonia origin prepared; Yandex resource update and public gate pending**.
Local builder/full suite passes (`151 passed`): one `Лучший обход`, one hidden
`cdn-nd` outbound and no `cdn-de` fallback. Production Remnawave reports both
delivered DHost nodes connected with `consumptionMultiplier=1.0`; the retired
disconnected Finland LTE node is the only remaining x10 record and is not in the
delivered LTE squad. Three real Netherlands Hysteria canaries returned HTTP 204;
three Germany Hysteria canaries failed to establish the SOCKS tunnel, confirming
the Germany complaint at least for that transport.

The sole-fallback release is not safe yet: `cdn-nd` and `cdn-de` currently resolve
to the same Yandex GSLB resource, both present Yandex's default wildcard
certificate rather than an ArcVPN-domain certificate, verified HTTPS fails, and
direct OPTIONS probes to both origin `/api-test` sites return 404. Estonia is
connected and x1 but has only TCP Reality/Hysteria2; no isolated XHTTP origin is
configured. Repair needs authenticated Yandex Cloud access plus working DHost
SSH access (local DE host key is not enrolled; the stored NL password is rejected).
On 2026-09-01 the Estonia profile was backed up server-side, then gained the
`EE_1CHOST_LTE_XHTTP` inbound on loopback port 10001. The inbound is active on
the connected Estonia node, authorized in the existing ArcVPN LTE squad and the
node multiplier remains `1.0`. Nginx now accepts HTTP origin traffic on port 80,
maps OPTIONS to POST for `/api-test` and proxies it without buffering to XHTTP.
The post-change preview reports three active Estonia inbounds and three LTE
squad inbounds. No user UUID, subscription URL, quota or public Host changed.

The subscription runtime remains undeployed until Yandex is set to Estonia as
active origin, Netherlands as backup, HTTP origin protocol, OPTIONS allowed and
a Certificate Manager certificate valid for `cdn-nd.arccnet.space`. Germany
must be absent from the origin group. The current shared Yandex resource can be
reused; `cdn-de` removal from DNS/secondary hostnames waits for the public XHTTP
canary. The user-owned landing prompt remains untouched.

# Current stage: Russia-safe Telegram entry

## 2026-08-31 restore bot deep link

Goal: make Telegram entry visible without access to Telegram's website-login
iframe by replacing it with a native ArcVPN button that opens the bot using a
`start=site_login` deep link. Non-goals: no email, account, subscription, trial,
payment or node changes. Affected components: public login config, standalone
login UI/static bundle and focused config tests.

Acceptance: the button renders without loading any Telegram-hosted iframe; its
destination is `https://t.me/<current bot>?start=site_login`; the existing
generic `/start` handler accepts this payload, clears state and renders the
canonical cabinet/onboarding; Mini App auth is unchanged; keyboard focus and
mobile/tablet/desktop/wide overflow pass; Vite/full tests pass; production
bundle/service and public destination verify. Telegram may require a first-time
user to press its own Start confirmation, which cannot be bypassed by a website.
The admin console mobile dock must also stay fully inside the viewport, reserve
content space, respect the device safe area and remain horizontally scrollable
without distorted or clipped navigation controls at widths up to 560px.
Rollback: revert the runtime commit and restart only the subscription service.

Status: **passed and deployed at `c542d5e`**. The native button and public
`bot_url` are live, the old iframe/widget configuration is absent, and the new
JS/CSS bundles are public. The mobile admin dock uses fixed border-box geometry,
safe-area-aware placement, stable 48 px controls and reserved bottom content
space. Local result: Vite build and 151 tests. Production result: 7 focused
tests, active subscription service and no post-restart errors. The user-owned
landing prompt remains untouched.

# Current stage: Telegram login visual correction

## 2026-08-31 remove nested-button appearance

Goal: make the official Telegram Login control read as one centered button,
without the wide empty ArcVPN wrapper visible behind it. Non-goals: no auth,
session, email, cabinet or Telegram flow changes. Affected component is only the
standalone login CSS and rebuilt static assets.

Before evidence: production desktop host is 416x52 while its official iframe is
234x40, leaving a bordered dark rectangle around the blue Telegram button; the
user screenshot shows the same nested-button defect. Acceptance: transparent,
borderless content-sized host; centered 234x40 official control; balanced space
to the divider; visible focus; no horizontal overflow at mobile, tablet,
desktop and wide viewports; Vite build passes; production bundle is current.
Risk: Telegram may change iframe dimensions. Rollback: revert the CSS/build
commit and restart only `arcvpn-subscription.service`.

Status: **passed and deployed at `0b097c5`**. The ArcVPN wrapper now has zero
border, transparent background and exactly matches the official iframe: local
mobile/tablet are 238x40 and scaled desktop/wide are 261.8x44; client and scroll
widths match at all four viewports. Vite build passed. Production serves
`index-B9dzVAaN.js`, the host and iframe both measure 234x40 at the live default
viewport, the Telegram button is interactive, and the service is active. The
user-owned landing prompt remains untouched.

# Current stage: direct Telegram website login

## 2026-08-31 Telegram API authentication

Goal: replace the standalone site's Telegram-to-bot link with Telegram's
official website login flow and open the existing ArcVPN cabinet immediately
after successful Telegram authorization.

Non-goals: no Telegram Mini App auth change, no email-flow change, no account
merge, subscription, UUID, tariff, payment or node mutation.

Affected components: public auth configuration, a dedicated Telegram auth API,
web-session issuance, standalone login UI, focused auth tests and subscription
service.

Acceptance:

1. The standalone login screen shows an official Telegram authorization control
   rather than opening `t.me/<bot>`; Telegram mobile WebApp keeps initData auth.
2. Telegram authorization data is accepted only after constant-time HMAC-SHA256
   verification with the bot token and a fresh `auth_date`; malformed, forged,
   stale and unknown-user payloads cannot create a session.
3. A valid existing Telegram user receives the same 30-day HttpOnly/Secure/Lax
   website session used by email login and is taken into the existing cabinet
   without a page reload.
4. The login control has loading, unavailable and error states, keyboard focus,
   no overflow at mobile, tablet, desktop and wide viewports.
5. Focused/full automated checks and Vite build pass; production service is
   active, health/public assets are current, and the direct Telegram login flow
   is verified as far as possible without transmitting a real Telegram identity.

Risks: forged/replayed Telegram identity data, duplicate identities, popup
blocking and BotFather domain mismatch. Mitigations: server-only token use,
freshness bound, constant-time comparison, existing-user-only lookup, explicit
states and official Telegram widget. Rollback: revert the runtime commit,
restart only `arcvpn-subscription.service`, and restore the prior login bundle.

Verification matrix: API unit tests for valid/invalid/stale/unknown payloads;
frontend build; live before/after DOM and visual checks at 390x844, 768x1024,
1440x1000 and 1920x1080; production health, bundle marker and service journal.

Status: **runtime deployed, external acceptance blocked** at `0b7c4eb`.
Implementation and security acceptance passed: local full suite `151 passed`,
focused production suite `12 passed`, Vite production build passed, forged
production auth returned 401, service is active, the public bundle is
`index-DiMorTPU.js`, and all four viewport classes have exact client/scroll
width equality. The live official iframe is present on `arccnet.space` but
Telegram returns `Bot domain invalid`. The bot owner must add
`https://arccnet.space` under BotFather -> bot -> Login Widget -> Allowed URLs
(or `/setdomain` for the legacy widget). No code redeploy is needed afterward.
Do not mark the direct-login stage accepted until the live iframe shows the
Telegram authorization control and one owner-performed login reaches the
existing cabinet.

# Current stage: renewal Back returns to bot cabinet

## 2026-08-31 renewal navigation destination correction

Goal: make Back from the bot tariff-family screen return to the canonical bot
personal cabinet (`start`), not the separate text-only subscription details.
Non-goals: no cabinet redesign, pricing, WebApp, entitlement or node changes.
Affected components: shared tariff product keyboard, navigation assertions and
bot service only.

Acceptance: both purchase and renewal product keyboards keep the custom-tariff
button before Back; Back uses `start`; the registered `start` callback remains
the canonical cabinet renderer; focused/full tests pass; production bot restarts
active and the generated production keyboard uses `start`.

Risk is limited to one callback destination. Rollback is the runtime commit
revert and bot restart.

Status: **passed and deployed at `24ca0d6`**. Current renewal Back used `my_keys`, which correctly
opens the text-only subscription detail but does not match the requested main
cabinet shown in the reference screenshot. The cabinet callback is `start`.
The shared product keyboard now uses `start` for purchase and renewal while
keeping the custom WebApp action immediately before Back. Focused result: 6
passed; full suite: 146 passed; diff check passed.
Production is fast-forwarded to `24ca0d6`, the bot restarted active, all six
focused navigation tests pass in production and the post-restart warning journal
is empty. No cabinet layout, pricing, subscriptions or node state changed.

# Historical stages

# Current stage: active-subscription Back callback repair

## 2026-08-31 second renewal Back failure

Goal: make renewal Back render the active subscription screen end to end.
Non-goals: no keyboard layout, pricing, entitlement, WebApp or node changes.
Affected components: subscription URL helper, active-subscription regression
test and bot service only.

Acceptance: `_subscription_urls()` reads the configured subscription base without
an undefined global; a regression test executes `show_my_keys()` with an active
subscription through URL rendering; full tests pass; production bot is restarted
and a post-restart production execution of the active renderer succeeds with no
new `my_keys` NameError.

Risk is limited to the subscription-summary link. Rollback is the runtime commit
revert and bot restart.

Status: **passed and deployed at `0944546`**. Production evidence from the current PID showed the first
fix working past `webapp_url`, then failing at line 124 with `SUBSCRIPTION_URL is
not defined`; `_subscription_urls()` imported `config` but read a bare name. It
now uses `config.SUBSCRIPTION_URL`. The regression suite executes both empty and
active subscription Back renders, including the stable link and renewal button.
Focused result: 6 passed; full suite: 146 passed.
Production is fast-forwarded to `0944546`, the bot restarted active, the same six
focused tests pass in production and the post-restart warning journal is empty.
The landing-page generation prompt requested alongside this repair is stored at
`docs/design/arcvpn-landing-page-prompt.md`; it uses the established ArcVPN visual
system and preserves all existing application routes and business logic.

# Historical stages

# Current stage: bot custom-tariff entry and renewal back navigation

## 2026-08-31 bot purchase navigation correction

Goal: expose the WebApp custom-tariff builder directly from the bot product
selection and restore the Back action on the renewal product screen.

Non-goals: no pricing, entitlement, payment, subscription URL/UUID, node or
catalog changes.

Affected components: shared bot tariff-product keyboard, subscription summary
renderer, WebApp query-screen bootstrap, focused navigation tests, bot and
subscription services.

Acceptance:

1. A `Создать свой тариф` WebApp button appears immediately after Family and
   before Back for both initial purchase and renewal product menus.
2. The button opens the configured public WebApp at `/app?screen=custom-tariff`.
3. That query opens the purchase flow directly in custom-builder mode after
   authentication, retaining the existing default Standard-like values.
4. Renewal Back opens `Моя подписка` without an exception; the configured WebApp
   URL is defined when that screen is rendered.
5. Focused/full tests and Vite build pass; production bot and subscription
   services, public health/bundle and warning journals pass.

Risk: Telegram WebApp button URL construction and query bootstrap timing.
Rollback is the runtime commit revert plus restart of bot and subscription
services.

Status: **passed and deployed at `5b6f869`**. Root cause for Back was an
undefined `webapp_url` in `show_my_keys()`, which made the `my_keys` callback
fail while rebuilding the subscription screen. The shared keyboard now renders
Economy, Standard, Family, the custom WebApp button, then Back; its exact public
URL is `/app?screen=custom-tariff`. A browser navigation to that query opens the
custom builder directly with 3 months/3 devices/45 GB and the current 399 RUB
quote. A regression test executes the subscription-screen renderer after Back.
Focused result: 5 passed; full suite: 145 passed; Vite production build passed
with the pre-existing unused-selector warnings only.
Production is fast-forwarded to `5b6f869`; bot and subscription services are
active, public health and the custom-tariff WebApp URL return 200, the current
hashed bundle is served, all 5 focused tests pass on production and both service
warning journals are empty. No pricing, entitlement, URL/UUID or node state was
changed.

# Historical stages

# Current stage: custom tariff anchor parity and savings

## 2026-08-31 custom-plan pricing correction

Goal: make fixed-plan-equivalent custom configurations cost exactly the fixed
catalog price, while protecting margin on genuinely custom combinations and
showing multi-month savings clearly.

Non-goals: no fixed catalog price changes, entitlement changes, migrations,
subscription URL/UUID changes, node work or payment-provider changes.

Affected components: shared authoritative custom quote helper, matching WebApp
preview, custom quote/payment tests, generated WebApp bundle and subscription
service only.

Acceptance:

1. Economy 2 devices/0 GB, Standard 3/45 and Family 10/115 match their catalog
   price for every 1/3/6/12-month period.
2. Other combinations retain an 8% flexibility premium internally, but no UI or
   API copy labels it as a markup.
3. Any non-anchor configuration with bypass traffic costs at least 100 RUB per
   purchased month; specifically 1 device/15 GB/3 months is at least 300 RUB.
4. The server remains authoritative for payments and promo quotes and the client
   uses the identical anchor/floor/rounding rules.
5. For 3/6/12 months the price card shows the comparison total at the same
   one-month configuration price multiplied by the selected months, plus the
   positive saving when one exists; 1 month shows no comparison.
6. Builder, payment sheet and responsive states pass mobile/tablet/desktop/wide
   browser checks without overflow; focused/full tests and build pass; production
   health, bundle, service state and journal pass.

Risk: client/server drift around anchor matching and monthly floor. Tests cover
all anchors, the 1/15 floor and an intermediate non-anchor. Rollback is a revert
of the runtime commit and subscription-service restart.

Status: **passed and deployed at `4cd3f45`**. Before-state evidence:
Standard-equivalent custom was 431 RUB versus the catalog's 399 RUB, exposed an
8% markup label, and 1 device/15 GB/3 months was 82 RUB/month. After the change,
the two quotes are respectively 399 RUB and 300 RUB (100 RUB/month), and no
markup copy remains. Standard savings render as 435 -> 399 RUB (36 RUB) for 3
months, 111 RUB for 6 months and 271 RUB for 12 months. The 399 RUB payment sheet
matches the quote. Browser checks at 390x844, 430x932, 768x1024 and 1440x1000
all report zero horizontal overflow. Focused tests: 15 passed; full suite: 143
passed; Vite production build passed with pre-existing unused-selector warnings.
Production public health and WebApp return 200 and serve the new hashed bundle;
the production pricing suite passes 12 tests, the subscription service is
active/running and its post-release warning journal is empty. Existing fixed
prices, subscription URLs, UUIDs and user entitlements were not changed.

# Historical stages

# Current stage: custom tariff assembly markup

## 2026-08-31 custom-plan commercial guardrail

Goal: ensure the flexible tariff builder remains a convenience product rather
than a cheaper substitute for ArcVPN's already-discounted fixed plans.

Affected components: the shared server quote helper, matching customer preview,
focused pricing tests, builder copy, generated WebApp bundle and subscription
service only.

Acceptance: every custom quote receives an 8% assembly markup, rounded upward to
whole RUB after the catalog-derived base calculation. The matching fixed-plan
entitlements therefore cost more in the builder (for example Standard 3 months
399 -> 431 RUB), while relative device/traffic/period monotonicity remains. The
server remains authoritative for payment and promo quotes; standard catalog
prices, existing subscriptions, URLs and UUIDs do not change. The builder labels
the markup plainly, four viewport classes have no overflow, all tests/build and
production public/service checks pass.

Risk: client/server rounding drift. Both sides apply `ceil(base * 108 / 100)` and
tests cover all 12 fixed-plan anchor combinations plus an intermediate quote.
Rollback is the stage commit revert and subscription-service restart.

Status: **passed and deployed at `a94f240`**. Before-state browser evidence at
390 px showed custom 3 months/3 devices/45 GB at the same 399 RUB as Standard.
After the change, the same custom selection is 431 RUB (144 RUB/month), the 8%
markup is disclosed in the quote, and the payment sheet also carries 431 RUB.
Browser checks at 390x844, 430x932, 768x1024 and 1440x1000 all report zero
horizontal overflow. Focused tests: 14 passed; full suite: 142 passed; Vite
production build passed with the pre-existing unused-selector warnings only.
Production is fast-forwarded to `a94f240`; public subscription health and WebApp
return 200, the new hashed bundle is served, the focused production pricing suite
passes 11 tests, the subscription service is active/running, and its post-release
warning journal is empty. Existing subscription URLs, UUIDs and entitlements were
not changed.

# Historical stages

## 2026-08-31 custom tariff builder and compact mobile app cards

## 2026-08-31 custom tariff purchase flow

Goal: keep Happ/INCY artwork fully visible and separated from labels on mobile,
add a server-priced custom tariff builder to both purchase surfaces, and correct
environment-specific navigation, notifications and standalone email/session UX.

Affected components: customer purchase UI in `HomeFlowPreview.svelte`, WebApp API
client/mock catalog, payment and promo quote endpoints in `subscription_api.py`,
focused API coverage, generated WebApp bundle, and only the subscription service.

Acceptance:

1. At 390 px the two phone cards remain balanced and each full phone silhouette
   fits inside its card without clipping or oversized empty scroll.
2. A `Создать свой тариф` action sits immediately below the regular product
   selector. Activating it replaces the purchase main content with a dedicated
   builder; Back returns to the regular catalog without closing purchase.
3. Builder controls devices (1-10), bypass/LTE allowance (0/15/30/45/75/115 GB)
   and period (1/3/6/12 months), expose an accessible live total/monthly quote,
   and continue through the existing payment-method, promo and polling flow.
4. Pricing is authoritative on the server and derived from the active catalog at
   each period. Economy (2 devices/0 GB), Standard (3/45) and Family (10/115)
   custom selections reproduce their exact catalog prices; intermediate choices
   use the unique non-negative linear device/GB interpolation through those three
   anchors, rounded once to whole RUB. Client-supplied amounts are never trusted.
5. Paid custom orders persist their requested device/LTE entitlements; public
   URLs, UUIDs, existing subscriptions and standard tariff pricing are unchanged.
6. Mobile, tablet, desktop and wide browser checks cover regular/builder/payment
   transitions, no horizontal overflow, keyboard focus and disabled states. Full
   tests, Vite build and production health/public bundle pass.
7. A cold standalone visit renders a neutral session-check screen until `/status`
   resolves, never a flash of private cabinet data or navigation. Successful
   `auto` email verification immediately reloads authenticated data and enters the
   cabinet without a second code submission or manual refresh.
8. Notification preferences are shown only inside Telegram WebApp. Their 46x26
   switches use a true capsule (13 px semicircular end radius, implemented as
   999 px) rather than an ellipse overridden by global icon styling.
9. Back controls show on standalone mobile subpages/purchase and remain hidden in
   Telegram WebApp on phones; desktop behavior is unchanged.

Risks: under/overcharging from catalog drift and entitlement mismatch. The quote
helper rejects missing periods, malformed catalogs and values outside the bounded
choice set; payment and promocode paths share the same helper. Rollback is a
revert of the stage commit and restart of `arcvpn-subscription.service` only.

Status: **passed and deployed** through `3a20b04` (`eeed783` custom-pricing base). Before-state evidence:
at 390x844 the app cards cropped the lower phone silhouettes and purchase offered
only three fixed products. After-state browser evidence at the same viewport puts
both 162 px phone silhouettes fully inside their 310 px cards (`fits=true`) with
zero horizontal overflow. The builder exposes all bounded choices, reproduces
Standard 3/45/3 at 399 RUB, and a 6-month/5-device/75-GB selection produces the
same 1086 RUB/181 RUB monthly quote in the browser and Python helper. Its payment
sheet carries that total. Browser checks at 390, 768, 1366 and 1920 px have zero
horizontal overflow. Server-side anchor, validation, payment-pricing and persisted
entitlement coverage passes; full suite is `142 passed`, Python compile and Vite
production build pass. Production is active/enabled; `/health` and `/app/` return
200, public HTML serves `index-0jNBJqa0.js`, and the post-release warning journal
is empty. The deployed helper uses the live catalog and reproduces Standard
3 months/3 devices/45 GB at 399 RUB. Public unauthenticated rendering remains a
valid passwordless login shell; authenticated after-state evidence comes from the
same built bundle locally because production test credentials were not introduced.
Existing Vite unused-selector warnings remain pre-existing cleanup debt and do not
affect the generated bundle. Rollback was not used.

Follow-up evidence: at 390 px each phone is now 138 px wide, fully contained,
and begins 29 px below its label (`overlap=false`); standalone mobile connection
and purchase screens expose Back while the Telegram-mobile class hides it below
768 px. Standalone Settings contains zero notification rows; the switch CSS is
46x26 with 999 px radius and no later 50% override. A cold unauthorized render
contains zero Home regions and zero navigation docks, then shows the login screen.
`auto` email verification now follows the authenticated refresh branch rather
than the link-only confirmation branch. Full suite remains `142 passed`; Vite
production build and 390 px interaction checks pass without horizontal overflow.
Production serves `index-D_ZtMuG8.js` and `index-BB2tVbEZ.css`; `/health` and
`/app/` return 200, the service is active/running, and its post-release warning
journal is empty. Rollback was not used.

# Historical stages

## 2026-08-31 referral and VPN connection UX correction

## 2026-08-31 owner acceptance corrections

Goal: apply the owner's concrete copy, hierarchy, platform, install and import
corrections to the referral and in-page VPN setup screens.

Affected components: `HomeFlowPreview.svelte`, device icon data, WebApp assets,
the official INCY link encoder dependency and generated customer bundle.

Acceptance: FAQ contains four entries; referral heading matches Support/Settings
without a pill, reward terms live directly under the hero copy, site/bot link
choice is restored, and the supplied gift composition has real alpha. Connection
offers only iPhone/iPad, Android, Windows and Linux with the exact owner-provided
store/release destinations; Linux uses the supplied Tux path; heading is centered,
the eyebrow is absent, mobile Telegram hides the redundant back button, Happ/INCY
labels are larger, and existing-app actions deep-link directly into the selected
client. Four viewport classes, keyboard-visible controls, build/tests and public
production behavior pass.

Risks: third-party URI scheme drift and raster edge artifacts. Use Happ's existing
server-issued import URL and INCY's official encoder package; inspect alpha and
rendered edges. Rollback is the stage commit revert plus restart of only
`arcvpn-subscription.service`. Subscription URLs/UUIDs and entitlements are out
of scope and remain unchanged.

Status: **passed and deployed** at `1e9df54`. Vite production build passes; the
full Python suite is `131 passed`. Authenticated browser acceptance
covered referral, device and app stages at 390, 768, 1366 and 1920 px without
horizontal overflow. Both supplied raster assets have real RGBA alpha, and an
INCY encoder round-trip produced the official `incy://crypt1/` form. Production
is active/enabled, `/health` and `/app/` return 200, public HTML serves
`index-sTxDrGEh.js`, the new transparent gift asset returns 200, and the
post-release warning journal is empty.

Operational triage performed before this UI release found no control-plane fault
for the remaining reported Happ user: the local key and Remnawave identity are
active and aligned, the public subscription returns HTTP 200, active nodes are
connected, and a credential-safe real tunnel canary returned HTTP 204. The first
report was already resolved by deleting and reimporting the subscription in Happ;
the remaining evidence is consistent with the same stale client import/cache.
No UUID, URL or entitlement was changed.

# Historical stages

## 2026-08-31 referral hierarchy and device-to-app setup

Goal: rebuild the referral page in the requested content order and replace the
connection bottom sheet with a complete in-page device and application flow.

Acceptance: the referral page contains the section name, animated gift and
headline, reward conditions, counters, copyable link and QR action in that
order; the old share button and numbered steps are absent. `Подключить VPN`
replaces the home content with subscription link and device selection, then
shows Happ/INCY choices using the supplied artwork, official install links and
a safe import/copy step. Back navigation works at every stage. Production build,
responsive browser checks at four viewport classes and public deployment pass.

Non-goals: subscription URL or UUID changes, tariff/payment changes, node or
protocol work, and undocumented application deep links. Rollback is the stage
commit revert and restart of only `arcvpn-subscription.service`.

Status: **passed and deployed** at `2c77fce`. The referral page now follows the
requested hierarchy and contains no share button or numbered instruction block.
The home connection action opens an in-page device selector, then Happ/INCY
cards with the supplied artwork, official install destinations and a documented
import/copy finish step; back navigation returns one stage at a time. Vite
production build and full `131 passed` suite succeeded. Authenticated browser
checks covered the referral, device and application stages at 390, 768, 1366
and 1920 px with no horizontal overflow. Production is on `2c77fce`, the
subscription service is active/enabled, both new assets and `/health` return
200, public HTML serves `index-C-6KG4Dz.js`, and the post-release warning journal
is empty. Rollback was not used.

## 2026-08-31 actionable feedback and customer UX

Goal: replace the low-information trial score with actionable reasons, restore
authoritative main-traffic accounting, simplify passwordless email access, and
refresh notifications, support and referrals without changing entitlements.

Acceptance: category feedback and optional details are visible in admin;
successful Remnawave reads update main usage without zeroing known counters on
failure; email has one non-enumerating passwordless entry path; notification
switches are pill-shaped; FAQs contain current advice; referral UI has a
floating ArcVPN gift, real site/bot links, QR modal and copy confirmation. Full
tests/build, four responsive browser viewports and production services/public
behavior pass.

Non-goals: passwords, tariff/payment changes, subscription URL or UUID changes,
and node/protocol changes. Rollback is the stage commit revert and restart of
only the bot/subscription services. Generated art remains source-controlled as
a standalone transparent asset.

Status: **passed and deployed** at `6ef14e3`. Category feedback, optional detail,
admin aggregation, neutral email auto-login/register, current FAQ, 50%-rounded
notification switches, QR generation, copy toast and the transparent flying
gift are live. Authoritative main reconciliation updates successful identity
matches and preserves prior values on failures; production reports 20/24 active
keys with non-zero cached usage after the first scheduler pass. Local Python
compile, full `131 passed`, Vite production build, QR generation and mobile UI
render passed. Browser checks at 390, 768, 1366 and 1920 px found no horizontal
overflow; public login serves `index-BbOFLokv.js`, has one passwordless form and
no old mode switch. Both services are active/enabled, `/health` is `OK`, the
public art returns 200, and the post-release error journal is empty. Rollback was
not used; next step is to review the first categorized answers in Overview.

## 2026-08-29 Email delivery and account conversion UX

Goal: make email linking deliver a branded multipart OTP, let new email users
dismiss and later reopen the 10-ruble trial offer while no subscription exists,
and add a deliberate account logout confirmation.

Acceptance: settings email actions always use the `link` purpose; messages retain
plain text and add a responsive inline-styled HTML alternative; the paid-trial
dialog has an outlined `Позже` action, dismissal leaves a persistent home banner,
and both disappear once a subscription is active; logout is visible in the lower
left and requires a blurred modal confirmation. Build/tests and deployed mobile,
tablet, desktop and wide browser checks must pass.

Status: **passed and deployed**. Settings email now sends `purpose=link`
explicitly instead of accidentally serializing the click event; a production
request returned `sent=true` and Resend accepted the branded multipart message.
The paid-trial modal has `Позже`, dismissal persists locally and exposes a home
banner only while the email account has no active subscription. Logout is fixed
to the lower-left corner and opens a blurred `Да`/`Нет` confirmation. WebApp
build, full `125 passed`, service health and public HTTP 200 passed. Public login
has no horizontal overflow at 390, 768, 1366 and 1920 px; authenticated-state
visual confirmation remains a quick owner browser pass after refresh.

Follow-up `07a62c6`: removed the placeholder letter from the email brand,
persisted pending email/purpose for the full ten-minute code lifetime across
WebApp closes, and bound verification to the stored email. Email-only accounts
now show Telegram as disconnected. Logout moved into Settings / login methods,
uses a dedicated outlined icon, and is omitted inside Telegram Mini App. The
public site serves the new bundle without horizontal overflow; service health
is `OK`, journal has no error entries, and the full suite remains `125 passed`.

## 2026-08-29 TikTok forced proxy and Resend cutover

Goal: make TikTok/ByteDance traffic use the selected VPN route before Russian
direct-IP rules, including the five customer bypass profiles and their hidden
LTE/CDN fallback; prepare the existing OTP SMTP integration for Resend without
placing its API key in Git, logs or command arguments.

Acceptance: legacy Happ routing advertises explicit TikTok proxy domains; every
Happ JSON row places a TikTok proxy/balancer rule before all direct rules; the
AutoSelect rule retains LTE fallback; full tests and production recursive profile
verification pass. Resend acceptance additionally requires a verified sending
domain, protected production SMTP environment and a real delivered OTP; until
those external gates pass, email cutover is not claimed complete.

Components: subscription routing builder/tests, protected production SMTP env,
subscription service. Rollback restores the prior routing commit and service;
email rollback restores the protected SMTP env backup. Public URLs, UUIDs,
Remnawave identities and node bindings are unchanged.

Status: TikTok routing **passed and deployed**; Resend SMTP **passed and
deployed**.

- `TIKTOK_PROXY_SITES` covers TikTok and ByteDance delivery domains. Legacy
  Happ routing publishes them in `ProxySites`; all 13 generated Happ JSON rows
  place the forced VPN rule before Russian/private direct rules. AutoSelect and
  every named bypass row retain the same main-to-LTE fallback chain.
- Local suite: `125 passed`; focused test and Python compile pass. Runtime commit
  `07bf9a2` and standalone verifier fix `c595bd6` were pushed and fast-forwarded
  on Poland; only `arcvpn-subscription.service` was restarted.
- Production verifier reports `tiktok_routing_ok=true`, correct 13-row order,
  two Estonia AutoSelect outbounds, intact main/LTE credential isolation, active
  service and `OK` health. A real TikTok app test during throttling remains the
  external behavioral gate.
- The verified `arccnet.space` sender uses Resend STARTTLS on port 2587. The API
  key is stored in the local encrypted credential vault and in a root-only
  production environment file; it is absent from Git and command output.
  Production SMTP authentication and a Resend acceptance delivery passed,
  `arcvpn-subscription.service` is active, local health is `OK`, and the public
  site returns HTTP 200. A real user OTP remains the final inbox-level check.

## 2026-08-29 Estonia-first subscription order

Goal: move the existing Estonia TCP/Hysteria pair above the Netherlands pair in
plain, base64 and Happ JSON delivery, including AutoSelect candidate order,
without changing links, identities, node bindings or LTE fallback behavior.

Acceptance: exact public order is AutoSelect, YouTube, Estonia #1/#2,
Netherlands #1/#2, Germany #1/#2, five EU fallback rows; AutoSelect still has
both Estonia outbounds; main/LTE credentials remain isolated; local full tests,
commit/push, Poland pull, subscription-service restart, public verifier, service
health and error-log scan pass.

Components: `subscription_api.py`, subscription order tests and the credential-
safe production verifier. Risk is a stale catalog override or partial renderer
change. Rollback is the preceding runtime commit and service restart; no
Remnawave Host, squad, UUID or public URL is mutated.

Status: **passed and deployed**. Local `124 passed` and Python compile succeeded.
Commit `2f32b94` was pushed and fast-forwarded on Poland; only
`arcvpn-subscription.service` was restarted. The production verifier returned
`profile_order_ok=true`, 13 Happ rows, two Estonia AutoSelect outbounds, correct
main/LTE identity isolation, active service and `OK` health. No new error-level
journal entries were found. Rollback was not used.

## 2026-08-29 Estonia normal node admission

Goal: admit the owner-provided Estonia VPS as a normal Remnawave node matching
the proven Netherlands pattern: one VLESS TCP Reality profile and one native
Hysteria2 profile, both included in main AutoSelect and published immediately
after the Netherlands pair. Preserve all existing subscription URLs, user UUIDs,
LTE isolation and current nodes.

Target/current/desired: target alias `ee-1chost`; provider is 1chost (not DHost).
The host is not yet inventoried,
registered in Remnawave or present in subscription output. Desired state is a
dedicated RemnaNode with unique Reality material, unique inbound tags, a direct
ArcVPN-owned Estonia domain, consumption multiplier 1, production squad binding,
two enabled Remnawave Hosts, and real TCP/UDP tunneled traffic evidence.

Acceptance fixed before mutation:

1. SSH host key is recorded and the supplied credential is kept only in the
   local DPAPI vault; no password/private key/UUID/subscription token enters Git
   or logs.
2. Estonia has unique TCP Reality and Hysteria2 inbounds/configuration; syntax,
   sockets/firewall, RemnaNode authorization and online state pass.
3. `ee.arccnet.space` resolves to the node and is used as the public address;
   Reality uses the verified Firefox fingerprint baseline and unique key/SID.
4. Both inbounds belong to the production main squad and active identities keep
   their existing UUIDs/URLs. Generated client configurations pass real tunneled
   HTTP checks over TCP Reality and Hysteria2.
5. Public order is AutoSelect, YouTube alias, Netherlands #1/#2, Estonia #1/#2,
   Germany #1/#2, then the existing five EU fallback profiles. Estonia #1/#2 are
   included in AutoSelect and no LTE identity/inbound is mixed into them.
6. Local tests, exact diff, commit/push, Poland pull, affected service restart,
   public profile inspection and service/log health pass.

Risks: an unverified host key, DNS lag, duplicate Reality material, blocked UDP,
incorrect squad binding or host ordering can expose a dead profile. Rollback
disables/removes Estonia Hosts from subscription delivery first, removes its
inbounds from the main squad/config profile, then stops/disconnects the new node;
existing identities and URLs are never rotated.

Status: **passed and deployed**.

Evidence:

- DNS resolves `ee.arccnet.space` to the 1chost node. The DPAPI alias and pinned
  SSH host key are local-only; no supplied credential or generated Reality
  secret entered Git or command output.
- RemnaNode is connected and has unique `EE_1CHOST_VLESS_TCP` and
  `EE_1CHOST_HYSTERIA2` inbounds. TCP/UDP 443 listen publicly; the node control
  port is firewalled to Poland only. Both inbounds are in the production main
  squad and both Hosts are enabled.
- Real production tunnel canaries returned HTTP 204 through Estonia TCP Reality
  and through Estonia Hysteria2. The reusable Hysteria canary also passed the
  established Netherlands row, proving the earlier Xray-container failure was a
  canary-client mismatch rather than an Estonia transport failure.
- Local suite: `124 passed`; Python compile and diff checks pass. Runtime commits
  are `20e050a` and `4ca2ac6` (canary helper `ddd7b5b`). All were pushed and
  fast-forwarded on Poland; only `arcvpn-subscription.service` was restarted.
- Production verification reports `main_links=7`, `lte_links=5`, 13 Happ rows,
  exact order AutoSelect / YouTube / Netherlands pair / Estonia pair / Germany
  pair / five EU fallback rows, two Estonia outbounds inside AutoSelect, separate
  LTE identity, active service and `OK` health. Existing public URLs and UUIDs
  were unchanged.
- Rollback was not used. The exact rollback remains: disable the two Estonia
  Hosts, remove their inbounds from the main squad/env, resync, then stop the new
  node; do not rotate customer identities.

## 2026-08-29 hide customer node settings in Happ

Client acceptance correction (2026-08-29): the owner verified that settings
remain visible in the real Happ client. Header/body presence was transport
evidence only and did not prove UI behaviour, so the earlier acceptance claim
below is superseded. Official Happ documentation classifies `hide-settings` as
an advanced Provider-ID feature: the provider must be registered, the
subscription domain must be attached to that provider, and compatible clients
must recognise the provider. The supported import URL also accepts
`#?providerid=<8-char-id>`; ArcVPN currently supplies Provider ID only after the
subscription is fetched (header/body), not at import time.

Follow-up goal: preserve the existing header/body metadata and add the same
validated Provider ID to every Happ subscription target at import time. Verify
the production environment has an explicit Provider ID without disclosing it,
cover browser fallback and device-scoped imports, and deploy without changing
the subscription path, UUID, nodes, credentials or routing.

Follow-up acceptance fixed before implementation:

1. A valid configured Provider ID is appended to the HTTPS target as the
   documented URL fragment, including device-scoped imports; invalid/empty IDs
   never produce a fragment.
2. Existing query parameters (`format`, `device`) and stable subscription paths
   are preserved exactly; the fragment is not sent to the subscription server.
3. Header/body `providerid` and `hide-settings` metadata remain intact.
4. Unit tests cover query+fragment construction and both import paths; full
   tests, diff review, push, Poland pull, subscription-service restart and
   credential-safe public inspection pass.
5. Behaviour remains **deferred** until a current Happ client imports the
   refreshed URL under a Provider ID whose account contains the ArcVPN
   subscription domain. An updated client/delete-and-reimport/daily provider
   refresh may be required by Happ and cannot be proven by HTTP inspection.

Risk and rollback: an unregistered or domain-mismatched Provider ID will still
be ignored. Old clients may ignore the flag. The URL fragment is client-side and
does not reach ArcVPN, but malformed deeplinks could block import. Rollback
reverts only the helper/import changes and restarts
`arcvpn-subscription.service`; no topology or identity mutation is involved.

Follow-up closeout evidence: criteria 1-4 **passed** in commit `b8308c7`.
Focused import/metadata tests are `9 passed`; the full suite is `124 passed`;
Python compile and diff checks passed. The commit was pushed, fast-forwarded on
Poland and only `arcvpn-subscription.service` was restarted. It is active and the
post-restart error scan returned zero. A public non-customer import bridge
returned HTTP 200, preserved the stable target path/query and contained an
eight-character Provider-ID fragment; no ID or subscription token was logged.
Production has no explicit `HAPP_PROVIDER_ID` service environment override and
therefore uses the repository-configured public ID. Criterion 5 remains
**deferred/failed from the earlier client check** until that ID is confirmed in
the Happ provider dashboard for `sub.arccnet.space`, followed by a current-client
delete/reimport and UI check. Rollback is revert `b8308c7`, pull and restart only
the subscription service.

Goal: disable normal viewing, editing and sharing of ArcVPN subscription node
configurations in supported Happ clients without changing connectivity, stable
subscription URLs, UUIDs, domains, protocols or fallback behavior.

Scope and acceptance: emit Happ's documented `hide-settings: 1` through every
HTTP subscription response and through plain/base64 subscription metadata; cover
both paths with tests; verify the public owner subscription header after deploy.
JSON profile contents remain available to the VPN core because they are required
to connect. This is UI/export hardening, not cryptographic secrecy, and clients
that ignore Happ metadata cannot be forced to comply.

Risk and rollback: an old or non-Happ client may ignore the header, while a
modified/rooted client can still extract runtime credentials. The flag must not
alter the body or routing. Rollback removes the header/metadata line and restarts
only `arcvpn-subscription.service`.

Closeout evidence: commit `cda8604` is pushed and fast-forwarded on Poland;
`arcvpn-subscription.service` is active and its post-restart journal has no new
traceback/exception/unhandled entry. Local result is `120 passed`, Python compile
and `git diff --check`. The public owner subscription returns HTTP 200 with
`hide-settings: 1` in the JSON response header and `#hide-settings: 1` in plain
metadata. No public URL, UUID, credential, body routing or node configuration was
changed. This proved metadata delivery only; the later real-client check failed
and supersedes the original UI/export acceptance. Resistance to modified/rooted
clients is explicitly outside the achievable client-side boundary.

## 2026-08-29 Happ fallback-only customer layout

Goal: remove the two manually selectable direct XHTTP rows from Happ delivery,
replace them with two additional customer-facing AutoSelect clones using the
existing main-to-LTE loopback fallback, and confirm that the primary AutoSelect
also fails over and returns to main after observatory recovery.

Current state: Happ emits one primary AutoSelect, NL/DE main profiles, three
fallback AutoSelect clones and two direct LTE XHTTP rows. The generated primary
AutoSelect already contains `balancer_main -> LOOPBACK_TO_BACK -> balancer_back`;
all five LTE outbounds stay hidden inside it. Official Xray routing documentation
states that unavailable observed outbounds are excluded, `fallbackTag` is used
when all observed candidates are unavailable, and burst-observatory recovery
requires one successful probe. With the current 20-second interval and two
samples, recovery is eventual rather than instant.

Affected components: Happ JSON assembly and contract tests only. The underlying
Remnawave LTE identities/inbounds/CDN edges remain available as hidden fallback
outbounds. Plain/base64 output, public subscription URL, UUIDs, product quotas,
DNS, node bindings and server configuration are unchanged.

Acceptance fixed before implementation:

1. Happ order remains primary AutoSelect, YouTube, NL VLESS/Hysteria2, DE
   VLESS/Hysteria2, then exactly five EU-labelled bypass rows.
2. All five bypass rows are AutoSelect profiles containing observed main
   outbounds, hidden LTE outbounds, loopback and both balancers; no customer row
   exposes a direct `proxy` XHTTP profile.
3. The first primary AutoSelect uses the same LTE fallback chain. Main recovery
   is driven by continued burst-observatory probes and causes new connections to
   select main again; existing established connections are not promised to move.
4. Plain/base64 links and Remnawave topology are not deleted or mutated. Stable
   URLs/UUIDs and LTE accounting remain unchanged.
5. Local subscription tests and full suite pass; exact staged diff is reviewed;
   commit/push/Poland pull/restart subscription service/public Happ inspection
   confirm five fallback clones, hidden direct XHTTP rows and intact credentials.

Risks and rollback: unsupported client/core loopback behavior could break all
bypass clones or create a routing loop. Existing tests must verify dedicated
inbound re-entry and selector isolation. Rollback reverts only the subscription
assembly commit and restarts `arcvpn-subscription.service`; no identity, host,
inbound or subscription URL is changed.

Verification matrix: unit structure test; full pytest; generated JSON recursive
inspection; production public owner subscription comparison without printing its
URL/UUID; service health/log scan. A real client outage/recovery canary remains
the final behavioral proof because static JSON cannot force a network failure.

Closeout evidence (2026-08-29):

- Criteria 1, 2 and 4 **passed**: commit `ffc0915` is pushed and fast-forwarded
  on Poland; only `arcvpn-subscription.service` was restarted and remains active
  with no new traceback/exception/unhandled journal entries.
- Local contract slice: `30 passed`; full suite: `119 passed`; Python compile and
  `git diff --check` passed. Generated fixtures show the primary plus all five
  bypass rows with `LOOPBACK_TO_BACK`, five hidden LTE outbounds, and zero direct
  customer `proxy` XHTTP rows.
- Public owner subscription returned HTTP 200 with 11 rows in the required order,
  five EU bypass rows, `public_direct_xhttp_rows=0` and loopback present in all
  five. The first AutoSelect reports `fallbackTag=LOOPBACK_TO_BACK` and five
  hidden LTE outbounds. No URL, UUID or credential was printed or changed.
- Criterion 3 is **verified structurally and by upstream contract, behavioral
  canary deferred**: official Xray routing/observatory semantics return new
  connections to recovered observed main outbounds after a successful probe.
  An already-established fallback connection is not migrated. A real Happ
  main-outage/recovery test remains the final client proof and rollback trigger.
- Rollback is ready: revert `ffc0915`, pull on Poland and restart only the
  subscription service. No Remnawave, CDN, inbound, DNS or database mutation
  occurred.

## 2026-08-28 email registration and paid-trial funnel

Goal: make standalone email registration a real ArcVPN account path without a
free trial, offer that cohort one abuse-resistant 10 RUB Standard trial with
mandatory disclosed auto-renewal, make the admin mutation view truly reactive,
and expose paid-trial customers as an auditable admin cohort.

Pre-change evidence: public `arccnet.space` only says that email must already be
linked in Telegram and has no registration path. The owner confirmed that a
production add/remove-days operation still displays stale expiry until a full
reload after runtime `8fb6077`; the optimistic row patch is therefore not
accepted. Mailjet SPF/DKIM are authenticated and the empty verification URL is
public, but Mailjet domain status remains Pending while the support ticket is
transferred to another internal group. The Mailjet label is display-only and is
not part of DNS/file verification.

Affected components: user identity/schema and email-code flow; payment order and
one-time trial entitlement; standalone login/onboarding/payment modal; admin user
query/detail and reactive mutation state; tests, build, browser evidence and
production release. Product exploration is documented separately.

Non-goals: no free trial for email-only accounts; no trial for an account that
already received free or paid trial; no hidden charge, crypto/Stars, promo input,
custom tariff builder or immediate tariff-price change; no mutation of a real
customer during automated verification.

Acceptance fixed before implementation:

1. A new email can request and consume a six-digit registration code, creating
   one email-only user idempotently without Telegram identity and without free
   subscription/trial. Existing linked-email login remains unchanged, responses
   do not leak whether an account exists, and codes keep rate-limit, expiry and
   one-time semantics.
2. First authenticated cabinet load for an eligible email-only account presents
   an accessible centered modal over a blurred/inert background: `7 дней
   Standard за 10 ₽`, explicit unlimited main/5 GB LTE/device terms, SBP/card
   selection, a visibly checked non-editable auto-renew row, disclosure that the
   method is saved and cancellation is available in Settings, and one payment
   CTA. Promo and alternate trial bypasses are absent.
3. The 10 RUB order is server-authoritative, limited to one per person/account,
   revalidated at create and fulfillment, grants Standard trial entitlements only
   after successful provider payment, stores attribution `email_paid_trial`, and
   enables recurring only after provider confirmation. Concurrent/replayed
   requests cannot grant or charge twice.
4. Admin Users can filter `Платный trial 10 ₽`, see cohort size/status and payment
   evidence without exposing email unnecessarily. Abuse signals include reused
   payment identity where provider data supports it; no claim of device/fingerprint
   prevention without evidence.
5. Add/remove/activate/disable renders the returned subscription snapshot and a
   new timeline item immediately without waiting for any overview/detail refetch;
   background refresh cannot overwrite it with an older response. Buttons expose
   per-action loading/disabled/error state.
6. Unit/integration tests cover registration new/existing/replay/rate limit,
   paid-trial eligibility/payment/replay/race/fulfillment, admin filter and
   reactive mutation reducer. Vite build passes.
7. Browser-first before/after acceptance covers login, registration, modal,
   payment states and Admin Users at mobile/tablet/desktop/wide with keyboard,
   focus, loading, error, empty and no horizontal overflow.
8. Exact diff review and release use commit/push, Poland pull, only affected
   service restart, public verification, and rollback by reverting the release.

Risks: nullable Telegram identity can break legacy assumptions; a client-only
10 RUB price can be bypassed; mandatory renewal copy can be misleading; retries
can double-provision. Isolate email-only identity creation, enforce eligibility
and price server-side in a transaction, reuse payment idempotency, make renewal
terms prominent, and leave the offer retryable rather than provisioning early.

Verification matrix:

| Area | Automated | Browser/production |
|---|---|---|
| Email registration | code + identity integration tests | new-email flow |
| Paid trial | eligibility/payment/fulfillment tests | modal + safe provider boundary |
| Admin mutation | snapshot/version reducer test | owner-designated safe account |
| Cohort filter | query/API test | Users filter/empty/populated |
| Responsive/accessibility | build + component states | four viewport classes |

Implementation evidence (2026-08-29):

- Schema v59 adds standalone email identities, independent one-time registration codes, payment `offer_code`, and paid-trial cohort indexes. Schema v60 adds a per-user atomic checkout claim so concurrent requests are rejected before contacting YooKassa; canceled/failed provider attempts release the claim and successful fulfillment seals it as applied.
- Registration creates no free entitlement. The paid offer is fixed server-side at 10 RUB, Standard for 7 days, 3 devices and 5 GiB LTE; main Remnawave traffic is unlimited and no referral trial reward is emitted.
- Payment creation requires the selected YooKassa recurring capability. The existing verified webhook persists a method only when the provider reports it as saved.
- Admin Users exposes `Пробник за 10 ₽`. Subscription mutations now apply the returned key snapshot and timeline event without the stale list/detail refetch.
- Local evidence: `119 passed`, including a real SQLite reservation/retry test and an API provider-not-called race test; `npm --prefix webapp run build` passed; `git diff --check` passed.
- Browser evidence: cohort control is present and the affected admin screen has no horizontal overflow at 390x844, 768x1024, 1366x768, or 1920x1080.
- External: Mailjet SPF/DKIM are confirmed. The display label does not affect validation; final sender/domain activation remains with the Mailjet specialist group.
- Production evidence: `1e42b43` deployed the email registration/paid-trial funnel; atomic checkout follow-ups `561c886` and `2fa9072` were pushed and fast-forwarded on Poland after a restricted pre-v60 database backup. Provider cancellation releases the reservation through webhook or polling; provider success seals it even when provisioning needs manual reconciliation, preventing a second charge. Both affected services are active, migration v60 is recorded, the claim table is initially empty, and startup logs contain no migration/runtime failure. A real Mailjet-delivered registration and real 10 RUB YooKassa charge/saved-method cycle remain external acceptance gates and were not simulated against production customers.

Product follow-up to evaluate, not silently ship: replace the 0→45 GB LTE gap
with either Economy 5–10 GB or an explicit LTE add-on, and design a bounded
custom-plan configurator (devices/LTE/period with server-authoritative price
matrix and minimum margin) instead of arbitrary client-entered pricing.

## 2026-08-28 tariff transitions and admin reactivity/operations

Goal: prove and harden cross-tariff renewal, make admin mutations immediately
reactive, persist owner authentication reliably, expose per-user main/LTE usage
with useful sorting/filtering, remove catalog-label drift, and show real uptime in
Health.

Pre-change browser evidence: production `/admin` opened in the existing browser
session but rendered `Доступ к сводке ограничен` followed by the password form.
This reproduces the owner-session persistence defect before any code change. The
provided user-detail screenshot also shows repeated `adjust_days` events while
the displayed expiry remains stale until a manual reload.

Affected components: payment fulfillment and entitlement transition code; admin
auth/session API; user list/detail API and Svelte views; subscription catalog
normalization; Health metrics; related tests and production deployment.

Non-goals: do not mutate a real user's tariff/payment, send support messages,
rotate identities, change pricing, protocols, DNS or node topology. Validation
uses fixtures/read-only production evidence unless the owner supplies a safe
identity.

Acceptance fixed before implementation:

1. Renewal from any plan family to another preserves remaining active days,
   adds the purchased duration once, keeps the stable public URL/main UUID, and
   atomically applies the new plan's devices and LTE allowance to local state and
   Remnawave. Tests cover Economy→Standard, Standard→Family, Family→Economy,
   expired subscriptions and retry/idempotency.
2. Add/remove/activate-now/disable user actions update the visible row/detail,
   expiry and history immediately after a successful response without full-page
   reload; loading, disabled and error states are explicit.
3. User data exposes current-cycle main and LTE bytes per user. Admin can sort
   descending by main usage or LTE usage and filter to meaningful usage ranges;
   labels, units, zero/empty/error/loading states and keyboard controls are clear.
4. Owner login replaces the login surface immediately after success and remains
   valid across reload and following days within the configured 30-day lifetime.
   Cookie attributes and frontend bootstrap use one consistent session contract;
   unauthorized/expired sessions fail closed.
5. Catalog and published subscription use one normalized label source. Hysteria
   rows are `Нидерланды #2` and `Германия #2` everywhere; lightning emoji is
   absent from catalog, plain/base64 and Happ JSON without changing protocol/order.
6. Health shows real control-plane uptime (and node uptime where the backend has
   authoritative data), with timestamp/source and honest unavailable state.
7. Local unit/integration tests and warning-free build pass. Production UI is
   browser-accepted before/after at mobile, tablet, desktop and wide viewports:
   no horizontal overflow; keyboard/focus, hover, disabled, loading, error and
   empty states verified for touched controls; console has no new errors.
8. Exact diff is reviewed; commit/push → production `pull --ff-only` → restart
   only affected services → health and authenticated public verification.

Risks and rollback: tariff transition mistakes can over-extend access or apply a
wrong quota; auth-cookie changes can lock out the owner; usage joins can slow the
user list. Preserve idempotency keys and stable identities, use bounded indexed
queries, do not run production payment mutations, and rollback by reverting the
release commit plus restarting the affected services.

Verification matrix:

| Area | Automated | Production/browser |
|---|---|---|
| Tariff transitions | fulfillment matrix + retry tests | read-only contract inspection |
| Admin mutations | API/component state tests | safe UI state; no real user mutation |
| Usage ranking | query/serialization tests | users/detail filters and values |
| Auth | cookie/session/bootstrap tests | login, reload and renewed request |
| Catalog | plain/base64/Happ assertions | fresh owner subscription/catalog |
| Health | metrics serialization | uptime visible at four viewports |

Closeout evidence 2026-08-28 (runtime `8fb6077`):

- Criteria 1 and 4-6 **passed by automated/runtime evidence**. Active renewal
  adds the purchased period to the existing expiry; a lapsed subscription starts
  from now. The payment entitlement step applies the selected product before
  fulfillment, and fulfillment now updates the existing isolated LTE identity's
  quota, expiry, device limit and ACTIVE/DISABLED state. Stable main UUID and
  public URL are untouched. Economy disables LTE instead of treating a zero-byte
  Remnawave limit as unlimited. Hysteria labels no longer contain lightning in
  native/plain and Happ paths. The admin cookie is 30-day Lax/Secure/HttpOnly
  with an explicit expiry and login returns the owner access context immediately.
- Criteria 2-3 **passed locally and read-only in production**. The mutation API
  returns authoritative expiry/active state; the Svelte row and open detail are
  patched before background refresh. Production API smoke returned HTTP 200 and
  the expected `main_used_bytes`, `lte_used_bytes`, `lte_quota_gb` fields for the
  LTE-ranked query. The UI exposes main/LTE top sorts and non-zero filters.
- Criterion 6 **passed in production**: Overview returned Poland uptime
  `1451276` seconds and Health renders the formatted uptime in the primary status
  card. Both affected systemd services are active with zero restarts and no
  warning journal entries after deployment.
- Criterion 7 **partially passed**: 114 pytest tests and the Vite production
  build pass. Browser-first local inspection at 1280x720 verified Users and
  Health composition, controls, data labels and no horizontal overflow. The
  prior whole-admin four-viewport pass remains valid for the shared shell, but
  this browser runtime cannot change viewport, so fresh mobile/tablet/wide
  screenshots of these touched views remain open rather than being inferred.
- Criterion 8 **passed except owner-only interaction**: exact staged diff was
  reviewed; commit/push, Poland `pull --ff-only`, selective restart and public
  asset checks completed. Production `/admin` loads the new bundle with no
  overflow but correctly presents login because no owner password was supplied.
  A single owner login/reload and one safe manual add/remove-days interaction are
  still required for authenticated production acceptance; no real user was
  mutated without explicit designation.

Rollback: revert `8fb6077`, push/pull, then restart
`arcvpn-subscription.service` and `arcvpn-bot.service`.

## 2026-08-28 Germany Reality domain endpoint

Goal: replace the literal public address of the active Germany Reality profile
with `de.arccnet.space` in both ArcVPN fallback metadata and the authoritative
Remnawave Host, without changing its port, Reality SNI/material, UUIDs, squads,
subscription URLs, labels, order or active-user access.

Non-goals: no protocol, inbound, DNS-routing, LTE-balancer, node-agent or key
rotation changes; no change to the Germany Hysteria profile or other nodes.

Current and desired state: public DNS for `de.arccnet.space` resolves exactly to
the active `de-dhost` address recorded in the non-secret inventory. Germany
Reality #1 currently publishes that address literally; desired output publishes
the domain while retaining the same transport and authorization.

Acceptance fixed before implementation:

1. DNS A resolution matches `de-dhost`, and the node remains reachable on the
   unchanged Reality port.
2. The authoritative Remnawave Host and ArcVPN fallback metadata use
   `de.arccnet.space`; no UUID, public subscription URL, SNI, port, inbound or
   squad changes.
3. A fresh owner subscription in plain, base64 and Happ JSON contains the same
   ordered catalog as before, Germany Reality uses the domain everywhere
   (including AutoSelect/LTE fallbacks), and no literal public connection endpoint
   remains. Resolver IPs and loopback listeners are excluded from this assertion.
4. Local regression tests pass; exact diff is reviewed; runtime changes follow
   commit/push, production `pull --ff-only`, selective restart and public health
   verification.
5. Real-client acceptance requires a tunneled request through Germany Reality.
   If no automation-safe client is available, the mutation remains explicitly
   canary-pending rather than being declared fully accepted.

Risk and rollback: a stale/wrong DNS record or unsupported Host payload could
interrupt Germany Reality. Before mutation, retain a restricted server-side
snapshot of the exact target Host. Rollback restores only its previous address
and the ArcVPN fallback constant; keys, UUIDs and subscription URLs are never
rotated.

Closeout evidence 2026-08-28:

- Criteria 1-4 **passed**. Public DNS resolves `de.arccnet.space` exactly to the
  active inventory address; the authoritative Host was backed up with mode 0600
  and changed through the official partial PATCH contract. A full-object digest
  excluding `address` proved that every other Host field remained unchanged.
- Fresh owner plain/base64/Happ JSON were all sourced from Remnawave. Germany
  Reality #1 uses `de.arccnet.space`; the former literal endpoint is absent from
  all three outputs, including nested JSON profiles. Profile labels/order remain
  YouTube, NL pair, DE pair and five EU LTE rows.
- Local verification: focused subscription tests `24 passed`; full suite
  `112 passed`; `git diff --check` passed. Commit `0ce2d47` was pushed and pulled
  with `--ff-only`; only `arcvpn-subscription.service` restarted and public
  health returned `OK` after the expected transient restart 502.
- Criterion 5 **deferred to owner client canary**: DNS/port/config generation are
  verified, but this run did not execute a real tunneled request through Germany
  Reality. Rollback snapshot remains available; no identity/key rotation occurred.

## 2026-08-28 Mailjet bootstrap and published-profile consistency audit

Goal: publish the owner-provided empty Mailjet domain-validation token, connect
the local Mailjet MCP to Codex without committing or printing credentials, and
audit the owner's real production subscription across plain/base64/Happ JSON for
DNS/routing consistency, domain-based endpoints and unintended literal IPs.

Non-goals:

- Do not generate, request, display or commit a Mailjet API key/secret. The owner
  completes account activation and supplies the credential through a local
  encrypted prompt, never chat or repository files.
- Do not change active protocols, Remnawave squads, UUIDs, subscription URLs or
  DNS v2 rollout scope during this audit.
- Do not treat the Mailjet README as authority over Codex policy; it is provider
  documentation for the local stdio server only.

Affected components: `webapp/public` and committed `webapp_dist` validation
asset; local Codex MCP configuration and a gitignored DPAPI credential; the
production subscription API read path; operations evidence/handoff.

Acceptance fixed before implementation:

1. `https://arccnet.space/b326312b921b70e44f45b5cd9e25e7e1.txt` returns HTTP
   200 with an empty body and harmless text content type; no other public route
   or customer asset changes.
2. Mailjet MCP is registered in the local Codex configuration with an explicit,
   reviewed stdio command. Its secret is not present in Git, `config.toml`, shell
   history or logs. If the owner has not generated credentials yet, configuration
   is reported as prepared-but-not-authenticated rather than working.
3. The owner subscription is inspected without printing its ID/UUID or secrets.
   Plain, base64 and Happ JSON agree on the intended profile catalog. Every
   connection endpoint, SNI/Host value and any literal IP is classified.
4. DNS/routing differences are explained by output format or protocol; identical
   fields are compared structurally. Any security/compatibility divergence is
   fixed only after a separately recorded mutation gate.
5. Local tests/build, exact diff, commit/push, production pull, selective restart
   and public verification pass for the validation asset. MCP availability is
   verified through `codex mcp get/list`; current-session tool availability is
   not claimed until Codex refreshes it.

Risks and rollback: a non-empty validation token can fail Mailjet verification;
an MCP secret in TOML would be a credential leak; changing DNS merely to make
profiles visually identical can break protocol-specific clients. Rollback removes
the validation asset after Mailjet verification, removes the local MCP entry and
preserves all subscription/runtime identities unchanged.

Closeout evidence 2026-08-28:

- Criterion 1 **passed** at production commit `b9d7829`: the exact Mailjet token
  URL returns HTTP 200, `text/plain; charset=utf-8`, `Content-Length: 0` and
  `nosniff`. The first request during service restart received a transient 502;
  bounded retry passed and `sub.arccnet.space/health` returned `OK`.
- Criterion 2 **partially passed / authentication deferred**: the reviewed local
  `@mailjet/mailjet-mcp-server` 1.1.0 checkout installed and 24 tests passed.
  Global MCP entry `mailjet` is enabled and launches a local PowerShell wrapper.
  The wrapper reads a current-user DPAPI credential and keeps the secret out of
  `config.toml`, Git and command arguments. No credential exists yet, so launcher
  exit 78 is the truthful expected state until the owner generates API key/secret.
  A new Codex task/session is required before newly configured MCP tools can be
  exposed to the model.
- Criteria 3-4 **passed as an audit** for Telegram ID 2075630349 without emitting
  its subscription ID/UUID. Plain and base64 each contained the same ten manual
  profiles; Happ JSON added AutoSelect for eleven total. All eleven JSON profiles
  had one identical DNS structure. Routing intentionally had two structures:
  fallback-aware AutoSelect/LTE #1-#3 and ordinary direct profiles.
- Endpoint classification: NL Reality/Hysteria, DE Hysteria and all five XHTTP
  profiles use domains and domain SNI. DE Reality #1 still uses a literal public
  endpoint with domain SNI; therefore AutoSelect and LTE fallback #1-#3 contain
  the same address internally. Two literal resolver addresses and loopback
  inbound listens are expected DNS/client-local values, not VPN endpoint leaks.
  No endpoint mutation was authorized or attempted; converting DE Reality to a
  domain requires a separate real-client canary.
- Criterion 5 **passed except current-session MCP availability**: ArcVPN suite
  `111 passed`; Vite build succeeded; exact diff reviewed; commits `c2b652e` and
  `b9d7829` pushed and pulled with `--ff-only`; only
  `arcvpn-subscription.service` restarted for the exact route and remained active.
  The user-owned nested `mailjet-mcp-server/` checkout remains untracked and was
  not absorbed into the ArcVPN repository.

Rollback remains available: remove the exact route/assets after Mailjet validates
the domain and restart the subscription service; `codex mcp remove mailjet`
removes only the local integration. No subscription identity or topology changed.

## 2026-08-27 real operations dashboard, health and catalog truth

Goal: repair the production host split, make Overview and Health answer real
business/operations questions from ArcVPN-owned data, align the admin catalog with
the actually published subscription, restore the supported YouTube ad-free route,
and improve the desktop renewal composition without adding decorative controls.

Non-goals:

- Do not copy Axottle code, assets, text or exact layouts. Its screenshots are
  references for hierarchy, density, drill-down and actionable health evidence.
- Do not expose fake node-agent controls. Panel-driven node/inbound provisioning is
  recorded as a future authenticated agent stage unless a complete ArcVPN contract,
  rollback and real traffic gate are implemented here.
- Do not change stable subscription URLs, main/LTE UUIDs or active authorization.
- Do not create a Mailjet account or transmit credentials. This stage may prepare
  configuration, but activation waits for owner-created credentials and DNS values.

Affected components: production nginx host routing; `subscription_api.py` admin
overview/health/catalog APIs; database growth/payment/referral/traffic queries;
`webapp/src/views/admin/` Overview, Health and Catalog surfaces; purchase layout;
Happ routing/catalog preparation and regression tests; operations documentation.

Browser-first defects confirmed before implementation:

1. `https://panel.arccnet.space/` renders the indexed customer login (`ArcVPN —
   личный кабинет`) instead of the noindex admin entry. Production screenshot and
   DOM evidence captured on 2026-08-27.
2. The desktop purchase Back control is detached at the top-left instead of sitting
   near the centered purchase workflow.
3. Admin catalog shows retired Finland and obsolete/raw rows and therefore does not
   describe the ten profiles actually published to Happ.
4. Existing Overview/Health copy includes stale topology concepts and does not
   expose the requested real period cohorts, payment/product mix, referral source
   split, aggregate main/LTE usage, upstream/service state or resource pressure.

Acceptance fixed before code changes:

1. `panel.arccnet.space/` and `/admin` open the admin entry, carry `noindex`, and
   never render the customer login; `arccnet.space/` remains the indexable customer
   cabinet. Admin session persistence continues to work.
2. Desktop/laptop purchase Back sits with the centered workflow and remains visible,
   keyboard reachable and non-overlapping; mobile/tablet composition is unchanged
   or improved, with no horizontal overflow.
3. Overview reports from real persisted data: users joined today/7d/30d, successful
   payments and revenue for the same windows, popular paid products, referral users
   versus named advertising campaigns, aggregate main usage and LTE usage, live
   online devices/users, and a compact attention queue. Every timestamp/window and
   empty/error/loading state is explicit.
4. Health reports real Poland/Germany/Netherlands upstream/node evidence, Remnawave
   and ArcVPN service readiness, last-success/staleness, CPU/RAM/disk/load where an
   authenticated telemetry source exists, and actionable warning thresholds such as
   low disk/memory. Stale/unknown is never presented as healthy. The retired control
   plane label `Узлы Германия` is absent.
5. Referral/campaign detail lives in Growth when deeper comparison is required;
   Overview only summarizes and links to the real workflow. No dead button, fake
   report, mute/delete, node-add or repair action is introduced.
6. Admin catalog is derived from the same effective catalog preparation used by
   public subscription generation, with real order/names/visibility and no Finland,
   Canada, legacy x10 or hidden raw rows leaking into the published view. It clearly
   distinguishes source inbounds from generated AutoSelect/LTE fallback profiles.
7. The supported YouTube ad-free routing rule is restored in the ArcVPN-owned Happ
   routing payload, is syntactically valid, does not import unverified third-party
   geoassets, and has regression coverage.
8. Panel-driven node/server/protocol addition is either delivered end-to-end with
   authorization, safe validation, Remnawave binding and real-traffic acceptance, or
   documented as the next node-agent stage with an explicit data/API contract. The
   existing catalog editor must not claim it creates inbounds or nodes.
9. Local tests and WebApp build pass. Browser acceptance covers 390x844, 768x1024,
   1366x768 and 1920x1080 for admin entry, Overview, Health, Catalog and renewal;
   focus/hover/disabled/loading/error/empty states, keyboard order, contrast and
   overflow are checked. Before/after screenshots are recorded.
10. Exact diff is reviewed and secret-scanned; commit/push/pull/restart/public
    verification completes. Production proof includes real API values, service
    health, panel/customer host split and a freshly generated public subscription
    inspected without printing its identifier.

Risks and rollback: bad nginx routing can expose the wrong surface; expensive
aggregate queries can slow admin refresh; raw Remnawave names can leak retired
profiles; incorrect routing can break imports. Rollback restores the backed-up nginx
file and prior runtime commit, restarts only `arcvpn-subscription.service`, and keeps
all identities/URLs unchanged. New read-only metrics must fail closed as unknown,
not block customer subscription delivery.

Evidence recorded 2026-08-27:

- Released commits `20e3388` and `a4e6890`; production fast-forwarded to
  `a4e6890`. `arcvpn-subscription.service` and `arcvpn-bot.service` were active,
  and `nginx -t` passed. The prior nginx file and pre-cleanup SQLite catalog are
  recoverable from `/root/arcvpn-config-backups/`.
- Production `/api/admin/overview` returned HTTP 200 against the real database
  and Remnawave. It exposed payment/acquisition/product/traffic groups and two
  connected DHost nodes with live RAM telemetry. Example verified aggregates:
  2 successful payments/1260 RUB over 7 days and 5/1985 RUB over 30 days.
- The effective catalog now reports AutoSelect; Netherlands VLESS/Hysteria2;
  Germany VLESS/Hysteria2; YouTube without ads; and LTE #1..#5 with EU flags.
  Ten stale catalog overrides, including the old x10 label, were cleared only
  after a consistent SQLite backup.
- Fresh production subscription generation passed for plain, base64 and Happ
  JSON without printing the identifier: YouTube present, five LTE profiles,
  no Finland/Canada/France. Native Remnawave was the source with no fallback.
- Local regression suite: `110 passed`. Vite production build passed without
  Svelte warnings. Browser visual QA on the built code covered 390x844,
  768x1024, 1366x768 and 1920x1080; document overflow was false at all four.
  Desktop renewal, Overview and Health screenshots were captured in-browser.
- Public checks passed: `panel.arccnet.space/` redirects to `/admin`;
  `arccnet.space` serves the ArcVPN/Арк ВПН title, an allowlisted robots file and
  valid sitemap; panel robots disallow the entire host. A final new production
  browser navigation was blocked by Browser Use URL policy after a navigation
  timeout, so no circumvention was attempted. Authenticated production visual
  and keyboard activation remain open evidence, not silently accepted.
- Mailjet Free is selected but not activated: account/domain verification,
  provider-issued SPF/DKIM, DMARC and production SMTP credentials remain an
  owner-controlled external gate. Current official plan evidence: 6000 emails
  per month and 200 per day at the time of this check.

## 2026-08-27 apex activation, LTE metering audit and SMTP feasibility

Goal: activate the customer cabinet on `arccnet.space`, prove how LTE usage is
accounted for in direct and fallback profiles, and choose a deliverable email
path without weakening stable subscriptions or mail security.

Affected components: Poland SNI/nginx/TLS, customer `WEBAPP_URL`, Remnawave LTE
identity usage and scheduler reconciliation, Happ fallback JSON, public browser
surface, SMTP network/DNS feasibility and operations documentation.

Acceptance fixed before mutation:

1. Apex A record resolves to Poland before certificate issuance. TLS is valid,
   `https://arccnet.space/` serves the customer cabinet, and
   `panel.arccnet.space` remains admin-only. Stable `/sub/<id>` URLs stay on the
   existing subscription origin.
2. For Telegram ID 2075630349, compare Remnawave LTE identity usage, local
   `lte_used_bytes`, HTTP `Subscription-Userinfo`, and WebApp API without printing
   identifiers. Explain whether selected LTE #1-#3 used main or fallback.
3. LTE #1-#3 consume LTE quota only when their main balancer actually falls back
   to LTE XHTTP; #4-#5 always use the LTE identity. The info block mirrors the LTE
   identity, with bounded scheduler lag, and never estimates usage from a label.
4. SMTP decision is evidence-based: recheck outbound ports/PTR/DNS, compare
   currently available no-cost relays from primary provider documentation, and
   never install a self-hosted MTA that cannot deliver reliably.
5. Rollout uses config backup, nginx syntax check, certificate issuance, selective
   service reload/restart, public health/browser verification and an explicit
   rollback to the prior SNI map and unset `WEBAPP_URL`.

Risks: an incorrect SNI map can disrupt every TLS hostname; forcing LTE accounting
by profile label would charge main traffic; self-hosted mail without PTR and port
25 has poor deliverability. Stage remains open if a real client fallback or email
delivery cannot be proven.

Evidence on 2026-08-27:

- `arccnet.space` resolves to Poland. A Let's Encrypt certificate was issued,
  nginx syntax passed, and `/` plus `/app` return the customer cabinet over valid
  HTTPS. `panel.arccnet.space` still serves the noindex admin surface. The prior
  nginx file is backed up under `/root/arcvpn-config-backups/apex-20260827_0712`.
- The customer origin is injected as `WEBAPP_URL=https://arccnet.space` into both
  services. Telegram's persistent menu now reads the same environment variable;
  production logged `https://arccnet.space/app` after restart. Stable subscription
  URLs remain on `sub.arccnet.space`.
- LTE reconciliation previously crashed every cycle because the environment-backed
  Remnawave authority lacked the numeric cache `id`. Commit `ec6620c` reserves a
  negative cache identity. The full local suite passed (109 tests), production was
  pulled/restarted, and the selected account then matched byte-for-byte across
  Remnawave, local entitlement and `Subscription-Userinfo` (45-GiB quota).
- LTE #1-#3 use the unlimited main identity while the main balancer is healthy and
  consume LTE only after real loopback fallback to the separate LTE XHTTP identity.
  LTE #4-#5 always use that LTE identity. Current aggregate Remnawave accounting
  proves LTE consumption but cannot attribute past bytes to an individual profile.
- Browser acceptance passed at 390x844, 768x1024, 1366x768 and 1920x1080 with no
  horizontal overflow. Title, canonical URL, favicon, logo and theme metadata were
  present. The only console warnings are Telegram WebApp SDK capability warnings in
  a standalone browser, not application errors.
- Direct SMTP remains unsuitable: outbound 25/465/587 are blocked, current PTR is
  provider-owned, and apex has no mail-authentication records. Mailjet and Brevo
  port 2525 are reachable. Mailjet Free is the preferred minimal relay gate; an
  account, verified sending domain, provider-issued SPF/DKIM and SMTP credentials
  are still external prerequisites before a real email delivery pass.

## 2026-08-26 customer profile, LTE fallback and apex-domain correction

Goal: restore the useful Hysteria2 choices and the documented three-profile
main-to-LTE fallback behavior, make unlimited ordinary traffic truthful in every
customer surface, improve the wide purchase composition, and prepare the apex
domain/DNS/mail rollout without changing stable subscription URLs or UUIDs.

Mapped components: Happ subscription assembly and verification, DNS canary
selection, trial LTE entitlement, customer bot copy, WebApp purchase/account UI,
public metadata/domain configuration, legal copy, production environment and
REG.RU/mail operations guide.

Acceptance fixed before implementation:

1. Happ rows are ordered AutoSelect, Netherlands VLESS/Hysteria2, Germany
   VLESS/Hysteria2, then five EU LTE-labelled rows. LTE #1-#3 are independent
   main least-load balancers with LTE XHTTP fallback; LTE #4-#5 remain direct LTE
   profiles. Main/LTE credentials and stable URLs/UUIDs are preserved.
2. DNS v2 is enabled only for Telegram ID `2075630349`; global clients remain on
   the rollback profile until the user's real-device canary.
3. Trial remains Standard for seven days but receives exactly 5 GiB of LTE quota;
   ordinary traffic is unlimited. Paid Economy/Standard/Family descriptions all
   state unlimited main traffic and the exact LTE/device allowance.
4. WebApp account replaces the obsolete 1024-GB main display with `Безлимит` and
   a separate LTE remaining/quota line. Standard purchase defaults to SBP. At
   laptop/wide sizes the tariff/payment composition is vertically centered/lower,
   with no mobile/tablet overflow or interaction regression.
5. `arccnet.space` is the customer cabinet canonical origin and
   `panel.arccnet.space` remains admin-only. Deployment must not request a
   certificate before DNS ownership resolves to Poland.
6. Legal copy visibly explains no voluntary refunds and liability limitations,
   while preserving rights that cannot legally be waived. SMTP is accepted only
   with working outbound delivery, PTR/SPF/DKIM/DMARC and secrets outside Git; an
   infeasible self-hosted configuration is reported as an external blocker, not
   presented as working.
7. Focused/full tests and build pass; browser before/after acceptance covers
   390x844, 768x1024, 1366x768 and 1920x1080 without horizontal overflow. Runtime
   rollout follows commit/push/pull/restart/public verification.

Risks and rollback: malformed balancer JSON can break Happ imports or consume LTE
traffic unexpectedly; apex DNS/certificate or mail changes can disrupt public
access/deliverability. Rollback restores the previous subscription JSON builder,
DNS canary environment and nginx origin; it never rotates identities or URLs.

Status: in progress.

Local evidence:

- Full regression: `107 passed`; WebApp production build: 87 modules with no
  compiler warning; `git diff --check` passed.
- Browser pass at 390x844, 768x1024, 1366x768 and 1920x1080 found no horizontal
  overflow. Purchase copy shows unlimited main traffic plus the separate 45-GB
  LTE allowance, and SBP is active when the payment sheet first opens. Wide
  composition is vertically centered instead of pinned to the top.
- Happ unit coverage confirms Hysteria2 rows and three fallback LTE profiles;
  direct LTE remains only in rows 4-5. Trial coverage confirms a 5-GB LTE grant.
- Apex DNS currently has no A/MX/TXT record. Poland has no active MTA and outbound
  TCP/25 is blocked, so a self-hosted SMTP cannot be truthfully deployed there.
  A relay SMTP or provider unblock/PTR is still an external prerequisite.

Production rollout and acceptance status:

- Runtime commits `08fd884`, `610b261` and routing correction `d71af08` were
  pushed and fast-forwarded on Poland. Bot/subscription services are active and
  health is OK. Public admin root is HTTP 200, customer `/app` on the panel host
  is HTTP 404, the signed customer asset/legal page are HTTP 200.
- Criterion 1 passed: credential-safe verification reports five main and five
  direct LTE share links, zero identity crossover, exact 10-row Happ order and
  intact announce/header. The first three EU LTE JSON rows carry the tested
  main→LTE balancer contract; Hysteria2 is visible for NL and DE.
- Criterion 2 is configured and server-generated canary JSON for the selected ID
  uses DNS v2 while the global profile remains legacy. Real Wi-Fi/LTE client use
  is deliberately left to the owner.
- Criterion 3 passed for new provisioning and the three active legacy trials.
  Production backup `backups/vpn_bot.pre-trial-lte5-20260826.db` preceded the
  reconciliation; all three now satisfy unlimited main + 5-GiB separate LTE.
- Criterion 4 passed locally at all four viewports and production assets are live;
  the owner retains the authenticated real-device purchase scenario.
- Criterion 5 is prepared but deferred: REG.RU apex A record and TLS do not yet
  exist, so nginx apex activation and `WEBAPP_URL=https://arccnet.space` remain
  intentionally off. Stable subscription URLs are unchanged.
- Criterion 6 legal copy passed. SMTP is blocked by outbound TCP/25 and absent
  PTR/SPF/DKIM/DMARC; no fake or undeliverable SMTP was installed.
- Criterion 7 passed automated/local browser checks. Remaining external checks
  are the short owner DNS canary, apex DNS propagation/TLS, and one real email
  delivery after a relay or port/PTR solution. Stage remains in progress.

## 2026-08-26 LTE isolation and truthful quota rollout

Goal: make ordinary VPN traffic unlimited while metering and enforcing only the
0/45/115 GB LTE bypass allowance through Remnawave, without changing the stable
ArcVPN subscription URL or the existing main user UUID.

Mapped components: Remnawave adapter and sync scripts, user/key schema, billing
provisioning, calendar reset scheduler, subscription link transformation and
headers/announce, account API, focused LTE/subscription tests, production squads
and their inbound bindings.

Acceptance fixed before implementation:

1. Main and LTE usage are isolated by distinct Remnawave user identities; the
   current `client_uuid` remains the unlimited main identity and a new durable LTE
   UUID is used only on LTE XHTTP links.
2. Main squad contains no LTE inbounds; LTE squad contains only the reviewed
   `NL_DHOST_LTE_XHTTP` and `DE_DHOST_LTE_XHTTP` inbounds. No public subscription
   URL or main UUID changes.
3. Economy receives no LTE links. Standard and Family receive LTE links with the
   separate identity and Remnawave limits of 45/115 GiB. Renewal/reset is aligned
   to the existing personal calendar anniversary and is idempotent.
4. Subscription `upload/download/total` represents LTE usage/quota only. The
   approved five-line announce is emitted intact in HTTP/plain/base64/Happ output.
5. WebApp/API and announce reconcile against the same LTE usage. Quota exhaustion
   removes/disables only LTE access while ordinary VPN remains active.
6. Migration has backup plus preview/apply modes, provisions missing LTE identities,
   verifies UUID/squad/limit, and never deletes or rotates current identities.
7. Unit/integration/subscription tests pass; production requires squad/user
   verification, generated profile inspection and a real Standard-user LTE canary.

Risks: wrong squad edits can remove active access; using node-level usage is invalid
because both ordinary and LTE inbounds currently share DE/NL nodes. Implementation
therefore uses identity isolation, fail-closed topology validation and preview by
default. Rollback restores the previous main squad bindings/limits and generated
bundle while preserving both UUIDs.

Verification matrix: topology read-only audit, migration dry-run, focused tests,
full pytest, exact diff/secret scan, backup, production apply, service restart,
public format inspection and real tunneled main/LTE canary.

Status: in progress

Rollout evidence (2026-08-26):

- Production SQLite was backed up to the explicit pre-LTE artifact before schema
  v58. Migration preview selected 14 active users with zero errors; apply created
  14 LTE identities, updated 14 unlimited main identities, and the idempotent
  repeat updated 14/14 with zero errors.
- `ArcVPN Staging` now contains only the four reviewed DE/NL main inbounds.
  `ArcVPN LTE` contains exactly `DE_DHOST_LTE_XHTTP` and
  `NL_DHOST_LTE_XHTTP`. Existing main UUIDs and public ArcVPN URLs were retained.
- Credential-safe production inspection passed: five main share links use only
  the main identity; five LTE share links use only the LTE identity; header total
  equals the LTE quota; announce matches; Happ JSON contains exactly eight rows
  ordered AutoSelect, Netherlands, Germany, five EU LTE profiles.
- Finland is excluded from subscription delivery and from both backend/admin node
  surfaces. Its disconnected Remnawave records were not destructively deleted.
- Local regression passed `107 passed`; WebApp build passed with 87 modules.
  Production health is OK and bot/subscription services are active.
- Criteria 1-6 passed by migration/API/profile evidence. Criterion 7 remains
  partially external: generated production profiles passed, but a real tunneled
  Standard-user LTE exhaustion/main-survival canary still requires a user device.

## 2026-08-26 follow-up: login, tariff clarity, branding and LTE-only quota

Goal: remove the newly reported purchase/login friction and make the customer
traffic model explicit: ordinary VPN traffic is unlimited; only the LTE bypass
allowance is metered.

Affected components: `webapp/src/views/HomeFlowPreview.svelte`, standalone login
in `webapp/src/App.svelte`, admin session API/database, tariff copy helpers,
`subscription_api.py` announce/headers, public brand assets and focused tests.

Acceptance fixed before edits:

1. Promo input has no decorative rectangular focus fill/border/outline change;
   keyboard focus remains indicated by the field glyph, and there is at least
   12 px separation from recurring.
2. The supplied ArcVPN mark is used for favicon/manifest and standalone login.
3. Admin password sessions persist across normal browser restarts for 30 days;
   `/admin` never renders customer-login wording and logout still revokes access.
4. Standalone login centers brand/title and offers both Telegram and email paths;
   Telegram action opens the official bot/WebApp entry without accepting an
   unverified client identity.
5. Economy/Standard/Family descriptions contain no decorative emoji and state
   devices plus `Обход глушилок: нет` or the exact LTE allowance.
6. Customer-facing ordinary traffic is unlimited while LTE remains metered and
   reconciled. Announce exactly uses the approved five lines; LTE usage occupies
   subscription traffic headers/profile metadata without changing stable URLs or
   UUIDs. HTTP headers, plain/base64 and Happ JSON receive regression coverage.
7. Browser before/after evidence covers 390x844, 768x1024, 1366x768 and
   1920x1080; no horizontal overflow, promo disabled/error/success, keyboard focus,
   admin login/session copy, Telegram/email login and public assets are checked.

Risks/rollback: persistent admin cookies increase stolen-device exposure, so keep
HttpOnly/Secure/SameSite and server-side expiry/revocation. Traffic presentation
must not disable LTE enforcement or lie about Remnawave usage. Rollback is the
runtime commit plus previous generated bundle; no URL/UUID/database deletion.

Verification matrix: focused auth/announce/tariff tests, full pytest, WebApp build,
local browser four-view pass, staged diff/secret scan, production backup/pull,
affected-service restart, health/public/browser verification.

Evidence before rollout (2026-08-26):

- Local browser rendered standalone Telegram + email login with centered mark and
  heading. Purchase DOM exposes `126 ₽ / мес` before
  `6 месяцев · всего 759 ₽`; Standard copy is exactly
  `Основной трафик: 1024 ГБ (1 ТБ) · Обход глушилок: 45 ГБ · 3 устройства`.
- Local responsive pass at 390x844, 768x1024, 1366x768 and 1920x1080 found
  `scrollWidth == innerWidth`. Promo input CSS has no outline or box shadow and
  the promo surface has a 16 px bottom separation before recurring.
- WebApp production build passed: 87 modules, no compiler warning. Full Python
  regression passed: `104 passed in 4.85s`. `git diff --check` passed.
- Admin password cookie contract is now persistent for 30 days while retaining
  Secure, HttpOnly and SameSite=Strict; logout/server-side expiry remain intact.
- Criterion 6 is deliberately not claimed: current Remnawave identity aggregates
  normal and LTE links, while `lte_used_bytes` has no production per-node usage
  reconciliation. Presenting normal traffic as unlimited now would remove the
  only effective aggregate cap and make the requested announce false. Safe next
  work requires an LTE node UUID allowlist, node/user usage ingestion and a
  separately revocable LTE identity/squad before the text/header switch.

Rollout evidence:

- Runtime commit `33fad1e` was pushed to `origin/main`, production fast-forwarded
  from `afea781`, and only `arcvpn-subscription.service` restarted. Subscription
  and bot services are active.
- Public health, `/api/public/config`, the 23,332-byte WebP mark, manifest and
  admin HTML all returned HTTP 200. Production browser showed the standalone
  Telegram/email login and the distinct `Вход в ArcVPN Admin` password surface.
- Password persistence is proven by the 30-day cookie test/header contract; a
  manual existing-password browser login was intentionally not attempted.
- Acceptance 1-5 passed. Acceptance 7 passed for local four-viewport composition
  and public route/asset semantics; a real keyboard-only password-login pass is
  still external. Acceptance 6 is deferred for the enforcement reason above.
- Rollback is `git revert 33fad1e` followed by subscription-service restart; no
  schema, subscription URL, UUID or node topology changed in this release.

Status: in progress
Started: 2026-08-24
Expanded: 2026-08-24 after the Support deployment, before further runtime edits

## Follow-up correction: dashboard hierarchy and Schemes removal

User evidence on 2026-08-24 invalidated the visual usefulness of the deployed overview and Schemes screen. Before this correction, desktop production shows unequal KPI columns, an independently positioned logout control under the refresh cluster, stretched infrastructure whitespace, and unstructured device metrics. The Schemes editor has no ArcVPN apply/version/rollback contract and does not justify its navigation or bundle cost.

Acceptance fixed before the correction:

1. Remove Schemes from authorized navigation, rendering, source components, generated bundle, and the now-unused graph dependency. Direct stale section state must fall back to an available section; no placeholder or dead CSS remains.
2. Remove the overview logout control from the refresh/header composition; authentication expiration and the login surface remain functional.
3. Desktop/wide overview uses a consistent four-column KPI grid and a 12-column operational panel grid. Nodes and attention panels align at the top instead of stretching each other; device metrics have an explicit internal grid.
4. Tablet/mobile collapse predictably without horizontal document overflow; all remaining sections stay reachable.
5. Build and local tests pass with zero new touched accessibility/unused-CSS warnings; before/after browser evidence covers four viewport classes.
6. Exact diff is committed/pushed, production fast-forwards, only the subscription service restarts for the rebuilt admin bundle, and authenticated production browser verification confirms the removed route/navigation and corrected grid.

Correction evidence before deployment:

- Schemes navigation/rendering and both graph components are removed; `@xyflow/svelte` plus its graph/D3 dependency tree is removed from the package lock.
- Final bundle changed from `608.96 kB` JS / `231.06 kB` CSS to `381.71 kB` JS / `201.82 kB` CSS. The build passed; the only Svelte warnings remain the two pre-existing warnings in untouched `HomeFlowPreview.svelte`.
- Four-viewport overview geometry: desktop/wide KPI cards resolve to four equal columns; the operational surface resolves to 12 equal tracks; Nodes and Attention have identical top coordinates; device metrics resolve to five columns, then two on tablet and one on mobile.
- Responsive smoke covered the 10 remaining sections x four viewports (`40` combinations): no document overflow, Schemes navigation, or overview logout control. Screenshots: `.codex/stages/evidence/admin-dashboard-correction/{mobile,tablet,desktop,wide}-overview.png`.
- Full local Python regression remains `68 passed`; `git diff --check` passed.
- Correction commit `d111e11efa5f86738e54fc6e464fabe3e2dc9bb6` was pushed and fast-forwarded on production. Only `arcvpn-subscription.service` restarted; its readiness poll returned `OK`, and both subscription and bot services are active.
- Authenticated production verification passed at 390x844, 768x1024, 1366x768, and 1920x1080: no document overflow, Schemes nav, or logout control; desktop/wide KPI columns are equal and Nodes/Attention align. Public panel and the exact `index-JV-fiZUG.js` / `index-e0ypqx1N.css` assets returned HTTP 200.

## Goal

Turn every ArcVPN admin section into one coherent, original, production-grade operations panel. Preserve the already deployed Support workspace and real ArcVPN operations, close demonstrated functional gaps using existing or explicitly implemented ArcVPN contracts, and make the whole panel responsive, accessible, observable, and recoverable from failures.

## Non-goals

- Do not copy Axottle code, assets, naming, or exact visual treatment; its screenshot is only a reference for information hierarchy, dense-but-readable cards, and quick actions.
- Do not change subscription URLs, user UUIDs, node/protocol topology, Remnawave state, or active-user access.
- Do not promote Schemes into production routing control.
- Do not clone Axottle screens, code, assets, copy, information architecture, or branding. Its public documentation is comparative product research only.
- Do not add generic infrastructure controls merely because Axottle exposes them. A new action requires an ArcVPN-owned backend contract, permissions, safe confirmation, test coverage, and production evidence.
- Do not turn Schemes into production routing control or introduce node/CDN/GeoAssets/SelfSteal mutations in this frontend stage.
- Do not add backend schema migrations unless a browser-observed core workflow cannot be completed safely without one and the acceptance plan is amended before implementation.

## Baseline and component map

- Local branch `main`, `origin/main`, and production `/root/ArcVPN` were all at `3846570a73575601bb5a44bf84db96d24ce45ba3` before edits; local worktree was clean.
- Production `arcvpn-bot.service` and `arcvpn-subscription.service` were active/running/enabled with successful main status. Local service health and public panel/subscription endpoints returned HTTP 200.
- Production contains pre-existing tracked and untracked operational changes. They are owner-owned, outside this stage, and must not be reset, cleaned, or deleted. Deployment must check overlap before `git pull --ff-only`.
- `webapp/src/views/AdminConsole.svelte`: admin shell, navigation, Support state/actions, Support markup, and currently overlapping shell/Support style layers.
- `webapp/src/lib/api.js`: existing Support client calls and dev fixtures.
- `subscription_api.py`: existing authenticated Support list/detail/reply API and SPA delivery; change only if focused verification finds a real contract defect.
- `database/db_support.py`: existing thread/message persistence; inspect for tests, do not change without a demonstrated contract defect.
- `tests/`: focused Support/API and role regression coverage if backend behavior needs explicit proof.
- `webapp_dist/`: generated production bundle after the accepted source build.
- Runtime/deploy target: `arcvpn-subscription.service` and `arcvpn-bot.service`; both import the changed shared panel reconciliation code.

### Expanded screen and ownership map

| Section | Primary component | Required operator outcome |
|---|---|---|
| Главная | `AdminConsole.svelte` | Understand service health, business pulse, attention queue, and reach the responsible workflow. |
| Здоровье | `AdminHealth.svelte` | Diagnose stale/degraded/offline state and refresh evidence without confusing cached data for current state. |
| Схемы подключений | `AdminSchemes.svelte` | Inspect and validate declared connection layouts; clearly distinguish read-only/planned behavior from active routing. |
| Ноды | `AdminNodes.svelte` | Inspect node status and operational metadata; expose safe failure/empty/stale states. |
| Каталог подписки | `AdminCatalog.svelte` | Understand the user-visible catalog and its ordering/availability without implying unsupported mutations. |
| Пользователи | `AdminUsers.svelte` | Search and inspect users, subscriptions, devices, and relevant actions with permission/error feedback. |
| Финансы | `AdminFinance.svelte` | Inspect revenue and operational expenses, and distinguish loading, failed, validation, mutation, and empty states. |
| Поддержка | `AdminConsole.svelte` Support workspace | Triage threads and send one durable reply with recovery from all request failures. |
| Безопасность | `AdminSecurity.svelte` | Inspect access/device/audit evidence and perform only existing guarded actions. |
| Резервные копии | `AdminBackups.svelte` | See backup freshness/status and execute only existing confirmed backup operations. |
| Настройки | `AdminSettings.svelte` | Inspect integration readiness and effective access; owners can manage the supported administrator-role contract with validation and feedback. |

## Browser-first defect evidence

| ID | Page/component | Viewport | Severity | Reproduction and observed defect |
|---|---|---:|---|---|
| S-01 | Support navigation | mobile <=560 px | critical | Shell CSS hides navigation items 5+, while Support is item 8; the section cannot be opened from the UI. |
| S-02 | Thread list | tablet/mobile <=900 px | critical | Support CSS sets `.thread-list{display:none}` with no conversation-list/back control; only the auto-selected first thread is reachable. |
| S-03 | Support requests | all | high | Thread list/detail loaders have no visible loading or error/retry state; reply failure is silent. Old detail can remain visible while a new thread loads. |
| S-04 | Empty states | all | medium | Empty thread list and empty conversation have no distinct actionable states; the right pane can be blank. |
| S-05 | Keyboard/accessibility | all | high | Refresh glyph lacks an accessible name; reply textarea lacks an explicit label; selected nav/thread semantics are absent; textarea removes outline; no Support `:focus-visible` treatment. |
| S-06 | Disabled/loading | all | medium | Send disablement exists functionally but has no sufficiently distinct visual/loading feedback; double actions and request context are unclear. |
| S-07 | Layout/density | laptop/tablet | high | Support uses fixed viewport-height math inside the shell and hides overflow globally; composition can clip/conceal content instead of proving no horizontal overflow. |
| S-08 | CSS maintainability | shell/Support | all | Multiple successive style layers redefine the same shell and Support selectors, producing dead/overridden CSS risk and hard-to-predict breakpoints. |
| S-09 | Production auth baseline | wide 1920x1080 | gate | Real `https://panel.arccnet.space/admin` loaded in the in-app browser with no horizontal overflow, but the current browser session stopped at the owner login surface. Screenshot: `.codex/stages/evidence/support-before/wide-1920x1080.png`. Authenticated Support evidence is still required before acceptance. |
| P-01 | Whole-panel navigation | mobile 390x844 | critical | Authenticated production browser shows only Home, Health, Nodes, Support, and Settings. Schemes, Catalog, Users, Finance, Security, and Backups are `display:none` with no menu/scroll alternative. |
| P-02 | Admin shell/RBAC | all | critical | Backend `/api/admin/access` exposes effective permissions, but the shell always loads overview first, renders every section, and labels every session Owner/full access. A support-only role lacks `overview.read` and therefore cannot reach its permitted Support workspace. |
| P-03 | Users subscription mutation | all | critical | Local disable expires the SQLite key, while the minute sync selects only unexpired keys. The existing generic revoke path interprets Remnawave nodes as XUI inbounds, so an already provisioned remote identity can remain ACTIVE. |
| P-04 | Schemes | tablet/desktop/wide | high | Visible graph nodes extend beyond the main viewport even while document width reports equality because the shell masks overflow. UI copy implies an apply workflow, but no apply contract exists; background metric changes can rebuild and discard the local draft. |
| P-05 | Overview refresh | all | high | A transient 30-second refresh error replaces the authenticated workspace with the login card instead of retaining the last known snapshot and exposing stale/retry state. |
| P-06 | Health/Nodes/Catalog | all | high | Health omits Remnawave/subscription failures and uses an unsupported numeric score; Nodes calls SSH preflight “Add node” although no bootstrap exists and labels bps as MB/s; Catalog lacks error/empty/dirty/reset semantics and an audit failure after commit can invite a duplicate retry. |
| P-07 | Users/Finance/Security/Backups/Settings | all | high | Network/mutation state machines are incomplete; Finance can silently show zeros on failure; Security reports false empty while loading; Backups calls every historical file verified without a returned verification status; Settings is a static status page with a hard-coded SMTP state. |
| P-08 | Accessibility and CSS | all | high | Non-Support components have missing labels/live regions/current/expanded/disabled semantics, weak mobile reflow, unused props/selectors, and the shell retains an unreachable `active === 'network'` branch with legacy CSS. |

## Axottle comparison and disposition

The public Axottle documentation is used only to compare operator outcomes and safety contracts. ArcVPN implementation remains original and limited to ArcVPN-owned APIs.

| Documented product pattern | ArcVPN disposition for this stage | Evidence/constraint |
|---|---|---|
| Permission-aware navigation and protected actions | **Implement now** | ArcVPN already has `/api/admin/access`, `/api/admin/roles`, and a role matrix; the frontend is the missing link. Reference: `https://docs.axottle.com/ru/panel/navigation`, `.../access-and-sessions`. |
| Dashboard that answers health / recent change / next action | **Implement available evidence now** | Reuse ArcVPN overview, health, attention queue, audit, and existing route actions; do not invent incident objects or quick actions without contracts. Reference: `https://docs.axottle.com/ru/panel/dashboard`. |
| Operation/audit journal with filters | **Implement bounded version now** | ArcVPN already exposes the last 500 append-only audit events; client-side search/filter/refresh is valid. Server pagination and a distinct operations event model are deferred. Reference: `https://docs.axottle.com/ru/panel/journal-and-audit`. |
| Explicit health states/severity and stale evidence | **Implement from existing telemetry now** | Derive honest severity from Remnawave, services, registered nodes, database integrity, disk boundary, and timestamps. Do not invent self-heal or SLO percentages. Reference: `https://docs.axottle.com/ru/health/states`. |
| Node metrics/services/diagnostics | **Implement truthful inspection now; defer mutations** | Metrics and bounded diagnostics exist. Agent bootstrap, service start/stop, logs, GeoAssets, TLS, and provisioning lack an ArcVPN admin API and require a separate node-ops contract. Reference: `https://docs.axottle.com/ru/nodes/control-panel`. |
| Versioned connection-unit editor with validate/apply/rollback | **Reject imitation; make current screen honest** | ArcVPN has derived topology only, no version/apply/rollback backend. Keep read-only topology or clearly local planning; no production-control affordance. Reference: `https://docs.axottle.com/ru/connection-units/lifecycle`. |
| Backup histories with integrity status and previewed restore | **Implement truthful list/create now; defer restore** | ArcVPN API can create a quick-checked local SQLite snapshot and list files, but does not return persistent verification, download, retention, offsite storage, or restore preview. Reference: `https://docs.axottle.com/ru/operations/backups`. |
| Settings with real persisted forms, reset, roles, integrations | **Implement access/readiness evidence now; defer missing APIs** | Effective role/permissions and role assignments exist. SMTP readiness can be reported. 2FA, sessions, notification policy, health policy, integration mutation, and passwords require new security contracts. Reference: `https://docs.axottle.com/ru/panel/settings`. |
| Ticket SLA, assignment, priority, delivery queue, infrastructure context | **Defer** | ArcVPN Support currently has thread/message persistence and best-effort Telegram delivery only. Schema, delivery job state, operator ownership, and SLA clocks need a separate backend stage. Preserve the improved reliable reply flow. Reference: `https://docs.axottle.com/ru/support/tickets`. |
| CDN, SelfSteal, GeoAssets, Axosun, anti-abuse automation, status page | **Reject for this stage** | No matching ArcVPN-owned admin contracts or production acceptance gates. Decorative controls would be misleading and risky. |

## Whole-panel acceptance criteria (fixed before expanded implementation)

1. Every mapped section is reachable and usable at mobile 390x844, tablet 768x1024, laptop/desktop 1366x768, and wide 1920x1080.
2. At every section and viewport `documentElement.scrollWidth <= innerWidth`; content is not merely hidden by an x-overflow mask, and no required control, table cell, dialog, popover, or navigation item is clipped or unreachable.
3. Each section has a deliberate composition appropriate to the viewport: dense operational layout on desktop/wide, readable stacking or drill-down on tablet/mobile, and no information encoded by position or color alone.
4. Every network-backed surface exposes intentional loading, recoverable error, empty, stale/last-updated where relevant, and settled states. Mutations expose distinct ready, disabled, in-flight, success, validation-error, and server-error states without losing user input or duplicating actions.
5. Hover, selected/current, `:focus-visible`, disabled, loading, warning, error, and empty states are visually distinct and readable in all touched components.
6. A keyboard-only pass can reach every section and every visible control in logical order, activate safe controls, operate forms/dialogs, return focus after dismissal, and never lose visible focus.
7. Interactive elements have accessible names and semantics; headings/landmarks are coherent; current navigation, expanded state, tables, forms, errors, and live status updates are programmatically exposed. Touched components produce zero accessibility or unused/dead-CSS warnings.
8. Existing real operations remain intact and receive focused regression proof: overview refresh/routing, health refresh, node/catalog/user/payment inspection, Support list/open/reply persistence, security/device/audit actions, backup actions, and supported settings updates. No API/RBAC/path regression.
9. Axottle comparison produces a traceable gap matrix with three dispositions: implement now using an ArcVPN contract, defer with a concrete missing dependency, or reject as out of scope/risky. No proprietary code, assets, exact copy, or misleading unsupported control enters ArcVPN.
10. Original ArcVPN visual language is preserved: dark navy surfaces, ice-blue primary actions, compact operational metadata, restrained semantic accents, and consistent shell/page/state primitives across all sections.
11. Before/after screenshots exist for every section at all four viewport classes. Key dialogs, overflow behavior, empty/error/loading, hover/focus, disabled, and success states have additional evidence where static default screenshots are insufficient.
12. Local focused tests, full relevant Python regression, browser interaction checks, and `npm run build` pass. Generated assets are inspected with source changes; no touched warning or accidental fixture text ships in production.
13. Exact staged diff is reviewed and secret-scanned; commit is pushed; production performs `git pull --ff-only`; only affected services restart; service state, health, public assets/version, authenticated production workflows, all four viewport classes, and a real safe operation are verified.

## Risks and mitigations

- **Reply duplication or wrong-thread send:** keep one guarded send path, disable during flight, bind request to the selected thread id, and verify persisted result.
- **Responsive state trap:** model list/detail explicitly rather than hiding the list at a breakpoint; test browser navigation at all four widths.
- **Owner-only production access:** never expose credentials. Use an already-authorized browser session or obtain action-time confirmation before any password transmission; do not mark browser acceptance passed while gated.
- **Generated bundle drift:** build from the reviewed source and inspect `webapp_dist/` alongside source changes.
- **Production dirty tree:** compare incoming tracked paths with remote status before fast-forward; abort safely on overlap.
- **Unrelated shell regressions:** constrain shell edits to navigation reachability and Support layout; smoke-test another admin section at each viewport.
- **Local disable without Remnawave revocation:** target is the authorized admin mutation plus the shared panel reconciliation path, and only users explicitly changed by that operation. Current state can remove local eligibility while leaving an already provisioned Remnawave identity active. Desired state is idempotent remote deactivation keyed by the existing UUID, with no UUID or subscription URL replacement and no impact to still-active users. Gate with focused adapter/API tests, a production dry/read-only comparison, one explicitly safe disabled test identity if available, Remnawave state verification, and unchanged active-user authorization. Roll back the sync change and re-enable only the designated test identity if the remote transition is not exact.

## Rollback

- Revert the stage commit, rebuild `webapp_dist/`, push, production `git pull --ff-only`, and restart `arcvpn-subscription.service` plus `arcvpn-bot.service` because the shared panel reconciliation path changed.
- No database rollback should be needed because this stage must not migrate or rewrite support data.
- If deployment health or Support operations regress, immediately roll back the UI commit while preserving all production operational files.

## Verification matrix

| Check | Mobile 390x844 | Tablet 768x1024 | Desktop 1366x768 | Wide 1920x1080 | Evidence/status |
|---|---:|---:|---:|---:|---|
| No horizontal overflow / no clipped controls | local pass | local pass | local pass | local pass | All 11 sections: `scrollWidth == innerWidth`; required controls inside viewport after mobile Users filter correction; Schemes canvas is contained and pannable. |
| Composition and section navigation | local pass | local pass | local pass | local pass | 44 after screenshots under `.codex/stages/evidence/admin-after/`; every owner section is reachable, including horizontally scrollable mobile shell navigation. |
| Hover/focus/disabled/loading/error/empty | local pass | local pass | local pass | local pass | 17 cross-panel state/RBAC screenshots plus prior Support state evidence; child request fixtures cover error/empty, mutation controls expose guarded states. |
| Keyboard-only path and accessible names | partial | partial | partial | partial | names/current/live regions and focus-visible verified; in-app key injection focused controls but did not dispatch Tab/Enter activation, so a real keyboard pass remains a production/manual gate |
| RBAC and read-only behavior | local pass | local pass | local pass | local pass | Browser roles: support sees only Support and can reply; viewer mutations disabled; finance/operator nav matches effective permissions; access/role endpoint tests pass. |
| Real operations | pending prod | pending prod | local/API pass, prod pending | local/API pass, prod pending | 68 tests cover RBAC, Support, verified Remnawave disable and panel-sync failure. Production safe-operation and Support reply gates remain. |

## Evidence log

- `git status --short --branch`: clean local `main...origin/main` before stage.
- Production read-only baseline: matching local/origin/deployed commit; both services healthy; panel and public health HTTP 200.
- Production login baseline: `.codex/stages/evidence/support-before/wide-1920x1080.png`.
- Current UI fixture screenshots: `.codex/stages/evidence/support-before/wide-dev-1920x1080.png`, `desktop-1366x768.png`, `tablet-768x1024.png`, and `mobile-390x844.png`.
- Browser DOM metrics confirmed width equality at all four viewports. This did not count as overflow acceptance because `body` masked x-overflow; tablet/mobile hid the thread list, and mobile CSS set Support navigation to `display:none`.
- Baseline `npm run build` passed but reported pre-existing warnings, including unused selectors in `AdminConsole.svelte`. Touched-component warnings must be removed before acceptance; unrelated warnings are recorded as residual project debt rather than silently claimed fixed.
- After screenshots: `.codex/stages/evidence/support-after/{mobile,mobile-list,tablet,tablet-list,desktop,wide}-*.png` plus focused `state-*.png` for loading, list/detail/send errors, empty queue/history, sending, success, and focus.
- Responsive metrics after the cascade fixes: mobile workspace `16..374.4` at width 390 with nav `790.8..838.8`; tablet workspace `98..752` at width 768; desktop workspace `304..1334.4` at width 1366; wide workspace `316..1876` at width 1920. No required control crossed a viewport boundary.
- Browser state proof: list/detail failures expose retry UI; empty list/history are distinct; sending sets `aria-busy=true`, changes the label, and disables thread switching; send failure preserves the draft; successful dev reply increased messages 3→4, cleared the editor, updated the list preview, and announced success.
- Interaction proof: non-selected thread hover changed background/border/transform; keyboard-induced focus on thread/search/reply exposed a solid ice-blue outline; navigation, current section/thread, form labels, live/status regions, and disabled controls have accessible semantics.
- Focused API/RBAC tests after the audit-failure fix: `21 passed`. Full local Python suite: `57 passed`; `py_compile` passed.
- The earlier Support-only WebApp production build passed in 4.36s; `AdminConsole.svelte` produced zero accessibility or unused CSS warnings. Those historical results were superseded by the integrated whole-panel build below.
- Support commit `1da502d0e5423ee1c9e86b64653fcb17d0878a18` was pushed, fast-forwarded to production, and `arcvpn-subscription.service` is healthy. Public assets and the authenticated production overview load successfully.
- Support still retains two closeout gates: one authorized production reply and a real keyboard-only activation pass. They remain acceptance items of this expanded stage.
- Authenticated production baseline before this batch: 38 private screenshots under `C:/Users/babay/AppData/Local/Temp/arcvpn-admin-evidence/admin-before`. Tablet/desktop/wide cover all 11 sections; mobile captures the five reachable sections and proves the other six had no reachable navigation. They stay outside Git because they contain real operator data.
- Integrated safe-fixture after evidence: 44 screenshots under `.codex/stages/evidence/admin-after/` cover all 11 sections at 390x844, 768x1024, 1366x768, and 1920x1080. Browser geometry found zero document overflow and zero clipped required controls after the one-pixel Users filter fix.
- State/RBAC evidence: 17 screenshots under `.codex/stages/evidence/admin-after/states/` cover access denied/error, stale overview refresh, support/viewer roles, child error/empty states, and node-metrics error/empty states.
- Browser RBAC proof: support role booted directly into Support without overview access; viewer Support editor/send were disabled, Catalog inputs were read-only with no publish footer, and Backup creation was disabled. Owner, operator, finance, viewer, and support labels/navigation matched effective permissions.
- Backend operation proof: admin disable now updates Remnawave to `DISABLED` and verifies the authoritative read-back without changing the UUID; activate/adjust synchronizes immediately; a failed remote confirmation returns `502 panel_sync_failed` and is safely retryable. Focused and full local suite: `68 passed`; `py_compile` and `git diff --check` passed.
- Final integrated `npm run build` passed. All touched admin components have zero Svelte accessibility or unused-selector warnings. Two pre-existing warnings remain in untouched `HomeFlowPreview.svelte`; the existing bundle-size advisory remains.
- Runtime commit `9c77b67831f163605678c9b476d5c3b72741e349` was pushed and fast-forwarded on Poland production. Pre-existing remote dirty/untracked operational files were preserved; the only tracked dirty file remained `scripts/ssh_askpass.sh` and did not overlap the incoming diff.
- `arcvpn-bot.service` and `arcvpn-subscription.service` were restarted and are active/enabled with new main PIDs; local production health returned `OK`. The public panel, `index-D4WHQuS2.js`, and `index-BsuS_udP.css` returned HTTP 200 and the served HTML references those exact assets.
- Authenticated production browser acceptance covered all 11 sections at 390x844, 768x1024, 1366x768, and 1920x1080. All 44 combinations had `documentElement.scrollWidth == innerWidth`; no content control overflow was found. Four mobile nav buttons can be outside the instantaneous viewport only inside the intentional `overflow-x:auto` rail (`clientWidth 345`, `scrollWidth 558`) and were successfully scrolled to/opened.
- Production read-only operation proof: 3 node cards, 12 catalog profiles, 154 users with the first 40 rows loaded, 3 finance summary cards, 48 audit events, one listed backup, settings/readiness/RBAC data, and Support list/open with 3 threads and a four-message history. Support refresh settled without error; the empty reply remains correctly disabled.
- Private production after screenshots (real operator data, not committed): `C:/Users/babay/AppData/Local/Temp/arcvpn-admin-evidence/admin-after-production-9c77b67/` for representative mobile, tablet, desktop, and wide screens. Visual inspection confirmed the intended mobile bottom rail, contained/pannable Schemes composition, readable Users layout, and wide Settings/RBAC composition.

## Next step

The implementation and deploy are accepted except for three explicitly destructive/manual gates: a real keyboard-only activation pass, one authorized production Support reply with persistence/delivery evidence, and a designated safe disabled Remnawave test identity for live revoke confirmation. Do not mark the stage complete until those gates are confirmed or explicitly waived.
# Current stage — growth, billing, LTE, and Remnawave-native cutover

Started: 2026-08-25. Status: in progress.

## 2026-08-26 accepted expansion: onboarding, anniversary quotas and public cabinet

The user accepted a decision-complete implementation plan before runtime edits.
This expansion supersedes any conflicting 30-day/global-first-of-month reset
language below; all prior evidence remains historical.

### Goal and component map

- `database/` and scheduler: one calendar-month anniversary for normal and LTE
  quota, idempotent due-cycle processing, legal-consent version/time.
- Remnawave adapter and trial: one Standard Remnawave identity, retryable
  entitlement, safe preview/backfill without URL or UUID replacement.
- bot onboarding/purchase/admin: consent-aware channel gate, one image-free trial
  welcome, structured tariff copy, current cabinet, retire the visible legacy
  Telegram admin and all user-facing crypto/Stars affordances.
- `subscription_api.py`: coherent traffic/LTE status and announce, promo quote,
  public cabinet routing, SMTP-backed standalone email login, DNS/routing profile.
- `webapp/` and generated `webapp_dist/`: monthly-price hierarchy, one tariff
  title, contrast, real promo states, email/site metadata and route separation.

### Fixed acceptance

1. A purchase at an arbitrary timestamp resets normal and LTE quota on the same
   calendar day next month; days 29-31 clamp to month end without permanently
   changing the anchor. Early renewal preserves the active cycle; a lapsed new
   purchase starts a new cycle.
2. Each due cycle is processed exactly once locally and confirmed in Remnawave;
   retryable remote failure cannot silently advance the durable reset boundary.
3. Trial provisions one Standard user through the production Remnawave contract.
   Failed/stale entitlement retries are idempotent. Production backfill is
   backup + dry-run + exact confirmation and only targets the accepted eligible
   class.
4. Channel consent -> trial -> one image-free welcome with Connect/Continue;
   repeated start opens the current cabinet. Structured tariff descriptions
   cannot be hidden by stale message-editor text.
5. Promo Apply performs an authenticated quote, visibly updates base/discount/
   final price, preserves errors, and usage is recorded only by successful
   idempotent fulfillment. Crypto and Stars are absent from customer UI.
6. `/admin` is the admin SPA; `/app` and `/` are the customer cabinet. Public
   cabinet has favicon, manifest, canonical/OG/Twitter metadata; admin is noindex.
7. SMTP secrets remain outside Git. Standalone email codes are rate-limited,
   one-use, expiring and non-enumerating; live delivery is a deployment gate
   until the owner supplies the custom SMTP/DNS settings.
8. LTE announce is complete in response header, base64 profile and Happ JSON.
   DNS uses only reviewed supported categories and avoids public Google/
   Cloudflare UDP/DoH defaults; exact generated JSON is parsed in regression.
9. Browser before/after proof covers 390x844, 768x1024, 1366x768 and 1920x1080,
   with no document overflow and explicit hover/focus/disabled/loading/error/
   empty/success states. Build success alone is not visual acceptance.
10. Local full/focused tests and build pass; exact diff is reviewed and secret
    scanned; commit/push/pull/restart/public verification follow the production
    workflow. DNS global activation requires a real two-platform Wi-Fi/mobile
    client canary and rollback proof; the stage stays open if unavailable.

### Risks and rollback

- Quota double reset/access loss: store due state, use an operation lock, advance
  only after authoritative reset; restore the pre-migration DB and previous
  Remnawave counters on mismatch.
- Trial duplication: deterministic entitlement/identity lookup before create;
  never replace a live UUID/subscription URL.
- DNS regression: retain the previous routing payload, parse all formats, perform
  client canary before global default, revert payload without identity changes.
- Legal/SMTP incompleteness: do not claim live acceptance while operator fields
  are placeholders or SMTP delivery/DNS authentication is unverified.
- Existing owner change `webapp_dist/assets/payments/sbp.svg` remains excluded.

### Verification matrix

| Area | Local gate | Production gate |
|---|---|---|
| Anniversary quota | month-end/leap/renew/retry tests | aggregate due preview + one safe reset/reconciliation |
| Trial/onboarding | adapter/idempotency/bot flow tests | backup, preview/backfill, one new-user flow |
| Promo/payments | quote/race/fulfillment tests | one safe promo payment path |
| Email/site | auth tests, metadata/build/browser | custom SMTP delivery and public route/assets |
| Subscription/DNS | decoded header/profile/JSON tests | stable URL fetch + two-platform network canary |
| Responsive UI | four viewport before/after + keyboard/states | authenticated public cabinet four-view pass |

## Goal

Prepare ArcVPN for paid acquisition: reliable Standard trial, Economy/Standard/
Family products, real independent LTE quota, campaign attribution, web promo
management, and Remnawave-native subscription authority without changing public
subscription URLs, UUIDs, or active access.

## Non-goals

- No copying Axottle source or proprietary implementation.
- No unverified protocol/node topology changes.
- No direct client migration to new public subscription URLs.
- No deletion outside the explicitly authorized inactive never-paid user class.

## Component map

- Product/DB: `database/`, tariff, trial, payment, promo, campaign migrations.
- Bot: onboarding/trial and two-step tariff/payment UI.
- Web/API: `subscription_api.py`, `webapp/`, `webapp_dist/`.
- Subscription plane: native Remnawave fetch, thin ArcVPN compatibility gateway,
  legacy fallback telemetry and later retirement.
- Production: Poland control plane; Germany/Netherlands RemnaNode delivery.

## Acceptance

- Trial is idempotent, uses Standard entitlements, and partial failure is retryable.
- Economy/Standard/Family prices and 1/3/6/12-month periods have one source of truth.
- LTE is a real 0/45/115 GB quota resetting on the shared calendar-month
  anniversary; no `x10` customer model.
- WebApp contains no add-traffic purchase and shows real remaining LTE.
- Campaign links have immutable first-touch attribution, named comparison metrics,
  and configurable entry/payment bonuses.
- Promo usage is consumed only after successful idempotent fulfillment.
- Remnawave supplies all share links; ArcVPN only preserves stable URL, device
  controls, metadata/catalog, announce, and Happ rendering. Fallback is measured.
- Existing active users retain URL/UUID/access; migration preview and rollback exist.
- A destructive never-paid cleanup requires backup, dry-run counts and relational
  integrity verification before an explicitly scoped production apply.
- Touched UI passes mobile/tablet/laptop/desktop composition, no horizontal
  overflow, keyboard navigation, focus/hover/disabled/loading/error/empty states,
  accessibility checks, and before/after screenshots.
- Local tests/build pass; exact staged diff is reviewed; commit/push/pull/restart
  and public/browser verification are recorded.

## Risks and rollback

- Entitlement migration can revoke access: snapshot rows and Remnawave state,
  update without UUID/subscription changes, recheck every affected identity.
- LTE counters can reset upstream: store monotonic checkpoints and never subtract
  negative deltas; keep enforcement disabled until shadow reconciliation passes.
- Trial retries can duplicate access: deterministic operation key and transaction.
- Hard deletion is irreversible: encrypted backup plus dry-run manifest; rollback
  restores the DB before services resume.
- Native subscription outage: short cache and observable legacy fallback until a
  zero-fallback soak allows removal.

## Verification matrix

| Area | Local | Production/public evidence |
|---|---|---|
| DB/trial/tariffs | migration + unit/integration tests | aggregate preview, test identity |
| LTE | counter/reset tests, shadow fixtures | Remnawave usage reconciliation |
| Bot/payments | handler and fulfillment tests | authorized test purchase/trial |
| Web/admin | typecheck, tests, build | four viewport browser screenshots |
| Subscription | native/fallback contract tests | stable URL, UUID and real client fetch |
| Capacity | load-test scripts | CPU/RAM/latency/error baseline |

## Evidence log

- Current implementation regression suite: `102 passed`; Python compile succeeds.
- Browser-first integration found and fixed a standalone `/app` first-render crash
  caused by an empty promo quote comparing equal to an empty tariff selection.
- Post-fix responsive measurements at 390x844, 768x1024, 1366x768 and
  1920x1080 all report `scrollWidth == innerWidth`; mobile and desktop screenshots
  were captured. The tariff sheet exposes `126 ₽ / мес` above
  `6 месяцев · всего 759 ₽`, shows one Standard heading, and has no crypto/Stars.
- Promo browser states verified: disabled empty Apply, invalid `INVALID` error,
  valid DEV canary `START10` discount and recalculated payment total.
- `/app/admin` DEV route renders the actual admin console with
  `noindex,nofollow`; production routes remain `/app` customer and `/admin` admin.
- Production preflight reports schema v56 and usable Remnawave credentials in the
  protected runtime file, but no registered Remnawave server row and no explicit
  write mode. The implementation now supports the protected authority as a
  fallback while requiring `REMNAWAVE_WRITE_MODE=production` before any write.
- Runtime commits `804ae98`, `237d182`, and `83c3298` were pushed and
  fast-forwarded on Poland. Pre-existing production files and the local owner
  change `webapp_dist/assets/payments/sbp.svg` were preserved.
- Restricted backup `backups/release-20260826T120238Z-onboarding-v57` was created
  before migration/config changes. Schema v57 applied explicitly; exact trial
  backfill preview/apply was `2 -> provisioned 2, failed 0 -> preview 0`, with a
  separate SQLite backup. A live operational warning exposed an unclosed trial
  HTTP client; follow-up commit `83c3298` fixes it and the full suite is again
  `102 passed`.
- Protected Remnawave config now has explicit write mode `production`. Both
  `arcvpn-subscription.service` and `arcvpn-bot.service` are active, health is
  `OK`, journal scan has no new error/exception/traceback/unclosed entries, and
  production HEAD is `83c3298`.
- Public `/app/app-icon.svg` and `/app/site.webmanifest` return HTTP 200;
  `/admin` returns `X-Robots-Tag: noindex, nofollow`. Public `/app` renders the
  standalone email login at 390x844, 768x1024, 1366x768 and 1920x1080 with no
  horizontal overflow. Public `/admin` resolves to the admin/login surface,
  no overflow at laptop width, `noindex,nofollow`, and no console errors.
- Deferred external gates: real SMTP delivery and linked-email login need the
  owner's SMTP/SPF/DKIM/DMARC setup; legal acceptance needs verified operator
  details; authenticated payment/promo and keyboard-only passes need a safe test
  identity; DNS v2 stays disabled until Wi-Fi/mobile plus two-Happ-platform canary;
  anniversary reconciliation needs a real boundary observation. Stage remains
  **in progress** and is not declared complete.

- Pre-change worktree: only pre-existing owner change
  `webapp_dist/assets/payments/sbp.svg`; it is excluded from this stage.
- Baseline architecture: native Remnawave links are fetched by
  `_native_remnawave_links`, then rendered by the ArcVPN gateway; legacy generation
  remains a fallback.
- Implemented migrations v54-v56: durable Standard trial, product/LTE model,
  first-touch campaigns and promo activation state.
- Combined local verification: `84 passed`; modified Python modules compile.
- `webapp` production build completed with 87 modules and no Svelte accessibility
  or unused-CSS warnings.
- Local browser acceptance used authenticated DEV mocks. Growth and purchase flows
  have no horizontal overflow at 1440x900, 1180x760, 820x1180 and 390x844.
  Browser screenshots were emitted for desktop Growth, mobile Growth (top/bottom),
  and mobile tariff purchase. Mobile internal scroll reaches all campaign cards.
- Browser integration caught and fixed a late-device-response bug that had shown
  Standard as 2 devices / 0 LTE; recheck shows 3 devices / 45 GB LTE and correct
  Economy/Family switching. Monthly display now follows the approved floor values.
- Local browser console has no ArcVPN errors; warnings come only from Telegram's
  SDK reporting unsupported color/swipe methods in its DEV version 6.0 shim.
- Real keyboard Tab focus movement could not be demonstrated through the in-app
  browser automation (focus remained on the selected navigation control); semantic
  buttons/inputs and `:focus-visible` rules are present, but this acceptance item
  remains open for production keyboard verification.
- Runtime commit `91ba74a` and production-schema hotfix `f6b3156` were pushed and
  fast-forwarded on Poland. The pre-existing production dirty/untracked files and
  the local owner change `webapp_dist/assets/payments/sbp.svg` were preserved.
- A pre-deploy copy of `database/vpn_bot.db` and separate operation-level SQLite
  backups were created under production `backups/release-*` with restricted modes.
- Automatic bot startup had not yet reached its migration hook after restart;
  the checked-in idempotent migration runner was invoked explicitly. Production
  then reported schema v56, 12 active products across 3 families, both services
  active, and subscription health `OK`.
- Production dry-runs found 13 active non-Standard keys and 135 inactive,
  never-paid, non-admin users with no current key. The cleanup dry-run exposed a
  production-schema mismatch before mutation; hotfix `f6b3156` removed the
  nonexistent `users.is_active` dependency and its production-shaped regression
  suite passed (`35 passed`).
- After exact confirmation and backup, 13 active keys were migrated to Standard
  without UUID or URL replacement and 135 explicitly authorized cleanup records
  were deleted. Repeated dry-runs returned `active_keys=0` and
  `eligible_users=0`.
- Public `https://panel.arccnet.space/app` returned HTTP 200 and references the
  deployed `index-DBrs44gk.js` and `index-C2adVayo.css`; public/local health was
  `OK`. The browser's previous one-time owner verification is expired, so a new
  authenticated production four-viewport visual/keyboard pass remains open.
- The native Remnawave source is deployed behind the stable ArcVPN gateway, but
  legacy fallback retirement remains gated on production source metrics and a
  zero-fallback soak. This is not yet a direct public-URL cutover.

---
# Trial feedback and bot account navigation follow-up (2026-08-29)

## Acceptance

- A trial user receives the rating prompt once, no earlier than 24 hours after the trial entitlement is activated.
- Rating answers are persisted and visible in the authenticated admin overview, including distribution and recent respondents.
- Bot settings expose the existing verified-email flow, and the renew-tariff Back button returns to subscriptions.
- Existing lifecycle buttons, public subscription URLs, UUIDs and active access remain compatible.

## Components, risk and rollback

- Components: bot lifecycle scheduler/callbacks, bot settings keyboard, payment-flow keyboard, admin overview API/UI, WebApp deep link.
- Main risk: duplicate prompts during migration from `day5_rating`; prevented by excluding both event keys and accepting both callback generations.
- Rollback: revert the runtime commit and restart only `arcvpn-bot.service` and `arcvpn-subscription.service`; no schema migration or destructive data change is required.

## Closeout evidence

- Acceptance 1 passed: focused coverage proves the 23-hour boundary, 25-hour delivery and one-shot behavior; production created 9 `trial_day1_rating` events after deployment.
- Acceptance 2 passed in code/API and local rendered UI: answers are persisted, Overview returns aggregates plus recent respondents, and the empty state rendered at 360, 768, 1280 and 1920 px without horizontal overflow. Production authenticated visual inspection remains owner-session acceptance; the public bundle is current.
- Acceptance 3 passed: keyboard regression verifies renewal Back=`my_keys`; bot Settings links `/app?screen=email`, and the WebApp accepts the email deep link.
- Acceptance 4 passed: no schema/public identifier change; legacy rating callback coverage passes.
- Verification: 128 pytest tests passed, Vite production build passed, Python compilation passed, and public `/health` returned HTTP 200 with the expected JS/CSS asset hashes.
- Release: runtime commit `d27d11e` was pushed and fast-forwarded on Poland. Only `arcvpn-bot.service` and `arcvpn-subscription.service` restarted; both are active/enabled and their post-release error journal is empty.
- Rollback remains `git revert d27d11e`, push/pull, then restart the same two services. Next step: inspect the first real answers in Overview and confirm the email button/back button from a real Telegram client.
# Current stage: advertising acquisition correctness (2026-09-01)

## Goal

Count an advertising campaign only when its deep link creates a genuinely new
bot user, and report revenue from successful payments in normalized RUB.
Remove the two owner-identified invalid attributions from production without
changing either user account or payment history.

## Non-goals

- No edits to users, subscriptions, VPN keys, or payment rows.
- No change to campaign URLs, codes, bonus configuration, or first-touch for
  legitimate new users.
- No frontend redesign.

## Components

- `bot/handlers/user/start.py`: new-user eligibility at `/start ad_*`.
- `database/db_campaigns.py`: defensive attribution contract and normalized
  campaign aggregates.
- `tests/test_campaigns_and_admin_promos.py`: regression coverage.
- Production SQLite: narrowly remove attribution/bonus rows for the two supplied
  usernames after a separate backup and read-only target check.

## Acceptance

| Contract | Required observable result |
|---|---|
| Existing user opens `ad_*` | no attribution, no entry bonus, no campaign counters |
| New user opens active `ad_*` | one immutable first-touch attribution |
| Campaign payments | only successful payments at/after attribution are counted |
| Revenue | YooKassa provider rows are read as kopecks; legacy supported rows as whole RUB; UI receives normalized kopecks |
| Named correction | `@progressive_dev` and `@Turan11627` have no campaign attribution/bonus rows; their users/payments remain intact |
| Release | focused/full tests, diff review, push, production pull, affected-service restart, production aggregate verification |

## Risks and rollback

- Risk: deleting more than attribution metadata. Mitigation: resolve by exact
  normalized username, require exactly two targets, back up DB, delete only
  `campaign_bonus_grants` and `user_campaign_attribution` in one transaction.
- Risk: mixed historical payment units. Mitigation: preserve stored history and
  normalize only in the reporting query using the established provider contract.
- Rollback: revert runtime commit and redeploy; restore the timestamped DB backup
  only if the targeted metadata correction itself must be reversed.

## Verification matrix

- Passed: focused campaign suite, 8 tests.
- Passed: full local suite, 158 tests; Python compilation and `git diff --check`.
- Passed read-only production target check: exactly two supplied usernames, each
  has one attribution to `исма канал`; no campaign bonus rows. Their 26 and 2
  successful historical payments explain the incorrect 28-order aggregate.
- Pending: production backup and exact two-target correction.
- Pending: service/public/admin aggregate verification.

---
