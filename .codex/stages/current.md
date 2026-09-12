# Current stage — landing 10/10 refinement

## Goal

Turn the approved cabinet-aligned landing into a concise, readable conversion
story without changing the 5/5 Hero composition or the live pricing contract.

## Non-goals

- No invented testimonials, infrastructure counts, speed, uptime or privacy claims.
- No WebApp, payment, bot, subscription URL or backend changes.
- No React/shadcn migration and no replacement of the approved Hero.

## Components

- `webapp/src/views/LandingPage.svelte`: public copy, section hierarchy,
  spacing, typography, product proof, CTA hierarchy and responsive layout.
- Production static bundle only; no service restart expected.

## Content and interaction contract

- Primary acquisition: free seven-day Telegram trial when configured.
- Secondary acquisition: seven-day website trial for 10 RUB.
- Hero keeps its current headline, body, centered viewport composition and
  transparent bordered CTA.
- Verified proof only: unlimited ordinary traffic; separate bypass allowance;
  Happ and INCY; iPhone/iPad, Android, Windows and Linux; Telegram support.
- Live tariff API, period selectors, custom quote and all destination URLs stay
  unchanged.

## Acceptance

- Trial heading matches its offers and the two routes have clear primary and
  secondary hierarchy.
- Repeated feature claims are consolidated; app copy has no contradictory
  instruction and the abstract Auto-select proof becomes understandable.
- Body copy is at least 14 px on mobile and important muted text meets readable
  contrast against cabinet surfaces.
- Excess vertical space is reduced at mobile, tablet, desktop and wide sizes;
  no section exposes a near-empty viewport between content groups.
- Pricing remains stable at 720–900 px, Standard never changes height on hover,
  and live/custom prices remain visible.
- Navigation, tariff selection, custom controls, FAQ, external links, keyboard
  focus and reduced-motion behavior remain functional with zero horizontal
  overflow.
- Vite build, Impeccable detector, local browser QA, diff inspection,
  production deployment and public browser QA pass.

## Risks and rollback

- Risk: denser spacing can crowd mobile cards or sticky navigation.
- Risk: acquisition-copy changes can accidentally imply identical trials.
- Mitigation: preserve the exact verified conditions and inspect all four
  viewport classes plus interactive states.
- Rollback: revert the single runtime commit and rebuild static assets.

## Verification matrix

| Surface | Viewport | Checks |
| --- | --- | --- |
| Mobile | 390x844 | hierarchy, type, stacked cards, pricing, controls, overflow |
| Tablet | 768x1024 | density, three-plan grid, final links, hover invariants |
| Desktop | 1280x900 | rhythm, proof hierarchy, active nav, interactions |
| Wide | 1600x900 | max-widths, negative space, balanced section composition |

## Evidence

- Before: production body measured 10,273 px at 390x844 and 8,919 px at
  768x1024. Mobile body copy reached 10.5–12 px. Large empty intervals appeared
  before bypass, pricing, steps, FAQ and contact links.
- Before: “Много локаций” introduced trial-channel cards rather than locations;
  the app heading asked users to choose while its body said no choice was needed.
- Local after: the trial heading now describes trial activation; Telegram is the
  primary route and the 10 RUB website trial is explicitly secondary.
- Local after: the owner rejected the interim proof strip, so Hero flows
  directly into trial content with no extra text panel. Capability cards are
  reduced from four repetitive claims to Auto-select, country choice and
  bypass. App copy now gives one direct installation/import instruction.
- Local after: mobile body copy computes to at least 14 px in the audited Hero,
  trial, capability, bypass, tariff, steps and FAQ content. At 1280 px the main
  supporting type is 14–15 px.
- Responsive QA passed at 390x844, 768x1024, 1280x900 and 1600x900 with zero
  horizontal overflow. Body height fell from 10,273 to 8,909 px on mobile and
  from 8,919 to 8,034 px on tablet; the former empty viewport intervals are
  replaced by adjacent content. At 768 px all tariff cards remain equal at
  455 px and do not use a height-changing transform.
- Mobile steps render as a readable 2x2 grid. Desktop feature and trial captures
  show balanced cabinet surfaces without the rejected pure-black section bands.
- Period selection, custom bypass selection and FAQ expansion pass locally.
  Vite production build and Impeccable detector exit 0; only pre-existing
  unused-selector warnings remain.
- Owner follow-up: pricing now uses the same translucent deep-navy cabinet
  surfaces, cold hairlines, cyan action family and restrained blue Standard
  light as the rest of the product. The former neutral grey/black treatment is
  gone and no hard glow seam is visible in the rendered desktop capture.
