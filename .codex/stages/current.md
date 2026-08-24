# Current stage: browser-first Support workspace redesign

Status: in progress
Started: 2026-08-24

## Goal

Turn the ArcVPN admin Support section into an original, production-grade operations workspace that keeps the existing support APIs and Telegram delivery intact while making thread triage and replies clear, responsive, accessible, and recoverable from failures.

## Non-goals

- Do not copy Axottle code, assets, naming, or exact visual treatment; its screenshot is only a reference for information hierarchy, dense-but-readable cards, and quick actions.
- Do not change subscription URLs, user UUIDs, node/protocol topology, Remnawave state, or active-user access.
- Do not promote Schemes into production routing control.
- Do not redesign unrelated admin pages except shell rules strictly required for Support reachability/responsiveness.
- Do not add ticket assignment/status workflow or backend schema migrations in this bounded stage.

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
- Runtime/deploy target: `arcvpn-subscription.service` only unless bot runtime is actually changed.

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

## Acceptance criteria (fixed before implementation)

1. Support is reachable and usable at mobile 390x844, tablet 768x1024, laptop/desktop 1366x768, and wide 1920x1080.
2. At every viewport `documentElement.scrollWidth <= innerWidth`; content is not merely hidden by an x-overflow mask, and no required control is clipped.
3. Wide/desktop use a balanced list + conversation composition; tablet/mobile provide an explicit list/detail flow with a visible back action and preserve thread selection.
4. Thread list, thread detail, refresh, and reply expose intentional loading, error with retry/recovery, empty, disabled, and success/settled states. No stale thread is presented as the newly selected one.
5. Hover, active/selected, `:focus-visible`, disabled, loading, error, and empty states are visually distinct and meet readable contrast in the touched surface.
6. A keyboard-only pass can reach Support, refresh, filters/search if present, every visible thread, back navigation, reply field, and send action in a logical order; focus never disappears.
7. Interactive elements have accessible names; current section/thread state is programmatically exposed; form errors/status changes are announced appropriately; touched build warnings for accessibility and unused/dead CSS are zero.
8. Existing real operations remain intact: list threads, open/read a thread, reply once, persist the message, and retain best-effort Telegram delivery/audit behavior. No API path or permission regression.
9. Original ArcVPN visual language is preserved: dark navy surface, ice-blue action color, compact operational metadata, restrained status accents, no Axottle assets/code/exact copy.
10. Before/after screenshots exist for all four viewport classes, with precise paths recorded here; key interaction states have additional evidence where a static screenshot cannot prove behavior.
11. Local focused tests, full relevant Python regression, and `npm run build` pass; generated bundle is inspected with the source diff.
12. Exact staged diff is reviewed and secret-scanned; commit is pushed; production performs `git pull --ff-only`; only `arcvpn-subscription.service` is restarted if it is the only affected runtime; service state, health, public asset/version, and authenticated production browser behavior are verified.

## Risks and mitigations

- **Reply duplication or wrong-thread send:** keep one guarded send path, disable during flight, bind request to the selected thread id, and verify persisted result.
- **Responsive state trap:** model list/detail explicitly rather than hiding the list at a breakpoint; test browser navigation at all four widths.
- **Owner-only production access:** never expose credentials. Use an already-authorized browser session or obtain action-time confirmation before any password transmission; do not mark browser acceptance passed while gated.
- **Generated bundle drift:** build from the reviewed source and inspect `webapp_dist/` alongside source changes.
- **Production dirty tree:** compare incoming tracked paths with remote status before fast-forward; abort safely on overlap.
- **Unrelated shell regressions:** constrain shell edits to navigation reachability and Support layout; smoke-test another admin section at each viewport.

## Rollback

- Revert the stage commit, rebuild `webapp_dist/`, push, production `git pull --ff-only`, and restart `arcvpn-subscription.service`.
- No database rollback should be needed because this stage must not migrate or rewrite support data.
- If deployment health or Support operations regress, immediately roll back the UI commit while preserving all production operational files.

## Verification matrix

| Check | Mobile 390x844 | Tablet 768x1024 | Desktop 1366x768 | Wide 1920x1080 | Evidence/status |
|---|---:|---:|---:|---:|---|
| No horizontal overflow / no clipped controls | local pass | local pass | local pass | local pass | `scrollWidth == innerWidth`; all visible Support controls stayed inside viewport bounds |
| Composition and list/detail navigation | local pass | local pass | local pass | local pass | mobile/tablet list + detail screenshots; explicit back flow; dual-pane desktop/wide |
| Hover/focus/disabled/loading/error/empty | local pass | local pass | local pass | local pass | computed hover/focus styles + state screenshots |
| Keyboard-only path and accessible names | partial | partial | partial | partial | names/current/live regions and focus-visible verified; in-app key injection focused controls but did not dispatch Tab/Enter activation, so a real keyboard pass remains a production/manual gate |
| Real list/open/reply persistence | n/a | n/a | local pass, prod pending | local pass, prod pending | 21 focused/RBAC tests and dev persisted reply; one production reply still required |
| Other admin section shell smoke | local pass | local pass | local pass | local pass | Home/Support shell and visible nav geometry; mobile nav click regression fixed and reverified |

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
- Final WebApp production build passed in 4.36s; `AdminConsole.svelte` produced zero accessibility or unused CSS warnings. Pre-existing warnings remain in untouched `HomeFlowPreview`, `AdminSchemes`, `AdminCatalog`, and `AdminFinance`, plus the existing bundle-size warning.
- Commit, production deployment, authenticated browser reply, and keyboard/manual gate are still pending.

## Next step

Review and stage the exact diff, deploy the accepted source/bundle, then complete authenticated production reply and keyboard evidence before closeout.
