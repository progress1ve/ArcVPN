# ArcVPN handoff — public Northern Flow landing

## 2026-09-10 bypass light and tablet pricing

- Production runtime `6ef7795` replaces the grey full-width bypass wash with
  two contained blue side sources and a dark centre.
- At 720-900px, the three live tariff cards form one compact row; public browser
  evidence at 770px showed 356/360/356px card heights and no horizontal overflow.
- Hero, trial, app proof, pricing data and actions are unchanged. Vite build,
  public root/CSS/JS checks and public browser verification passed; nginx and
  the subscription service remain active. Static deployment needed no restart.
- Pending owner choice: page-pacing composition, asymmetric capability story,
  and replacement direction for the final CTA background.

## 2026-09-10 neutral application proof

- Production runtime is `0c910a0` after removing the decorative blue light and
  external glow from the Happ/INCY proof frame.
- The two phone captures, their overlap, copy, platform list and surrounding
  applications content are unchanged. Hero and trial remain untouched.
- Vite build passed. Public root and the new landing CSS/JS return HTTP 200;
  `nginx` and `arcvpn-subscription.service` are active. The public browser shows
  a neutral dark app frame with both phone captures loaded.
- Owner changes in the main checkout remain excluded; release work used the
  isolated clean worktree.

Updated: 2026-09-09. Current production runtime commit: `a0a0fff`.

## Current landing state

- Every section after the trial block now uses the completed lower-page system:
  asymmetric upper-left to lower-right light, compact live pricing, reduced
  product framing, sequenced onboarding, editorial FAQ, and composed CTA/footer.
- The former four-card applications grid, Happ/INCY phone mockups, and
  `supported-apps` label are removed. Two code-native Happ/INCY placeholders are
  intentionally temporary and can be replaced without changing layout.
- Runtime commit `a0a0fff` is deployed on production. Public release assets
  return 200; nginx and the subscription service remain active.

- Hero uses the wide real cabinet capture on desktop and the portrait real
  cabinet capture on mobile. Its mobile illuminated container leaves deliberate
  black side margins.
- Project-local Impeccable skill/hook installation was attempted twice but its
  bundle download timed out and nothing was installed. The existing
  `npx --yes impeccable detect` path remains available and passed.
- The applications section lists Happ and INCY as supported clients and shows
  iPhone/iPad, Android, Windows and Linux as static text with icons. It has no
  app selector, store CTA or phone-application screenshot.
- The fourth section explains bypass traffic as a separate allowance and keeps
  the existing tariff anchor. One factual summary panel sits on a horizontal
  cold-blue light field; surrounding page background is true black.
- Live tariff data is unchanged. The local pricing presentation uses three
  compact ArcVPN-blue plans with contained top panels, a shared period switch,
  pill actions and no trailing card space below the CTA.
- Runtime commit `42e60dc` is pushed and fast-forwarded on production. The
  separate local login redesign remains uncommitted and was excluded from the
  generated release bundle.
- Final checks: Impeccable detector passed, Vite production build passed, 177
  tests passed, and browser review covered desktop plus 390x844 mobile.

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
- Page, wheel, trackpad and internal-anchor scrolling use the browser's native
  behavior. There is no custom wheel interception or CSS smooth scrolling.
- Instagram and TikTok stay hidden until exact HTTPS URLs are configured.

## Evidence

- Runtime commit `9a69ba1` removes the experimental smooth-scrolling handlers
  and CSS; it is pushed to `main` and pulled fast-forward on production
  `pl-control`.
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

## 2026-09-09 visual correction

- Production is at `1e533cc` after the owner's Hero/app-proof correction.
- Hero cabinet proof no longer has the nested black frame. It uses one thin
  translucent glass rim around the real desktop/portrait cabinet image.
- Happ and INCY phone screenshots are again visible in the applications
  section as static labelled product evidence; no selection or install CTA was
  restored.
- Phone and bypass light fields use layered, blurred elliptical side volumes
  without a sharp white horizon rule.
- Local build, Impeccable detector, 177 tests, desktop browser QA, 390x844 QA,
  public asset checks, and production service checks passed.
- Owner changes in `Connect.svelte`, `HomeFlowPreview.svelte`, the deleted
  design prompt, and unrelated generated/untracked files remain untouched.

## Rollback

Revert `9a69ba1` only if the removed scrolling experiment must be restored.
`/app`, payment, authentication and subscription URL contracts are unchanged;
no service restart is needed for this static-only rollback.
