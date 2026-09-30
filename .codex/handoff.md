# ArcVPN handoff — FI repeat + admin node automation plan (2026-09-29)

## Daily ordinary/LTE traffic — 2026-09-30

Production commit `ffdcfd3` adds an authenticated UTC-day Remnawave internal-squad usage split to `/admin/traffic-usage`, with cards for ordinary and LTE identities. Poland subscription service is active, and a production browser check showed nonzero data for both groups. This is product-group traffic, not a physical-server breakdown; existing table below remains cumulative. Source and tests: `bot/services/remnawave_stats.py`, `subscription_api.py`, `admin_webapp/src/pages/AdminTrafficUsage.tsx`, `tests/test_admin_traffic_today.py`. Evidence and remaining narrow-viewport check: `.codex/stages/traffic-usage-today.md`.

## Active work — React node operations, 2026-09-30

Work is in isolated `netherlands-alias` checkout at baseline d7d9ca5; the owner's dirty primary checkout and production files are untouched. React node detail now has useful tabs with existing SVG icons, hidden tab scrollbar, real agent charts/capacity and fleet-history availability. SSH preflight now requires an independently checked fingerprint and never persists the password. Read APIs and additive migrations 69–70 are local only. The full Python suite passes (301 tests), both frontend builds pass, and React browser widths 390/768/1280/1600 were inspected. Multitest worker, LatencyLab mobile adapter, Telegram integration and installation worker are **not implemented**; the owner authorized production release only once ready. LatencyLab API documentation is pending. The owner confirmed there is no test VPS now and installer testing will happen later. See `.codex/stages/current.md`. Do not run the unpinned Multitest `curl | bash` command or deploy this partial stage as a complete solution.

Latest FI original RU repeat (MSK19:29–19:31): Moscow5606Mbps/27ms,
SPB2202Mbps/24ms, NN2114Mbps/30ms, Chely1752Mbps/78ms, Tyumen519Mbps/56ms.
Upstream columns are forward sender/receiver, not two directions. This strong
repeat prevents declaring FI bad from earlier weak snapshots. Keep FI/EE peers.
Evidence: docs/operations/finland-ru-repeat-2026-09-29.md. Full terminal logs
outside Git in Temp/ArcVPN-multitest-569. Node healthy; no runtime changes.
Plan only: docs/roadmaps/admin-node-automation.md; owner wants admin workers
for IP/password provisioning and Multitest, not reliance on Codex. Existing
AdminNodes only SSH preflight; proposed durable jobs, secret vault, benchmark
terminal/history then hidden provisioning and real-tunnel publish gates.
Repository skills now cover full node onboarding (`arcvpn-add-node`) and owner-requested
Multitest benchmarking (`arcvpn-benchmark-nodes`). The dated non-secret route/CDN
snapshot is `docs/operations/node-topology-current.md`; current GET/header/key CDN
contract supersedes historical OPTIONS notes. No runtime topology changed in this
documentation stage. Admin-worker implementation still needs an owner-approved stage.

## Previous Multitest results

Owner requires Multitest for requested server speed comparisons; method in
docs/operations/server-benchmark-method.md, evidence multitest-2026-09-29.md.
Actual Multitest RU speed/IPQuality-private-IPv4/short CPU completed on active
FI, EE, Moscow, Poland. No network tuning, report upload or runtime deployment.
FI repeat: NN remains4Mbps, Moscow6431->520Mbps, SPB second receiver0 invalid.
EE around1Gbps to Moscow/SPB/NN, lower RTT; FI geobases FI/JP/IR/AE, services
AE/NL, one VPN marker. DNSBL blacklisted0 all four isn't universal clean-IP.
Skill update explicitly deferred: present full-new-node workflow proposal AFTER
tests, implement only following owner consent. No skill files changed.

## Production remains: replacement Finland + CDN GET

Runtime cc5d21d deployed on Poland. New FI151.241.137.174 is real main peer with
EE in Auto/YouTube; manual FI follows YouTube. Reciprocal Moscow SS, ordinary
Reality and public CDN GET/header EE/FI passed real HTTP from Moscow. Poland
CDN TLS still fails before XHTTP; mobile censorship gate requires owner test.
Public fin DNS updated, cert valid/renewed; old fake FI hosts disabled; no Germany.
Poland/NL now display aliases on FI; Sweden EE. GET/header/X-Session-Token on
server, panel Hosts and rendered subscriptions for all users; preserve /api-fin
rather than rewriting to /api-test. Users must refresh subscriptions. Owner
links saved outside Git in Temp ArcVPN-progressive-dev-xhttp.md, EE and FI only.
288 tests; health200, both services active. Short SPB test favors EE (15ms,
540/590Mbps vs FI22ms,169/403Mbps upload/download); do not prioritize FI higher.
Evidence/backups/open gates: `.codex/stages/finland-replacement.md`. Old FI kept
for rollback; next owner tests repaired links on affected mobile operators.

## Superseded Netherlands-only state

Runtime4d5049e adds manual Netherlands backed by Estonia, not a real NL location.
Live outbound equals EE; real tunnel exits87.251.19.197 HTTP200;286 tests passed.
Germany remains retired. Future owner request: after replacing and validating
Finland, move Netherlands to new FI and add Poland backed by it. Do not activate
on current FI: direct Moscow route still blocked. Evidence:
`.codex/stages/netherlands-alias.md`; subscription restarted, public HTTP200.

# ArcVPN handoff — admin broadcasts MVP (2026-09-29)

## Latest production incident fix

Runtime `a5efeb4`: unbound generic subscription GETs without stable HWID cannot
allocate or reactivate recovery slots. Bound device URLs and recognized clients
keep existing access. 279 tests passed, including 18 probe regression checks.
Poland pulled ff-only; subscription service restarted and active; public health
200. Three real public probes left all device rows unchanged. One verified
synthetic active slot was deactivated after a restricted DB backup; zero active
synthetic generic rows remain. @sso095 has one active INCY iPhone 14 Pro and its
public subscription returns the existing UUID. Key URLs/UUIDs are unchanged.
No rollback needed. Unrecognized unbound clients use the existing reimport
response; use explicit import for those clients. Broadcast owner test below
remains pending. Evidence: `.codex/stages/device-generic-fix.md`.

MVP runtime: `e2d3892` (with UI release `48b006f` and order guards `7e634ed`), based on `e810aae`.
Poland remains the control plane. This release preserves the latest Germany
retirement/Estonia CDN changes. Primary checkout has unrelated owner changes;
continue broadcasts in the attached managed `admin-broadcasts` worktree.

## Current behavior

`https://arccnet.space/admin/broadcasts` is the working owner-only campaign UI.
Drafts, recipient snapshots, test revisions, deliveries and reward state are
stored in SQLite (migrations 67/68). HTML and length are validated; preview is
sanitized. Tests go only to a configured Telegram admin and never grant bonuses.
Editing invalidates test; start needs the tested revision and recipient count.
Days are atomically extended once and externally synced before notification.
New shared/private campaign codes reserve order capacity atomically; private
codes are recipient-bound. Ambiguous Telegram deliveries are marked uncertain
for manual review, rather than automatically duplicated.

## Owner review / pending action

Latest UI verification: owner's “Проблема с серверами решена” is stopped,
22 deliveries out of 24. The earlier compensation draft still has 63 recipients.
Those state changes were performed outside the agent's workflow; the agent did
not send or grant rewards. Any further agent sending requires owner instruction.

## Evidence and rollback

257 baseline full-suite tests passed; 67 after latest-main rebase; 38 broadcast/
promocode tests and 2 payment-storage tests after final order guards. Admin
build, type-check and scoped Biome passed. Authenticated production browser QA
at 390x844, 768x1024, 1280x900, 1600x900 found no horizontal overflow. Screenshots
are local `.codex/evidence/broadcasts/production-*-top.png` / `*-launch.png`.
Backup: `/root/ArcVPN/backups/broadcasts-20260929-pre-mvp.sqlite3`, mode 0600.
Existing subscription UUIDs/URLs match the backup. Stop jobs before reverting
runtime commits; retain ledger and additive tables, and never blindly undo days.
See `.codex/stages/current.md` for exact deployment status and residual limits.

## Day-bonus copy correction — 2026-09-29

Runtime ee7c079 removes the automatic gift sentence from preview and Telegram;
owner authors the bonus copy. Actual reward grants are unchanged. 31 campaign
checks and admin build passed; production four-width browser check passed.
There are now two drafts: owner's outage message for 24 active subscribers and
previous compensation draft for 63. Both untested after invalidating one old
successful day test; neither started or delivered. Repeat the test before any
mass confirmation. Generic-device repair from 83976e6 is preserved.

## Draft deletion — 2026-09-29

Runtime d992578 deployed. Delete buttons in history and saved-draft editor use
explicit named confirmation. Only drafts can be soft-deleted atomically; deleted
rows are hidden, retained for recovery, and cannot be edited/tested/started.
Started/stopped/completed histories cannot be deleted. 37 focused tests, build,
Biome and four-width demo/production UI checks passed. Only subscription API
restarted; both services healthy. Agent deleted no owner draft and sent nothing.
Owner prefers no screenshot attachments in replies. Next: refresh admin to use.
