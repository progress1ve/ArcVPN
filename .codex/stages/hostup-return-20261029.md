# HostUp return — 2026-10-29

Economy, no subagents. Owner explicitly requests restoring HostUp, Auto and YouTube leastLoad between Sweden/Lithuania, Estonia/Netherlands/AI/Games on Sweden, a separate Sweden immediately after YouTube and before Lithuania, and Lithuania Multitest. No new approval inferred from documents; these are direct owner instructions. Preserve all customer UUIDs, subscription/device URLs, quotas and paid LTE separation.

## Accepted route contract

| Client profile | Entry / transport | Backend / YouTube | Selection / fallback | Public impact / rollback |
| --- | --- | --- | --- | --- |
| Auto | direct LT88.216.62.135:443 and SE136.148.220.228:443, RealityFirefox | Ordinary exits selected LT/SE; YouTube -> Moscow95.182.120.237:2444 | leastLoadexpected2/maxRTT3s/baseline1s/tolerance0.2; retained LTfragment candidate; authorized CDN24000 last; noLTE retries LTfragment | Existing URL/UUID/name; disable hostup-return state and restart API |
| YouTube without ads | Same LT/SE Reality | Both nodes use existing Moscow SS2444 outbound | Same leastLoad; no CDN authorization added | Same URL/UUID/name; state rollback |
| Sweden | directSE443/SNIse.arccnet.space | SE / YouTube Moscow | Standalone ordinary | New visible profile after YouTube, before LT; state rollback |
| Lithuania | directLT443/SNIlt.arccnet.space | LT / YouTube Moscow | Existing ordinary | Unchanged |
| Estonia / Netherlands | directSE443/SNIse.arccnet.space | SE / YouTube Moscow | Display aliases, not geographic exits | Existing names/UUIDs retained; state rollback |
| AI | SE8444/Reality | SE WARP proxy40000 | Existing separate WARP profile | Existing Swedish name/flag; state rollback |
| Gaming | SEUDP443/Hysteria2/SNIse.arccnet.space | SE ordinary | Existing separate gaming profile | Existing Swedish name/flag/auth; state rollback |
| CDN / bypasses | Existing cdn-de.arccnet.space and /api-lt paths | Existing LT origin | Unchanged paid LTE identity, transport and quota | No CDN mutation |

All multipliers1; no new CDN/origin groups. Existing customer Reality identity reused on already authorized SE inbound. No fixed61/39 weighting. Health30s/3samples/5s retained to avoid false fragmented-path rejection. Only client renderer changed, no stack change.

## Recovery and verification

HostUp rebooted after owner recovered provider service. SSH/RemnaNode22600 alive but panel node still disabled and443 refused. Existing node enabled through panel; connected and443 reachable. Protected before metadata PL`.secrets/hostup-enable-before-20261029.json`. Existing SE config YOUTUBE_RU replaced with exact current LT Moscow outbound, preserving secrets on controller only. Main squads containing LT ordinary inbound extended with existing SE ordinary/WARP/Hysteria inbound IDs; no user UUID or quota changed. Before snapshot PL`.secrets/hostup-return-before-20261029.json`. Moscow UFW allowed only136.148.220.228->2444; previously onlyEE/LT had access. Reverse that exact UFW rule for infrastructure rollback, retaining LT allowances.

Actual owner-authorized SE standalone tunnel: trace136.148.220.228/SE. Initial YouTube timed out due missing new-Moscow firewall allowance; after scoped allowance full YouTube page200/regionRU. Four candidate real gates: Auto with both LT endpoints synthetically refused -> SE, YouTube profile forcedSE -> SE; both general tracesSE and YouTubeRU. AI tracewarp=on; gaming real Hysteria traceSE. All18 generated profiles pass Xray26.7.28 syntax with existing geodata. Temporary loopback configs/processes removed. This proves HTTP routing/protocols, not affected-operator censorship or absence of ads in actual video.

14focused tests pass locally and on production baseline. Reviewed staged scoped runtime changes; commits c52223fc/1c5bab40/78e97314 pushed main and PolandFFpulled. Only subscription service restarted; bot/API active. Root-only state`.secrets/hostup-return-20261029.json` enabled after actual candidate gates. JSON and plain delivery match; owner/otherLTE/noLTE public bound-device fetches all200, JSON18/18/10 and plain17/17/9. Order Auto/YouTube/Sweden/LT correct, both composite profilesleastLoad, SE/EE/NL/AI/Games endpointsSE. No customer messages, charges, node restart or unrelated container change.

## Multitest

Lithuania completed network-focused Multitest components: IPRegion, Russian iPerf and single-thread10s sysbench; no disk/Geekbench stress or automatic report upload. Upstream Multitestv2 reviewed, existing dependencies reused. Original RU run completed118s: table reports Moscow1037.0/1050.8Mbps17ms, SPb1064.0/1085.8Mbps38ms, NN1032.5/1056.4Mbps34ms, Chelyabinsk980.3/1002.3Mbps44ms, Tyumen437.6/447.2Mbps44ms. Inspected source: its Download/Upload labels are actually sender/receiver of ONE LT->RU transfer, not two independent directions. Report useful approximate LT->RU throughput1Gbps Moscow/SPb and0.44GbpsTyumen; do not mislabel it download+upload. IPRegion responding primary databases100%LT. Sysbench719.11events/s, p95latency1.89ms in first10s; second validCPUrun698.97events/s. An attempted bounded network repeat used3s process timeout with5s transfer and produced incomplete receive counters0; exclude that entire network repeat from speed acceptance. No zero-download claim. Independent real-R reverse probes follow separately. Remote raw log `/root/arcvpn-benchmarks/lithuania-multitest-20261029.log`. No benchmark processes remain. These are server endpoint measurements, not affected-client speed or all Multitest menu modules.

Additional healthy leastLoad live samples12connections each: AutoLT8/SE4, YouTubeLT4/SE8. Statistical samples prove both backends exercised, not a promised fixed split. Both existing owner/nonowner public subscription formats verified after final runtime78e97314 publication. Ad-free video playback remains owner-device acceptance; observed YouTube regionRU only. All requested profile and route changes deployed;14focused tests and18Xray syntax gates pass. Documentation closeout only follows, no runtime restart required.

Rollback: turn state enabled=false and restart subscription; previous LT delivery returns without DB restore. Narrowly restore SE profile/squads from protected snapshot only if needed; disable SE and remove exact Moscow firewall rule after clients refresh. Keep LT and CDN unaffected. Residual: shared client probe schedule, cold-start/transient CDN behavior, client refresh required, provider bandwidth allowance and real-device playback remain external gates.

Independent reverse iperf-R gates: Moscow->Lithuania877.4Mbps, SaintPetersburg->Lithuania862.5Mbps,5seconds/4streams; confirms true reverse direction separately from mislabeled source table.
