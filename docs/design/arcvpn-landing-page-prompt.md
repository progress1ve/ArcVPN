# ArcVPN landing page generation prompt

Build a premium single-page landing page for **ArcVPN (Арк ВПН)** in Russian.
This is not a generic cybersecurity website: avoid shields, padlocks, neon
globes, hacker imagery, matrix rain, anonymous hooded people, stock photography,
and exaggerated claims. The page should feel like the public, editorial sibling
of the existing ArcVPN personal cabinet: calm, precise, dark navy, icy blue,
technically confident and easy to understand.

Use **Svelte 4 + Vite + JavaScript + semantic HTML + component-scoped CSS**.
Reuse the project's existing ArcVPN logo and icon components/assets where
available. Do not replace the application or account pages; build the public
landing route and preserve the existing `/app` and `/admin` behavior.

---

## Product and page goal

Audience: Russian-speaking users who need a simple VPN for everyday internet,
multiple devices, and a separate reserve of traffic for bypassing disruptions.

The page has one job: explain ArcVPN in under a minute and move the visitor to
the existing account/WebApp flow.

Primary CTA: **«Открыть ArcVPN»** → `/app`.

Secondary CTA: **«Выбрать тариф»** → scroll to pricing.

Telegram CTA: **«Открыть в Telegram»** → use the configured bot URL, never a
hard-coded placeholder.

Use only truthful product facts:

- unlimited regular traffic on all current plans;
- a separate allowance for disruption-bypass traffic where included;
- support for iPhone/iPad, Android, Windows and Linux;
- Happ and INCY are supported connection applications;
- login through Telegram or passwordless email code;
- plans can be purchased for 1, 3, 6 or 12 months;
- a custom tariff builder lets the user choose devices, bypass allowance and
  period;
- referral rewards are +5 days when a friend joins and +15 days after the
  friend's first purchase;
- do not invent server counts, speeds, uptime percentages, user counts, reviews,
  awards or security certifications.

---

## Visual thesis

The signature element is an **Arc Route**: a restrained luminous route that bends
through the page like the negative-space cut in the ArcVPN mark. In the hero it
connects a small device tile to two quiet server points; as the visitor scrolls,
the same line becomes a section divider and finally resolves into the ArcVPN
logo near the final CTA. It should communicate continuity and connection without
using a globe or map.

Spend visual boldness on this one element. Keep the rest disciplined: large type,
deep space, few surfaces, precise borders, no decorative card explosion.

### Color tokens

```css
:root {
  --bg-deep: #02050b;
  --bg: #03070e;
  --surface: #0a111b;
  --surface-raised: #101b29;
  --surface-blue: #13283a;
  --text: #f4f9fd;
  --muted: #8da2b5;
  --muted-soft: #64798c;
  --line: rgba(166, 211, 244, 0.13);
  --line-strong: rgba(142, 211, 247, 0.34);
  --ice: #9bd9ff;
  --sky: #75c6f3;
  --blue: #448fcf;
  --success: #72d3a3;
}
```

Primary button gradient:

```css
linear-gradient(128deg, #b3e4ff 0%, #72c5f4 48%, #448fcf 100%)
```

Background atmosphere: very subtle radial blue light, concentrated around the
Arc Route. Do not put gradients on every card. Avoid pure black for surfaces.

### Typography

Use **Manrope** for display and interface text, with **Inter** as fallback.

- Display: Manrope 700–800, tight tracking from `-0.055em` to `-0.035em`.
- Body: Manrope 450–550, comfortable `1.55–1.7` line height.
- Utility labels: Manrope 750, uppercase only for short technical labels,
  `0.12em` letter spacing.
- Use tabular numerals for prices and statistics.

Do not use a serif display font. Do not italicize random words. Emphasis comes
from scale, line breaks and the ice-blue light.

### Geometry

- Main content width: `min(1180px, calc(100% - 40px))`.
- Desktop section spacing: 120–160px; mobile: 76–96px.
- Large panels: 28–34px radius.
- Inner controls: 16–20px radius.
- Pills only for navigation, compact statuses and CTAs.
- Hairline borders, never heavy white outlines.

---

## Global behavior

- Forced dark theme; no light-mode toggle.
- Smooth anchor navigation with correct reduced-motion fallback.
- Use Motion One or lightweight Svelte transitions. Do not add GSAP unless the
  Arc Route cannot be implemented cleanly without it.
- Animate opacity and transforms only. Keep movement subtle and purposeful.
- Respect `prefers-reduced-motion`: remove route drawing, parallax and floating
  motion while preserving all content.
- No blocking loading screen and no fake 0–100 counter.
- No autoplay video. The brand identity must work without a heavy media asset.
- Optimize for LCP: hero text and CTA render immediately; decorative SVG is
  non-blocking.

---

## Section 1 — Floating navigation

Sticky/fixed at the top with safe-area support. Transparent at the hero top;
after 40px of scroll it becomes a compact dark glass bar:

```css
background: rgba(7, 15, 24, 0.82);
backdrop-filter: blur(18px) saturate(125%);
border: 1px solid rgba(166, 211, 244, 0.12);
```

Desktop layout:

1. ArcVPN mark + `ArcVPN` wordmark on the left.
2. Links: `Возможности`, `Как подключить`, `Тарифы`, `Поддержка`.
3. Secondary text action `Войти` → `/app`.
4. Primary button `Открыть ArcVPN` → `/app`.

Mobile layout:

- Logo left, primary compact CTA and accessible menu button right.
- Menu opens as an anchored dark panel, not a full-screen generic drawer.
- Keep visible keyboard focus and close on Escape/outside click.

---

## Section 2 — Hero: «Связь остается»

Full first viewport, but allow content to breathe on short mobile screens.
Desktop uses an asymmetric 7/5 grid; mobile stacks text before the visual.

Left content:

- Eyebrow with a tiny live-looking—but static—blue point:
  `ARCVPN · ДОСТУП БЕЗ ЛИШНИХ ДЕЙСТВИЙ`.
- H1, maximum 3 lines:

  **«Интернет, который  
  остается с вами.»**

- Supporting copy:

  `Подключите ArcVPN один раз. Обычный трафик остается безлимитным, а отдельный запас для обхода глушилок помогает, когда привычного соединения недостаточно.`

- CTA row: `Открыть ArcVPN` and `Как это работает`.
- Quiet compatibility line with icons/text:
  `iPhone / iPad · Android · Windows · Linux`.

Right visual: create a native HTML/SVG **Arc Route console**, not a dashboard
screenshot. It contains:

- a small device card labeled `Ваше устройство`;
- a route bending through two understated nodes labeled `Основной` and
  `Обход глушилок`;
- one status capsule `Подключено`;
- a tiny endpoint card `ArcVPN` with the real logo;
- a 3–4 second route pulse traveling from device to endpoint;
- very slow 4–8px vertical drift of the endpoint card.

The composition should read as a product artifact, not a sci-fi diagram. No
fake speedometer or fabricated latency.

Hero entrance: logo/nav first, then eyebrow, headline, paragraph, CTAs and route
console with 70ms stagger. Total animation under 900ms.

---

## Section 3 — Product truth strip

A single wide horizontal band under the hero, divided into four factual cells:

- `Безлимит` / `обычный трафик`;
- `4 платформы` / `телефон и компьютер`;
- `2 способа входа` / `Telegram или email`;
- `1–10 устройств` / `в своем тарифе`.

Use typography and dividers, not four floating cards. On mobile, make it a 2×2
grid. Reveal each cell on scroll with a small upward fade.

---

## Section 4 — How it works

Heading:

**«От оплаты до подключения — несколько минут.»**

Use a real three-step sequence because order matters:

1. `Выберите тариф` — ready plan or custom configuration.
2. `Выберите устройство` — iPhone/iPad, Android, Windows or Linux.
3. `Импортируйте подписку` — Happ or INCY opens with the ArcVPN link.

Desktop: a horizontal route with three large stops that continue the Arc Route
visual language. Mobile: vertical route. Each stop has one icon and no more than
two lines of explanation.

CTA below: `Подключить VPN` → `/app?screen=connect` if supported by the existing
router; otherwise `/app` without inventing a broken route.

---

## Section 5 — Disruption-bypass explanation

This is the educational centerpiece. Use a split composition with large copy on
the left and an interactive two-lane comparison on the right.

Heading:

**«Обычный интернет — отдельно.  
Запас для сложных моментов — отдельно.»**

Copy:

`ArcVPN не считает обычный трафик по гигабайтам. В тарифах с обходом вы получаете отдельный лимит, который используется для доступа в условиях ограничений.`

Right-side visual has two lanes:

- `Основной трафик` — continuous ice-blue line, label `Безлимит`.
- `Обход глушилок` — five small route branches, quota label that changes between
  `45 ГБ` and `115 ГБ` when the user toggles Standard/Family.

Do not claim that bypass is guaranteed against every restriction. Add a quiet
note: `Доступность зависит от сети, устройства и характера ограничений.`

---

## Section 6 — Devices and applications

Heading: **«Работает там, где вы уже работаете.»**

Two-tier layout:

- Four device tiles: iPhone / iPad, Android, Windows, Linux.
- Beneath them, one calm comparison panel for Happ and INCY.

Use the real Happ and INCY artwork already supplied in the project, but keep the
phone/device images fully visible and modest in size. Never crop the phone frame,
and never allow the `Happ` or `INCY` labels to overlap the images.

Each app tile has only:

- app name;
- `Рекомендуем` for Happ or `Поддерживается` for INCY;
- one sentence: `Установите приложение и импортируйте подписку из ArcVPN.`

CTA: `Выбрать устройство` → existing connection flow.

---

## Section 7 — Pricing

Heading: **«Тариф на нужное количество устройств.»**

Supporting copy:

`Во всех тарифах обычный трафик безлимитный. Отличаются количество устройств и запас обходного трафика.`

Use the live catalog/API where possible. Never duplicate production prices in
business logic. Initial visual values may show the current `от` prices:

- Эконом — `от 78 ₽/мес`, 2 устройства, без обходного трафика;
- Стандарт — `от 122 ₽/мес`, 3 устройства, 45 ГБ обхода;
- Семейный — `от 282 ₽/мес`, 10 устройств, 115 ГБ обхода.

Layout:

- Desktop: three cards in one row; Standard slightly emphasized with a stronger
  blue border, not physically oversized.
- Mobile: horizontal scroll-snap cards with the next card visibly peeking in.
- Period switch: 1 / 3 / 6 / 12 months.
- For 3/6/12 months show crossed-out one-month total and `Выгода N ₽` only when
  the catalog calculation produces a positive saving.
- Each card CTA: `Выбрать` → existing purchase flow.

Below the cards, add one distinct wide custom-plan panel:

- label `СВОЙ ТАРИФ`;
- title `Платите только за нужную конфигурацию`;
- copy `Выберите 1–10 устройств, запас обхода и срок.`;
- CTA `Создать свой тариф` → `/app?screen=custom-tariff`.

Do not mention markup, internal pricing rules or implementation details.

---

## Section 8 — Referral program

Use the supplied ArcVPN open blue-and-white gift artwork with a truly transparent
background. Do not use a phone image. The gift lid and box should float as a
single composition with a restrained 6px vertical loop; disable under reduced
motion.

Heading: **«Приглашайте друзей.»**

Terms displayed directly, without a separate “conditions” card:

- `+5 дней` — когда друг присоединится;
- `+15 дней` — после его первой покупки, вам и другу.

CTA: `Получить ссылку` → `/app?screen=referral` if available, otherwise `/app`.

---

## Section 9 — Support and FAQ

Split header:

- H2: **«Помощь без лишних кругов.»**
- Copy: `Живой чат и короткие ответы на частые вопросы.`
- CTA: `Перейти в поддержку` → existing support flow.

Keep exactly four FAQ items:

1. `VPN не подключается — что проверить?`
2. `Как установить ArcVPN на новое устройство?`
3. `Почему интернет может стать медленнее?`
4. `Как работает трафик для обхода глушилок?`

Accordion requirements: only one item open at once, keyboard accessible, animate
height without layout jumps, use `aria-expanded` and a rotating chevron. Answers
must be practical and short; do not promise impossible troubleshooting results.

---

## Section 10 — Final CTA and footer

The Arc Route from earlier sections resolves into a large, faint ArcVPN mark in
the background.

Headline:

**«Подключение, о котором  
не приходится думать.»**

Copy:

`Выберите готовый тариф или соберите свой. ArcVPN проведет через установку шаг за шагом.`

Buttons: `Открыть ArcVPN` and `Открыть в Telegram`.

Footer includes:

- ArcVPN logo and short line `Доступ без лишних действий.`;
- links: `Тарифы`, `Поддержка`, `Пользовательское соглашение`, `Политика конфиденциальности`;
- current year generated dynamically;
- no fake social networks or office address.

---

## Components

Create focused components rather than one huge page:

- `LandingNav.svelte`
- `ArcRouteHero.svelte`
- `TruthStrip.svelte`
- `ConnectionSteps.svelte`
- `BypassExplainer.svelte`
- `DeviceApps.svelte`
- `LandingPricing.svelte`
- `ReferralFeature.svelte`
- `LandingFaq.svelte`
- `LandingFooter.svelte`

Share tokens through one landing stylesheet. Keep application/account styles
isolated so the landing page cannot change the WebApp or admin panel.

---

## Responsive and accessibility acceptance

- Verify at 390×844, 768×1024, 1280×800 and 1440×1000.
- No horizontal page overflow at any size.
- Minimum 44×44px interactive targets.
- Visible `:focus-visible` treatment using `--ice` with sufficient offset.
- Semantic landmarks and one H1 only.
- All decorative SVGs use `aria-hidden="true"`; meaningful visuals have text
  alternatives.
- Pricing controls and FAQ work with keyboard only.
- Contrast meets WCAG AA for body text and controls.
- Reduced-motion mode removes route pulses, floating gift and reveal movement.
- Avoid `100vh` mobile browser traps; prefer `100svh` with content-safe minimums.
- Test 320px width even though the primary mobile acceptance width is 390px.

---

## Implementation constraints

- Preserve existing authentication, purchase, payment, email, Telegram, custom
  tariff, referral and connection logic. The landing page only links into those
  flows.
- Read URLs and prices from existing configuration/API; do not hard-code secrets,
  bot tokens, payment data or private subscription values.
- Do not add analytics, external trackers, autoplay media or large dependencies.
- Do not use placeholder URLs, lorem ipsum, fake testimonials or fake metrics.
- Do not copy competitor layouts or assets. The Arc Route composition and ArcVPN
  visual system must make the result recognizable without the logo.
- Finish with a production build and inspect all four target viewports, hover,
  focus, open FAQ, mobile menu, pricing-period states and reduced motion.

Deliver a polished, production-ready page—not a static mockup. Every CTA must
lead to a real existing ArcVPN route, and every claim must match current product
behavior.
