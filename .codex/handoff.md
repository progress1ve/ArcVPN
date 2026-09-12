# ArcVPN handoff — public Northern Flow landing

## 2026-09-12 pricing/navigation polish

- Production runtime `4eedf60` is deployed. At scroll top the landing navigation
  has no visible container; its bordered rounded shell returns after scrolling.
- Standard uses a neutral card with a separate diffuse lower light layer. Tariff
  SVGs are unboxed neutral icons, INCY is offset 4 px, and the custom tariff is a
  wide three-column enterprise-style builder.
- Vite build and public desktop/mobile browser checks passed; no service restart.

## 2026-09-12 frontend closeout

- Production `cfad811`: login pseudo-layers and logo backing removed.
- Pricing composition updated from the owner reference without changing live
  tariff data, quote calculation or selection behavior.
- Public browser verification passed; current landing stylesheet is
  `LandingPage-C0y5E1qs.css`. No services were restarted.

## 2026-09-10 login and consent release

- Visual follow-up `a682b6c` is deployed: the login again uses the personal
  cabinet's deep navy background and soft blue aurora glows. The glass panel,
  ArcVPN tile/wordmark, “Добро пожаловать” heading, and removed home link were
  verified in the public browser; this static-only update needed no restart.
- The unauthenticated `/app/` screen now uses a dark welcome composition with
  passwordless email as the primary path and “Войти через Telegram” as the
  secondary path. Both reuse the existing authentication APIs.
- The Telegram middleware no longer checks channel membership. It gates only on
  the current legal document version, with one “Принять и продолжить” button;
  the channel is an optional recommendation for news, bonuses, and service status.
- Legacy `check_subscribe` callbacks remain accepted so old bot messages do not
  strand users. Advertising attribution and automatic trial provisioning remain.
- Responsive browser QA covered 390, 768, 1280, and 1600 px; 178 local tests and
  the Vite production build passed. Runtime commit `89b41d2` is deployed;
  `arcvpn-bot.service` is active and the public page/assets return HTTP 200.

## 2026-09-10 hierarchy, Hero and Arc horizon

- Production runtime `bb2551b` makes Hero height-aware so the full real cabinet
  capture remains visible at tablet, laptop and wide heights; mobile uses the
  full portrait capture with a viewport-derived width.
- Capability proof is now one primary Auto-select story with a route diagram
  plus three compact supporting facts. Section spacing is shorter and less
  repetitive. The final CTA uses a code-native matte `Arc horizon`; the old
  raster wallpaper is no longer rendered.
- Standard tariff hover is fixed at 720-900px: all public 770px tariff cards are
  exactly 360px high and do not translate. Page scroll width remains contained.
- Vite build and Impeccable detector passed. Public root/new CSS/new JS return
  HTTP 200; nginx and the subscription service are active. No restart required.

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

## 2026-09-10 legal revision and apps-intro polish

- Production is at `470a325` after `ea12398` and the placeholder hardening.
- `/legal/user-agreement` contains distinct ArcVPN User Agreement and Privacy
  Policy parts dated 10 September 2026. It covers Telegram/email accounts,
  YooKassa-backed payments, opt-in auto-renewal, self-service cancellation,
  lawful refund handling, actual data categories, processors, retention,
  security and data-subject rights.
- Production operator requisites remain unset. The renderer suppresses raw
  `[УКАЖИТЕ ...]` values, but the owner must provide verified legal name, INN,
  OGRN/OGRNIP, address and legal email before final legal sign-off.
- “Работает на ваших устройствах” is centered at every breakpoint and the
  decorative `.apps-signal` markup/styles were removed. Hero and trial were not
  changed.
- Focused tests (4), syntax, Vite build, staged diff, public browser QA, HTTP
  checks and service checks passed. Nginx and subscription service are active.

## 2026-09-10 legal synchronization and backup-notification removal

- Production runtime is `e989cf3` (`9c3c452` plus scheduler import correction).
- WebApp settings use the 10 September 2026 revision and link to the canonical
  full Agreement + Privacy Policy; the stale embedded summary and placeholders
  are removed. Purchase links remain canonical.
- Telegram channel gate names both documents, and production records new
  consent as `2026-09-10`.
- Daily 09:10 UTC backup maintenance still creates retained local DB copies and
  cleans expired copies, but no longer creates or sends a Telegram archive to
  admins. Daily stats, expiry notifications and manual log exports are intact.
- Seven focused tests, scheduler import, Python compilation, Vite build, public
  asset/browser checks and production setting checks passed. Bot, subscription
  and nginx services are active.
- Follow-up `1fe7b69` also disables the daily “Суточная статистика” Telegram
  report to admins. Production verification confirms both daily admin outputs
  are absent while local backup maintenance remains enabled; all services are
  active.
