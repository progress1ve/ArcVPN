2026-10-04 economy mode. LTE fleet audit:29activeaccounts,28positiveLTE. Four additionalEXPIRED despiteactive main(Linkholder,myrktt,pv_realestate,managerproduce);17staleLTEexpiries total. Mainidentitiesall28ACTIVEcorrectexpiry. Two custompaidorders(stethemahueni/myrktt)manual_review mainpushfailureafterDBextension; LTEprovisionaborted. Admin/referralextensionsalsoleftLTEexpirybehind. 73a4d1a+5001ccbdeployedPolandbot/subactive:existingminuteLTEusagejobnowalignsactiveunbannedsubscriptionexpiryandreactivatesonlyEXPIREDwithremainingquota;neverresetsusage/UUID/quota/squads orreactivatesDISABLED/LIMITED/exhausted/expiredlocal. pv_realestatepanelquota5->authorized45GBscopedcanonicalprovision,persist_base_quotaFalse. NativeHappall28renderfivebypassprofiles. Publicpaneloverview/payments200;custom/device/LTEaddonlabelsverified. Migration73explicitis_custom_tarifffuturecheckout;historicalcustominferredlimitdifference;oldidenticalcustomvsstandardnotprovable. Legacyuser77requested20GBthenmanualentitlement45later:notreduced. PrivatePolandbackups.secrets/lte-audit-before-20261004.jsonanddb-before-lte-audit-20261004.sqlite600.383testsPASS+14focusedafterexpired-skipfix.No browserownerinstruction. Devicebans/future-onlyimportalertsstillpending.

2026-10-03 stethemahueni LTE restoredACTIVE fromEXPIRED preservingUUID/quota15/used; renderer12profiles/five bypass. ecb0553pricing deployed:custom5/10choices inlanding/cabinet/API;1device80/90rub/month.1device0cap80avoidspriceinversion.369tests/SveltebuildPASS;no browserownerinstruction. Subscriptionrefreshneeded.

2026-10-03 friends repair f7529c0 deployed Poland both servicesactive. Root403=panel.arccnet.space missing create/delete origin allowlist; real public panelPOST now200. Halfday0.5=12h,5/10GB quotas actualpanel verified; UI10GB creationQR passed, bothQAcleaned. Presence connection recency3min inclprobes,lastactivity,20sec cache/30sec refresh; providerunknown. created_id last-list-row bug fixed.361tests/buildPASS/4viewports nooverflow. Device blocking+future-only TG device alerts remain pending.

2026-10-02 user cards: Telegram IDs hidden incl fallback names; actual payments replace hardcoded0balance; highlighted recent CDN badge Обход глушилок. Owner live+browser probe-only,200rub; previous canary could produce3min highlight. Fresh friend creation1day/3devices/15GB succeeded+QAcleanup; previous403 root cause not reproduced, diagnostic and session-error UI added.359tests/buildPASS/4widths no overflow. See current stage.

2026-10-02 CDN classification deployed57acf88 (+38d0780,d47d714,e18ab00). Exclusive probe sub:18080 enabled in7balanced profiles after actual EE/FI/CDN204 tunnels. Numeric panel identity mapping including legacy main identities verified; node RAM collector fresh/available; UI marks recent non-probe connection starts, probe-only muted, legacy/stale unknown.359tests/buildPASS, browser4widths no overflow. Owner refresh needed; arbitrary app probes/long existing connections not definitive ongoing-use evidence. Device ban + future-only TG device alerts still pending .codex/stages/device-bans-pending.md. Full evidence current stage.

2026-10-02 numeric form fix deployed2c44653: empty drafts preserved until submit, friend1day/device and promo10rub/percent browser verified,4widths/build/23tests PASS. LTE badge now activity including probes; generated CDN is fallback-only, background cdn-fast health probes prevent claiming actual user route from Remnawave onlineAt. No route changes. See current stage for exact gates.

## Completed delivery evidence — 2026-10-02
Runtime efc5183 deployed to Poland main with ff-only pull; bot/subscription active. Includes b493ba6, 655be95, b3ecd48 (actual ArcAdminRoot route), preserving remote Estonia-only monitor changes. Full suite 354 PASS; both frontend builds PASS. Production guest: main/LTE identities provisioned, exact expiry/device/quota applied; fresh Happ GET JSON 200 contains both identities; excess HWID receives no usable identities after enforcing managed slots; expired root404; scoped panel cleanup deleted both identities. All test guests removed. Existing nonguest UUIDs/tokens unchanged against post-deploy/pre-canary snapshot; no pre-migration snapshot was made in this run.
Browser PASS: Friends form, selection/disabled state/back navigation; online users LTE badges and normal rows; widths390/768/1280/1600 no horizontal overflow. QR live bearer not captured; cabinet reserve not browser-tested in authenticated customer session. CDN restricted-network first import and real mobile tunnel remain DEFERRED to owner phone test. No automatic primary URL failover claimed. Rollback: revert feature runtime commits, revoke guests before stopping cleanup; preserve migration audit rows. Next: owner first-import through reserve CDN under mobile restrictions.
Owner acceptance 2026-10-02 supersedes previous single-URL restriction: separately imported CDN reserve is allowed as a secondary bot/cabinet action. Admin temporary friend access has selectable days/devices/LTE allowance and QR, auto-expiry plus scoped panel cleanup. Direct primary subscription URLs and all existing identities remain unchanged. Current stage `.codex/stages/current.md`; deployment evidence pending below.

2026-10-02: LTE operator worker now monitors and notifies Estonia only (/api-test). Finland removed from scheduled checks and required link set; notification allowlist drops stale Finland alert/recovery events. Three failures / two recoveries and timer cadence preserved. Fast/reserve variant-specific scheduled monitoring remains separate follow-up. Focused tests: 7 passed. Deployment evidence: .codex/stages/estonia-alerts-2026-10-02.md.

Subscription single-URL decision 2026-10-02: owner rejected the separately imported `cdn-de.arccnet.space/sub/<same-id>` reserve released in `db76df0`; the bot, API, and Svelte presentation must be rolled back. Required user experience is one unchanged `https://sub.arccnet.space/sub/<id>` URL for both addition and refresh in Happ and INCY, without Provider ID or a second subscription. Existing DNS remains direct to Poland. Same-URL automatic fallback needs an always-reachable entry or client support; low-TTL DNS failover is delayed and not a reliable instant fallback. No DNS/CDN route changes are authorized until a precise route and tradeoff contract is accepted. Details `.codex/stages/current.md` and `docs/operations/subscription-cdn-refresh-2026-10-02.md`.

2026-10-02 nginx upload repair deployed (script4e9dff3): EE CDN origin single header limit increased8KiB->64KiB (4buffers), upstream keepalive32 on10002/10003, worker_connections4096. Before32KiB headerHTTP400;afterHTTP404 from Xray as expected. nginx-t/reload/active/listeners PASS. Same private24000/10ms CDN tunnel: GoogleHTTP2040.735s,64KiB uploadHTTP2000.717s,1MiB uploadHTTP2003.155s (~2.66Mbps end-to-end). This fixes a demonstrated origin header rejection, not proof all Ookla/mobile failures solved. Backup/root/arcvpn-nginx-upload-before.8g0neyr8 (site+nginx.conf). No subscription/client/cloud settings changed. Owner retest same link; restricted-mode/long upload gate open.

Ordered CDN fallbacks deployed f792ba4 on Poland, live flag=1. Owner keeps five bypass profiles (Best=1). Auto/Best/2/3 ordinary->CDN4096/1;4/5 ordinary->CDN4096/1->reserve24000/10 X-Request-Trace. Both directions CDN Estonia. Public allowed owner device verified HTTP200/12profiles/6fast/2reserve;51 focused tests passed; forced terminal fallback realHTTP204. Reserve standalone failed once and64KiB upload timed out; actual restricted-mode/video acceptance remains open. Evidence and rollback docs/operations/cdn-ordered-fallbacks-2026-10-01.md. Owner dirty primary preserved.

Owner-authorized real local Xray CDN benchmarks completed: 4096/1ms split best observed17.42–19.22Mbps and2/2 complete downloads; 2048/10ms15.27 with failures,8192/1ms19.09 with failures, shared4096/1ms no complete download. All1MiB upload tests failed, direct control accepted. No production changes/global publication. Evidence docs/operations/cdn-tunnel-comparison-2026-10-01.md; private rawresults/URIs/configs outsideGit Temp/ArcVPN-CDN-benchmark-20261001. Restricted-mode/mobile/video gate and upload defect remain open; local source measurements not fleet capacity.

Estonia full-CDN canary applied fd64ccb; owner switched cloud away from slower Moscow. EE_OWNER_DIRECT_XHTTP local10002 /api-ee-direct authorized owner-only, scoped YouTube DIRECT; no published Host/profile added. EE nginx HTTP80 new path added with syntax/reload/listener passed, backup /root/arcvpn-ee-owner-direct-before.tmwrba3o; panel backup .secrets/owner-estonia-youtube-before.json. Private link Temp/ArcVPN-full-CDN-Estonia-direct-YouTube-test-2026-10-01.txt, both directions CDN4096/1ms padding100-200. Owner instructed cloud origin EE87.251.19.197 HTTP, Hostorigin.arccnet.space; actual cloud state/real tunnel/video/whitelist acceptance owner-pending. No network tests run. FI/MSK previous canaries preserved for rollback, active route depends on owner cloud setting.

Full-CDN owner canary comparison ready: owner cloud origin Moscow; added only Moscow TLS /api-fin-direct → FI80 owner inbound10002, preserving old routes. Nginx syntax/reload passed; backup /root/arcvpn-msk-owner-direct-before.awlqhuak. Private link Temp/ArcVPN-full-CDN-direct-YouTube-Moscow-test-2026-10-01.txt now has both upload/download through CDN, TLS H2/H1.1, direct FI YouTube egress. Same link can compare FI cloud origin without server edits. Previous direct-download canary video worked in owner client/all5LL, but whitelist-state not established. No network tests; new full-CDN speed/video gate owner-pending. No published profiles changed.

Owner-only direct YouTube canary applied (e6f1665). Private FI_OWNER_DIRECT_XHTTP port10002 path/api-fin-direct authorized through owner-only squad; no published Host or subscription profile added. Scoped geosite:youtube DIRECT precedes existing YOUTUBE_RU; all old inbound routes preserved. FI nginx80 and8444 new path → same10002; syntax/reload/listeners passed. Panel rollback private /root/ArcVPN/.secrets/owner-direct-youtube-before.json; nginx backup /root/arcvpn-owner-direct-nginx-before.cyXB1I. URI outside Git Temp/ArcVPN-Finland-direct-YouTube-owner-test-2026-10-01.txt. Owner traffic/YouTube gate pending; no network tests run.

Private direct-download experiment: commit ea3e1dc pushed/pulled Poland; FI dedicated nginx TLS8444 → same local10001 /api-fin installed with valid fin certificate. Syntax/reload and listener passed; backup /root/arcvpn-direct-download-before.I4LbdN. Owner prohibited network tests; real traffic, client import and restriction gates remain OPEN. Private URI outside Git in Temp/ArcVPN-CDN-upload-Finland-direct-download-2026-10-01.txt. Upload CDN4096/1ms padding100-200, download FI151.241.137.174:8444 TLS SNI fin.arccnet.space /api-fin, Hostcdn-de. No subscription edits. Owner returned cloud origin to FI after Moscow was slower; decreased padding and separate same-CDN download did not fix video. Rollback remove only dedicated /etc/nginx/conf.d/arcvpn-direct-download.conf and nginx-t/reload.

## Current production — 2026-10-01

Admin runtime 0c20ff8 deployed on Poland. Overview is compact: EE/FI online, observed aggregate headroom, main/LTE traffic7/30days/history and node/CDN health. Moscow is hidden from the node list but operational bridges remain. Capacity uses 7day paired panel-user/network and agentCPU/RAM observations, minimum12points/2hours, resource ceilings70%CPU/80%RAM/30%network reserve; no manual Mbps/person selector. Browser verified15online and28estimated additional; this is an observational estimate, not certified capacity. Collector excludes heavy benchmark periods. All339 tests and React build passed;390/768/1280/1600 no page overflow. Effective12-profile Happ order matches owner's subscription; auto, YouTube and five bypasses are real balancers. No new policy published.

Owner switched existing CDN group ee-origin to Finland151.241.137.174, protocolHTTP and Hostorigin.arccnet.space (confirmed screenshots). FI nginx now accepts old Host, /api-fin remains local10001; new /api-test relays to EE87.251.19.197:80. Moscow removed only from CDN path, reciprocal Shadowsocks/YouTube untouched. Pinned FI SSH key; nginx syntax/reload/active passed, backup/root/arcvpn-fi-cdn-before.Aj3YxP. Real local Windows Xray client publicCDN: FI HTTP204/1.918s, EE viaFI HTTP204/1.263s. Poland-source TLS still fails as before; it is not universal outage evidence. Private owner FI VLESS link exported outsideGit to Temp/ArcVPN-CDN-Finland-direct-2026-10-01.txt. Owner LTE restricted-mode and speed comparison pending; no claim Moscow caused slowdown. Rollbackcloudgroup to prior Moscow HTTPSorigin, restore FI backup if necessary.

Historical traffic now uses Remnawave analytics since earliest local account2026-04-11 (not resettable current-cycle counters): main1645594433811bytes,LTE234201401110bytes at verification. Scoped fleet diagnostic ignores private bridge listeners and retirednodes; serviceResultsuccess, publicadmin200. Remaining: installer/vault and testVPS gate (owner deferred), Multitest6/9/servicegeolocation, true stress-tested comfortable capacity, realTGfailure/recovery, final ownerCDNspeed/whitelistgate.

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
changes are involved. The UI correction at 3190ec5 was deployed and verified in
the authenticated production browser: four "VPN подключился" cards, Beeline
"Нет данных", Moscow-localized times and an explicit unconfirmed restriction
notice. An actual restricted/whitelist window and Telegram failure/recovery
delivery have not been observed; do not claim those gates passed.
The final LTE UI adds one manual "Проверить все сети" action for both EE/FI
and all currently online operators. Its admin POST uses the existing role,
an exact Origin allowlist, a 15-minute cooldown, and a fixed systemd unit;
the page polls the history for the new batch. Commit 64c0725 is deployed;
the authenticated production browser showed the button and the expected
cooldown message without submitting another provider job. Unauthenticated
POST returned 403. Build and full Python suite (313 passed) are complete.

## Owner UI correction — 2026-10-01

Current isolated checkout adds downloaded operator brand SVGs (sources.json), live provider offline/region metadata, CDN terminology, visible back-to-node-list, hides unobserved uptime bins, prioritizes people in Load and shows sanitized TCP port facts in logs instead of empty failed diagnostics. Python suite: 315 passed; React build passed. Broad owner acceptance remains open: balancer/subscription editor, LTE/bridge service creation, original Multitest queue/history and calibrated comfortable-user capacity are not implemented. Provider currently reports only Orel; do not invent regions or restricted-period proof. Primary owner checkout untouched.

## Subscription refresh correction — 2026-10-02

Owner chose direct Poland as primary and CDN as **automatic fallback on the same `sub.arccnet.space` URL**. The preceding CDN-primary cutover plan is superseded. No `sub` DNS change or CDN certificate swap occurred. Reg.ru authoritative A TTL is 86400 seconds, so a DNS switch alone cannot promptly recover clients with cached answers. A valid CDN-path request from Poland timed out before Estonia; actual fallback remains unverified. Existing issued dual-domain certificate and prepared Estonia proxy routes remain unused; do not remove them without lifecycle review. See `docs/operations/subscription-cdn-refresh-2026-10-02.md`. Next: design and accept a same-host failover mechanism with real restricted-network evidence before any DNS/CDN mutation.
Follow-up feasibility: Reg.ru's minimum TTL is 3600 seconds, and the owner declined a stable front door in place of direct Poland entry. Thus prompt same-URL automatic failover cannot be delivered with the current stack. Existing CDN allows only GET/HEAD/OPTIONS, whereas device import requires POST. Poland's outbound connection to two CDN edge IPs timed out before the Estonia origin, so valid edge parity remains unproven. No DNS/CDN settings changed. A slower DNS failover would require explicit acceptance of the cache delay and all-path validation.
2026-10-02 owner Wi-Fi diagnosis: current manual Estonia contains TCP proxy/direct/block, zero balancers or XHTTP. Read-only two owner panel samples onlineAt17:32/17:33UTC: normal lifetime bytes +24,492,971; LTE +5,160. Small LTE increment is consistent with CDN health probes, not proof every byte is a probe. No evidence manual Estonia diverted to CDN; actual phone routing cannot be proven from aggregated identity counters. Screenshot still old LTE/CDN bypass label; latest frontend has Activity LTE/CDN and probe caveat. No topology/runtime mutation in this diagnostic turn.
