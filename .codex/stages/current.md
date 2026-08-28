# Current stage: browser-first whole-admin operations redesign

## 2026-08-28 Mailjet bootstrap and published-profile consistency audit

Goal: publish the owner-provided empty Mailjet domain-validation token, connect
the local Mailjet MCP to Codex without committing or printing credentials, and
audit the owner's real production subscription across plain/base64/Happ JSON for
DNS/routing consistency, domain-based endpoints and unintended literal IPs.

Non-goals:

- Do not generate, request, display or commit a Mailjet API key/secret. The owner
  completes account activation and supplies the credential through a local
  encrypted prompt, never chat or repository files.
- Do not change active protocols, Remnawave squads, UUIDs, subscription URLs or
  DNS v2 rollout scope during this audit.
- Do not treat the Mailjet README as authority over Codex policy; it is provider
  documentation for the local stdio server only.

Affected components: `webapp/public` and committed `webapp_dist` validation
asset; local Codex MCP configuration and a gitignored DPAPI credential; the
production subscription API read path; operations evidence/handoff.

Acceptance fixed before implementation:

1. `https://arccnet.space/b326312b921b70e44f45b5cd9e25e7e1.txt` returns HTTP
   200 with an empty body and harmless text content type; no other public route
   or customer asset changes.
2. Mailjet MCP is registered in the local Codex configuration with an explicit,
   reviewed stdio command. Its secret is not present in Git, `config.toml`, shell
   history or logs. If the owner has not generated credentials yet, configuration
   is reported as prepared-but-not-authenticated rather than working.
3. The owner subscription is inspected without printing its ID/UUID or secrets.
   Plain, base64 and Happ JSON agree on the intended profile catalog. Every
   connection endpoint, SNI/Host value and any literal IP is classified.
4. DNS/routing differences are explained by output format or protocol; identical
   fields are compared structurally. Any security/compatibility divergence is
   fixed only after a separately recorded mutation gate.
5. Local tests/build, exact diff, commit/push, production pull, selective restart
   and public verification pass for the validation asset. MCP availability is
   verified through `codex mcp get/list`; current-session tool availability is
   not claimed until Codex refreshes it.

Risks and rollback: a non-empty validation token can fail Mailjet verification;
an MCP secret in TOML would be a credential leak; changing DNS merely to make
profiles visually identical can break protocol-specific clients. Rollback removes
the validation asset after Mailjet verification, removes the local MCP entry and
preserves all subscription/runtime identities unchanged.

Closeout evidence 2026-08-28:

- Criterion 1 **passed** at production commit `b9d7829`: the exact Mailjet token
  URL returns HTTP 200, `text/plain; charset=utf-8`, `Content-Length: 0` and
  `nosniff`. The first request during service restart received a transient 502;
  bounded retry passed and `sub.arccnet.space/health` returned `OK`.
- Criterion 2 **partially passed / authentication deferred**: the reviewed local
  `@mailjet/mailjet-mcp-server` 1.1.0 checkout installed and 24 tests passed.
  Global MCP entry `mailjet` is enabled and launches a local PowerShell wrapper.
  The wrapper reads a current-user DPAPI credential and keeps the secret out of
  `config.toml`, Git and command arguments. No credential exists yet, so launcher
  exit 78 is the truthful expected state until the owner generates API key/secret.
  A new Codex task/session is required before newly configured MCP tools can be
  exposed to the model.
- Criteria 3-4 **passed as an audit** for Telegram ID 2075630349 without emitting
  its subscription ID/UUID. Plain and base64 each contained the same ten manual
  profiles; Happ JSON added AutoSelect for eleven total. All eleven JSON profiles
  had one identical DNS structure. Routing intentionally had two structures:
  fallback-aware AutoSelect/LTE #1-#3 and ordinary direct profiles.
- Endpoint classification: NL Reality/Hysteria, DE Hysteria and all five XHTTP
  profiles use domains and domain SNI. DE Reality #1 still uses a literal public
  endpoint with domain SNI; therefore AutoSelect and LTE fallback #1-#3 contain
  the same address internally. Two literal resolver addresses and loopback
  inbound listens are expected DNS/client-local values, not VPN endpoint leaks.
  No endpoint mutation was authorized or attempted; converting DE Reality to a
  domain requires a separate real-client canary.
- Criterion 5 **passed except current-session MCP availability**: ArcVPN suite
  `111 passed`; Vite build succeeded; exact diff reviewed; commits `c2b652e` and
  `b9d7829` pushed and pulled with `--ff-only`; only
  `arcvpn-subscription.service` restarted for the exact route and remained active.
  The user-owned nested `mailjet-mcp-server/` checkout remains untracked and was
  not absorbed into the ArcVPN repository.

Rollback remains available: remove the exact route/assets after Mailjet validates
the domain and restart the subscription service; `codex mcp remove mailjet`
removes only the local integration. No subscription identity or topology changed.

## 2026-08-27 real operations dashboard, health and catalog truth

Goal: repair the production host split, make Overview and Health answer real
business/operations questions from ArcVPN-owned data, align the admin catalog with
the actually published subscription, restore the supported YouTube ad-free route,
and improve the desktop renewal composition without adding decorative controls.

Non-goals:

- Do not copy Axottle code, assets, text or exact layouts. Its screenshots are
  references for hierarchy, density, drill-down and actionable health evidence.
- Do not expose fake node-agent controls. Panel-driven node/inbound provisioning is
  recorded as a future authenticated agent stage unless a complete ArcVPN contract,
  rollback and real traffic gate are implemented here.
- Do not change stable subscription URLs, main/LTE UUIDs or active authorization.
- Do not create a Mailjet account or transmit credentials. This stage may prepare
  configuration, but activation waits for owner-created credentials and DNS values.

Affected components: production nginx host routing; `subscription_api.py` admin
overview/health/catalog APIs; database growth/payment/referral/traffic queries;
`webapp/src/views/admin/` Overview, Health and Catalog surfaces; purchase layout;
Happ routing/catalog preparation and regression tests; operations documentation.

Browser-first defects confirmed before implementation:

1. `https://panel.arccnet.space/` renders the indexed customer login (`ArcVPN —
   личный кабинет`) instead of the noindex admin entry. Production screenshot and
   DOM evidence captured on 2026-08-27.
2. The desktop purchase Back control is detached at the top-left instead of sitting
   near the centered purchase workflow.
3. Admin catalog shows retired Finland and obsolete/raw rows and therefore does not
   describe the ten profiles actually published to Happ.
4. Existing Overview/Health copy includes stale topology concepts and does not
   expose the requested real period cohorts, payment/product mix, referral source
   split, aggregate main/LTE usage, upstream/service state or resource pressure.

Acceptance fixed before code changes:

1. `panel.arccnet.space/` and `/admin` open the admin entry, carry `noindex`, and
   never render the customer login; `arccnet.space/` remains the indexable customer
   cabinet. Admin session persistence continues to work.
2. Desktop/laptop purchase Back sits with the centered workflow and remains visible,
   keyboard reachable and non-overlapping; mobile/tablet composition is unchanged
   or improved, with no horizontal overflow.
3. Overview reports from real persisted data: users joined today/7d/30d, successful
   payments and revenue for the same windows, popular paid products, referral users
   versus named advertising campaigns, aggregate main usage and LTE usage, live
   online devices/users, and a compact attention queue. Every timestamp/window and
   empty/error/loading state is explicit.
4. Health reports real Poland/Germany/Netherlands upstream/node evidence, Remnawave
   and ArcVPN service readiness, last-success/staleness, CPU/RAM/disk/load where an
   authenticated telemetry source exists, and actionable warning thresholds such as
   low disk/memory. Stale/unknown is never presented as healthy. The retired control
   plane label `Узлы Германия` is absent.
5. Referral/campaign detail lives in Growth when deeper comparison is required;
   Overview only summarizes and links to the real workflow. No dead button, fake
   report, mute/delete, node-add or repair action is introduced.
6. Admin catalog is derived from the same effective catalog preparation used by
   public subscription generation, with real order/names/visibility and no Finland,
   Canada, legacy x10 or hidden raw rows leaking into the published view. It clearly
   distinguishes source inbounds from generated AutoSelect/LTE fallback profiles.
7. The supported YouTube ad-free routing rule is restored in the ArcVPN-owned Happ
   routing payload, is syntactically valid, does not import unverified third-party
   geoassets, and has regression coverage.
8. Panel-driven node/server/protocol addition is either delivered end-to-end with
   authorization, safe validation, Remnawave binding and real-traffic acceptance, or
   documented as the next node-agent stage with an explicit data/API contract. The
   existing catalog editor must not claim it creates inbounds or nodes.
9. Local tests and WebApp build pass. Browser acceptance covers 390x844, 768x1024,
   1366x768 and 1920x1080 for admin entry, Overview, Health, Catalog and renewal;
   focus/hover/disabled/loading/error/empty states, keyboard order, contrast and
   overflow are checked. Before/after screenshots are recorded.
10. Exact diff is reviewed and secret-scanned; commit/push/pull/restart/public
    verification completes. Production proof includes real API values, service
    health, panel/customer host split and a freshly generated public subscription
    inspected without printing its identifier.

Risks and rollback: bad nginx routing can expose the wrong surface; expensive
aggregate queries can slow admin refresh; raw Remnawave names can leak retired
profiles; incorrect routing can break imports. Rollback restores the backed-up nginx
file and prior runtime commit, restarts only `arcvpn-subscription.service`, and keeps
all identities/URLs unchanged. New read-only metrics must fail closed as unknown,
not block customer subscription delivery.

Evidence recorded 2026-08-27:

- Released commits `20e3388` and `a4e6890`; production fast-forwarded to
  `a4e6890`. `arcvpn-subscription.service` and `arcvpn-bot.service` were active,
  and `nginx -t` passed. The prior nginx file and pre-cleanup SQLite catalog are
  recoverable from `/root/arcvpn-config-backups/`.
- Production `/api/admin/overview` returned HTTP 200 against the real database
  and Remnawave. It exposed payment/acquisition/product/traffic groups and two
  connected DHost nodes with live RAM telemetry. Example verified aggregates:
  2 successful payments/1260 RUB over 7 days and 5/1985 RUB over 30 days.
- The effective catalog now reports AutoSelect; Netherlands VLESS/Hysteria2;
  Germany VLESS/Hysteria2; YouTube without ads; and LTE #1..#5 with EU flags.
  Ten stale catalog overrides, including the old x10 label, were cleared only
  after a consistent SQLite backup.
- Fresh production subscription generation passed for plain, base64 and Happ
  JSON without printing the identifier: YouTube present, five LTE profiles,
  no Finland/Canada/France. Native Remnawave was the source with no fallback.
- Local regression suite: `110 passed`. Vite production build passed without
  Svelte warnings. Browser visual QA on the built code covered 390x844,
  768x1024, 1366x768 and 1920x1080; document overflow was false at all four.
  Desktop renewal, Overview and Health screenshots were captured in-browser.
- Public checks passed: `panel.arccnet.space/` redirects to `/admin`;
  `arccnet.space` serves the ArcVPN/Арк ВПН title, an allowlisted robots file and
  valid sitemap; panel robots disallow the entire host. A final new production
  browser navigation was blocked by Browser Use URL policy after a navigation
  timeout, so no circumvention was attempted. Authenticated production visual
  and keyboard activation remain open evidence, not silently accepted.
- Mailjet Free is selected but not activated: account/domain verification,
  provider-issued SPF/DKIM, DMARC and production SMTP credentials remain an
  owner-controlled external gate. Current official plan evidence: 6000 emails
  per month and 200 per day at the time of this check.

## 2026-08-27 apex activation, LTE metering audit and SMTP feasibility

Goal: activate the customer cabinet on `arccnet.space`, prove how LTE usage is
accounted for in direct and fallback profiles, and choose a deliverable email
path without weakening stable subscriptions or mail security.

Affected components: Poland SNI/nginx/TLS, customer `WEBAPP_URL`, Remnawave LTE
identity usage and scheduler reconciliation, Happ fallback JSON, public browser
surface, SMTP network/DNS feasibility and operations documentation.

Acceptance fixed before mutation:

1. Apex A record resolves to Poland before certificate issuance. TLS is valid,
   `https://arccnet.space/` serves the customer cabinet, and
   `panel.arccnet.space` remains admin-only. Stable `/sub/<id>` URLs stay on the
   existing subscription origin.
2. For Telegram ID 2075630349, compare Remnawave LTE identity usage, local
   `lte_used_bytes`, HTTP `Subscription-Userinfo`, and WebApp API without printing
   identifiers. Explain whether selected LTE #1-#3 used main or fallback.
3. LTE #1-#3 consume LTE quota only when their main balancer actually falls back
   to LTE XHTTP; #4-#5 always use the LTE identity. The info block mirrors the LTE
   identity, with bounded scheduler lag, and never estimates usage from a label.
4. SMTP decision is evidence-based: recheck outbound ports/PTR/DNS, compare
   currently available no-cost relays from primary provider documentation, and
   never install a self-hosted MTA that cannot deliver reliably.
5. Rollout uses config backup, nginx syntax check, certificate issuance, selective
   service reload/restart, public health/browser verification and an explicit
   rollback to the prior SNI map and unset `WEBAPP_URL`.

Risks: an incorrect SNI map can disrupt every TLS hostname; forcing LTE accounting
by profile label would charge main traffic; self-hosted mail without PTR and port
25 has poor deliverability. Stage remains open if a real client fallback or email
delivery cannot be proven.

Evidence on 2026-08-27:

- `arccnet.space` resolves to Poland. A Let's Encrypt certificate was issued,
  nginx syntax passed, and `/` plus `/app` return the customer cabinet over valid
  HTTPS. `panel.arccnet.space` still serves the noindex admin surface. The prior
  nginx file is backed up under `/root/arcvpn-config-backups/apex-20260827_0712`.
- The customer origin is injected as `WEBAPP_URL=https://arccnet.space` into both
  services. Telegram's persistent menu now reads the same environment variable;
  production logged `https://arccnet.space/app` after restart. Stable subscription
  URLs remain on `sub.arccnet.space`.
- LTE reconciliation previously crashed every cycle because the environment-backed
  Remnawave authority lacked the numeric cache `id`. Commit `ec6620c` reserves a
  negative cache identity. The full local suite passed (109 tests), production was
  pulled/restarted, and the selected account then matched byte-for-byte across
  Remnawave, local entitlement and `Subscription-Userinfo` (45-GiB quota).
- LTE #1-#3 use the unlimited main identity while the main balancer is healthy and
  consume LTE only after real loopback fallback to the separate LTE XHTTP identity.
  LTE #4-#5 always use that LTE identity. Current aggregate Remnawave accounting
  proves LTE consumption but cannot attribute past bytes to an individual profile.
- Browser acceptance passed at 390x844, 768x1024, 1366x768 and 1920x1080 with no
  horizontal overflow. Title, canonical URL, favicon, logo and theme metadata were
  present. The only console warnings are Telegram WebApp SDK capability warnings in
  a standalone browser, not application errors.
- Direct SMTP remains unsuitable: outbound 25/465/587 are blocked, current PTR is
  provider-owned, and apex has no mail-authentication records. Mailjet and Brevo
  port 2525 are reachable. Mailjet Free is the preferred minimal relay gate; an
  account, verified sending domain, provider-issued SPF/DKIM and SMTP credentials
  are still external prerequisites before a real email delivery pass.

## 2026-08-26 customer profile, LTE fallback and apex-domain correction

Goal: restore the useful Hysteria2 choices and the documented three-profile
main-to-LTE fallback behavior, make unlimited ordinary traffic truthful in every
customer surface, improve the wide purchase composition, and prepare the apex
domain/DNS/mail rollout without changing stable subscription URLs or UUIDs.

Mapped components: Happ subscription assembly and verification, DNS canary
selection, trial LTE entitlement, customer bot copy, WebApp purchase/account UI,
public metadata/domain configuration, legal copy, production environment and
REG.RU/mail operations guide.

Acceptance fixed before implementation:

1. Happ rows are ordered AutoSelect, Netherlands VLESS/Hysteria2, Germany
   VLESS/Hysteria2, then five EU LTE-labelled rows. LTE #1-#3 are independent
   main least-load balancers with LTE XHTTP fallback; LTE #4-#5 remain direct LTE
   profiles. Main/LTE credentials and stable URLs/UUIDs are preserved.
2. DNS v2 is enabled only for Telegram ID `2075630349`; global clients remain on
   the rollback profile until the user's real-device canary.
3. Trial remains Standard for seven days but receives exactly 5 GiB of LTE quota;
   ordinary traffic is unlimited. Paid Economy/Standard/Family descriptions all
   state unlimited main traffic and the exact LTE/device allowance.
4. WebApp account replaces the obsolete 1024-GB main display with `Безлимит` and
   a separate LTE remaining/quota line. Standard purchase defaults to SBP. At
   laptop/wide sizes the tariff/payment composition is vertically centered/lower,
   with no mobile/tablet overflow or interaction regression.
5. `arccnet.space` is the customer cabinet canonical origin and
   `panel.arccnet.space` remains admin-only. Deployment must not request a
   certificate before DNS ownership resolves to Poland.
6. Legal copy visibly explains no voluntary refunds and liability limitations,
   while preserving rights that cannot legally be waived. SMTP is accepted only
   with working outbound delivery, PTR/SPF/DKIM/DMARC and secrets outside Git; an
   infeasible self-hosted configuration is reported as an external blocker, not
   presented as working.
7. Focused/full tests and build pass; browser before/after acceptance covers
   390x844, 768x1024, 1366x768 and 1920x1080 without horizontal overflow. Runtime
   rollout follows commit/push/pull/restart/public verification.

Risks and rollback: malformed balancer JSON can break Happ imports or consume LTE
traffic unexpectedly; apex DNS/certificate or mail changes can disrupt public
access/deliverability. Rollback restores the previous subscription JSON builder,
DNS canary environment and nginx origin; it never rotates identities or URLs.

Status: in progress.

Local evidence:

- Full regression: `107 passed`; WebApp production build: 87 modules with no
  compiler warning; `git diff --check` passed.
- Browser pass at 390x844, 768x1024, 1366x768 and 1920x1080 found no horizontal
  overflow. Purchase copy shows unlimited main traffic plus the separate 45-GB
  LTE allowance, and SBP is active when the payment sheet first opens. Wide
  composition is vertically centered instead of pinned to the top.
- Happ unit coverage confirms Hysteria2 rows and three fallback LTE profiles;
  direct LTE remains only in rows 4-5. Trial coverage confirms a 5-GB LTE grant.
- Apex DNS currently has no A/MX/TXT record. Poland has no active MTA and outbound
  TCP/25 is blocked, so a self-hosted SMTP cannot be truthfully deployed there.
  A relay SMTP or provider unblock/PTR is still an external prerequisite.

Production rollout and acceptance status:

- Runtime commits `08fd884`, `610b261` and routing correction `d71af08` were
  pushed and fast-forwarded on Poland. Bot/subscription services are active and
  health is OK. Public admin root is HTTP 200, customer `/app` on the panel host
  is HTTP 404, the signed customer asset/legal page are HTTP 200.
- Criterion 1 passed: credential-safe verification reports five main and five
  direct LTE share links, zero identity crossover, exact 10-row Happ order and
  intact announce/header. The first three EU LTE JSON rows carry the tested
  main→LTE balancer contract; Hysteria2 is visible for NL and DE.
- Criterion 2 is configured and server-generated canary JSON for the selected ID
  uses DNS v2 while the global profile remains legacy. Real Wi-Fi/LTE client use
  is deliberately left to the owner.
- Criterion 3 passed for new provisioning and the three active legacy trials.
  Production backup `backups/vpn_bot.pre-trial-lte5-20260826.db` preceded the
  reconciliation; all three now satisfy unlimited main + 5-GiB separate LTE.
- Criterion 4 passed locally at all four viewports and production assets are live;
  the owner retains the authenticated real-device purchase scenario.
- Criterion 5 is prepared but deferred: REG.RU apex A record and TLS do not yet
  exist, so nginx apex activation and `WEBAPP_URL=https://arccnet.space` remain
  intentionally off. Stable subscription URLs are unchanged.
- Criterion 6 legal copy passed. SMTP is blocked by outbound TCP/25 and absent
  PTR/SPF/DKIM/DMARC; no fake or undeliverable SMTP was installed.
- Criterion 7 passed automated/local browser checks. Remaining external checks
  are the short owner DNS canary, apex DNS propagation/TLS, and one real email
  delivery after a relay or port/PTR solution. Stage remains in progress.

## 2026-08-26 LTE isolation and truthful quota rollout

Goal: make ordinary VPN traffic unlimited while metering and enforcing only the
0/45/115 GB LTE bypass allowance through Remnawave, without changing the stable
ArcVPN subscription URL or the existing main user UUID.

Mapped components: Remnawave adapter and sync scripts, user/key schema, billing
provisioning, calendar reset scheduler, subscription link transformation and
headers/announce, account API, focused LTE/subscription tests, production squads
and their inbound bindings.

Acceptance fixed before implementation:

1. Main and LTE usage are isolated by distinct Remnawave user identities; the
   current `client_uuid` remains the unlimited main identity and a new durable LTE
   UUID is used only on LTE XHTTP links.
2. Main squad contains no LTE inbounds; LTE squad contains only the reviewed
   `NL_DHOST_LTE_XHTTP` and `DE_DHOST_LTE_XHTTP` inbounds. No public subscription
   URL or main UUID changes.
3. Economy receives no LTE links. Standard and Family receive LTE links with the
   separate identity and Remnawave limits of 45/115 GiB. Renewal/reset is aligned
   to the existing personal calendar anniversary and is idempotent.
4. Subscription `upload/download/total` represents LTE usage/quota only. The
   approved five-line announce is emitted intact in HTTP/plain/base64/Happ output.
5. WebApp/API and announce reconcile against the same LTE usage. Quota exhaustion
   removes/disables only LTE access while ordinary VPN remains active.
6. Migration has backup plus preview/apply modes, provisions missing LTE identities,
   verifies UUID/squad/limit, and never deletes or rotates current identities.
7. Unit/integration/subscription tests pass; production requires squad/user
   verification, generated profile inspection and a real Standard-user LTE canary.

Risks: wrong squad edits can remove active access; using node-level usage is invalid
because both ordinary and LTE inbounds currently share DE/NL nodes. Implementation
therefore uses identity isolation, fail-closed topology validation and preview by
default. Rollback restores the previous main squad bindings/limits and generated
bundle while preserving both UUIDs.

Verification matrix: topology read-only audit, migration dry-run, focused tests,
full pytest, exact diff/secret scan, backup, production apply, service restart,
public format inspection and real tunneled main/LTE canary.

Status: in progress

Rollout evidence (2026-08-26):

- Production SQLite was backed up to the explicit pre-LTE artifact before schema
  v58. Migration preview selected 14 active users with zero errors; apply created
  14 LTE identities, updated 14 unlimited main identities, and the idempotent
  repeat updated 14/14 with zero errors.
- `ArcVPN Staging` now contains only the four reviewed DE/NL main inbounds.
  `ArcVPN LTE` contains exactly `DE_DHOST_LTE_XHTTP` and
  `NL_DHOST_LTE_XHTTP`. Existing main UUIDs and public ArcVPN URLs were retained.
- Credential-safe production inspection passed: five main share links use only
  the main identity; five LTE share links use only the LTE identity; header total
  equals the LTE quota; announce matches; Happ JSON contains exactly eight rows
  ordered AutoSelect, Netherlands, Germany, five EU LTE profiles.
- Finland is excluded from subscription delivery and from both backend/admin node
  surfaces. Its disconnected Remnawave records were not destructively deleted.
- Local regression passed `107 passed`; WebApp build passed with 87 modules.
  Production health is OK and bot/subscription services are active.
- Criteria 1-6 passed by migration/API/profile evidence. Criterion 7 remains
  partially external: generated production profiles passed, but a real tunneled
  Standard-user LTE exhaustion/main-survival canary still requires a user device.

## 2026-08-26 follow-up: login, tariff clarity, branding and LTE-only quota

Goal: remove the newly reported purchase/login friction and make the customer
traffic model explicit: ordinary VPN traffic is unlimited; only the LTE bypass
allowance is metered.

Affected components: `webapp/src/views/HomeFlowPreview.svelte`, standalone login
in `webapp/src/App.svelte`, admin session API/database, tariff copy helpers,
`subscription_api.py` announce/headers, public brand assets and focused tests.

Acceptance fixed before edits:

1. Promo input has no decorative rectangular focus fill/border/outline change;
   keyboard focus remains indicated by the field glyph, and there is at least
   12 px separation from recurring.
2. The supplied ArcVPN mark is used for favicon/manifest and standalone login.
3. Admin password sessions persist across normal browser restarts for 30 days;
   `/admin` never renders customer-login wording and logout still revokes access.
4. Standalone login centers brand/title and offers both Telegram and email paths;
   Telegram action opens the official bot/WebApp entry without accepting an
   unverified client identity.
5. Economy/Standard/Family descriptions contain no decorative emoji and state
   devices plus `Обход глушилок: нет` or the exact LTE allowance.
6. Customer-facing ordinary traffic is unlimited while LTE remains metered and
   reconciled. Announce exactly uses the approved five lines; LTE usage occupies
   subscription traffic headers/profile metadata without changing stable URLs or
   UUIDs. HTTP headers, plain/base64 and Happ JSON receive regression coverage.
7. Browser before/after evidence covers 390x844, 768x1024, 1366x768 and
   1920x1080; no horizontal overflow, promo disabled/error/success, keyboard focus,
   admin login/session copy, Telegram/email login and public assets are checked.

Risks/rollback: persistent admin cookies increase stolen-device exposure, so keep
HttpOnly/Secure/SameSite and server-side expiry/revocation. Traffic presentation
must not disable LTE enforcement or lie about Remnawave usage. Rollback is the
runtime commit plus previous generated bundle; no URL/UUID/database deletion.

Verification matrix: focused auth/announce/tariff tests, full pytest, WebApp build,
local browser four-view pass, staged diff/secret scan, production backup/pull,
affected-service restart, health/public/browser verification.

Evidence before rollout (2026-08-26):

- Local browser rendered standalone Telegram + email login with centered mark and
  heading. Purchase DOM exposes `126 ₽ / мес` before
  `6 месяцев · всего 759 ₽`; Standard copy is exactly
  `Основной трафик: 1024 ГБ (1 ТБ) · Обход глушилок: 45 ГБ · 3 устройства`.
- Local responsive pass at 390x844, 768x1024, 1366x768 and 1920x1080 found
  `scrollWidth == innerWidth`. Promo input CSS has no outline or box shadow and
  the promo surface has a 16 px bottom separation before recurring.
- WebApp production build passed: 87 modules, no compiler warning. Full Python
  regression passed: `104 passed in 4.85s`. `git diff --check` passed.
- Admin password cookie contract is now persistent for 30 days while retaining
  Secure, HttpOnly and SameSite=Strict; logout/server-side expiry remain intact.
- Criterion 6 is deliberately not claimed: current Remnawave identity aggregates
  normal and LTE links, while `lte_used_bytes` has no production per-node usage
  reconciliation. Presenting normal traffic as unlimited now would remove the
  only effective aggregate cap and make the requested announce false. Safe next
  work requires an LTE node UUID allowlist, node/user usage ingestion and a
  separately revocable LTE identity/squad before the text/header switch.

Rollout evidence:

- Runtime commit `33fad1e` was pushed to `origin/main`, production fast-forwarded
  from `afea781`, and only `arcvpn-subscription.service` restarted. Subscription
  and bot services are active.
- Public health, `/api/public/config`, the 23,332-byte WebP mark, manifest and
  admin HTML all returned HTTP 200. Production browser showed the standalone
  Telegram/email login and the distinct `Вход в ArcVPN Admin` password surface.
- Password persistence is proven by the 30-day cookie test/header contract; a
  manual existing-password browser login was intentionally not attempted.
- Acceptance 1-5 passed. Acceptance 7 passed for local four-viewport composition
  and public route/asset semantics; a real keyboard-only password-login pass is
  still external. Acceptance 6 is deferred for the enforcement reason above.
- Rollback is `git revert 33fad1e` followed by subscription-service restart; no
  schema, subscription URL, UUID or node topology changed in this release.

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

## 2026-08-26 accepted expansion: onboarding, anniversary quotas and public cabinet

The user accepted a decision-complete implementation plan before runtime edits.
This expansion supersedes any conflicting 30-day/global-first-of-month reset
language below; all prior evidence remains historical.

### Goal and component map

- `database/` and scheduler: one calendar-month anniversary for normal and LTE
  quota, idempotent due-cycle processing, legal-consent version/time.
- Remnawave adapter and trial: one Standard Remnawave identity, retryable
  entitlement, safe preview/backfill without URL or UUID replacement.
- bot onboarding/purchase/admin: consent-aware channel gate, one image-free trial
  welcome, structured tariff copy, current cabinet, retire the visible legacy
  Telegram admin and all user-facing crypto/Stars affordances.
- `subscription_api.py`: coherent traffic/LTE status and announce, promo quote,
  public cabinet routing, SMTP-backed standalone email login, DNS/routing profile.
- `webapp/` and generated `webapp_dist/`: monthly-price hierarchy, one tariff
  title, contrast, real promo states, email/site metadata and route separation.

### Fixed acceptance

1. A purchase at an arbitrary timestamp resets normal and LTE quota on the same
   calendar day next month; days 29-31 clamp to month end without permanently
   changing the anchor. Early renewal preserves the active cycle; a lapsed new
   purchase starts a new cycle.
2. Each due cycle is processed exactly once locally and confirmed in Remnawave;
   retryable remote failure cannot silently advance the durable reset boundary.
3. Trial provisions one Standard user through the production Remnawave contract.
   Failed/stale entitlement retries are idempotent. Production backfill is
   backup + dry-run + exact confirmation and only targets the accepted eligible
   class.
4. Channel consent -> trial -> one image-free welcome with Connect/Continue;
   repeated start opens the current cabinet. Structured tariff descriptions
   cannot be hidden by stale message-editor text.
5. Promo Apply performs an authenticated quote, visibly updates base/discount/
   final price, preserves errors, and usage is recorded only by successful
   idempotent fulfillment. Crypto and Stars are absent from customer UI.
6. `/admin` is the admin SPA; `/app` and `/` are the customer cabinet. Public
   cabinet has favicon, manifest, canonical/OG/Twitter metadata; admin is noindex.
7. SMTP secrets remain outside Git. Standalone email codes are rate-limited,
   one-use, expiring and non-enumerating; live delivery is a deployment gate
   until the owner supplies the custom SMTP/DNS settings.
8. LTE announce is complete in response header, base64 profile and Happ JSON.
   DNS uses only reviewed supported categories and avoids public Google/
   Cloudflare UDP/DoH defaults; exact generated JSON is parsed in regression.
9. Browser before/after proof covers 390x844, 768x1024, 1366x768 and 1920x1080,
   with no document overflow and explicit hover/focus/disabled/loading/error/
   empty/success states. Build success alone is not visual acceptance.
10. Local full/focused tests and build pass; exact diff is reviewed and secret
    scanned; commit/push/pull/restart/public verification follow the production
    workflow. DNS global activation requires a real two-platform Wi-Fi/mobile
    client canary and rollback proof; the stage stays open if unavailable.

### Risks and rollback

- Quota double reset/access loss: store due state, use an operation lock, advance
  only after authoritative reset; restore the pre-migration DB and previous
  Remnawave counters on mismatch.
- Trial duplication: deterministic entitlement/identity lookup before create;
  never replace a live UUID/subscription URL.
- DNS regression: retain the previous routing payload, parse all formats, perform
  client canary before global default, revert payload without identity changes.
- Legal/SMTP incompleteness: do not claim live acceptance while operator fields
  are placeholders or SMTP delivery/DNS authentication is unverified.
- Existing owner change `webapp_dist/assets/payments/sbp.svg` remains excluded.

### Verification matrix

| Area | Local gate | Production gate |
|---|---|---|
| Anniversary quota | month-end/leap/renew/retry tests | aggregate due preview + one safe reset/reconciliation |
| Trial/onboarding | adapter/idempotency/bot flow tests | backup, preview/backfill, one new-user flow |
| Promo/payments | quote/race/fulfillment tests | one safe promo payment path |
| Email/site | auth tests, metadata/build/browser | custom SMTP delivery and public route/assets |
| Subscription/DNS | decoded header/profile/JSON tests | stable URL fetch + two-platform network canary |
| Responsive UI | four viewport before/after + keyboard/states | authenticated public cabinet four-view pass |

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
- LTE is a real 0/45/115 GB quota resetting on the shared calendar-month
  anniversary; no `x10` customer model.
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

- Current implementation regression suite: `102 passed`; Python compile succeeds.
- Browser-first integration found and fixed a standalone `/app` first-render crash
  caused by an empty promo quote comparing equal to an empty tariff selection.
- Post-fix responsive measurements at 390x844, 768x1024, 1366x768 and
  1920x1080 all report `scrollWidth == innerWidth`; mobile and desktop screenshots
  were captured. The tariff sheet exposes `126 ₽ / мес` above
  `6 месяцев · всего 759 ₽`, shows one Standard heading, and has no crypto/Stars.
- Promo browser states verified: disabled empty Apply, invalid `INVALID` error,
  valid DEV canary `START10` discount and recalculated payment total.
- `/app/admin` DEV route renders the actual admin console with
  `noindex,nofollow`; production routes remain `/app` customer and `/admin` admin.
- Production preflight reports schema v56 and usable Remnawave credentials in the
  protected runtime file, but no registered Remnawave server row and no explicit
  write mode. The implementation now supports the protected authority as a
  fallback while requiring `REMNAWAVE_WRITE_MODE=production` before any write.
- Runtime commits `804ae98`, `237d182`, and `83c3298` were pushed and
  fast-forwarded on Poland. Pre-existing production files and the local owner
  change `webapp_dist/assets/payments/sbp.svg` were preserved.
- Restricted backup `backups/release-20260826T120238Z-onboarding-v57` was created
  before migration/config changes. Schema v57 applied explicitly; exact trial
  backfill preview/apply was `2 -> provisioned 2, failed 0 -> preview 0`, with a
  separate SQLite backup. A live operational warning exposed an unclosed trial
  HTTP client; follow-up commit `83c3298` fixes it and the full suite is again
  `102 passed`.
- Protected Remnawave config now has explicit write mode `production`. Both
  `arcvpn-subscription.service` and `arcvpn-bot.service` are active, health is
  `OK`, journal scan has no new error/exception/traceback/unclosed entries, and
  production HEAD is `83c3298`.
- Public `/app/app-icon.svg` and `/app/site.webmanifest` return HTTP 200;
  `/admin` returns `X-Robots-Tag: noindex, nofollow`. Public `/app` renders the
  standalone email login at 390x844, 768x1024, 1366x768 and 1920x1080 with no
  horizontal overflow. Public `/admin` resolves to the admin/login surface,
  no overflow at laptop width, `noindex,nofollow`, and no console errors.
- Deferred external gates: real SMTP delivery and linked-email login need the
  owner's SMTP/SPF/DKIM/DMARC setup; legal acceptance needs verified operator
  details; authenticated payment/promo and keyboard-only passes need a safe test
  identity; DNS v2 stays disabled until Wi-Fi/mobile plus two-Happ-platform canary;
  anniversary reconciliation needs a real boundary observation. Stage remains
  **in progress** and is not declared complete.

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
- Runtime commit `91ba74a` and production-schema hotfix `f6b3156` were pushed and
  fast-forwarded on Poland. The pre-existing production dirty/untracked files and
  the local owner change `webapp_dist/assets/payments/sbp.svg` were preserved.
- A pre-deploy copy of `database/vpn_bot.db` and separate operation-level SQLite
  backups were created under production `backups/release-*` with restricted modes.
- Automatic bot startup had not yet reached its migration hook after restart;
  the checked-in idempotent migration runner was invoked explicitly. Production
  then reported schema v56, 12 active products across 3 families, both services
  active, and subscription health `OK`.
- Production dry-runs found 13 active non-Standard keys and 135 inactive,
  never-paid, non-admin users with no current key. The cleanup dry-run exposed a
  production-schema mismatch before mutation; hotfix `f6b3156` removed the
  nonexistent `users.is_active` dependency and its production-shaped regression
  suite passed (`35 passed`).
- After exact confirmation and backup, 13 active keys were migrated to Standard
  without UUID or URL replacement and 135 explicitly authorized cleanup records
  were deleted. Repeated dry-runs returned `active_keys=0` and
  `eligible_users=0`.
- Public `https://panel.arccnet.space/app` returned HTTP 200 and references the
  deployed `index-DBrs44gk.js` and `index-C2adVayo.css`; public/local health was
  `OK`. The browser's previous one-time owner verification is expired, so a new
  authenticated production four-viewport visual/keyboard pass remains open.
- The native Remnawave source is deployed behind the stable ArcVPN gateway, but
  legacy fallback retirement remains gated on production source metrics and a
  zero-fallback soak. This is not yet a direct public-URL cutover.

---
