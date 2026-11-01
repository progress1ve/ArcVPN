# Owner Shorts A/B deployed — 2026-11-01

Economy, no subagents. Owner explicitly accepted three profiles with identical Sweden -> Moscow -> YouTube path: zapret on, zapret bypass, and zapret on with UDP443 rejected. Existing normal profiles, UUIDs, subscription URLs and quotas preserved. Existing direct-Moscow trial not restored.

Runtime38ed60ea committed/pushed main; Poland fast-forward pulled; only subscription service restarted, bot/API active. Root-only enabled overlay `.secrets/shorts-canary-20261101.json` expires about 11h40 after activation; missing/disabled/expired state returns original profiles. Append3 only owner2075630349. Plain URI subscriptions unchanged: chaining requires full JSON, supported existing Happ/INCY format.

## Accepted route and isolation

| Profile | Path | Control | Failure / rollback |
|---|---|---|---|
| Shorts · zapret | Existing Sweden Reality -> Moscow2446 SS -> Google | zapret retained | No silent fallback; disable owner state |
| Shorts · без zapret | Same Sweden Reality -> Moscow2445 SS -> Google | Freedom output mark0x01000000 returns before NFQUEUE, retains conntrack | Same; remove exact mark rule |
| Shorts · без QUIC | Same as zapret control | Client UDP443 blackhole before routing | Same |

Existing Sweden Host/SNI/inbound and owner authorization reused via dialerProxy; no CDN/origin changes, multiplier unchanged. YouTube domain group uses chained SS test outbound; other domains retain Sweden routing. Test SS password private, root-only state, no extra UUID. Moscow test ports accept only Sweden136.148.220.228 via scoped iptables rules; others dropped. No 2444/default Remnawave profile change. Both test egresses force IPv4 consistently to isolate zapret.

## Evidence

- Syntax on all3 generated owner Xray configs passed. Owner isolation/source preservation/chaining/QUIC rule assertions passed.
- Real same signed YouTube media, HTTP206 exact262144 bytes via each: on firstbyte305ms,total515ms; off219/335ms; noQUIC214/326ms. Single samples NOT improvement evidence, HTTP1 curl does not test QUIC. All homepage responses regionRU.
- nft bypass counter285packets; ordinary NFQUEUE rules remain, zapret and canary active. Exact bypass comment `arcvpn-shorts-canary-20261101`; NOTRACK0x40000000 untouched.
- Owner renderer21profiles including3tests; nonowner renderer unaffected. Nonowner publicJSON200/18profiles/0tests. Collector without owner's device-bound URL receives existing device-revoked/reimport notices, not actual owner JSON. Device gate untouched; live phone subscription refresh and QUIC/Shorts playback remain owner acceptance gates.
- Temporary local SOCKS processes terminated, listeners19501-19503 absent. Signed media URLs deleted local/PL/RU. Temporary local credential state deleted after private upload. Safe media results PL `/opt/arcvpn/staging/shorts-canary-gate.public.json`.

Moscow service `arcvpn-shorts-canary.service` has RuntimeMaxSec43200, Restart=no, not boot-enabled; ExecStopPost cleans exact nft rule and scoped iptables rules. Config/binary/firewall helper root-only under `/opt/arcvpn/shorts-canary-20261101/`. Runtime Xray copied from existing remnanode26.7.28, no package upgrade. Ordinary zapret remains active.

Rollback: disable owner state first, restart subscription service; stop only arcvpn-shorts-canary.service; verify exact firewall cleanup and ordinary zapret active. Scoped runtime revert/FF deployment if removing overlay code; no database restore. Existing owner device URL must remain unchanged.

Next: owner refreshes existing JSON subscription and compares 15-20 different Shorts per profile. Record pauses/failures, alternate order; no claim of eliminated startup latency until phone test. Public owner device-bound HTTP behavior not independently proven in this collector.
