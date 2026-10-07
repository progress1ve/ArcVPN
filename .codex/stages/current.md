# CDN Speedtest download investigation — 2026-10-07
Mode economy; no subagents/browser. Goal: identify and repair reported Ookla download failure around100Mbps in Auto/Best bypass. Scope nginx/CDN transport; preserve identities and routing. Acceptance: reproduce owner failure and verify same scenario after evidence-based repair. No production configuration changes without causal evidence.

Evidence: Estonia nginx -t PASS; existing64KB header buffers,4096worker connections,32upstreamkeepalive retained; buffering off/read+send3600s on fast/reserve. Disk2.4GBfree,RAM412MBavailable,noOOM. Today's nginx errors have no upstream timeout;54open-socket alerts coincide with04:06UTC service stop timeout/restart, not continuous download errors.
Poland canary cannot reach CDN188.72.103.4:443 (TCPconnect timeout); this is diagnostic origin reachability, not proof of owner client failure. Estonia reaches CDN404root. Existing canary picks obsolete native/api-test path; adapted ephemeral owner-only outbound using monitoring.cdn_fallbacks.apply and actualcdn-fast settings. On Estonia real CDN/TLS/XHTTP tunnel:1MB200/complete0.593sec;25MB200/complete0.924sec,27.05MB/s(~216Mbps). Temporary config600/binary removed; no credentials printed, other customers unused. No runtime edits/restarts.
Acceptance: server health/prior fix confirmed PASS; reported Ookla scenario reproduction DEFERRED; fix verification DEFERRED. Need owner network/client VPN app and Ookla target server, compare forcedmanualbypass withAuto. Do not claim fixed or conclude nginx/CDN categorically innocent. Rollback unnecessary; no production config change.

## Completed Sweden replacement, 2026-10-07
Owner accepted routing; runtime 9a8517f published and fast-forward pulled on Poland,
subscription service restarted and healthy; bot/nginx healthy, /app200. Full
acceptance/evidence/rollback .codex/stages/sweden-migration.md. Node/Reality and
YouTube tunnels, customer profile rendering and all aliases passed. Weighted
health failover runtime tested; FI physical transport absent; FI display alias on
EE immediately before Best Bypass and excluded from weights. Root-only rollback snapshots retained,
temporary canary revoked. Peak-hour/device and concurrent stress stability open;
CDN-on-Sweden deferred. Eight bypass profiles, #6/7/8 equal #5; served JSON HTTP200 verified. No unrelated owner files included. Mode economy.
