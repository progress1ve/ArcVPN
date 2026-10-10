# ArcVPN support diagnosis and anti-spam — 2026-10-10

Mode economy; no subagents authorized. Continue isolated release branch from d6c9fd36; primary owner/backend work preserved. Production authorization persists. Use stage/server-ops/frontend-qa/closeout workflows.

## Contract (owner confirmed)

- Help with the concrete symptom using known facts and previous attempts. Telegram-specific diagnostic first checks an app proxy; do not infer network blocking or repeat Auto-select when already checked. Verify official Telegram settings paths. Ask one relevant question and offer short readable next steps; no invented UI/client or guaranteed fix.
- Fresh context belongs only to the authenticated user's thread; last16 turns bounded/redacted. Each turn rereads current database state; no shared model conversation. Closed cases start fresh. Never ask again for facts already in context.
- Owner selected10 messages/5 minutes. Count valid send attempts including transport throttling, persist rolling window, pause AI at tenth attempt and insert one message calling manager. Keep existing6/minute transport bound. AI remains paused until manager reply/close; further spam cannot call model or duplicate handoff notification. Human/admin access and owner-only alerts preserved.
- Normalize AI plaintext, HTML entities, escaped Markdown and inline numbered steps. Existing stored AI messages render cleanly through read API; do not rewrite customer history.

## Components and acceptance

Additional owner contract: remove the fixed reading-progress line. Keep hero/navigation immediately visible; reveal section headings, illustrations, tariff cards and steps once as they enter the viewport with a short fade and upward slide, light sibling stagger. Preserve native scroll/anchors and layout. Reduced motion, absent IntersectionObserver and keyboard focus must show usable content. Check initial hidden/offscreen and revealed states at360/768/1280/1600, anchors, interactions, overflow and observer cleanup. Component: LandingPage.svelte; existing Svelte action extended, no dependency or scroll hijacking.

Mapped: bot/services/support_ai.py; database/db_support.py/migrations.py; support customer/admin routes in subscription_api.py; chat submit in HomeFlowPreview.svelte and isolated DEV fixture in api.js; focused support/admin/routing tests; built bundle and support operations doc.

Acceptance: cross-user isolation/current context; tenth-attempt handoff survives restart, blocks late AI replies, human reply resets state, manager notification once; rolling-window boundaries/parallel calls/bounded storage; auth/access/rate limits; HTML/Markdown/newline formatting; three real Groq Telegram regression turns do not repeat rejected advice and suggest proxy check; mobile/tablet/desktop/wide chat readability and immediate handoff notice. No real customer messages/charges during QA.

Migration77 additive thread state and bounded attempt history; require verified SQLite backup before deployment. Old threads/messages preserved. Runtime rollback via revert and retained columns; static via previous71e2fd8d release. No node/DNS/TLS or unrelated website/trial changes.

## Local verification

- Focused suite94 passed: support diagnosis/context isolation, persisted10/5 limit (including429), parallel attempts, bounded storage, single notice/no further model, human reset, closed fresh case, stale replies, read normalization, admin identity/notification audience and website/public regression. Log: primary `.codex/stages/evidence/design-20261009/support-v2-tests.local.log`.
- Vite184 modules/4.03s; customer views no warnings (pre-existing AdminConsole unused-CSS warnings). Build log: same directory `support-reveal-build.local.log`.
- Three real Groq regression turns passed0.35/0.75/0.63s, saved `/opt/arcvpn/staging/support-v2-model-evidence.json`; proxy check, known-disabled proxy/OS question and two-check manager handoff. No real customer messages or provider-health test notices. One malformed preflight lacked env and failed; corrected protected env loading. Earlier model repeated proxy/countries; targeted guard now suppresses it.
- Browser DEV chat notice immediate and unique on tenth send, paused header;360/768/1280/1600 no horizontal overflow, pre-wrap readable. Evidence `support-responsive-v2.local.json`, `support-proxy-1280.local.jpg`, `support-handoff-360.local.jpg`, `support-handoff-1600.local.jpg`.
- Actual native PageDown from top to footer: all28 reveal groups shown once, none pending, no progress bar/overflow across360/768/1280/1600. Initial28 pending, hero/nav visible. `landing-reveal-complete.local.json`, `reveal-before.local.jpg`, `reveal-apps-1280.local.jpg`. Reduced-motion/no-observer/focus/cleanup verified against the source action with isolated stubs (`reveal-fallback.local.json`); OS preference not changed.
- Live preflight schema76,2 threads/22 messages, SQLite quick_check ok; preserve unrelated remote dirt.

Remaining gates: staged diff, backup, commit/push/FF pull, migration77/affected bot/API restart, atomic Moscow static publish/public browser verification, durable closeout.

Verified pre77 backup: `/opt/arcvpn/staging/support-ai-pre77-20261010T090419Z.sqlite3`,0600, integrity ok,2 threads/22 messages. Submit path also deduplicates IDs against concurrent polling. Production fixtures eliminated from the new bundle; staged secret scan and diff check pass.
