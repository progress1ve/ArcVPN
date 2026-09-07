# ArcVPN handoff — public Northern Flow landing

Updated: 2026-09-07. Current production runtime commit: `658a2a7`.

## Shipped

- `https://arccnet.space/` remains the public Svelte landing; `/app` keeps the
  existing authentication, paid trial and cabinet flows.
- The rejected fake Happ/INCY-style subscription window is removed. Its place
  is a concise trial panel explaining many locations, ordinary profiles and
  separate censorship-bypass profiles.
- Telegram trial CTA uses the configured public bot URL and is scoped to a new
  user. Website trial CTA uses `/app` and accurately states: new email account,
  7 days Standard, 5 GB bypass, 10 RUB and cancellable auto-renewal.
- The owner's anonymized real cabinet screenshots now form the desktop/phone
  product proof. Source WebP sizes are 25,164 and 20,166 bytes.
- Pricing is three separate rounded live-data cards; Standard remains the clear
  recommendation. Custom tariff uses the server quote inside one cohesive
  rounded builder and always exposes the numeric result when available.
- Mobile navigation is logo, `ArcVPN` and cabinet CTA only. The brand is shifted
  five pixels right; there is no burger menu.
- Internal landing links use explicit smooth scrolling; reduced-motion users
  retain immediate navigation.
- Discrete mouse-wheel scrolling has short, responsive inertia with bounded
  backlog and immediate direction changes. Trackpads keep native high-resolution
  scrolling, and reduced-motion disables the interpolation.
- Instagram and TikTok stay hidden until exact HTTPS URLs are configured.

## Evidence

- Runtime commits `5dfb6df`, `4571145`, `3b9eec1` and wheel-speed correction
  `658a2a7` pushed to `main` and pulled fast-forward on production `pl-control`.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: exit 0,
  no findings.
- `npm run build`: passed; Landing JS 13.83 kB gzip, CSS 5.98 kB gzip. Existing
  `HomeFlowPreview.svelte` unused-selector warnings are unchanged.
- `.venv\\Scripts\\python.exe -m pytest -q`: 177 passed.
- Browser QA: 360x800, 390x844, 768x1024, 1280x900 and 1600x900; no horizontal
  overflow, fake client count 0, trial offers 2, tariffs 3, numeric custom quote,
  no mobile burger, both cabinet images load at natural dimensions.
- Public `/`, `/app` and both cabinet WebP files return HTTP 200; public config
  has bot and cabinet URLs. `arcvpn-subscription.service` and `nginx.service`
  remain active. Static-only deployment required no restart.

## Owner files intentionally untouched

- `webapp/src/views/Connect.svelte` remains owner-modified.
- `docs/design/arcvpn-landing-page-prompt.md` remains owner-deleted.

## Follow-up

- Add verified Instagram/TikTok HTTPS URLs when ready.
- Optional separate cleanup: pre-existing unused-CSS warnings in
  `HomeFlowPreview.svelte`.

## Rollback

Revert `658a2a7`, `3b9eec1`, `4571145` and `5dfb6df`, push and pull
fast-forward on `pl-control`. `/app`, payment, authentication and subscription
URL contracts are unchanged; no service restart is needed for this static-only
rollback.
