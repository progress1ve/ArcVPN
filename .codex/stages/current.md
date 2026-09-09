# Stage: ArcVPN landing — supported apps and bypass section

## Goal

Refine the third section into a static supported-apps statement, narrow the
mobile Hero light field, and rebuild the fourth bypass section as a focused
reference-led explanation using only real ArcVPN facts.

## Visible contract

| Surface         | Required result                                                                                                   |
| --------------- | ----------------------------------------------------------------------------------------------------------------- |
| Hero            | Centered, compact value proposition followed immediately by one clear CTA and the real ArcVPN cabinet proof       |
| Visual language | Black field, restrained cold-blue light and fine orbital structure; the product remains the brightest proof       |
| Transition      | No visible rule or ambient blue wash between Hero and trial; the page field is true black                         |
| Trial           | Centered introduction and two quiet, separate trial cards using only real ArcVPN offers                           |
| Mobile Hero     | Use the real portrait cabinet capture without cropping a desktop screenshot into a phone-shaped viewport          |
| Applications    | Happ, INCY and supported platforms are presented as information, not interactive store choices                    |
| Product proof   | Real Happ and INCY phone screenshots return as a static pair; there is no selector, store link, or install CTA    |
| Hero frame      | The cabinet proof has one thin translucent glass rim and no nested black shell                                    |
| Light field     | A broad diffused horizon with asymmetric side volumes replaces the sharp white line                               |
| Fourth section  | Centered bypass explanation, one tariff CTA and one compact factual proof panel over a horizontal cold-blue light |

## Components

- `webapp/src/views/LandingPage.svelte`
- `.codex/stages/current.md`

## Non-goals

- No testimonial, fake customer, invented metric, tariff formula, or API/auth change.
- No smooth wheel or anchor scrolling.
- No testimonial, invented success statistic, or fabricated product screen.
- No change to pricing formulas, authentication, API contracts, or server topology.
- Do not touch the owner's existing changes in `webapp/src/views/Connect.svelte` or deleted design prompt.

## Acceptance

- Headline, body, CTA, and cabinet proof form one continuous first-screen story
  without the previous oversized empty gaps.
- White controls use a neutral grey hover, never a blue-tinted hover.
- Hero uses the real anonymized ArcVPN cabinet images; no testimonial, invented
  claim, fake application chrome, moving background, or decorative badge is added.
- Hero does not introduce page-level horizontal overflow at mobile, tablet,
  desktop, or wide widths; mobile uses the portrait capture at its native ratio.
- Applications list Happ, INCY, iPhone/iPad, Android, Windows and Linux without
  implying that the visitor must choose or install anything in this section.
- No outbound application-store link remains in the section.
- Both supported application screenshots are visible as non-interactive product evidence.
- The Hero cabinet has no heavy black or opaque grey nested frame.
- Phone and bypass light fields contain no sharp one-pixel horizon rule.
- The fourth section preserves the current traffic semantics and tariff anchor.
- Build and Impeccable detector pass; browser evidence covers Hero and applications.
- The Hero/trial join has no border and no section-transition glow. Trial copy,
  bot URL, website URL, analytics events, and eligibility wording are unchanged.

## Risks and rollback

- A large cabinet screenshot can hurt mobile composition; switch the source at
  the mobile breakpoint and reserve its portrait aspect ratio.
- Revert the Hero-only CSS diff in `LandingPage.svelte` to restore the prior
  treatment. Runtime contracts are unchanged.

## Result and evidence

- Hero-only CSS refinement implemented. Copy and behavior are unchanged; the
  headline is calmer, the vertical story is tighter, and more of the real
  cabinet proof is visible in the first viewport.
- Product backdrop was revised against the owner's newest close reference: a
  wide black field now fades into cold-blue illuminated side walls, while the
  cabinet capture sits inside one heavy dark rounded frame. The prior orbital
  field and rounded outer capsule are removed.
- The Hero border and inherited transition light are removed. Document, body,
  landing, Hero, and trial fields now resolve to true black outside the product
  side-light treatment.
- Trial section is rebuilt as a centered reference-led composition with two
  separate quiet cards. Existing Telegram and website trial facts, conditional
  bot CTA, URLs, and analytics handlers are unchanged.
- Desktop browser review at the default 1280-wide viewport passed. Mobile
  review at 390x844 passed: navigation, headline, copy, CTA, and intentional
  cabinet crop remain legible and contained.
- Geometry checked at 390, 768, 1280, and 1600 CSS-pixel widths. The Hero frame
  remains contained. Existing mobile page overflow comes from the later tariff
  period control (`12 мес.`), outside this Hero-only stage, and is deferred.
- `npm --prefix webapp run build`: passed. Existing unused-selector warnings in
  `LandingPage.svelte` and `HomeFlowPreview.svelte` remain.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: passed with
  no findings.
- Latest desktop review confirms a seamless black Hero/trial join and no blue
  wash behind the trial heading. Latest 390x844 review confirms the stacked
  trial cards remain legible and contained.
- `npx --yes impeccable install` was attempted twice for a project-local skill
  and design hook; both downloads timed out before installation and the
  installer confirmed that nothing was installed. The already available
  detector remains usable.
- Mobile Hero now switches to `cabinet-mobile.webp` below 560px and uses its
  portrait ratio, while desktop keeps the wide cabinet proof.
- The third section now presents four real subscription capabilities, then the
  existing application and device choices inside a single focused install scene.
- The section field is true black; its only illumination is the intentional
  horizontal cold-blue product light behind the phone, matching the reference.
- Production evidence will be appended after commit, push, pull and public QA.
- Third-section desktop and 390x844 browser review passed: no selectors or
  install link remain, all four platforms render as one static icon row, and
  the decorative compatibility proof contains no phone screenshot.
- Fourth-section desktop review passed: the factual proof panel crosses one
  horizontal cold-blue light band and the surrounding field remains black.
- Mobile Hero review at 390x844 confirms the portrait cabinet remains intact
  while the illuminated container is narrowed to leave black side margins.
- `npm --prefix webapp run build`: passed. Existing unused-selector warnings remain.
- `npx --yes impeccable detect webapp/src/views/LandingPage.svelte`: passed.
- `.venv\\Scripts\\python.exe -m pytest -q`: 177 passed.
- Acceptance: passed for static app/platform presentation, removal of the phone
  mockup and install CTA, mobile Hero width, fourth-section content and light field.
- Runtime commit `42e60dc` was pushed to `main` and pulled fast-forward on
  `pl-control`; `nginx.service` and `arcvpn-subscription.service` remain active.
- Public `/`, release JS and release CSS return HTTP 200 and public HTML points
  to `index-CHUuioc0.js`. Production mobile browser QA confirms the new section.
- No service restart was needed because this was a checked-in static build.
- Rollback is a normal revert of `42e60dc`; no data or API migration occurred.
- Next step: continue the section-by-section review with pricing.
- Owner feedback correction shipped in runtime commit `1e533cc`: Hero now has
  one thin translucent glass rim and no nested black shell.
- The real Happ and INCY phone screenshots are restored as a static, labelled
  pair. The section still has no selector, store URL, or install action.
- The phone and bypass illumination now uses layered elliptical volumes and a
  diffused horizon; the prior sharp one-pixel light rule is removed.
- Desktop and 390x844 browser QA passed. Both phone assets load at their
  natural 480 px width, and the changed mobile surfaces introduce no overflow.
- Production `pl-control` fast-forwarded to `1e533cc`; nginx and
  `arcvpn-subscription.service` remained active. New JS/CSS assets return 200.
