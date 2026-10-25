# WebApp Telegram safe area and headings — 2026-10-25

Mode: economy. No subagents authorized. Base: production ccaa3ca; customer static a76f09ee. Primary owner checkout and admin work preserved in isolated managed worktree.

## Owner contract / acceptance before implementation

- Center page/task titles throughout customer Svelte WebApp, including support chat, subscription/custom tariff, addons, connection, settings/subpages and modal titles. Keep existing content, routes, actions and brand styling.
- Respect combined device safe area and Telegram content safe area on every edge, updating on resize/fullscreen/inset events. Native Back/menu controls must not cover content. Browser without Telegram must retain sensible spacing.
- Autorenew control stays a true circle when adjacent Russian text wraps; on/off, keyboard focus and payment choices still work. No purchase or actual renewal setting change during QA.
- Latest owner font correction: native Apple system SF Pro on iPhone/iPad; retain current fonts on other devices and existing Manrope brand/day counter. No downloaded/bundled SF Pro. Landing/admin out of scope.
- Verify before/after screenshots and geometry at 360/768/1280/1600; emulate Telegram Android/iOS fullscreen controls, orientation/inset changes, zero insets and ordinary browser. Explicitly distinguish emulation from real Telegram device acceptance.

## Components / exclusions

`webapp/src/lib/telegram.js`, `webapp/src/app.css`, `webapp/src/views/HomeFlowPreview.svelte`, built `webapp_dist/`. Local-only Vite QA harness; no fixtures shipped. No backend, billing, API, identity, URLs, server topology or admin change.

## Risks / rollback / verification

Inset coordinates may differ across clients: add device+content insets, avoid fallback double counting, exercise dynamic updates and horizontal safe area. Circle flex shrink and centered title/button collision checked at narrow widths. SF rendering can only be visually confirmed on Apple hardware; desktop QA checks CSS and unchanged fallback. Rollback: revert isolated source/build commit; restore previous Moscow static symlink, retaining hashed assets. Publish only after build, browser evidence and staged diff review; Poland FFpull and Moscow atomic static release; no runtime service restart for frontend-only artifacts.

## Evidence

Local acceptance passed: Vite184 modules/5.71s; only existing legacy AdminConsole unused-CSS warnings. `git diff --check` passed after normalizing generated HTML line endings. Old tracked hashed assets restored after build; no DEV fixture identifiers in production assets.

Browser QA: 28 task-page checks plus friends/settings/support/chat/payment at360/768/1280/1600. Title centers within0.007px of page center; all headings below80px emulated Telegram occupied area; no horizontal overflow. Chat title moved from70.975px (overlap) to94.975px. Autorenew fixed from19.7875x30 to30x30px at360 and remained30x30 at every width; keyboard Space off/on exposes false/true without dismissing dialog, Escape closes normally. Payment and topic dialogs stay usable; short780x390 landscape payment sheet scrolls inside bounds72..362px. Left/right device44/20px reflected in shell padding. Dynamic zero insets heading38px -> portrait118px; browser fallback remains Manrope. No browser console errors in final support run.

Evidence folder `C:/Users/babay/.codex/visualizations/2026/10/25/01a17261-5177-76b1-bc0c-63f58d90a6f3/`: webapp-support-before360.png, webapp-support-final360.png; webapp-payment-before360.png, webapp-payment-after360.png and widths768/1280/1600; webapp-responsive.json, webapp-support-payment.json, webapp-inset-browser-states.json, webapp-zero-portrait.json. Screenshots explicitly use a localhost Telegram-control fixture. Real iOS SF Pro rendering and real Telegram-client insets remain hardware-dependent owner checks, not claimed as device testing. No payments/support messages submitted.

Publication and public verification pending.
