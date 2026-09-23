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
