# Stage: ArcVPN landing — mobile Hero and applications section

## Goal

Finish the approved product-led landing direction by adapting the Hero to the
real mobile cabinet capture, rebuilding the third applications section from
real ArcVPN capabilities, and shipping the accepted landing to production.

## Visible contract

| Surface | Required result |
|---|---|
| Hero | Centered, compact value proposition followed immediately by one clear CTA and the real ArcVPN cabinet proof |
| Visual language | Black field, restrained cold-blue light and fine orbital structure; the product remains the brightest proof |
| Transition | No visible rule or ambient blue wash between Hero and trial; the page field is true black |
| Trial | Centered introduction and two quiet, separate trial cards using only real ArcVPN offers |
| Mobile Hero | Use the real portrait cabinet capture without cropping a desktop screenshot into a phone-shaped viewport |
| Applications | Four factual capability cards followed by a focused, interactive Happ/INCY and platform selector |
| Production | Commit only the approved landing scope, deploy by fast-forward, and verify the public page |

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
- Applications retain working Happ/INCY, platform, install-link and analytics behavior.
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
