# Current stage: browser-first whole-admin operations redesign

Status: in progress
Started: 2026-08-24
Expanded: 2026-08-24 after the Support deployment, before further runtime edits

## Follow-up correction: dashboard hierarchy and Schemes removal

User evidence on 2026-08-24 invalidated the visual usefulness of the deployed overview and Schemes screen. Before this correction, desktop production shows unequal KPI columns, an independently positioned logout control under the refresh cluster, stretched infrastructure whitespace, and unstructured device metrics. The Schemes editor has no ArcVPN apply/version/rollback contract and does not justify its navigation or bundle cost.

Acceptance fixed before the correction:

1. Remove Schemes from authorized navigation, rendering, source components, generated bundle, and the now-unused graph dependency. Direct stale section state must fall back to an available section; no placeholder or dead CSS remains.
2. Remove the overview logout control from the refresh/header composition; authentication expiration and the login surface remain functional.
3. Desktop/wide overview uses a consistent four-column KPI grid and a 12-column operational panel grid. Nodes and attention panels align at the top instead of stretching each other; device metrics have an explicit internal grid.
4. Tablet/mobile collapse predictably without horizontal document overflow; all remaining sections stay reachable.
5. Build and local tests pass with zero new touched accessibility/unused-CSS warnings; before/after browser evidence covers four viewport classes.
6. Exact diff is committed/pushed, production fast-forwards, only the subscription service restarts for the rebuilt admin bundle, and authenticated production browser verification confirms the removed route/navigation and corrected grid.

Correction evidence before deployment:

- Schemes navigation/rendering and both graph components are removed; `@xyflow/svelte` plus its graph/D3 dependency tree is removed from the package lock.
- Final bundle changed from `608.96 kB` JS / `231.06 kB` CSS to `381.71 kB` JS / `201.82 kB` CSS. The build passed; the only Svelte warnings remain the two pre-existing warnings in untouched `HomeFlowPreview.svelte`.
- Four-viewport overview geometry: desktop/wide KPI cards resolve to four equal columns; the operational surface resolves to 12 equal tracks; Nodes and Attention have identical top coordinates; device metrics resolve to five columns, then two on tablet and one on mobile.
- Responsive smoke covered the 10 remaining sections x four viewports (`40` combinations): no document overflow, Schemes navigation, or overview logout control. Screenshots: `.codex/stages/evidence/admin-dashboard-correction/{mobile,tablet,desktop,wide}-overview.png`.
- Full local Python regression remains `68 passed`; `git diff --check` passed.
- Correction commit `d111e11efa5f86738e54fc6e464fabe3e2dc9bb6` was pushed and fast-forwarded on production. Only `arcvpn-subscription.service` restarted; its readiness poll returned `OK`, and both subscription and bot services are active.
- Authenticated production verification passed at 390x844, 768x1024, 1366x768, and 1920x1080: no document overflow, Schemes nav, or logout control; desktop/wide KPI columns are equal and Nodes/Attention align. Public panel and the exact `index-JV-fiZUG.js` / `index-e0ypqx1N.css` assets returned HTTP 200.

## Goal

Turn every ArcVPN admin section into one coherent, original, production-grade operations panel. Preserve the already deployed Support workspace and real ArcVPN operations, close demonstrated functional gaps using existing or explicitly implemented ArcVPN contracts, and make the whole panel responsive, accessible, observable, and recoverable from failures.

## Non-goals

- Do not copy Axottle code, assets, naming, or exact visual treatment; its screenshot is only a reference for information hierarchy, dense-but-readable cards, and quick actions.
- Do not change subscription URLs, user UUIDs, node/protocol topology, Remnawave state, or active-user access.
- Do not promote Schemes into production routing control.
- Do not clone Axottle screens, code, assets, copy, information architecture, or branding. Its public documentation is comparative product research only.
- Do not add generic infrastructure controls merely because Axottle exposes them. A new action requires an ArcVPN-owned backend contract, permissions, safe confirmation, test coverage, and production evidence.
- Do not turn Schemes into production routing control or introduce node/CDN/GeoAssets/SelfSteal mutations in this frontend stage.
- Do not add backend schema migrations unless a browser-observed core workflow cannot be completed safely without one and the acceptance plan is amended before implementation.

## Baseline and component map

- Local branch `main`, `origin/main`, and production `/root/ArcVPN` were all at `3846570a73575601bb5a44bf84db96d24ce45ba3` before edits; local worktree was clean.
- Production `arcvpn-bot.service` and `arcvpn-subscription.service` were active/running/enabled with successful main status. Local service health and public panel/subscription endpoints returned HTTP 200.
- Production contains pre-existing tracked and untracked operational changes. They are owner-owned, outside this stage, and must not be reset, cleaned, or deleted. Deployment must check overlap before `git pull --ff-only`.
- `webapp/src/views/AdminConsole.svelte`: admin shell, navigation, Support state/actions, Support markup, and currently overlapping shell/Support style layers.
- `webapp/src/lib/api.js`: existing Support client calls and dev fixtures.
- `subscription_api.py`: existing authenticated Support list/detail/reply API and SPA delivery; change only if focused verification finds a real contract defect.
- `database/db_support.py`: existing thread/message persistence; inspect for tests, do not change without a demonstrated contract defect.
- `tests/`: focused Support/API and role regression coverage if backend behavior needs explicit proof.
- `webapp_dist/`: generated production bundle after the accepted source build.
- Runtime/deploy target: `arcvpn-subscription.service` and `arcvpn-bot.service`; both import the changed shared panel reconciliation code.

### Expanded screen and ownership map

| Section | Primary component | Required operator outcome |
|---|---|---|
| Главная | `AdminConsole.svelte` | Understand service health, business pulse, attention queue, and reach the responsible workflow. |
| Здоровье | `AdminHealth.svelte` | Diagnose stale/degraded/offline state and refresh evidence without confusing cached data for current state. |
| Схемы подключений | `AdminSchemes.svelte` | Inspect and validate declared connection layouts; clearly distinguish read-only/planned behavior from active routing. |
| Ноды | `AdminNodes.svelte` | Inspect node status and operational metadata; expose safe failure/empty/stale states. |
| Каталог подписки | `AdminCatalog.svelte` | Understand the user-visible catalog and its ordering/availability without implying unsupported mutations. |
| Пользователи | `AdminUsers.svelte` | Search and inspect users, subscriptions, devices, and relevant actions with permission/error feedback. |
| Финансы | `AdminFinance.svelte` | Inspect revenue and operational expenses, and distinguish loading, failed, validation, mutation, and empty states. |
| Поддержка | `AdminConsole.svelte` Support workspace | Triage threads and send one durable reply with recovery from all request failures. |
| Безопасность | `AdminSecurity.svelte` | Inspect access/device/audit evidence and perform only existing guarded actions. |
| Резервные копии | `AdminBackups.svelte` | See backup freshness/status and execute only existing confirmed backup operations. |
| Настройки | `AdminSettings.svelte` | Inspect integration readiness and effective access; owners can manage the supported administrator-role contract with validation and feedback. |

## Browser-first defect evidence

| ID | Page/component | Viewport | Severity | Reproduction and observed defect |
|---|---|---:|---|---|
| S-01 | Support navigation | mobile <=560 px | critical | Shell CSS hides navigation items 5+, while Support is item 8; the section cannot be opened from the UI. |
| S-02 | Thread list | tablet/mobile <=900 px | critical | Support CSS sets `.thread-list{display:none}` with no conversation-list/back control; only the auto-selected first thread is reachable. |
| S-03 | Support requests | all | high | Thread list/detail loaders have no visible loading or error/retry state; reply failure is silent. Old detail can remain visible while a new thread loads. |
| S-04 | Empty states | all | medium | Empty thread list and empty conversation have no distinct actionable states; the right pane can be blank. |
| S-05 | Keyboard/accessibility | all | high | Refresh glyph lacks an accessible name; reply textarea lacks an explicit label; selected nav/thread semantics are absent; textarea removes outline; no Support `:focus-visible` treatment. |
| S-06 | Disabled/loading | all | medium | Send disablement exists functionally but has no sufficiently distinct visual/loading feedback; double actions and request context are unclear. |
| S-07 | Layout/density | laptop/tablet | high | Support uses fixed viewport-height math inside the shell and hides overflow globally; composition can clip/conceal content instead of proving no horizontal overflow. |
| S-08 | CSS maintainability | shell/Support | all | Multiple successive style layers redefine the same shell and Support selectors, producing dead/overridden CSS risk and hard-to-predict breakpoints. |
| S-09 | Production auth baseline | wide 1920x1080 | gate | Real `https://panel.arccnet.space/admin` loaded in the in-app browser with no horizontal overflow, but the current browser session stopped at the owner login surface. Screenshot: `.codex/stages/evidence/support-before/wide-1920x1080.png`. Authenticated Support evidence is still required before acceptance. |
| P-01 | Whole-panel navigation | mobile 390x844 | critical | Authenticated production browser shows only Home, Health, Nodes, Support, and Settings. Schemes, Catalog, Users, Finance, Security, and Backups are `display:none` with no menu/scroll alternative. |
| P-02 | Admin shell/RBAC | all | critical | Backend `/api/admin/access` exposes effective permissions, but the shell always loads overview first, renders every section, and labels every session Owner/full access. A support-only role lacks `overview.read` and therefore cannot reach its permitted Support workspace. |
| P-03 | Users subscription mutation | all | critical | Local disable expires the SQLite key, while the minute sync selects only unexpired keys. The existing generic revoke path interprets Remnawave nodes as XUI inbounds, so an already provisioned remote identity can remain ACTIVE. |
| P-04 | Schemes | tablet/desktop/wide | high | Visible graph nodes extend beyond the main viewport even while document width reports equality because the shell masks overflow. UI copy implies an apply workflow, but no apply contract exists; background metric changes can rebuild and discard the local draft. |
| P-05 | Overview refresh | all | high | A transient 30-second refresh error replaces the authenticated workspace with the login card instead of retaining the last known snapshot and exposing stale/retry state. |
| P-06 | Health/Nodes/Catalog | all | high | Health omits Remnawave/subscription failures and uses an unsupported numeric score; Nodes calls SSH preflight “Add node” although no bootstrap exists and labels bps as MB/s; Catalog lacks error/empty/dirty/reset semantics and an audit failure after commit can invite a duplicate retry. |
| P-07 | Users/Finance/Security/Backups/Settings | all | high | Network/mutation state machines are incomplete; Finance can silently show zeros on failure; Security reports false empty while loading; Backups calls every historical file verified without a returned verification status; Settings is a static status page with a hard-coded SMTP state. |
| P-08 | Accessibility and CSS | all | high | Non-Support components have missing labels/live regions/current/expanded/disabled semantics, weak mobile reflow, unused props/selectors, and the shell retains an unreachable `active === 'network'` branch with legacy CSS. |

## Axottle comparison and disposition

The public Axottle documentation is used only to compare operator outcomes and safety contracts. ArcVPN implementation remains original and limited to ArcVPN-owned APIs.

| Documented product pattern | ArcVPN disposition for this stage | Evidence/constraint |
|---|---|---|
| Permission-aware navigation and protected actions | **Implement now** | ArcVPN already has `/api/admin/access`, `/api/admin/roles`, and a role matrix; the frontend is the missing link. Reference: `https://docs.axottle.com/ru/panel/navigation`, `.../access-and-sessions`. |
| Dashboard that answers health / recent change / next action | **Implement available evidence now** | Reuse ArcVPN overview, health, attention queue, audit, and existing route actions; do not invent incident objects or quick actions without contracts. Reference: `https://docs.axottle.com/ru/panel/dashboard`. |
| Operation/audit journal with filters | **Implement bounded version now** | ArcVPN already exposes the last 500 append-only audit events; client-side search/filter/refresh is valid. Server pagination and a distinct operations event model are deferred. Reference: `https://docs.axottle.com/ru/panel/journal-and-audit`. |
| Explicit health states/severity and stale evidence | **Implement from existing telemetry now** | Derive honest severity from Remnawave, services, registered nodes, database integrity, disk boundary, and timestamps. Do not invent self-heal or SLO percentages. Reference: `https://docs.axottle.com/ru/health/states`. |
| Node metrics/services/diagnostics | **Implement truthful inspection now; defer mutations** | Metrics and bounded diagnostics exist. Agent bootstrap, service start/stop, logs, GeoAssets, TLS, and provisioning lack an ArcVPN admin API and require a separate node-ops contract. Reference: `https://docs.axottle.com/ru/nodes/control-panel`. |
| Versioned connection-unit editor with validate/apply/rollback | **Reject imitation; make current screen honest** | ArcVPN has derived topology only, no version/apply/rollback backend. Keep read-only topology or clearly local planning; no production-control affordance. Reference: `https://docs.axottle.com/ru/connection-units/lifecycle`. |
| Backup histories with integrity status and previewed restore | **Implement truthful list/create now; defer restore** | ArcVPN API can create a quick-checked local SQLite snapshot and list files, but does not return persistent verification, download, retention, offsite storage, or restore preview. Reference: `https://docs.axottle.com/ru/operations/backups`. |
| Settings with real persisted forms, reset, roles, integrations | **Implement access/readiness evidence now; defer missing APIs** | Effective role/permissions and role assignments exist. SMTP readiness can be reported. 2FA, sessions, notification policy, health policy, integration mutation, and passwords require new security contracts. Reference: `https://docs.axottle.com/ru/panel/settings`. |
| Ticket SLA, assignment, priority, delivery queue, infrastructure context | **Defer** | ArcVPN Support currently has thread/message persistence and best-effort Telegram delivery only. Schema, delivery job state, operator ownership, and SLA clocks need a separate backend stage. Preserve the improved reliable reply flow. Reference: `https://docs.axottle.com/ru/support/tickets`. |
| CDN, SelfSteal, GeoAssets, Axosun, anti-abuse automation, status page | **Reject for this stage** | No matching ArcVPN-owned admin contracts or production acceptance gates. Decorative controls would be misleading and risky. |

## Whole-panel acceptance criteria (fixed before expanded implementation)

1. Every mapped section is reachable and usable at mobile 390x844, tablet 768x1024, laptop/desktop 1366x768, and wide 1920x1080.
2. At every section and viewport `documentElement.scrollWidth <= innerWidth`; content is not merely hidden by an x-overflow mask, and no required control, table cell, dialog, popover, or navigation item is clipped or unreachable.
3. Each section has a deliberate composition appropriate to the viewport: dense operational layout on desktop/wide, readable stacking or drill-down on tablet/mobile, and no information encoded by position or color alone.
4. Every network-backed surface exposes intentional loading, recoverable error, empty, stale/last-updated where relevant, and settled states. Mutations expose distinct ready, disabled, in-flight, success, validation-error, and server-error states without losing user input or duplicating actions.
5. Hover, selected/current, `:focus-visible`, disabled, loading, warning, error, and empty states are visually distinct and readable in all touched components.
6. A keyboard-only pass can reach every section and every visible control in logical order, activate safe controls, operate forms/dialogs, return focus after dismissal, and never lose visible focus.
7. Interactive elements have accessible names and semantics; headings/landmarks are coherent; current navigation, expanded state, tables, forms, errors, and live status updates are programmatically exposed. Touched components produce zero accessibility or unused/dead-CSS warnings.
8. Existing real operations remain intact and receive focused regression proof: overview refresh/routing, health refresh, node/catalog/user/payment inspection, Support list/open/reply persistence, security/device/audit actions, backup actions, and supported settings updates. No API/RBAC/path regression.
9. Axottle comparison produces a traceable gap matrix with three dispositions: implement now using an ArcVPN contract, defer with a concrete missing dependency, or reject as out of scope/risky. No proprietary code, assets, exact copy, or misleading unsupported control enters ArcVPN.
10. Original ArcVPN visual language is preserved: dark navy surfaces, ice-blue primary actions, compact operational metadata, restrained semantic accents, and consistent shell/page/state primitives across all sections.
11. Before/after screenshots exist for every section at all four viewport classes. Key dialogs, overflow behavior, empty/error/loading, hover/focus, disabled, and success states have additional evidence where static default screenshots are insufficient.
12. Local focused tests, full relevant Python regression, browser interaction checks, and `npm run build` pass. Generated assets are inspected with source changes; no touched warning or accidental fixture text ships in production.
13. Exact staged diff is reviewed and secret-scanned; commit is pushed; production performs `git pull --ff-only`; only affected services restart; service state, health, public assets/version, authenticated production workflows, all four viewport classes, and a real safe operation are verified.

## Risks and mitigations

- **Reply duplication or wrong-thread send:** keep one guarded send path, disable during flight, bind request to the selected thread id, and verify persisted result.
- **Responsive state trap:** model list/detail explicitly rather than hiding the list at a breakpoint; test browser navigation at all four widths.
- **Owner-only production access:** never expose credentials. Use an already-authorized browser session or obtain action-time confirmation before any password transmission; do not mark browser acceptance passed while gated.
- **Generated bundle drift:** build from the reviewed source and inspect `webapp_dist/` alongside source changes.
- **Production dirty tree:** compare incoming tracked paths with remote status before fast-forward; abort safely on overlap.
- **Unrelated shell regressions:** constrain shell edits to navigation reachability and Support layout; smoke-test another admin section at each viewport.
- **Local disable without Remnawave revocation:** target is the authorized admin mutation plus the shared panel reconciliation path, and only users explicitly changed by that operation. Current state can remove local eligibility while leaving an already provisioned Remnawave identity active. Desired state is idempotent remote deactivation keyed by the existing UUID, with no UUID or subscription URL replacement and no impact to still-active users. Gate with focused adapter/API tests, a production dry/read-only comparison, one explicitly safe disabled test identity if available, Remnawave state verification, and unchanged active-user authorization. Roll back the sync change and re-enable only the designated test identity if the remote transition is not exact.

## Rollback

- Revert the stage commit, rebuild `webapp_dist/`, push, production `git pull --ff-only`, and restart `arcvpn-subscription.service` plus `arcvpn-bot.service` because the shared panel reconciliation path changed.
- No database rollback should be needed because this stage must not migrate or rewrite support data.
- If deployment health or Support operations regress, immediately roll back the UI commit while preserving all production operational files.

## Verification matrix

| Check | Mobile 390x844 | Tablet 768x1024 | Desktop 1366x768 | Wide 1920x1080 | Evidence/status |
|---|---:|---:|---:|---:|---|
| No horizontal overflow / no clipped controls | local pass | local pass | local pass | local pass | All 11 sections: `scrollWidth == innerWidth`; required controls inside viewport after mobile Users filter correction; Schemes canvas is contained and pannable. |
| Composition and section navigation | local pass | local pass | local pass | local pass | 44 after screenshots under `.codex/stages/evidence/admin-after/`; every owner section is reachable, including horizontally scrollable mobile shell navigation. |
| Hover/focus/disabled/loading/error/empty | local pass | local pass | local pass | local pass | 17 cross-panel state/RBAC screenshots plus prior Support state evidence; child request fixtures cover error/empty, mutation controls expose guarded states. |
| Keyboard-only path and accessible names | partial | partial | partial | partial | names/current/live regions and focus-visible verified; in-app key injection focused controls but did not dispatch Tab/Enter activation, so a real keyboard pass remains a production/manual gate |
| RBAC and read-only behavior | local pass | local pass | local pass | local pass | Browser roles: support sees only Support and can reply; viewer mutations disabled; finance/operator nav matches effective permissions; access/role endpoint tests pass. |
| Real operations | pending prod | pending prod | local/API pass, prod pending | local/API pass, prod pending | 68 tests cover RBAC, Support, verified Remnawave disable and panel-sync failure. Production safe-operation and Support reply gates remain. |

## Evidence log

- `git status --short --branch`: clean local `main...origin/main` before stage.
- Production read-only baseline: matching local/origin/deployed commit; both services healthy; panel and public health HTTP 200.
- Production login baseline: `.codex/stages/evidence/support-before/wide-1920x1080.png`.
- Current UI fixture screenshots: `.codex/stages/evidence/support-before/wide-dev-1920x1080.png`, `desktop-1366x768.png`, `tablet-768x1024.png`, and `mobile-390x844.png`.
- Browser DOM metrics confirmed width equality at all four viewports. This did not count as overflow acceptance because `body` masked x-overflow; tablet/mobile hid the thread list, and mobile CSS set Support navigation to `display:none`.
- Baseline `npm run build` passed but reported pre-existing warnings, including unused selectors in `AdminConsole.svelte`. Touched-component warnings must be removed before acceptance; unrelated warnings are recorded as residual project debt rather than silently claimed fixed.
- After screenshots: `.codex/stages/evidence/support-after/{mobile,mobile-list,tablet,tablet-list,desktop,wide}-*.png` plus focused `state-*.png` for loading, list/detail/send errors, empty queue/history, sending, success, and focus.
- Responsive metrics after the cascade fixes: mobile workspace `16..374.4` at width 390 with nav `790.8..838.8`; tablet workspace `98..752` at width 768; desktop workspace `304..1334.4` at width 1366; wide workspace `316..1876` at width 1920. No required control crossed a viewport boundary.
- Browser state proof: list/detail failures expose retry UI; empty list/history are distinct; sending sets `aria-busy=true`, changes the label, and disables thread switching; send failure preserves the draft; successful dev reply increased messages 3→4, cleared the editor, updated the list preview, and announced success.
- Interaction proof: non-selected thread hover changed background/border/transform; keyboard-induced focus on thread/search/reply exposed a solid ice-blue outline; navigation, current section/thread, form labels, live/status regions, and disabled controls have accessible semantics.
- Focused API/RBAC tests after the audit-failure fix: `21 passed`. Full local Python suite: `57 passed`; `py_compile` passed.
- The earlier Support-only WebApp production build passed in 4.36s; `AdminConsole.svelte` produced zero accessibility or unused CSS warnings. Those historical results were superseded by the integrated whole-panel build below.
- Support commit `1da502d0e5423ee1c9e86b64653fcb17d0878a18` was pushed, fast-forwarded to production, and `arcvpn-subscription.service` is healthy. Public assets and the authenticated production overview load successfully.
- Support still retains two closeout gates: one authorized production reply and a real keyboard-only activation pass. They remain acceptance items of this expanded stage.
- Authenticated production baseline before this batch: 38 private screenshots under `C:/Users/babay/AppData/Local/Temp/arcvpn-admin-evidence/admin-before`. Tablet/desktop/wide cover all 11 sections; mobile captures the five reachable sections and proves the other six had no reachable navigation. They stay outside Git because they contain real operator data.
- Integrated safe-fixture after evidence: 44 screenshots under `.codex/stages/evidence/admin-after/` cover all 11 sections at 390x844, 768x1024, 1366x768, and 1920x1080. Browser geometry found zero document overflow and zero clipped required controls after the one-pixel Users filter fix.
- State/RBAC evidence: 17 screenshots under `.codex/stages/evidence/admin-after/states/` cover access denied/error, stale overview refresh, support/viewer roles, child error/empty states, and node-metrics error/empty states.
- Browser RBAC proof: support role booted directly into Support without overview access; viewer Support editor/send were disabled, Catalog inputs were read-only with no publish footer, and Backup creation was disabled. Owner, operator, finance, viewer, and support labels/navigation matched effective permissions.
- Backend operation proof: admin disable now updates Remnawave to `DISABLED` and verifies the authoritative read-back without changing the UUID; activate/adjust synchronizes immediately; a failed remote confirmation returns `502 panel_sync_failed` and is safely retryable. Focused and full local suite: `68 passed`; `py_compile` and `git diff --check` passed.
- Final integrated `npm run build` passed. All touched admin components have zero Svelte accessibility or unused-selector warnings. Two pre-existing warnings remain in untouched `HomeFlowPreview.svelte`; the existing bundle-size advisory remains.
- Runtime commit `9c77b67831f163605678c9b476d5c3b72741e349` was pushed and fast-forwarded on Poland production. Pre-existing remote dirty/untracked operational files were preserved; the only tracked dirty file remained `scripts/ssh_askpass.sh` and did not overlap the incoming diff.
- `arcvpn-bot.service` and `arcvpn-subscription.service` were restarted and are active/enabled with new main PIDs; local production health returned `OK`. The public panel, `index-D4WHQuS2.js`, and `index-BsuS_udP.css` returned HTTP 200 and the served HTML references those exact assets.
- Authenticated production browser acceptance covered all 11 sections at 390x844, 768x1024, 1366x768, and 1920x1080. All 44 combinations had `documentElement.scrollWidth == innerWidth`; no content control overflow was found. Four mobile nav buttons can be outside the instantaneous viewport only inside the intentional `overflow-x:auto` rail (`clientWidth 345`, `scrollWidth 558`) and were successfully scrolled to/opened.
- Production read-only operation proof: 3 node cards, 12 catalog profiles, 154 users with the first 40 rows loaded, 3 finance summary cards, 48 audit events, one listed backup, settings/readiness/RBAC data, and Support list/open with 3 threads and a four-message history. Support refresh settled without error; the empty reply remains correctly disabled.
- Private production after screenshots (real operator data, not committed): `C:/Users/babay/AppData/Local/Temp/arcvpn-admin-evidence/admin-after-production-9c77b67/` for representative mobile, tablet, desktop, and wide screens. Visual inspection confirmed the intended mobile bottom rail, contained/pannable Schemes composition, readable Users layout, and wide Settings/RBAC composition.

## Next step

The implementation and deploy are accepted except for three explicitly destructive/manual gates: a real keyboard-only activation pass, one authorized production Support reply with persistence/delivery evidence, and a designated safe disabled Remnawave test identity for live revoke confirmation. Do not mark the stage complete until those gates are confirmed or explicitly waived.
# Current stage — growth, billing, LTE, and Remnawave-native cutover

Started: 2026-08-25. Status: in progress.

## Goal

Prepare ArcVPN for paid acquisition: reliable Standard trial, Economy/Standard/
Family products, real independent LTE quota, campaign attribution, web promo
management, and Remnawave-native subscription authority without changing public
subscription URLs, UUIDs, or active access.

## Non-goals

- No copying Axottle source or proprietary implementation.
- No unverified protocol/node topology changes.
- No direct client migration to new public subscription URLs.
- No deletion outside the explicitly authorized inactive never-paid user class.

## Component map

- Product/DB: `database/`, tariff, trial, payment, promo, campaign migrations.
- Bot: onboarding/trial and two-step tariff/payment UI.
- Web/API: `subscription_api.py`, `webapp/`, `webapp_dist/`.
- Subscription plane: native Remnawave fetch, thin ArcVPN compatibility gateway,
  legacy fallback telemetry and later retirement.
- Production: Poland control plane; Germany/Netherlands RemnaNode delivery.

## Acceptance

- Trial is idempotent, uses Standard entitlements, and partial failure is retryable.
- Economy/Standard/Family prices and 1/3/6/12-month periods have one source of truth.
- LTE is a real 0/45/115 GB quota resetting every 30 days; no `x10` customer model.
- WebApp contains no add-traffic purchase and shows real remaining LTE.
- Campaign links have immutable first-touch attribution, named comparison metrics,
  and configurable entry/payment bonuses.
- Promo usage is consumed only after successful idempotent fulfillment.
- Remnawave supplies all share links; ArcVPN only preserves stable URL, device
  controls, metadata/catalog, announce, and Happ rendering. Fallback is measured.
- Existing active users retain URL/UUID/access; migration preview and rollback exist.
- A destructive never-paid cleanup requires backup, dry-run counts and relational
  integrity verification before an explicitly scoped production apply.
- Touched UI passes mobile/tablet/laptop/desktop composition, no horizontal
  overflow, keyboard navigation, focus/hover/disabled/loading/error/empty states,
  accessibility checks, and before/after screenshots.
- Local tests/build pass; exact staged diff is reviewed; commit/push/pull/restart
  and public/browser verification are recorded.

## Risks and rollback

- Entitlement migration can revoke access: snapshot rows and Remnawave state,
  update without UUID/subscription changes, recheck every affected identity.
- LTE counters can reset upstream: store monotonic checkpoints and never subtract
  negative deltas; keep enforcement disabled until shadow reconciliation passes.
- Trial retries can duplicate access: deterministic operation key and transaction.
- Hard deletion is irreversible: encrypted backup plus dry-run manifest; rollback
  restores the DB before services resume.
- Native subscription outage: short cache and observable legacy fallback until a
  zero-fallback soak allows removal.

## Verification matrix

| Area | Local | Production/public evidence |
|---|---|---|
| DB/trial/tariffs | migration + unit/integration tests | aggregate preview, test identity |
| LTE | counter/reset tests, shadow fixtures | Remnawave usage reconciliation |
| Bot/payments | handler and fulfillment tests | authorized test purchase/trial |
| Web/admin | typecheck, tests, build | four viewport browser screenshots |
| Subscription | native/fallback contract tests | stable URL, UUID and real client fetch |
| Capacity | load-test scripts | CPU/RAM/latency/error baseline |

## Evidence log

- Pre-change worktree: only pre-existing owner change
  `webapp_dist/assets/payments/sbp.svg`; it is excluded from this stage.
- Baseline architecture: native Remnawave links are fetched by
  `_native_remnawave_links`, then rendered by the ArcVPN gateway; legacy generation
  remains a fallback.
- Implemented migrations v54-v56: durable Standard trial, product/LTE model,
  first-touch campaigns and promo activation state.
- Combined local verification: `84 passed`; modified Python modules compile.
- `webapp` production build completed with 87 modules and no Svelte accessibility
  or unused-CSS warnings.
- Local browser acceptance used authenticated DEV mocks. Growth and purchase flows
  have no horizontal overflow at 1440x900, 1180x760, 820x1180 and 390x844.
  Browser screenshots were emitted for desktop Growth, mobile Growth (top/bottom),
  and mobile tariff purchase. Mobile internal scroll reaches all campaign cards.
- Browser integration caught and fixed a late-device-response bug that had shown
  Standard as 2 devices / 0 LTE; recheck shows 3 devices / 45 GB LTE and correct
  Economy/Family switching. Monthly display now follows the approved floor values.
- Local browser console has no ArcVPN errors; warnings come only from Telegram's
  SDK reporting unsupported color/swipe methods in its DEV version 6.0 shim.
- Real keyboard Tab focus movement could not be demonstrated through the in-app
  browser automation (focus remained on the selected navigation control); semantic
  buttons/inputs and `:focus-visible` rules are present, but this acceptance item
  remains open for production keyboard verification.

---
