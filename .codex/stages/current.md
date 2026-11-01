# Active: Auto CDN leastPing reserve — 2026-11-01

Economy,no subagents. Owner explicitly accepts LT+SE leastLoad primary and CDN leastPing reserve. Existing device hostnames, CDN origins, Host/SNI/inbounds/paths/UUIDs/URLs and traffic multipliers unchanged. Only Auto full JSON with existing authorized cdn-safe gains copied authorized Best bypass XHTTP pool; no-entitlement and manual/YouTube profiles unchanged. Existing primary tags/leastLoad settings retained. Loopback reserve dispatch before general rules prevents recursive primary selection. All candidates probed on existing Best bypass HTTP204 endpoint,15s/2/5s. CDN all-down fallback existing cdn-safe, no direct escape. Risk: endpoint outage creates false failures, phone censorship unverified. Gates: syntax, source/authorization/other-profile preservation, real normal/primary-failed/CDN-failed/recovery traffic; staged review+commit+push+FFpull+subscriptionrestart only after gate. Rollback scoped module hook revert. No nodes/firewall changes.

# Production YouTube zapret disabled — 2026-11-01

Economy,no subagents. Owner phone test confirmed no-zapret much better, noQUIC no benefit; explicitly authorized all-user rollout. Moscow95.182.120.237 arcvpn-youtube-zapret.service disabled+inactive,NFQUEUE table removed; LT/SE->RU2444 paths unchanged,QUIC allowed. Remnawave/UUID/URL/quota untouched,no node restart. Owner test overlay disabled, isolated canary stopped and exact firewall rules/ports removed. Ordinary Sweden/Lithuania real same-media206/262144bytes+YouTubeRU passed from Poland; bot/APIactive,health200. No universal speed guarantee. Root-only before /root/arcvpn-youtube-no-zapret-before-20261101; rollback systemctl enable --now arcvpn-youtube-zapret.service. Stage .codex/stages/youtube-production-no-zapret-20261101.md. Owner refreshes subscription and selects ordinary profile. Old entries below historical.

# Active: production YouTube without zapret — 2026-11-01

Owner authorized rollout after successful phone test. Contract/evidence: youtube-production-no-zapret-20261101.md. Existing SE/LT->RU2444 path retained, QUIC enabled. Acceptance: real media via both ordinary profiles, NFQUEUE removed, rollback saved.

# Owner Shorts canary published — 2026-11-01

Economy,no subagents. Owner accepted Sweden->Moscow three-way test. Runtime38ed60ea pushed/main and PolandFFpulled;subscription restarted,bot/APIactive. Three owner-only JSON profiles appended: Shorts zapret / без zapret / без QUIC. Existing identities, URLs, ordinary routes and quotas preserved. Root-only owner state expires ~11h40; Moscow isolated canary service RuntimeMaxSec12h,no restart/no boot enable. RU2445 bypass mark0x01000000,2446 zapret; source allow Sweden only; exact scoped firewall cleanup ExecStopPost. All3 syntax and real same-media206/262144bytes+YouTubeRU passed; QUIC runtime/phone improvement unverified. Owner renderer21, nonowner public18/no tests. Owner public collector missing device-bound URL receives existing device gate; do not alter device protection. Update existing JSON subscription, compare15-20Shorts/profile. Evidence/rollback .codex/stages/shorts-canary-20261101.md. Signed URLs/temp credential files/diagnostic listeners cleaned. Disable owner state and stop only canary to rollback; ordinary zapret remains active.

# Closed — Admin Sweden and Online, 2026-10-30

Economy,no subagents. Runtime82ef7846307cb77338e9ffdbbae84f8b31392f2c pushed/PolandFFpulled, subscription restarted;bot/APIactive. SwedenHostUp now visible with flag/traffic/statistics link and included in3-node summaries. Cabinet-version card replaced by unique customerOnline (3-minute observation,60srefresh); mobile includesOnline. Missing telemetry--,known0 preserved. Shared overviewcache10s,failedrequestsretry. No node/catalog/billing/identity/URL/DB/permission changes;oldassetsretained.

PASSED:5frontendtests,TS/build, candidate+deployed11browserchecks each(home/nodes360/768/1280/1600,Swedenstatsnavigation,0/errorfixtures),noJSerrors/overflow;root/app/admin/health/new+oldassets200,anonymousoverview403. Source/buildstage review done. NativeCUAunavailableURLrecognition;isolatedtestbrowserverifiedactualUI. Temporaryauthenticatedstate removed afterlogout. ExistingVitewarnings; unrelatedlegacybackendtestenvironment/staleexpectation noted inreport.

Evidence/report:.codex/stages/admin-sweden-online-20261030.md and evidence/admin-sweden-online-20261030/. Rollbackscopedruntimebuildrevert/FFpull;noDBrestore. Next:ownerreloadsadmin. DocumentationcloseoutFFpull,noextra restart.
