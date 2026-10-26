# Stage: Best bypass CDN-only — 2026-10-26

Status: owner explicitly accepted CDN-only Best bypass and rejected competitor transport parameters on2026-10-26. Implementing only selection changes. Economy; no subagents.

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
22 focused tests passed using the existing primary checkout virtualenv (default Python lacked Flask); compile and staged diff/whitespace checks passed. Local reviewable commit on codex/best-bypass-cdn-only; not pushed/published. No deployment or candidate flag mutation.

Next: deploy accepted CDN-only selector and verify.
