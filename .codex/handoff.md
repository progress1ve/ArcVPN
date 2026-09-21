# ArcVPN handoff — referral activation and RU web gateway

## Current production state — 2026-09-21

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
