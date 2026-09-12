# Current stage — integrated ArcVPN footer

## Goal

Replace the separate support block and small footer with one large editorial
ArcVPN footer derived structurally from the owner reference, while simplifying
features, bypass actions, tariff destinations and FAQ controls exactly as asked.

## Non-goals

- No Hero, trial terms, live pricing, backend, bot or WebApp redesign.
- No copying the reference's light palette or brand identity.
- No unverified social, infrastructure or privacy claims.

## Components and public contract

- `webapp/src/views/LandingPage.svelte` only.
- TikTok: `https://www.tiktok.com/@arcvpn4?_r=1&_t=ZT-99fjaeRQ9dO`.
- Instagram: `https://www.instagram.com/arc_vpnn?stkn=MW1scmgwc2s0ZjM3dw==`.
- Every preset tariff “Выбрать” action and custom “Создать тариф” action goes
  directly to `/app`; analytics events remain.
- Remove the three capability cards, bypass chip and bypass tariff link.
- FAQ uses code-native SVG arrows with accessible expanded state.

## Acceptance

- Support/management links and footer form one responsive dark-navy shell with
  clear brand, management, community, help and legal hierarchy plus oversized
  ArcVPN wordmark treatment.
- Exact TikTok and Instagram URLs are visible, external and safe (`noopener`).
- No removed feature, chip or bypass CTA remains in DOM.
- All four tariff actions resolve to `/app`; no product/month/custom query is
  emitted from the landing.
- FAQ arrows rotate without shifting row height; expansion still works.
- Mobile 390x844, tablet 768x1024, desktop 1280x900 and wide 1600x900 have no
  overflow or clipped footer content.
- Vite build, Impeccable detector, local/public browser checks and deployment
  workflow pass.

## Risks and rollback

- Risk: oversized footer wordmark clips interactive links or produces overflow.
- Risk: removing tariff intent parameters changes the cabinet entry context;
  this is explicitly requested and must resolve to plain `/app`.
- Rollback: revert the runtime commit and rebuild static assets.

## Evidence

- Before: support links and the legal footer were two disconnected sections;
  social links depended on unset config, so Instagram/TikTok were absent.
- Local build: `npm run build` passed; generated landing assets
  `LandingPage-DnJeUPZy.js` and `LandingPage-_qWWOCID.css`.
- Design lint: `impeccable detect src/views/LandingPage.svelte` passed with no
  findings after replacing decorative gradient text with a solid wordmark.
- Browser at 926x930: zero horizontal overflow; footer shell 863x620; removed
  feature cards, chip and bypass tariff link all have zero DOM matches.
- Browser interactions: FAQ arrow changes from 90 to -90 degrees and
  `aria-expanded` becomes true; exact Instagram/TikTok URLs and custom `/app`
  destination were confirmed from the rendered DOM.
- Production: commit `2ae95c6` fast-forwarded on Poland; nginx,
  `arcvpn-bot.service` and `arcvpn-subscription.service` remained active.
- Public `https://arccnet.space/`: stylesheet `LandingPage-_qWWOCID.css`, zero
  overflow, exact social destinations, plain custom `/app`, all removed-element
  counts zero, and the integrated footer was visually inspected.
