# Custom tariff: 500 GB bypass — 2026-09-27

Goal: let customers select and purchase 500 GB of bypass quota in the existing custom tariff builder.

Contract: append exactly one `500 ГБ` choice after 225 GB on landing and customer cabinet; 1/3/6/12-month server quotes use the existing anchor-based per-GB pricing formula, with no new discount or fixed price. Payment order stores 500 GB requested entitlement and uses that exact server quote. This is not a 500-GB top-up/add-on option. Ordinary traffic remains unlimited.

Components: `subscription_api.py`, `webapp/src/views/{LandingPage,HomeFlowPreview}.svelte`, focused quote/payment tests. No migration, pricing-formula change, subscription identifier change, or other tariff change.

Acceptance: 500 GB can be selected at 390/768/1280/1600 px without overflow; quote is numeric and increases monotonically from 225 GB; payment initiation accepts and persists 500 GB at the quoted price; 501 GB and other unsupported values fail; existing choices and payment paths remain intact. Verify local tests/build, rendered before/after UI, staged diff, production rollout, and public quote response. Never submit a real payment during QA.

Risks/rollback: a mismatch between frontend selection and backend allowlist rejects checkout, so release both together. Existing per-GB extrapolation may create a high price; show the exact server quote before payment. Roll back the scoped commit and restart the subscription service; no data migration or active-subscription changes.

Baseline: public landing's custom builder currently ends at 225 GB. Its three-column control and live server-quote behavior were inspected in the browser before edits. Existing backend supports 0–225 GB via explicit allowlist; 500 GB is currently rejected.

## Archived prior stage: referral reward recovery — 2026-09-27

Goal: grant configured entry and first-purchase day bonuses reliably, and restore only demonstrably missed production rewards.

Scope: payment fulfillment paths, first-connection telemetry, referral ledger, tests, and bounded recovery. No tariff, URL, UUID, node, or frontend change.

Acceptance: an applied first purchase grants the configured purchase bonus once to both parties regardless of payment entry point; genuine first VPN use grants the configured entry bonus once to the inviter; replay/recovery cannot add days twice; production candidates are audited against payments, referral edges, existing flags and VPN use; service and ledger/expiry are verified after release.

Risks: flags and expiries update separately; historical usage can be incomplete. Dry-run recovery, inspect candidates, snapshot affected state, skip ambiguity. Roll back code by revert and affected-service restart; data by per-account journal, not broad restore.

Verification matrix: focused tests, relevant suite, staged diff, commit/push, production ff-only pull, restart only affected services, service/public health, live ledger/expiry audit.

Pre-release evidence: production read-only audit found seven referred accounts, one eligible paid-applied account without purchase reward, and one account with authoritative VPN usage but no entry reward; both are the same referral pair. The inviter has no ledger row. Local 225 tests pass (one existing datetime deprecation warning). Recovery command defaults to dry-run and requires explicit expected counts for apply.

Release evidence: runtime commit `89bbaf2` was pushed to main and pulled ff-only on the Poland control plane. Bot and subscription services restarted and are active. The bot's first post-restart usage sync granted the missing 5-day entry reward; guarded recovery granted the missing 15-day purchase reward. Ledger now records 20 days with both one-time flags set. Inviter expiry moved by 20 days, friend's by 15 days. Remnawave expiry matches the database for both accounts, and recovery dry-run reports 0/0 remaining. Public panel and landing return HTTP 200. Initial recovery invocation with system Python failed before mutation because dependencies were absent; the service virtualenv invocation succeeded.

Residual risk: external panel synchronization is separate from the SQLite transaction and can fail transiently; reward key sync logs false/exception and live production was explicitly checked. A future durable sync outbox would strengthen this further. Rollback status: no rollback needed; reverting runtime code does not undo correctly awarded customer days.

## Archived prior stage: AutoSelect session load distribution — 2026-09-27

## Accepted behavior

The owner accepted selection on subscription refresh using current Remnawave
`usersOnline`, with the selected main node retained while the user is active.
There is no permanent account-to-country binding and no Moscow ingress hop.
Xray's `leastLoad` is an RTT/stability selector, not a server-user-count selector;
it may send consecutive connections to different countries. Replace it only in
the customer-facing AutoSelect profile. Preserve the existing CDN emergency
fallback, manual country profiles, YouTube profile, quota, and identifiers.

| Client path | Visible profile | Client hostname | CDN resource / origin | Host/SNI | Inbound/path | Multiplier | Public impact | Failure / rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Assigned main | AutoSelect | Germany `de.arccnet.space` or Estonia `87.251.19.197` | none | existing node-specific SNI | existing Reality TCP/443 | 1 | same subscription URL and user UUID; one selected main at a time | existing CDN fallback only if selected main fails; revert subscription-code commit |
| Emergency | AutoSelect fallback | `cdn-de.arccnet.space` | existing single Yandex CDN / Moscow origin | existing CDN Host/SNI | XHTTP `/api-test` | 1 | no new profile or URL | unchanged resource and origin; revert code commit |
| Manual/other | Country, YouTube, bypass profiles | existing published hosts | existing resources | unchanged | unchanged | 1 | unchanged | unchanged |

## Components and acceptance

- Components: `subscription_api.py`, one small persistence helper or migration,
  focused tests, current stage, handoff. No node, DNS, firewall or panel write.
- On refresh, choose the connected main node with fewer `usersOnline` users;
  account for concurrent recent assignments so a burst of new users splits.
- Keep the selected main while panel activity is recent. Reconsider only after
  at least 30 minutes without panel activity and a subsequent refresh.
- While panel telemetry is unavailable, retain an existing assignment. Never
  issue an invalid or empty AutoSelect profile.
- AutoSelect has exactly one normal main candidate; CDN remains an emergency
  fallback. No Germany/Estonia switching among successive video connections.
- Verify representative live subscriptions, syntax and real tunneled requests
  through AutoSelect, and that public URLs/UUIDs and other profiles remain stable.

## Risk and rollback

- A subscription refresh is the only observable decision point; INCY does not
  call this API each time the VPN switch is pressed. New users may retain a
  previously downloaded assignment until the next refresh.
- A stale `onlineAt` or panel outage could skew distribution; retain prior
  assignment and use a conservative connected-node fallback.
- Roll back the single runtime commit and restart only
  `arcvpn-subscription.service`; do not alter node configuration.

## Verification matrix

| Check | State | Evidence |
| --- | --- | --- |
| Current production behavior and counters | Passed | `leastLoad` client routing; Remnawave exposes `usersOnline` for connected DE/EE |
| Focused tests | Passed | 51 relevant tests passed in an isolated, migrated SQLite test database |
| Public subscription contract | Passed | Three active public JSON subscriptions: HTTP 200, 13 profiles, one main and one CDN fallback in AutoSelect, two YouTube outbounds |
| Real tunnel | Passed | Live AutoSelect JSON passed Xray config validation and returned HTTP 204 through a local SOCKS canary |
| Commit and deployment | Passed | Runtime commit `44dae54` pushed to `main`, production fast-forwarded, subscription service active; SQLite backup taken first |

# Trial feedback, conversion and client usage — 2026-09-23

## INCY AutoSelect correction — 2026-09-23

- Acceptance: the reported INCY subscription exposes AutoSelect first without
  changing its URL, user access, Hiddify output or node routing. Passed on the
  public endpoint: HTTP 200, JSON, 13 profiles, first profile AutoSelect with
  a balancer.
- Cause: INCY defaulted to base64 share links, which cannot contain a composite
  Xray balancer profile. Only its default format now resolves to JSON.
- Release: `9ce4d3b` pushed to `main`, pulled fast-forward on `pl-control`, and
  only `arcvpn-subscription.service` restarted. Service active; 13 focused tests
  passed in production. Local pytest was unavailable due to absent private
  `config.py`; the production environment supplied it.
- Rollback: revert `9ce4d3b` and restart the subscription service if INCY JSON
  import fails. Residual: app-side refreshed profile list is not remotely
  observable; owner should refresh and confirm the row appears.

## Follow-up: INCY identity and automated conversion

- Replace the provisional `I` device mark with a transparent SVG `INCY` wordmark in the existing device-icon blue. Only devices positively identified as INCY receive it; unknown clients are not guessed.
- Preserve existing lifecycle campaigns while specifying a single, deduplicated automated messaging policy with eligibility, frequency limits, stop conditions, and measurement.
- New outbound campaigns remain disabled until the owner chooses the initial journeys and approves their copy. No campaign is sent as part of the icon release.
- Verify the WebApp build and diff; browser visual acceptance remains with the owner per their instruction.
- Outcome: `c1f0e7f` deployed on `pl-control`; WebApp build passed (existing unused-CSS warnings), subscription service active, `/app/` and the new `/app/assets/App-B4lS35NJ.js` return HTTP 200. No browser QA per owner request. New outbound campaigns remain disabled; implementation awaits approval of the first journeys and copy.

## Previous stage

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

## Outcome

- Released `46f5344` and `0b0df96` to production; schema v66. Backup created
  before migration and passed SQLite `quick_check`.
- 214 backend tests passed; admin type-check/build and WebApp build passed.
- Public admin/WebApp plus both referenced bundles return 200; feedback without
  authentication returns 403. Bot and subscription services active. Browser QA
  omitted per owner request.
- LTE reported account has effective 50 GB in local DB and Remnawave and over
  5 GB counted; no traffic cap fix or data mutation was necessary.
- Outstanding: source of any existing generic GET-created slot cannot be
  identified from protocol traffic alone. No existing slot was revoked.

## 2026-09-23 Happ AutoSelect import repair

- Goal: restore the existing `Автовыбор | Самый быстрый` profile for Happ
  subscriptions imported through `/import/<sub_id>`.
- Current state: normal JSON subscriptions contain AutoSelect; the Happ
  User-Agent branch of the import endpoint redirects to `format=plain`, which
  cannot represent the composite AutoSelect profile.
- Desired state: that redirect selects `format=json`; existing Happ links with
  explicit `format=plain` refresh as JSON. Hiddify remains plain and other
  clients retain their prior formats. URLs, UUIDs, node topology and active
  authorization are unchanged.
- Affected path: Happ → `/import/<sub_id>` → `/sub/<sub_id>?format=json` →
  AutoSelect JSON profile with Germany/Estonia main routes and existing CDN
  fallback. Rollback: revert this redirect change and restart only the
  subscription service.
- Acceptance: focused redirect regression and real production subscription
  generation show AutoSelect first; service stays active. If a specific device
  returns a limit/revoked profile, diagnose its access state separately.
- Result: `98cf0c9` pushed to `main`, pulled fast-forward on `pl-control`, and
  only `arcvpn-subscription.service` restarted. It is active.
- Checks: 38 focused tests passed; Python compilation and staged diff check
  passed. In 16 sampled active subscriptions, 14 old Happ plain URLs now
  produce JSON with AutoSelect, while two produce explicit device-limit rows.
  The Happ import redirect points to `format=json`; Hiddify stays on plain.
- Residual: the owner's individual device has not yet been identified. If it
  sees a limit notice, resolve its device access rather than altering the
  subscription generator. If it still shows an old list after refresh, check
  the Happ cache/imported subscription identity.
