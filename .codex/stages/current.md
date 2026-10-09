# ArcVPN design polish and optional AI support — 2026-10-09

Mode economy; no subagents. Owner explicitly authorized production publication,
superseding the earlier local-only request. Release branch is isolated from owner
dirt and based on verified GitHub/production 8cc0b1cb.

## Contract and scope

Preserve the published hero, Svelte stack, billing, subscriptions, login, reserve
links and 500 GB custom options. Refine lower landing, footer, typography, phone
art, cabinet payment/referral/support and motion. Borderless surfaces use existing
cabinet colors; date separators alone divide the chat. AI replies are optional,
clearly labeled and retain manager handoff. No DNS, TLS, node or bot changes.

## Verification before publication

- PASS: duration prices have identical top positions at 360/768/1280/1600; all
  four borders are 0; money is nowrap. Three composition rows, no duplicate
  category heading, payment CTA visible initially (bottom653.4 at360x800).
- PASS: custom/addon controls are readable and borderless; 500 GB preserved;
  DEV quote3239 RUB for3 months/3 devices/500 GB; addon15 GB/1 device60 RUB.
  These are UI fixtures, not production transactions.
- PASS: referral and support center exactly at x800 at1600; gift levitation;
  metrics above sharing; copy toasts for referral/subscription and expiry.
- PASS: complete topic drafts, no automatic send;44x44 round Send, multiline
  upward-growing composer; date dividers only; accessible dialog focus/Escape.
- PASS: landing phone fade and contour light, footer seamless top-glow fade,
  larger typography/platforms; no horizontal overflow at four widths; hidden
  scrollbars preserve scrolling. CTA gradient/shadow matches actual renewal.
- PASS: hero content and87 CSS rules match published8cc0b1c (line endings ignored).
- PASS:65 focused tests cover public catalog/custom quotes/admin support/AI:
  disabled configuration, redaction, timeout, late-reply races, idempotence,
  worker limits, authentication, rate limiting and manager notification.
- PASS: Vite184 modules/4.66s; mapped views zero warnings. Existing unrelated
  AdminConsole unused CSS warnings retained; vendor/fonts.css exists at runtime.
- PASS: static SEO canonical/schema/alternate names/noscript/no-noindex; hosted
  fonts and conditional Telegram SDK preserved. API helper unchanged.

Evidence: primary .codex/stages/evidence/design-20261009/, tariff-grid-final.local.json,
*-polish-*.jpg, tariff-aligned-final-1600.jpg, custom-tariff-final-*.jpg,
addons-final-390.jpg and support-centered-final-1600.jpg. Older screenshots are
superseded where corresponding latest evidence exists.

## Deployment and rollback

Ready to commit/push/fast-forward Poland, restart only subscription service, then
publish the same static build to Moscow (public A85.198.101.79 verified). Preserve
remote ssh_askpass dirt/runtime files and previous static releases. Previous hash
chunks retained for already-open clients. Rollback by reverting task runtime
commit and switching Moscow current to previous8cc0b1cb static release.

## Explicit remaining gate

Real AI inference is DEFERRED: no server API key exists. Integration is disabled;
ChatGPT/Codex subscription billing is separate. Activation instructions are
in docs/operations/support-ai.md. No provider request, billing transaction or
customer message was made during QA. Live AI latency/quality and real Telegram
keyboard remain unverified. Search recrawl/ranking and owner visual acceptance
remain external observations. Production verification follows publication.
