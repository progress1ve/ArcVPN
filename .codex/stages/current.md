# Stage: Public landing — Hero and bypass refinement

## Goal

Correct the shipped landing where the Hero typography collides, the global
guide lines read as an accidental grid, the mobile header is over-controlled,
and bypass value is under-explained. Bring the Hero closer to the owner-supplied
Aura reference without copying its product UI or React implementation.

## Exact visible contract

| Surface | Required result |
|---|---|
| Hero | Smooth blue ribbon video from the exact owner-supplied Aura prompt, locally optimized; readable copy with no collision |
| Hero copy | Remove `Подписка для Happ и INCY`; keep one H1, one useful paragraph and two actions |
| Guides | Remove the two fixed vertical guide lines from the whole landing |
| Mobile nav | Logo, `ArcVPN` wordmark and `Личный кабинет`; no burger or mobile menu |
| Applications | Keep the selected-app install CTA; remove `Инструкция подключения` |
| Bypass | Explain its purpose in Hero/product/features/dedicated section and tariff context without guarantees or infrastructure detail |
| Motion | Desktop/tablet video only; mobile, Save-Data and reduced-motion use the matching poster |

## Components

- `webapp/src/views/LandingPage.svelte`
- locally owned Hero WebM/MP4 and poster under `webapp/public/assets/landing/`
- generated `webapp_dist/` assets

## Non-goals

- No changes to `/app`, authentication, payment, subscription URLs, catalog
  delivery or server topology.
- No fabricated ping, protocol, host, node, review or performance claim.
- Do not modify the owner's `webapp/src/views/Connect.svelte` change or deleted
  `docs/design/arcvpn-landing-page-prompt.md`.
- Do not hotlink the 16.5 MB CloudFront source in production.

## Acceptance

- H1, paragraph and actions do not overlap at 360x800, 390x844, 768x1024,
  1280x800 and 1600x900.
- The blue ribbon remains clearly visible but never reduces text contrast.
- No global vertical guide/grid remains.
- Mobile header contains exactly brand mark, visible `ArcVPN` and cabinet CTA.
- No mobile menu exists and the desktop anchor navigation remains available.
- The applications scene has no `Инструкция подключения` action.
- Bypass copy appears before pricing, explains separate quota and explicitly
  states that ordinary unlimited profiles keep working after it is exhausted.
- Video is muted, looped, plays inline, has no controls; WebM and MP4 are each
  under 2.5 MB and poster dimensions prevent layout shift.
- Save-Data/reduced-motion/mobile do not download or play video.
- Impeccable detector, Vite build and relevant tests pass.
- Production browser has no horizontal overflow or new console errors across
  all four viewport classes.

## Risks and rollback

- Source video is third-party hosted but was explicitly supplied in the owner's
  prompt; vendor it locally and retain attribution only in Git history, not the
  runtime dependency graph.
- Autoplay can fail; the matching poster is always the initial visual.
- Roll back the single runtime commit to restore the previous static Hero.

## Verification matrix

- Source media: duration, dimensions, no audio, encoded size.
- Automated: `npx impeccable detect`, `npm run build`, `pytest -q`, diff check.
- Browser: desktop video, mobile/poster fallback, readable Hero, mobile nav,
  removed guide/menu/instruction, bypass copy, pricing and calculator.
- Deployment: scoped commit, push, production fast-forward, public asset and UI
  checks; restart only if a runtime service file requires it.

## Completed evidence

- Runtime commit `c800338` was pushed to `main` and pulled fast-forward on
  production `pl-control`.
- The Hero uses the exact owner-supplied Aura ribbon source, re-encoded locally
  to an 8-second, 1280x720, 24-fps loop: MP4 1,000,091 bytes and WebM
  1,816,648 bytes. Both contain video only; the matching WebP poster is 39,202
  bytes.
- `npm run build` passed. Landing JavaScript is 15.72 kB gzip and the existing
  App remains a separate 153.41 kB gzip chunk. The only warnings are the
  pre-existing unused selectors in `HomeFlowPreview.svelte`.
- `.venv\Scripts\python.exe -m pytest -q`: 177 passed.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: exit 0,
  no findings.
- Local browser matrix passed at 360x800, 390x844, 768x1024, 1280x800 and
  1600x900: no overflow or content collision; desktop/tablet use video and
  mobile uses only the poster.
- Production browser checks passed at 1280-class desktop and 390x844 mobile:
  no guide lines, no burger, no removed Hero/app text, no horizontal overflow;
  the custom quote resolves to a numeric server price and the bypass section
  contains the separate-quota explanation.
- Public `/`, `/app`, poster, MP4 and WebM return HTTP 200. The subscription
  service remained active; no restart was required for the static-only release.

## Status

Complete and deployed on 2026-09-07.
