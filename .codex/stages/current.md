# Stage: Public landing — proof, trial and pricing refinement

## Goal

Remove the rejected subscription-client imitation, replace placeholder cabinet
proof with the owner's real desktop/mobile screenshots, and give pricing a
cohesive rounded ArcVPN treatment. Add accurate trial discovery without
inventing a new purchase route.

## Exact visible contract

| Surface | Required result |
|---|---|
| Subscription area | Remove the entire large fake client shown in the owner's first screenshot |
| Locations/trial | State that the subscription contains many locations and invite visitors to inspect them through a real trial |
| Telegram trial | `Бесплатно в Telegram`; CTA uses the configured public `bot_url`; copy limits the claim to a new user |
| Website trial | `7 дней Standard за 10 ₽`; CTA uses the existing `/app` email flow; disclose that the offer is for a new email account and includes auto-renewal |
| Cabinet proof | Use the supplied anonymized 1844x1068 desktop and 568x920 mobile screenshots, not CSS placeholders |
| Mobile nav | Keep logo/name/cabinet only; move the brand five pixels to the right |
| Pricing | Keep live API prices and all current product/period intents, but use three separated rounded plans with a clear Standard recommendation |
| Custom tariff | Keep server quote and current controls/intent; place them in one rounded builder with a distinct rounded result area |

## Design plan

- Palette: Ink `#030508`, Carbon `#080d14`, Raised `#0d151f`, Snow
  `#f4f7fa`, Arc blue `#79c9f4`, line `rgba(219,234,247,.12)`.
- Type: existing Manrope only; large sentence-case headings, readable body,
  numeric price as the main card anchor.
- Layout: one concise trial panel, two real screenshots in a desktop/phone
  composition, three independent pricing cards, one horizontal custom builder.
- Geometry: 28-34 px outer radii for primary surfaces, pill actions, 14-18 px
  controls. Avoid a universal radius and avoid nested decorative cards.
- Distinctive element remains the Hero ribbon. Pricing and proof stay quiet and
  use blue only to explain hierarchy or selection.

## Affected components

- `webapp/src/views/LandingPage.svelte`
- `webapp/public/assets/landing/cabinet-desktop.webp`
- `webapp/public/assets/landing/cabinet-mobile.webp`
- generated `webapp_dist/`

## Non-goals

- No changes to `/app`, authentication, payment fulfillment, tariffs, trial
  eligibility, subscription URLs or server catalog endpoints.
- No invented location count, availability guarantee, review, performance
  metric or hidden infrastructure detail.
- No Instagram/TikTok URLs until configured.
- Do not modify the owner's dirty `webapp/src/views/Connect.svelte` or deleted
  `docs/design/arcvpn-landing-page-prompt.md`.

## Acceptance

- Rejected client-window markup and its catalogue fetch are absent.
- Trial copy and CTAs match the existing bot and email-account behavior.
- Supplied cabinet screenshots are readable, lazy-loaded, correctly cropped and
  do not expose identifiers.
- Tariffs and custom quote still load from public server APIs; error states do
  not show invented prices.
- Selected period, product CTA and custom tariff CTA retain their existing URL
  contracts.
- Pricing has independent rounded surfaces and no square joined ledger.
- Mobile navigation fits at 360 px and the brand is shifted slightly right.
- No horizontal overflow at 360x800, 390x844, 768x1024, 1280x800 and 1600x900.
- Keyboard focus, hover, active, loading/error and reduced-motion states remain
  visible.
- Impeccable detector, Vite build and Python tests pass.
- Production `/`, `/app`, screenshot assets, tariffs and custom quote are
  verified after a fast-forward deployment.

## Risks and rollback

- Screenshot text can become illegible when scaled. Preserve high-resolution
  WebP sources, use aspect-ratio containers, and stack the proof on narrow
  viewports.
- Trial wording can over-promise eligibility. Explicitly scope both offers to a
  new user/account and retain the existing application flows.
- Pricing restyle can hide live failure states. Verify both loaded and local
  error markup before release.
- Roll back the single runtime commit to restore the previous landing; `/app`
  and backend contracts are unchanged.

## Verification matrix

- Automated: `npx impeccable detect`, `npm run build`, `pytest -q`, diff check.
- Browser: trial CTAs/copy, real screenshot composition, tariff periods and
  quote, mobile nav, overflow and focus across five viewports.
- Deployment: scoped commit, push, production pull, public UI/assets/API checks;
  no service restart for static-only changes.

## Result and evidence

- Status: complete and released to production on 2026-09-07.
- Runtime commits: `5dfb6df` (`fix: refine landing proof and pricing`),
  `4571145` (`fix: smooth landing anchor navigation`) and `3b9eec1`
  (`feat: add smooth wheel scrolling to landing`), pushed to `main` and pulled
  fast-forward on `pl-control`.
- The fake subscription client and its catalog request are absent. The new
  trial panel shows a configured Telegram-bot CTA and the existing `/app`
  email route for the 10 RUB website trial.
- Owner captures were exported to 25,164-byte desktop and 20,166-byte mobile
  WebP assets. Production natural dimensions are 1600x924 and 568x912.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: exit 0,
  no findings.
- `npm run build`: passed. Landing chunk is 40.45 kB JS / 13.83 kB gzip and
  37.20 kB CSS / 5.98 kB gzip. Existing App remains a separate 153.41 kB gzip
  chunk. Existing unused-selector warnings remain confined to
  `HomeFlowPreview.svelte`.
- `.venv\\Scripts\\python.exe -m pytest -q`: 177 passed.
- Browser QA at 360x800, 390x844, 768x1024, 1280x900 and 1600x900: no
  horizontal overflow; three tariff cards and two trial offers render; custom
  quote is numeric; mobile has no burger; cabinet images load at natural size.
- Public `/`, `/app`, both cabinet WebP assets and public config return HTTP
  200; `bot_url` is configured. `arcvpn-subscription.service` and
  `nginx.service` remain active. No restart was performed for the static-only
  deployment.
- All landing `#` links now use explicit smooth scrolling while preserving an
  immediate path for `prefers-reduced-motion`.
- Discrete mouse-wheel input is eased with a bounded animation; high-resolution
  trackpad input remains native and reduced-motion disables the effect.
- Rollback: revert `3b9eec1`, `4571145` and `5dfb6df`, push and pull
  fast-forward on `pl-control`; no service restart is required for the current
  static serving path.
