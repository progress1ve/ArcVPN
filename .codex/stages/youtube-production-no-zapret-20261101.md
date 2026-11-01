# Production YouTube without zapret — accepted 2026-11-01

Economy,no subagents. Owner reports markedly better Shorts on isolated no-zapret control, QUIC rejection no benefit, explicitly authorizes production rollout for everyone. Use node/server-ops/stage/closeout. No topology or public identity changes: disable processing on existing Moscow YouTube egress only; preserve QUIC.

| Visible path | Host/CDN/origin/SNI/inbound | Target behavior | Multiplier/URL | Failure/rollback |
|---|---|---|---|---|
| Lithuania and Auto selecting Lithuania -> RU2444 -> YouTube | Existing LT/Reality or CDN authorization, origin, Host/SNI unchanged | Existing RU egress without NFQUEUE/zapret; TCP+UDP retained | Unchanged | If real media fails, enable/start previous zapret unit |
| Sweden and Auto selecting Sweden; YouTube/SE-based profiles -> RU2444 -> YouTube | Existing SE hostname/Reality/CDN/origin/Host/SNI/inbound unchanged | Same | Unchanged | Same |

Acceptance: preserve Remnawave configuration and UUIDs; service disabled+inactive and NFQUEUE table absent after application; existing ordinary LT and SE full generated profiles pass real YouTube media HTTP206 exact range and RU region; bot/subscription active. Disable/remove temporary test delivery, stop only isolated canary before deleting queue table. No node restart. Owner actual Shorts outcome already supports no-zapret choice, but universal user speed cannot be guaranteed. Risk: future filtering may require restarting saved zapret; immediate rollback retained. No new purchases.

Implementation/evidence pending. Back up unit, queue settings and firewall state root-only before change. Signed URLs private and removed at closeout.

## Complete
Moscow zapret disabled+inactive, NFQUEUE table absent; isolated canary stopped first, its exact firewall rules/listeners removed. Existing RU2444 stays listening, UDP/QUIC not rejected. Root-only before snapshot /root/arcvpn-youtube-no-zapret-before-20261101. Rollback: systemctl enable --now arcvpn-youtube-zapret.service. No node/Remnawave config or identity changes; no node restart. Owner overlay disabled through existing hot-read protected state, original18 profiles restored. Controller app code unchanged.

Real published ordinary generated profiles from Poland: Sweden media206 exact262144bytes firstbyte252.5ms total400.4ms; Lithuania206 exact262144 firstbyte280.9ms total481.6ms; both homepageYouTubeRU. Single HTTP1 samples validate access, not universal latency guarantee/actual QUIC throughput. Owner already confirmed isolated no-zapret Shorts markedly better; QUIC block offered no improvement. Actual post-rollout phone comparison remains observation, not reason to delay authorized rollout. Safe result /opt/arcvpn/staging/youtube-production-no-zapret.public.json. Diagnostic SOCKS processes stopped, signed URLs removed local/PL/RU. API/bot active, health200.

Accepted rollout complete. Next owner switches from retired test profile to ordinary Sweden/Lithuania/Auto, refreshes subscription to hide tests. Future censorship/access regressions: restore previous zapret service and verify media, without identity/topology changes.
