# ArcVPN handoff — AutoSelect balance and CDN/XHTTP diagnosis

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
