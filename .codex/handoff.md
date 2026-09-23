# ArcVPN handoff — INCY AutoSelect restored

## 2026-09-23 INCY subscription fix

- Release `9ce4d3b` is deployed on `pl-control`; only the subscription service
  was restarted and is active.
- INCY's default `/sub/<id>` request now receives the full JSON profiles,
  including the composite AutoSelect profile. Happ remains JSON, Hiddify remains
  plain, and subscription URLs, user UUIDs and node topology are unchanged.
- Production check with the reported subscription and INCY User-Agent: HTTP 200,
  JSON, 13 profiles, AutoSelect first with a routing balancer. Focused production
  tests: 13 passed.
- Owner should refresh the existing subscription in INCY. If the profile is
  still absent, inspect its imported subscription cache/profile visibility in
  the app; do not change node routing based on that symptom alone.

## Previous state

## 2026-09-23 current production

- Release `98cf0c9` is deployed on `pl-control`; subscription service is active.
- Happ `/import/<sub_id>` redirects to JSON; old Happ links containing
  `format=plain` are served as JSON when refreshed, restoring the composite
  `Автовыбор | Самый быстрый` profile without changing subscription URLs or
  user UUIDs. Hiddify's plain format remains unchanged.
- Production check: 14 of 16 sampled active subscriptions expose AutoSelect
  through their old Happ plain URLs. The other two are device-limit responses,
  which intentionally contain no normal VPN profiles and need account-specific
  access diagnosis if reported by the owner.
- Next action for the owner: refresh the subscription in Happ. If the profile
  remains absent, capture the visible profile names or a redacted screenshot to
  distinguish a device-limit response from a client cache problem.

## Previous state

## Current production state — 2026-09-23

- Production is `0b0df96` on Poland control plane; database schema v66,
  `arcvpn-subscription.service` and `arcvpn-bot.service` active.
- `/admin/feedback` now shows aggregate trial/win-back answer categories,
  response counts, payment-history filter and links to users. The old per-user
  tab remains for drill-down. `speed` is the complaint «Низкая скорость».
- Connected expired trial users without commercial payment are split by user
  parity: one cohort receives a one-use 20% offer for a 3-month tariff for 48h
  and at most one reminder; the other keeps the existing survey. Eligibility
  and discount are checked server-side. Production eligible audience was zero
  immediately before rollout.
- 175 and 225 GB bypass choices are available in public/WebApp custom builders
  and server quote validation. Add-on GB screen says they last until the next
  traffic reset. Main traffic remains unlimited.
- A `HEAD` subscription check no longer reserves a direct-import device slot.
  INCY is labelled only when the request identifies it; unknown stays unknown.
  Existing generic slots were not removed.
- For the reported add-on account, local and Remnawave both showed an active
  50 GB allowance and just over 5 GB used, so no 5 GB cap or counter repair was
  justified.
- Full backend suite: 214 passed (one old deprecation warning); WebApp and
  admin builds and admin TypeScript passed. Public admin/WebApp plus referenced
  assets return 200; unauthenticated feedback returns 403. Browser QA remains
  with the owner by request.

## Next step

- Owner checks the new answer dashboard and custom-tier/add-on presentation on
  phone. Capture a real INCY import User-Agent if it still appears as generic;
  do not infer the app from a VPN connection or delete an unknown slot.

## Previous release

## Current production state — 2026-09-23

- Production runtime is `75b78c6`; `arcvpn-subscription.service` is active.
- Client 360 now has an «Ответы» tab with each user's trial-rating and expired
  win-back answers, optional free-text detail and answer time. The protected
  user-detail API returns only the selected user's answered lifecycle events.
- Admin waits for Russian i18n readiness before React mounts, so raw
  `admin.*` keys no longer flash on a cold load.
- `/admin` is dark-only and no longer exposes theme controls. Desktop, mobile,
  login and unavailable states use the native white ArcVPN SVG mark.
- Dashboard trial counts come from active `trial_entitlements` with an
  unexpired linked VPN key. Production currently reports 3 trials and 14 paid
  active subscriptions instead of the old hard-coded zero.
- New `/admin/profit` recognizes paid subscription revenue across the covered
  calendar months, excludes trials, and subtracts categorized one-time or
  recurring expenses. Existing `service_expenses` rows are reused.
- Production admin HTML and its referenced bundle return 200; unauthenticated
  user-detail API access returns 403. Browser QA was explicitly left to owner.

## Next step

- Review «Ответы» on a real user and approve the proposed segmented trial
  win-back experiment before any discount or broadcast is created.

## Prior infrastructure state

## Current production state — 2026-09-22

- Production runtime is `47536e1`; `arcvpn-subscription.service` is active.
- Happ AutoSelect keeps Germany and Estonia in a two-candidate `leastLoad` pool:
  `expected=2`, `tolerance=0.2`, `maxRTT=3s`. Failed/high-RTT candidates are
  still removed; CDN remains a hidden fallback and public names/URLs/UUIDs are
  unchanged.
- Production-generated JSON was inspected without exposing user identifiers:
  two main outbounds, the new strategy settings and the existing CDN fallback
  are present. Users must refresh their subscription to receive the change.
- Germany and Estonia RemnaNodes are connected. The observed session snapshot
  during diagnosis was Estonia 9 / Germany 7; distribution is statistical per
  connection and cannot guarantee exact global 50/50 for twelve users.
- The reported CDN/XHTTP fade is not caused by ArcVPN nginx's idle timeout:
  Moscow and Germany `/api-test` proxy timeouts are 3600 seconds. Moscow logs
  contained 108,651 successful XHTTP requests and 35 non-2xx; clustered 5xx
  aligned with an origin interruption rather than a repeating two-minute cut.
- Yandex CDN has an independently reproduced roughly 60-second idle-response
  threshold for XHTTP `packet-up`. A client/platform-specific timed reproduction
  is still required before changing mode because current Xray has no generic
  packet-up downlink keepalive/reopen fix and `stream-up` compatibility must be
  proven through the existing OPTIONS-to-POST edge path.

## Next step

- Obtain the affected friend's OS, Happ version, approximate failure time and
  whether the fade happens during upload/idle or ordinary browsing; run a
  correlated 3–5 minute real tunnel capture before any CDN transport mutation.

## Prior still-current product state — 2026-09-21

- Runtime release `f28662f` is deployed on `pl-control`; bot, subscription API
  and nginx are active.
- Referral entry/trial days are no longer granted when a trial is issued. They
  are granted once only after the invited user's key is observed online with at
  least one device. Purchase rewards remain unchanged.
- Admin marketing is live: referral-link and promocode management, campaign
  attribution edges, corrected trial classification and current-server detail.
- The bot uses the new ArcVPN blue cover family for cabinet, payment, referral,
  settings and subscription screens. Source assets are versioned in
  `bot/assets/`.
- `https://ru.arccnet.space/`, `/app` and `/admin` are served through the Moscow
  VPS as an HTTPS reverse proxy to the Poland control plane. Primary domains,
  API contracts, user UUIDs and subscription URLs are unchanged.
- The RU nginx rollback copy is
  `/opt/arcvpn/staging/ru-arccnet.conf.before-web-gateway` on `msk-beget`.

## Verification

- Full test suite: 204 passed; one `datetime.utcnow()` deprecation warning.
- Svelte WebApp production build and React admin TypeScript/build passed.
- Public primary and RU landing, cabinet and admin pages return 200; sampled
  referenced JS assets return 200.
- Browser evidence confirms the RU landing renders and RU admin reaches the
  ArcVPN login surface.
- Bot traffic synchronization completed multiple post-restart cycles without a
  first-connection processing error; fleet check reports three current nodes
  and zero events.

## Preserved server-local state

- `pl-control` still contains the pre-existing modified
  `scripts/ssh_askpass.sh`, runtime databases, secrets and historical backup
  files. They were not changed or removed.

## Next step

- Observe one new real referred signup through first device connection and
  confirm the single reward/audit row in production; automated idempotency and
  ordering tests already pass.
# INCY icon and lifecycle automation follow-up — 2026-09-23

- Customer device list now has a transparent inline SVG `INCY` wordmark inheriting the existing blue icon color; it is shown only for `device.browser === 'incy'`. Unknown clients remain unknown.
- Existing lifecycle scheduler sends day-1 feedback, expired-winback survey, and a 20% connected-trial offer with one reminder. New campaign ideas and a deduplicated queue/permission/frequency contract are in `docs/roadmaps/automated-lifecycle-messaging.md`; no new campaign has been enabled.
- Owner requested no browser-based deployment check; use local build, service and public HTTP checks, and let the owner visually inspect the cabinet.
