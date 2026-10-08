# WARP DNS repair — 2026-10-08
Scope: restore DNS for existing AI profile, same se.arccnet.space:8444 / Reality / WARP exit / multiplier1; no CDN, subscription URL or identity change. Existing UDP53 hits BLOCK, reproduced client DNS timeout; Google/Gemini/Wikipedia HTTPS200 through actual VLESS/WARP connection.
Repair: only WARP inbound UDP53 -> DNS outbound rewriting to TCP1.1.1.1:53 chained through WARP SOCKS40000. Other UDP still blocked; Hysteria/ordinary routes unchanged. This restores intended profile behavior within owner repair request.
Acceptance: actual client UDP DNS google.com response, Google/Gemini/Wikipedia HTTPS, WARP exit still on; inbound identity unchanged. Rollback: root-only sweden-warp-before-dns-fix.json profile snapshot.
Evidence pending. No subagents; economy.
