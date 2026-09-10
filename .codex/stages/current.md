# Stage: ArcVPN legal revision and landing polish

## Current scope — 2026-09-10

- Rewrite the public legal page into a product-specific User Agreement and
  Privacy Policy using the supplied GG's VPN text only as a structural example.
- Keep operator identity and contacts dynamic; do not invent legal details.
- Match actual Telegram/email accounts, YooKassa payments, optional
  auto-renewal and self-service cancellation.
- Preserve mandatory consumer and data-subject rights; reject blanket
  no-refund, chargeback-ban and exclusive-forum clauses from the example.
- Center “Работает на ваших устройствах” and remove `.apps-signal` entirely.
- Do not change Hero, trial, billing, authentication or product behavior.

## Current acceptance

- Distinct agreement and privacy-policy parts with readable navigation.
- Dynamic legal values remain escaped; no secret or invented value enters Git.
- `apps-signal` is absent from source and rendered output; applications intro is
  centered at every breakpoint.
- Focused tests, Vite build, browser QA, diff review, deployment, service state
  and public content checks pass.

## 2026-09-10 result

- Public legal page now has separate User Agreement and Privacy Policy parts,
  optional auto-renewal/cancellation terms, lawful refund wording, actual data
  categories, processor classes, retention, security and user rights.
- Unset operator fields are no longer exposed as `[УКАЖИТЕ ...]`; production
  still requires the owner's verified legal name, INN, OGRN/OGRNIP, address and
  legal email for a complete operator disclosure.
- Applications intro is centered and `.apps-signal` is absent from source,
  generated assets and public markup.
- Four focused tests passed; Vite production build passed with pre-existing
  unused-selector warnings. The broader landing route test could not collect in
  the isolated worktree without the production-local config/database.
- Browser QA passed on the public legal page and desktop applications section.
  Public checks returned HTTP 200, no placeholders, current date and both legal
  parts. `arcvpn-subscription.service` and nginx are active.
- Runtime commits: `ea12398`, `470a325`; production is at `470a325`.

## Residual risk

The document is a product-aligned draft rather than individual legal advice.
Add verified operator requisites and obtain counsel review before treating it
as a final compliance document.

## Previous stage record

## Goal

Rebuild every landing section after the trial block in one coherent reference-led
composition: fewer generic cards, stronger product hierarchy, an asymmetric
falling light field, clear live tariffs, and a deliberate final/footer sequence.

## Visible contract

| Surface      | Required result                                                                                                               |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Applications | Restore the four factual feature cards; keep phone mockups, `supported-apps`, chooser, store link, and install CTA absent     |
| App proof    | Two standalone Happ and INCY icon assets over an asymmetric cold-blue light stream                                            |
| Light        | A soft volume descends from upper-left through the centre and exits lower-right; no straight horizontal bar or one-pixel rule |
| Bypass       | Existing factual traffic semantics and tariff CTA, presented as one compact proof object over the same flowing light language |
| Pricing      | Live server-backed tariffs remain authoritative; three clearer plans and the custom builder form one composed pricing system  |
| Cabinet      | Real ArcVPN desktop and mobile captures remain the visual evidence, with reduced nested framing                               |
| Steps        | Four onboarding steps read as a continuous sequence rather than a plain ruled list                                            |
| FAQ          | Questions remain keyboard-operable and gain a calmer two-column editorial layout                                              |
| Final/footer | Final CTA, useful links, and footer close the page as one dark composition with restrained corner light                       |

## Components

- `webapp/src/views/LandingPage.svelte`
- code-native Happ and INCY placeholder tiles in `LandingPage.svelte`
- generated `webapp_dist/` release assets
- `.codex/stages/current.md`
- `.codex/handoff.md`

## Non-goals

- No change to tariff formulas, API/authentication, trial eligibility, analytics,
  URLs, subscription semantics, or server topology.
- No invented testimonials, metrics, application features, or third-party store links.
- No React/shadcn migration and no custom wheel/anchor scrolling.
- Do not include owner changes in `Connect.svelte`, `HomeFlowPreview.svelte`, the
  deleted design prompt, or unrelated generated/untracked files.

## Acceptance

- `supported-apps` and phone figures are absent; the four factual application
  feature cards are restored with their original copy.
- Happ and INCY are represented by two static, labelled icon objects; supported
  platforms remain visible as a plain icon/text row.
- The application glow has visibly different vertical positions at its left and
  right ends and contains no sharp horizontal rule.
- Tariff values still come from the existing catalog/quote flow; selection and
  custom-tariff actions retain their current behavior.
- Real cabinet images load at natural dimensions and no fake product UI is added.
- FAQ disclosure buttons retain accessible expanded state and keyboard behavior.
- Mobile 390x844, tablet, desktop, and wide layouts introduce no new horizontal
  overflow, clipped controls, or unreadable overlap.
- Vite build, Impeccable detector, automated tests, and public browser QA pass.

## Risks and rollback

- Large blurred layers can create overflow or excessive GPU work; constrain them
  to section-owned pseudo-elements and verify all viewport classes.
- Placeholder icons must stay visibly generic client identifiers and make no
  official artwork or download/store claim.
- Rollback is a normal revert of the single runtime commit; no data migration or
  service restart is required for static assets.

## Verification matrix

| Check                   | Status  | Evidence                                     |
| ----------------------- | ------- | -------------------------------------------- |
| Source/content contract | Passed  | Removed legacy app grid, phones and label    |
| Mobile 390x844          | Passed  | Icon bounds 41.6–333.6 px; content contained |
| Tablet 768x1024         | Passed  | Lower sections and controls contained        |
| Desktop 1280            | Passed  | Applications, pricing and cabinet reviewed   |
| Wide 1600               | Passed  | Pricing remains centred at 1120 px           |
| Build/detector/tests    | Passed  | Clean build, detector exit 0, 177 tests      |
| Production/public       | Pending | commit, pull, HTTP and browser evidence      |

## Result and evidence

- Removed the generic four-card device/features grid, all phone mockups, and
  `supported-apps`. Happ and INCY now use replaceable code-native placeholders.
- Application light uses three vertically offset elliptical volumes: upper-left,
  centre, and lower-right. There is no straight light rule.
- Rebuilt bypass proof, live pricing cards and custom builder, cabinet proof,
  four-step sequence, FAQ, final CTA, links and footer in one dark system.
- Existing live pricing/catalog behavior, actions, URLs, copy facts, cabinet
  images, analytics and FAQ disclosure behavior are unchanged.
- Browser QA covered 390, 768, 1280 and 1600 px. FAQ expands with
  `aria-expanded=true`; cabinet images load at natural widths 1600 and 568.
- Production verification pending commit and deployment.

## 2026-09-10 app-proof light correction

- Feedback: the blue glow behind the Happ/INCY phones competed with the product
  images and was removed entirely.
- Scope: only the app-proof shadow and internal decorative light layers. Phone
  composition, copy, Hero, navigation, trial and bypass remain unchanged.
- Acceptance: passed locally and publicly at the available tablet/desktop
  browser size; both phones remain legible and overlapping. Vite build passed,
  public root and new CSS/JS returned HTTP 200, and both production services are
  active.
- Runtime commit: `0c910a0`. Static deployment required no restart. Rollback is
  a normal revert of that commit.
- Residual: exact 390x844 and 1600x900 captures were not available in the app
  browser during this correction; responsive rules were not changed.
- Next step: improve product proof and page pacing only after owner approval;
  do not add more decorative light as a substitute for content.

## 2026-09-10 bypass light and tablet pricing correction

- Approved implementation: replace the full-width grey-blue bypass fog with
  two contained side sources and a dark centre; compact the three live tariff
  cards into one row at 720-900px without changing pricing or actions.
- Proposal-only scope: page pacing, capability-card composition and final CTA
  background remain unchanged until the owner selects a direction.
- Preserve Hero, navigation, trial, app-proof composition, copy, pricing data,
  handlers and public links.
- Acceptance: no grey full-width bypass wash; card stays legible; at tablet
  width all three tariff cards fit in one compact row with no horizontal
  overflow; mobile remains one column; build and browser checks pass.
- Rollback: revert the single static landing commit; no service restart needed.

### Result

- Passed: public 770x930 Hero stage ends at 781px and the complete product
  capture is visible; local 1366x768 and 1600x900 captures also contain it.
- Passed: capability hierarchy is asymmetric and factual; no invented product
  UI or claims were introduced.
- Passed: public 770px tariffs are three equal 360px cards, Standard has no
  tablet hover translation, and scroll width is below viewport width.
- Passed: final CTA renders the code-native `Arc horizon`; the raster background
  was removed from markup.
- Passed: Vite build, Impeccable detector, staged diff, commit `bb2551b`, push,
  production fast-forward pull, public HTTP/browser and service checks.
- Rollback: revert `bb2551b`; static change, no service restart.
- Next step: owner visual review on personal phones; tune only specific feedback
  without re-expanding page spacing or restoring generic card symmetry.

### Result

- Passed: bypass proof uses only two soft side sources; there is no central grey
  wash or sharp beam.
- Passed: at the public 770px viewport tariff columns are `234px 234px 234px`,
  heights are `356/360/356px`, and page scroll width is below viewport width.
- Passed: Vite build, staged diff, commit `6ef7795`, push, production fast-forward
  pull, public root/CSS/JS HTTP 200, service state and public browser rendering.
- Deferred: exact 390px screenshot automation loaded only the shell spinner;
  the current change does not alter mobile tariff layout, and Hero remains an
  explicit exclusion.
- Next step: owner selects one of the proposed pacing/card/final-background
  directions before those broader visual changes are implemented.

## 2026-09-10 approved hierarchy implementation

- Owner approved all proposed directions and explicitly allowed Hero changes.
- Implement: viewport-height-aware Hero that keeps the complete product capture
  visible; stable Standard hover at 720-900px; asymmetric capability hierarchy;
  shorter alternating section rhythm; code-native `Arc horizon` final backdrop.
- Preserve all factual copy, live tariffs, actions, phone captures, navigation,
  trial behavior, API contracts and public links.
- Acceptance: full Hero product capture fits 390x844, 768x1024, common laptop
  heights, 1280x900 and 1600x900 without horizontal overflow; Standard does not
  change height or vertical position on tablet hover; capabilities read as one
  primary Auto-select story plus three compact supporting facts; final CTA has
  no raster wallpaper or noisy texture; build and public browser checks pass.
- Rollback: revert the single static landing commit; no service restart needed.
