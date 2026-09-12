# Stage: ArcVPN login and Telegram consent redesign

## 2026-09-10 result

- Visual follow-up: login background matches the personal cabinet's deep navy
  field with soft blue aurora glows; the home link is removed, the logo keeps
  its dark tile and sits beside the ArcVPN wordmark, and the heading reads
  “Добро пожаловать в ArcVPN”. Runtime and built assets are deployed at
  `a682b6c`; the public desktop screen was visually verified.

- `/app/` login: warm welcome heading, email-code flow first, Telegram second,
  reference-led dark panel, preserved auth behavior.
- Bot onboarding: current legal-version acceptance is required; channel
  membership is never queried or required and is presented only as advice.
- Compatibility: legacy callback accepted; campaign payload and trial flow kept.
- Browser acceptance: 390x844, 768x1024, 1280x900, 1600x900 contained all
  controls with no horizontal overflow; email-to-code transition verified.
- Verification: 178 tests passed in the primary checkout and clean Vite build
  passed. Runtime commit `89b41d2` was pushed and fast-forwarded on production;
  the bot restarted active, startup logs are healthy, and the public login plus
  hashed JS/CSS assets return HTTP 200. Desktop and 390 px public UI were checked.

## Previous stage: legal-version synchronization and quiet daily backups

## Goal

Make the 10 September 2026 User Agreement and Privacy Policy canonical in every
ArcVPN surface, and stop the bot from sending the daily backup archive to
administrators while preserving local backup creation and cleanup.

## Exact contract

| Surface | Required result |
| --- | --- |
| Public legal page | Remains the canonical full Agreement + Privacy Policy |
| WebApp settings | Shows the current date and opens the canonical full document; no stale embedded summary or placeholders |
| Purchase disclosures | Continue linking to the canonical legal URL |
| Telegram gate | Names both documents and records version `2026-09-10` |
| Production setting | `legal_consent_version` is explicitly `2026-09-10` |
| Daily scheduler | Still creates a local DB backup and removes expired local backups; sends no backup archive/document to admins |
| Other notifications | Daily statistics and backup delivery are disabled; expiry notices and failure logging remain unchanged |

## Components

- `webapp/src/views/HomeFlowPreview.svelte` and generated `webapp_dist/`
- `bot/middlewares/subscription_check.py`
- `bot/handlers/user/start.py`
- `bot/services/scheduler.py`
- focused tests and production setting
- closeout context files

## Non-goals

- No change to the legal text, tariffs, payment processing or existing consent history.
- No deletion of local/server backups and no disabling backup creation.
- No removal of user expiry alerts, error logging or manually requested admin log exports.
- No Hero or landing-content changes.

## Risks and rollback

- A stale production setting could keep recording the prior consent version; verify it directly after deployment.
- Scheduler refactoring must not accidentally stop local backup retention.
- Roll back with a normal revert and restart only the bot/subscription services affected by the reverted runtime files.

## Verification

| Check | Status | Evidence |
| --- | --- | --- |
| Source inventory | Passed | Stale WebApp dates/summary and bot fallback located |
| Scheduler boundary | Passed | Daily Telegram archive call is separate from local backup work |
| Focused tests | Passed | 7 focused tests; scheduler import verified |
| Vite build | Passed | Production bundle built |
| Public browser | Passed | `/app` and current assets verified |
| Production setting/services | Passed | `2026-09-10`; all affected services active |

## Result

- WebApp settings now show “Соглашение и конфиденциальность”, revision date 10
  September 2026, a concise scope summary and a link to the canonical full
  document. The stale embedded copy, old date and operator placeholders are gone.
- Telegram channel gate names both documents. New recorded consent uses version
  `2026-09-10`; production setting was explicitly written and read back.
- Daily scheduler no longer builds or sends a Telegram backup archive. It still
  runs `save_local_backup()` and `cleanup_old_backups()` at 09:10 UTC. Daily
  statistics are also no longer sent; expiry alerts, error logs and manual
  admin log export remain.

## Verification result

| Check | Status | Evidence |
| --- | --- | --- |
| Source inventory | Passed | No stale 29 July date or 2026-08-26 fallback in scoped surfaces |
| Focused tests | Passed | 7 tests; scheduler import checked separately |
| Vite build | Passed | Production bundle built; only pre-existing unused-selector warnings |
| Public browser | Passed | `/app` loaded the production login surface; current JS asset returns 200 and contains current date/canonical URL only |
| Backup boundary | Passed | Production scheduler has local maintenance and no archive sender |
| Production setting/services | Passed | Version `2026-09-10`; bot, subscription and nginx active/running |

Runtime commits: `9c3c452`, `e989cf3`. Rollback remains a normal revert followed
by bot restart; static WebApp files do not require subscription-service restart.

## 2026-09-12 login surface and pricing reference

- Removed the `login-screen` `::before` and `::after` layers and the visual tile
  behind `login-mark`; the existing cabinet aurora is now unobstructed.
- Pricing follows the supplied structure: centered intro and segmented term
  control, three equal comparison cards, Standard highlighted inside its lower
  surface, and one wide custom-tariff row below.
- At tablet width the three rendered cards are exactly 430 px high with
  `transform: none`; no hover position jump remains.
- Build and public browser verification passed for production commit `cfad811`.
  Static deployment required no service restart.

## 2026-09-12 pricing polish follow-up

- Replace tariff checkmarks with existing inline SVG product icons.
- Remove the translucent `rgba(4,9,16,.68)` login-screen background so the
  cabinet aurora is not covered.
- Remove the 500 px tariff minimum height and the Standard card's hard blue
  gradient boundary; retain a contained soft lower accent.
- Make the custom tariff visually part of the same pricing-card family while
  preserving server quote controls and navigation.
- Acceptance: no sharp cyan rule, no forced 500 px cards, transparent login
  surface, responsive pricing without overflow, successful build and public QA.

### Owner correction

- INCY phone moves down by 4 px.
- SVG tariff icons lose their tiles and inherit the adjacent neutral text color.
- At page top the navigation has no visible shell; the bordered rounded shell
  returns only after scrolling.
- Standard uses a neutral card with a diffuse bottom glow layer, including hover,
  so no blue perimeter or horizontal seam can appear.
- Custom pricing reads as one wide enterprise-style tariff: clear left offer,
  three compact control rows and a high-contrast price/action column.

### Result and evidence

- Passed: desktop browser shows a transparent square navigation shell at the
  page top and restores the dark bordered pill after scrolling.
- Passed: Standard has a neutral `rgba(255,255,255,.09)` perimeter; its light is
  a separate blurred bottom pseudo-layer with no hard horizontal edge.
- Passed: INCY computed `top` is 4 px; tariff icons inherit neutral text color
  and have no tile background or border.
- Passed: the wide custom tariff renders as three readable columns; mobile has
  no horizontal overflow (`scrollWidth` equals `clientWidth`).
- Passed: Vite build, diff check, production fast-forward and public asset/browser
  verification. Runtime commit `4eedf60`; static release, no restart required.
- Rollback: revert `4eedf60`. No known residual functional risk.

## 2026-09-12 Impeccable pricing color pass

- Remove the internal `// СВОЙ ТАРИФ` kicker from the customer-facing custom plan.
- Consolidate pricing interaction, CTA and Standard-card light into one restrained
  ArcVPN blue accent family instead of unrelated cyan values.
- Replace the detached blurred Standard pseudo-layer with a soft integrated lower
  highlight that cannot create a hard cyan seam.
- Increase the visual gap between the custom monthly price and its creation CTA.
- Acceptance: Vite build and Impeccable detector pass; pricing has no horizontal
  overflow at 390, 768 and 900 px; Standard has no generated glow layer; active
  controls and CTA share the same accent token; public browser QA passes.

### Result and evidence

- Passed: `// СВОЙ ТАРИФ` is absent from source and rendered DOM.
- Passed: Standard `::after` computes to `none`; the highlight is an integrated
  two-step radial layer with a neutral `rgba(255,255,255,.09)` perimeter.
- Passed: selected custom control and CTA both compute to `rgb(120, 207, 255)`;
  their price-to-CTA gap is 28 px.
- Passed: Vite production build and `impeccable detect` exit 0; browser has no
  horizontal overflow and public loads `LandingPage-Bxwwu1jX.css`.
- Passed: production fast-forwarded to `53ebcc4`; nginx, bot and subscription
  services remain active. Static-only release required no restart.
- Rollback: revert `53ebcc4`. No known residual functional risk.

### Owner follow-up: stronger Standard light

- Increase the integrated lower radial mass to the visual strength of the
  supplied pricing reference while retaining a long, continuous falloff.
- Keep the implementation inside the card background: no pseudo-element, hard
  stop, horizontal seam or blue perimeter.

- Passed locally and publicly: the stronger radial field renders from the lower
  half of Standard, `::after` remains `none`, horizontal overflow is zero and
  production serves `LandingPage-BZ0SXwmu.css` at commit `a04b38f`.

## 2026-09-12 centered luminous Hero

### Contract

- Keep the existing ArcVPN headline, explanatory copy and primary cabinet CTA,
  centered as the only Hero content.
- Remove the desktop/mobile cabinet screenshot and its decorative frame from
  Hero. The later cabinet proof remains untouched.
- Build the atmosphere from deep navy into a broad soft electric-blue lower
  light inspired by the supplied reference, using the existing ArcVPN cyan and
  navy accent family rather than the reference's cobalt palette.
- Replace Standard's visible gradient boundary with a neutral card plus a
  bottom light layer whose transparent falloff starts inside the card.
- Preserve navigation, anchors, live tariff data, interactions and all sections
  after Hero.

### Acceptance

- Mobile, tablet, desktop and wide Hero: centered copy remains readable, CTA is
  reachable, no screenshot/frame remains and no horizontal overflow appears.
- Standard has strong lower blue emphasis without a horizontal seam or blue
  perimeter; hover does not change its height at 720-900 px.
- Keyboard focus and reduced-motion behavior remain intact.
- Vite build, Impeccable detector, local browser visual QA, staged diff, deploy
  and public browser verification pass.

### Local result

- Hero contains zero image/picture/frame nodes and keeps only centered copy and
  the cabinet CTA over the ArcVPN cyan/navy light field.
- Browser visual checks passed at 500x844, 768x1024 and 1280x720; the 390px CSS
  state additionally removes the inherited no-wrap title rule. No horizontal
  overflow was found.
- Standard uses a blurred oversized radial source on a neutral card; its fade is
  elliptical rather than a horizontal gradient boundary, and its perimeter
  remains neutral.
- Vite build and Impeccable detector pass. Existing unrelated Svelte unused-CSS
  warnings remain unchanged.

### Production result

- Passed: production fast-forwarded to `6fbb72a`; nginx, bot and subscription
  services remain active and required no restart for the static release.
- Passed: public browser loads `LandingPage-RT20uY6Q.css`, renders zero Hero
  image/frame nodes, the ArcVPN cyan/navy background and the neutral Standard
  perimeter with an elliptical blurred inner light. Horizontal overflow is 0.
- Rollback: revert `6fbb72a`. No known residual functional risk.

### Owner viewport correction

- Hero must cover at least the complete visible viewport at every breakpoint;
  remove the 940 px height cap that exposed the next black section on tall
  displays.
- Move the centered copy group lower without changing its content or alignment.
- Acceptance: computed Hero height is never less than the viewport height on
  mobile, tablet, desktop and tall/wide checks; no black strip appears inside
  the first screen and horizontal overflow remains zero.

- Passed locally: 1600x1200 capture is filled by Hero edge-to-edge with no black
  strip; the copy group is shifted down by 5svh (4svh tablet, 2.5svh mobile).
- Passed: 500x844, 768x1024 and 1600x1200 visual checks retain readable centered
  copy; Vite build and Impeccable detector exit 0.

- Passed publicly at `31aee4d`: computed Hero and viewport heights are both 720
  px in the live browser, Hero bottom equals the viewport bottom, copy shift is
  36 px and horizontal overflow is zero. Production services remain active;
  static release required no restart. Rollback is a normal revert of `31aee4d`.

## 2026-09-12 cabinet-system Hero alignment

### Contract

- Replace the landing's broad bright floor with the customer cabinet's deep
  `#03070e` base, restrained blue edge auroras and the cabinet CTA gradient.
- Hero message hierarchy: free internet, price from 80 RUB per month, separate
  bypass profiles for jammed networks, stable quality.
- Keep one centered text/CTA group. Centre the grid track itself with
  `place-content`, then use one small viewport-relative optical shift so the
  group is consistently just below centre across breakpoints.
- Preserve navigation, all downstream sections, pricing behavior and routes.

### Acceptance

- At mobile, tablet, desktop and wide sizes the copy group centre remains close
  to the viewport centre and below it; headline fits without clipping.
- Hero uses the same base, aurora family and primary-button colors as the
  customer cabinet; no flat bright cyan floor remains.
- Full-viewport coverage, zero horizontal overflow, keyboard focus, reduced
  motion, build, Impeccable detector and browser QA remain passing.

### Local result

- At 1280x720 the copy centre is 42 px below the viewport centre; Hero height is
  exactly 720 px and horizontal overflow is zero.
- 500x844 and 768x1024 captures show centred, unclipped headline/body/CTA with
  consistent cabinet-style navy negative space and restrained aurora edges.
- CTA computes to the customer cabinet gradient `#b6e7ff -> #6bc0ef`; Hero base
  is `#03070e`. Vite build and Impeccable detector pass.

### Production result

- Passed at runtime `8792cda`: public headline and cabinet-gradient CTA match
  the local result; Hero height matches the 930 px viewport within subpixel
  rounding, copy centre is 48 px below viewport centre and overflow is zero.
- Nginx, bot and subscription services remain active. Static release required
  no restart. Rollback is a normal revert of `8792cda`.

## 2026-09-12 landing-wide cabinet system pass

### Audit and contract

- Preserve the approved Hero composition and copy. Change its CTA to a
  transparent cabinet-style bordered action and make the existing edge auroras
  modestly more visible without returning to a bright cyan floor.
- Establish shared landing tokens from the cabinet: `#03070e` canvas,
  translucent `#070d17` surfaces, `#101a27` raised surfaces, cold low-contrast
  borders, muted blue-grey copy and one cyan action family.
- Trial: keep the two factual offers but render them as cabinet surfaces.
- Capabilities/apps: retain the asymmetric hierarchy and real phone evidence;
  replace neutral-black cards/frame with cabinet surfaces and local aurora.
- Bypass: remove the oversized empty vertical presentation. Use a readable
  two-column proof with copy beside the four-row cabinet ledger.
- Pricing: preserve approved card structure and live data; only harmonize its
  surrounding canvas and neutral surfaces.
- Steps, FAQ, final CTA and links: convert isolated black decorations into the
  same surface/group language used by cabinet metrics and settings.

### Acceptance

- All sections read as one product with Hero/cabinet tokens; no abrupt pure-black
  banding or unrelated accent colors remain.
- Mobile, tablet, desktop and wide layouts retain hierarchy and zero horizontal
  overflow. Bypass becomes one column below 900 px.
- Links, tariff selectors, FAQ expansion, focus, hover and reduced motion remain
  functional; live pricing and all copy contracts are unchanged.
- Vite build, Impeccable detector, local visual QA, staged diff, deployment and
  public browser verification pass.

### Local result

- Hero CTA is transparent with cabinet border `rgb(60,111,143)`; edge auroras
  are modestly stronger while the centre remains dark.
- Trial and capability sections no longer render isolated pure-black rectangles;
  their backgrounds are transparent over the shared `#03070e` canvas.
- Bypass is a 574/470 px two-column proof at 1280 px with the ledger visible
  beside copy, replacing the former 820-940 px empty stage.
- FAQ renders as one translucent cabinet settings group; its first row expands
  correctly. Changing the pricing period to 6 months leaves exactly one pressed
  selector. Horizontal overflow is zero.
- 500x844, 768x1024 and 1280x720 captures/checks passed. Vite build and
  Impeccable detector exit 0; unrelated pre-existing Svelte warnings remain.
