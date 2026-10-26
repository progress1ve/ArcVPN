# Stage: Best bypass CDN-only — 2026-10-26

Status: completed and deployed2026-10-26. Owner accepted only CDN selector changes and rejected competitor transport parameters. Economy; no subagents.

## Scope and route contract

Only 🇪🇺 Лучший обход changes. Ordinary AutoSelect/YouTube/manual locations and bypasses #1–#8 retain behavior, names, order, authorization and URLs. No DNS/resource/provider/billing change. Existing own LTE identity is reused, never competitor credentials.

| Profile | Client hostname / Host / TLS SNI | CDN resource / group | Active / backup origin | Inbound / path | Multiplier / URL | Failure / rollback |
|---|---|---|---|---|---|---|
| Best bypass | cdn-de.arccnet.space:443 | existing bc8r4rihi5cxxmbj3qgs / ee-origin | Estonia87.251.19.197 HTTP80, Host origin.arccnet.space / none | existing EE CDN10012,10013,10015 / /api-se-test-4096, /api-se-test-24000, /api-se-32768 | 1 / unchanged | CDN-only leastLoad, CDN24000 final fallback; revert renderer |
| Other profiles | unchanged | unchanged | unchanged | unchanged | unchanged | unchanged |

Best baseline4096/7+XMUX,24000/10,32768/10 with their existing transport settings. Competitor524288/150 and feature flag completely removed. Balancer leastLoad expected2/maxRTT800ms/baselines200,400ms/tolerance0.05; probes30s/3samples/2s retaining destination. RU/private direct and explicit block rules retained. No ordinary Reality or unrestricted direct failure fallback. All candidates share one CDN/origin.

## Acceptance and rollback

Components monitoring/cdn_fallbacks.py and tests only; no origin/nginx/Remnawave/DNS/authorization changes. Existing URLs, user identities and LTE entitlement preserved. Tests cover weighted-loopback removal, CDN-only routing, retained direct/block rules, no-entitlement stays closed, other profiles unchanged. Verify fresh actual subscription and real tunneled request, restart subscription only after commit/push/FFpull. Rollback renderer commit with customer data retained. Mobile censorship cannot be reproduced here and remains hardware gate.

## Evidence

Production base6c6ecb1639dedcf1b0a79280a1380f4526519bd7 imported via incremental Git bundle (local GitHub TLS fetch unavailable). Branch codex/best-bypass-cdn-only. Production tracked tree unchanged and owner files preserved.
Live EE nginx1.18.0, origin.arccnet.space /etc/nginx/conf.d/estonia-cdn.conf buffers4x128KiB and existing ports10012–15; default server4x64KiB;10016 not listening. Moscow chunked-header48KB probe returns empty400;700KB returns nginx Header Too Large. Rejecting layer not isolated; bounded admission checks are not tunnel/speed evidence. Poland direct CDN requests time out.
22 focused tests passed using existing primary virtualenv; compile and staged diff/whitespace checks passed. Reviewed local408f2b20386e0ba03a75c6bb49e961fb0e9892ee and published runtimebfe5e7d7471393e08685739521f25523a2a2dbef have identical treee087916b714c0ec99a5254901e3606c55cc0ceb7. Guarded GitHub main update, Poland git pull --ff-only, subscription service restart; subscription and bot active. No bot restart, DB flag, identity, origin or Remnawave change.

Acceptance PASS: actual fresh owner subscription17profiles; other16 identical before/after; Best only three authorized XHTTP CDN candidates, no ordinary Reality/weighted loopbacks, CDN24000 final fallback. Public subscription HTTP200/17profiles/BestCDNonly and publichealth200. Real Moscow Xray client normal selection and forced-failed primary selector both returned tunneled204 and Cloudflare trace exit87.251.19.197. Standalone canary lacked geosite assets, so geo-specific direct rules were omitted only in private transport test; delivered split routing is retained and covered by focused tests. Temporary private canary configs cleaned; no messages or quota changes.

Residual risk: all variants share one domain/edge/origin; real restricted mobile operator experience remains an owner hardware check. No speed improvement claim. Rollback not used; revert renderer to prior6c6ecb16 behavior through normal release without touching user data.

Next: users refresh subscriptions to receive the updated Best bypass.
