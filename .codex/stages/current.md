# Current stage — referral deep-link recovery

## Result

- Acceptance passed: `ref_…` and `ad_…` survive the consent gate; referral
  binding precedes trial provisioning; existing users are not rebound.
- Acceptance passed: Remnawave zero-inbound compatibility rows synchronize
  bonus expiry through the authority panel.
- Verification: focused tests 8 passed; Python compile and diff checks passed;
  production commits `460c86e` and `ce952ab` pulled fast-forward; bot active.
- Production repair: one verifiable invite attempt, zero paid invite evidence,
  +5 days credited. SQLite backup and admin audit record created. DB, main
  Remnawave and LTE expiry all verified at 2026-09-23 13:51:26 UTC.
- Residual limitation: discarded historical Telegram payloads cannot be mapped
  back to a friend account. No speculative referral edge was created.
- Rollback: revert the two commits and restart the bot. Restore the exact
  pre-repair backup only if the manual +5-day compensation must be reversed.

# Previous stage — application and bypass visual alignment

## Goal

Bring the Happ/INCY proof onto the cabinet navy canvas and replace the abstract
bypass ledger with a reference-led split composition using the owner's real
INCY screenshot inside a code-native phone frame.

## Non-goals

- No Hero, pricing data, trial terms, footer or application-flow changes.
- No green accent from the structural reference and no fabricated app UI.

## Components

- `webapp/src/views/LandingPage.svelte`
- New optimized public asset derived from the owner-supplied INCY screenshot.

## Acceptance

- Application proof uses the same deep navy/translucent surface family as the
  landing and no black-on-different-black container or black active control.
- Bypass section is a desktop split: left-aligned copy, real INCY screen in a
  large phone on the right; it stacks cleanly on tablet/mobile.
- Phone content remains legible, correctly cropped and not stretched.
- No horizontal overflow at mobile, tablet or desktop sizes.
- Vite build and rendered browser review pass before deployment.

## Risks and rollback

- Tall screenshot can dominate mobile height; constrain with responsive phone
  height and top-aligned cover crop.
- Rollback by reverting this stage commit and rebuilding static assets.

## Evidence

- Before: application proof and active platform control use neutral black while
  surrounding sections use cabinet navy; bypass is an abstract ledger without
  the requested product screen.
- Generated with the built-in image tool: corrected premium 3D phone with an
  iPhone-style status bar, straight device geometry, real INCY/ArcVPN hierarchy
  and transparent alpha; saved as
  `webapp/public/assets/landing/incy-bypass-phone-3d-v2.png`.
- Application proof now uses the cabinet navy surface; the near-black website
  trial action uses the shared raised navy control color.
- Local Vite build passed. Browser review confirmed the corrected `9:41` iPhone
  status area, loaded 1024x1536 asset and zero horizontal overflow.
- Owner follow-up removed the rectangular bypass background entirely; only a
  borderless local elliptical light remains behind the phone. Browser computed
  background is `none` and overflow remains zero.
- Bypass support copy is reduced to 13 px with a 10.5 px secondary note
  (12/10 px on mobile). Standard hover is pinned to identical height, border,
  transform and glow geometry so it cannot jump or expose a seam.
