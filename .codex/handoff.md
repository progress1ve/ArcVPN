# ArcVPN handoff — feedback and trial conversion (2026-09-27)

Runtime `803d29f` is on Poland. The feedback survey now sends an ArcVPN-blue "Ваше мнение" image, parses HTML captions, has a Back action for provisional Other/service answers, and stores free text for both current and legacy feedback events. A global Telegram parse-error fallback strips markup instead of displaying literal tags. Admin feedback displays the saved detail, and sales stats now derive trial and paid conversion from activation/purchase cohorts. Local tests: 229 passed; admin build passed. Both affected services active, panel HTTP 200. Production sales API: eight active trials, 33 trial activations and five later purchasers in the last 30 days. Exactly six historical 1/3/5 answer values were cleared (events retained) and one afterfive detail restored from the owner's screenshot. Restricted DB backup: `/root/ArcVPN/backups/feedback-20260927-pre-cleanup.sqlite3`. No browser QA at owner's request. Already-sent Telegram messages remain unchanged unless the user interacts with their buttons. Some unrelated sales widgets remain placeholder zero (manual top-ups and expired subscriptions); do not imply those are fixed.

## Archived YouTube handoff

# ArcVPN handoff — YouTube video routing for JSON subscriptions

On 2026-09-27 the owner confirmed that the afterfive canary fixed YouTube playback and authorized the same rule for other users. Runtime commit `39bcc2b` is deployed on Poland. All generated INCY/Happ JSON profiles now put narrow YouTube/googlevideo/ytimg proxy domains before the unchanged `geoip:ru` direct-IP rule; Russian-app direct routing, nodes, DNS, bridge, subscription URLs/UUIDs, and plain share-link subscriptions were not changed. Only `arcvpn-subscription.service` restarted and is active. Local suite: 228 passed, one existing deprecation warning. Public landing and panel HTTP 200; production rule and RU-direct checks passed. Clients must refresh their subscription to receive the new profile. The owner withdrew the request for a shareable troubleshooting instruction. Next: observe other clients after refresh; real playback was confirmed for the original canary, not yet independently for every client.

## Archived canary handoff

On 2026-09-27 the owner approved a one-account YouTube routing canary for afterfive (@progressive_dev). Runtime commit `b97c79f` was pushed to main and deployed by fast-forward on Poland; only `arcvpn-subscription.service` restarted and is active. Generated JSON profiles for this account put narrow YouTube/googlevideo/ytimg proxy domains before the unchanged `geoip:ru` direct-IP rule. The gate requires both stored account names and fails closed. Plain share-link output, other users, nodes, Moscow bridge, DNS and Windows binary were not changed.

Evidence: 229 local tests passed (one existing deprecation warning); production DB found exactly one account matching both names; after deployment, live gate returned true for it and false for a control account. Landing and panel returned HTTP 200. Real INCY playback has not been tested; ask the owner to refresh the subscription and retry the same video. If unsuccessful, revert `b97c79f`, pull fast-forward and restart only the subscription service. Stage details are in `.codex/stages/current.md`.

## Archived rollback handoff

On 2026-09-27 the unverified YouTube routing release `e80bd3e` and its closeout `aca715a` were reverted by `8a2a508` and `24d6a24`. Poland production is at `8a2a508`; `subscription_api.py` and routing tests match pre-change `7f4fc75`. The subscription service is active; landing and panel return HTTP 200. No route diagnosis or Moscow bridge mutation has been made. Next: diagnose the Moscow bridge and VPS read-only before proposing any fix.

## Prior tariff handoff

# ArcVPN handoff — custom 500 GB bypass tariff

## 2026-09-27 current stage

- Runtime commit `085808a` is deployed on Poland production. The custom tariff offers 500 GB of bypass traffic on landing and cabinet; the backend quote and payment order accept and persist this entitlement with the existing formula.
- Local focused tests: 19 passed; full suite: 227 passed with one existing deprecation warning. Vite build passed with existing unused-CSS warnings. Local browser confirmed 500 GB selection on both surfaces at its available viewport.
- `arcvpn-subscription.service` restarted and is active. Public 3-month / 3-device / 500-GB quote returned HTTP 200 and 3239 RUB; unsupported 501 GB returned HTTP 400. No real payment was submitted. Four exact viewport checks remain deferred.
- The owner's primary checkout has unrelated dirty files. Its `AI_CONTEXT.md` rewrite and Markdown audit are local-only work, not part of this deployed commit. Do not reset or sweep the owner's files.
- See `.codex/stages/current.md` for acceptance and rollback.

## Archived referral handoff

## 2026-09-27 current stage

- Production audit found one referred pair with a fulfilled first purchase and measured VPN traffic, but no entry/purchase reward flags or days.
- The payment webhook bypassed the old bot-only referral callback; online-IP polling missed a short VPN session despite authoritative traffic bytes.
- The release makes local key extensions and reward flags one transaction, awards purchase rewards from unified paid-order handling, detects first use from VPN traffic, and provides guarded dry-run-first recovery.
- Runtime `89bbaf2` is deployed; the affected pair received 5 entry days for the inviter and 15 purchase days for both parties. Ledger flags, DB expiries and Remnawave expiries agree; dry-run is 0/0. Both services active and public panel/site HTTP 200.
- Follow-up: consider a durable external-panel sync outbox; SQLite award is atomic but panel writes are a separate operation.
- See `.codex/stages/current.md` for acceptance and deployment evidence. Do not disclose customer or subscription identifiers.

## Archived AutoSelect handoff

## 2026-09-27 session-stable AutoSelect

- Runtime release `44dae54` is deployed on `pl-control`; only
  `arcvpn-subscription.service` was restarted and is active. A production SQLite
  backup was taken before the fast-forward pull.
- At subscription refresh, Remnawave `usersOnline` and recent assignment
  reservations select one connected Germany/Estonia main node. The assignment
  remains while panel activity is recent and can rebalance after 30 minutes
  offline and another refresh. Existing online users keep their current node
  on the first refresh where panel telemetry identifies it.
- The client receives one main AutoSelect outbound, so new video connections
  cannot jump between Germany and Estonia. The existing Yandex CDN path is
  still an emergency fallback. Manual country and YouTube profiles are unchanged.
- Evidence: 51 focused tests; three active public JSON subscriptions returned
  HTTP 200 with 13 profiles, one AutoSelect main, one CDN fallback, two YouTube
  outbounds; a live AutoSelect canary passed Xray config validation and returned
  HTTP 204 through the tunnel.
- Limit: distribution changes when a subscription refreshes, not when INCY's
  connect button is pressed. Inspect measured usersOnline after normal customer
  refreshes rather than treating an immediate static assignment count as load.

## Previous state

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
