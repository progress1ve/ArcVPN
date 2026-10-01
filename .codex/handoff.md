# ArcVPN handoff — FI repeat + admin node automation plan (2026-09-29)

## Daily ordinary/LTE traffic — 2026-09-30

Follow-up commit `df20b92` fixes the period selector and per-user rows using a new authenticated Remnawave range endpoint. Cards, rows and CSV now read the selected inclusive UTC interval. Only period, ordinary/LTE selector and CSV remain in the filter bar. Production API returned distinct 1d/7d values and correctly zeroed ordinary bytes for LTE-only rows. Production browser loaded new cards/filter bar; visual interaction after switching period awaits owner check because the inspection tool timed out. See `.codex/stages/traffic-period-2026-09-30.md`.

Earlier commit `ffdcfd3` introduced UTC-day cards. The subsequent `df20b92` release replaced the table's misleading cumulative values with actual range usage. Both are product-group traffic, not a physical-server breakdown. Source and tests: `bot/services/remnawave_stats.py`, `subscription_api.py`, `admin_webapp/src/pages/AdminTrafficUsage.tsx`, `tests/test_admin_traffic_period.py`.

## Active work — React node operations, 2026-09-30

Work is in isolated `netherlands-alias` checkout; the owner's dirty primary checkout remains untouched. Owner explicitly requested deploying the current panel before LTE testing. Commit 500d55a is deployed on Poland and both services active. Estonia and Finland 1chost have the existing telemetry agent enrolled with pinned SSH keys and both write minute samples. The next UI patch filters the node list to those two plus Moscow bridge, labels One Cent Host, and changes the blocked availability API path; deploy and verify this patch. Netherlands ops access failed host verification; do not bypass it. The full Python suite passed (301 tests) before the follow-up patch; 17 focused tests and React build passed afterward. Multitest worker, LatencyLab mobile adapter, Telegram integration and installation worker are **not implemented**. The owner clarified “OTE” means LTE checks on operators. LatencyLab API-key contract is still undocumented; its browser code shows `/api/lab/vpn-key` multiscan with session cookies, not a verified key integration. The owner confirmed there is no test VPS now. See `.codex/stages/current.md`. Do not run the unpinned Multitest `curl | bash` command.

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

## Node observability and LTE checks — 2026-10-01

The live React admin has a tabbed node detail and a list restricted to Estonia
1chost, Finland 1chost and Moscow bridge. This was deployed at 14d36f6. Read-only
telemetry runs on the EE/FI nodes and the admin shows actual sampled CPU, RAM,
network and observed uptime; missing samples remain unknown. The owner clarified
that “OTE multitests” means operator-side LTE client-tunnel checks.

Official LatencyLab OpenAPI is https://latencylab.ru/openapi.yaml. Its Bearer
API-key, operator list and account quota endpoints were verified on Poland. The
new key is in `/etc/arcvpn/latencylab.key` mode 0600, outside Git. Four mobile
operators were online at verification, so an offline fifth must remain unknown.
The worker code in `monitoring/lte_operator_worker.py` checks current EE/FI owner
links in memory across all online operators, stores history, and sends Telegram
alerts after three failed cycles, recovery after two good cycles. Commit 209cca4
is deployed. The first real scan completed on both nodes: T-Mobile, MegaFon, MTS,
T2 connected; Beeline was offline at LatencyLab and is recorded unknown. The
systemd timer is active for 07/13/19 MSK, with a small random delay. No Telegram
alert fired on this healthy first cycle. No node topology or subscription URL
changes are involved. A UI correction now displays tunnel outcomes independently
from restriction evidence; its follow-up deployment and browser check are pending.
