# ArcVPN current handoff

Updated: 2026-08-26. This file is current state, not a diary.

## Authority and topology

- Production/control plane: Poland `217.60.33.38`.
- Remnawave owns active subscription delivery; preserve existing URLs and UUIDs.
- Main DHost nodes: Germany and Netherlands. Product LTE allowance is now modeled
  independently (0/45/115 GB on the user's shared calendar-month anniversary); do not restore the old customer
  `x10` model.
- Canada was dropped. Vyrex canary was cancelled. Finland was retired from public delivery on 2026-08-24 and must not be reintroduced implicitly.

## Current product state

- Onboarding/billing/quota/WebApp runtime is deployed through `83c3298` on Poland.
  Production schema is v57; 20 users have calendar anchors, the due-reset preview
  was zero at deployment, and the old first-of-month reset is disabled.
- Growth/billing/LTE runtime is deployed through `f6b3156`: Economy, Standard and
  Family have 1/3/6/12-month products; trials are durable Standard entitlements;
  campaign attribution, configurable bonuses, promo activation, independent LTE,
  two-step bot purchase UI, and the WebApp family/period flow are implemented.
- Production schema is v56. Thirteen active keys were migrated to Standard without
  changing UUIDs/public subscription URLs. The explicitly authorized inactive
  never-paid cleanup deleted 135 users after dry-run and separate backups; both
  post-operation previews returned zero.
- Subscription assembly is hybrid by design: Remnawave is the authoritative
  share-link source while ArcVPN remains the stable URL/device/announce/Happ
  compatibility gateway. Legacy generation is an observable fallback and must
  remain until production source metrics demonstrate a zero-fallback soak.
- Trial provisioning now creates/reuses one unlimited-main Standard Remnawave
  identity plus a separate 5-GiB LTE identity. Exact
  production backfill provisioned 2 missing trials after a separate backup;
  repeated preview is zero. Protected Remnawave config has the explicit
  `production` write gate; secrets remain outside Git.
- `/` and `/app` are the standalone customer login/cabinet; `/admin` is the
  separate noindex admin surface. Promo validation/revalidation, one-time email
  code consumption, calendar reset fields, legal-consent versioning, full LTE
  announce, favicon and manifest are deployed. Crypto and Stars are absent from
  customer payment UI/routers.
- Login/branding/tariff follow-up is deployed at `33fad1e`: the supplied white
  Arc mark is used by the app/manifest, standalone login offers Telegram plus
  email with centered composition, tariff copy explicitly states LTE allowance
  and device count without emoji, the promo input no longer draws a rectangular
  focus highlight, and admin password cookies persist for 30 days.
- LTE identity isolation is deployed through `36db815` (runtime layout commit
  `662e8bb`) with schema v58. Fourteen active main identities are unlimited and
  remain on the four-inbound main squad; fourteen separate LTE identities are
  limited to the two reviewed XHTTP inbounds and 0/45/115 GiB entitlement.
  Scheduler reconciliation mirrors LTE Remnawave usage into WebApp/header state.
  Public URLs and main UUIDs are unchanged.
- Customer/LTE follow-up is deployed through `d71af08`. Happ delivery is exactly:
  AutoSelect, Netherlands VLESS/Hysteria2, Germany VLESS/Hysteria2, then five
  `🇪🇺 Обход глушилок #1..#5` rows. LTE #1-#3 are main least-load profiles with
  LTE XHTTP fallback; #4-#5 are direct LTE profiles. Main/LTE credential crossover is
  rejected and covered by credential-safe production verification. Finland is
  hidden from subscriptions and admin surfaces; disconnected Remnawave records
  remain intentionally undeleted.
- Three active legacy trials were reconciled after a separate backup: all now
  have unlimited main traffic, exactly 5 GiB LTE and a separate LTE identity.
  DNS v2 is enabled only for Telegram ID `2075630349`; the global profile remains
  legacy pending the owner's short Wi-Fi/LTE canary.
- Purchase UI now defaults to SBP, vertically centers the wide flow, and all tariff
  descriptions/customer cabinet surfaces state unlimited main traffic plus a
  separate LTE allowance. `panel.arccnet.space` serves admin only (`/app` is 404).
  Apex customer-domain nginx/metadata support is committed but not activated:
  `arccnet.space` still has no A record or certificate.
- Self-hosted SMTP on Poland is currently infeasible: no MTA is installed and
  outbound TCP/25 is blocked. Use a relay SMTP, or first obtain provider unblock,
  PTR/rDNS and DNS records; do not claim email delivery before that gate.
- Whole-admin operations redesign is deployed at runtime commit `9c77b67831f163605678c9b476d5c3b72741e349`; production evidence is recorded in `.codex/stages/current.md` and its docs follow-up `b0458b95b8bde59deae4fd093afff5d54f07605f`.
- All 11 owner sections passed authenticated production composition/overflow checks at mobile, tablet, desktop, and wide viewports. Capability-aware navigation/RBAC, honest state machines, role management, truthful Schemes/Nodes/Backups language, and immediate verified subscription-panel synchronization are implemented.
- The stage remains **in progress**, not closed: a real keyboard-only activation pass, one explicitly authorized production Support reply, and a designated safe disabled Remnawave identity for live revoke confirmation are still pending. Do not infer permission to mutate a real user or send a Support message.
- The non-operational Schemes editor and its graph dependency were removed in `d111e11efa5f86738e54fc6e464fabe3e2dc9bb6`. Axottle-only infrastructure features without ArcVPN backend contracts remain explicitly deferred/rejected in the current stage matrix.
- Frontend changes require live browser inspection at four viewport classes, not only code/tests.
- Node configuration facts live in `.codex/references/node-config-contract.md`.
- Non-secret server topology lives in `.codex/server-inventory.toml`; active Poland/Germany/Netherlands credentials are local DPAPI entries managed by `scripts/ops/server-vault.ps1`.
- Use `$arcvpn-node-ops` for node, Remnawave, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, or certificate work.

## Next recommended stage

Provide production SMTP credentials and verified operator/legal details, then run
a real linked-email delivery/login and authenticated promo/payment pass. Execute
the DNS v2 client canary on Wi-Fi/mobile and at least two Happ platforms before
enabling `ARCVPN_DNS_PROFILE=v2`. Reconcile one real user's local/Remnawave/WebApp
normal and LTE usage at their anniversary, run a real Standard-user LTE
exhaustion/main-survival canary, and complete keyboard-only production acceptance.
Do not claim the stage complete while these gates remain open.

## Starting a new chat

Read `AGENTS.md`, this file, `.codex/project-index.md`, and `.codex/orchestrator.toml`. Use the stage skill for non-trivial work. Search `AI_CONTEXT.md` only when a named historical fact is missing.
