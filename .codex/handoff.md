# ArcVPN handoff — public Northern Flow landing

Updated: 2026-09-07. Released to production from `main`.

## Shipped

- `https://arccnet.space/` is the public Svelte landing; `/app` keeps the
  existing authentication and cabinet flow.
- Hero uses the owner-supplied Aura blue-ribbon motion, vendored as an
  optimized 8-second muted loop: 1.0 MB MP4, 1.82 MB WebM and a 39.2 kB WebP
  poster. Mobile, Save-Data and reduced-motion render only the poster.
- Hero type has non-overlapping line metrics, the decorative guide lines are
  removed, and mobile navigation is limited to logo, `ArcVPN` and the cabinet
  CTA without a burger.
- Product proof is a clearly labelled ArcVPN preview with the real public
  profile catalog. Location initials and names render cleanly; no protocol,
  host, port, UUID, topology or fabricated ping is exposed.
- Pricing and the custom builder use server-owned public endpoints. The live
  3-month / 3-device / 45-GB quote is 399 RUB; changing the period to 6 months
  returns 759 RUB in production.
- Cabinet proof uses laptop and phone compositions with explicit places for
  later anonymized screenshots.
- Instagram and TikTok stay hidden until exact HTTPS values are configured.
- Stable landing intents are `/app?screen=tariffs&product=<code>&months=<n>`,
  `/app?screen=custom-tariff` and `/app?screen=connect`.

## Evidence

- Runtime commits: `89b1595`, `d6c9613` and Hero/bypass refinement `c800338`;
  all pushed to `main` and pulled fast-forward on Poland `pl-control`.
- `.venv\\Scripts\\python.exe -m pytest -q`: 177 passed.
- `npm run build`: passed. Landing JS is 15.72 kB gzip and the existing App
  remains a separate 153.41 kB gzip lazy chunk.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: exit 0,
  no findings.
- Production service `arcvpn-subscription.service`: active after the backend
  release restart.
- Public `/`, `/app`, tariffs, catalog, custom quote, config, sitemap, Hero
  poster, MP4 and WebM return HTTP 200. Tariffs have ETag and the profile
  projection contains only `display_name`, `kind` and `sort_order`.
- Browser QA at 360x800, 390x844, 768x1024, 1280x800 and 1600x900: no
  horizontal overflow or Hero content collision. Desktop/tablet video plays;
  mobile loads only the poster. Mobile has no menu; profile selection and
  custom quote recalculation work.
- Browser console has no landing errors. Only expected Telegram WebApp warnings
  appear when the public page runs outside Telegram.

## Owner files intentionally untouched

- `webapp/src/views/Connect.svelte` remains modified in the working tree.
- `docs/design/arcvpn-landing-page-prompt.md` remains owner-deleted.

## Follow-up

- Replace the laptop/phone proof placeholders when anonymized cabinet captures
  are ready.
- Configure verified Instagram and TikTok HTTPS URLs when available.
- Optional: remove pre-existing unused-CSS warnings in `HomeFlowPreview.svelte`
  as a separate cleanup; they do not affect the landing build or runtime.

## Rollback

Revert `c800338`, `d6c9613` and `89b1595`, push, pull fast-forward on
`pl-control`, then
restart only `arcvpn-subscription.service`. `/app`, authentication, payment,
import, subscription URLs and user identities were not renamed by this stage.
