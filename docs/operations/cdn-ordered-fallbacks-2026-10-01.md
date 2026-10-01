# Ordered CDN fallbacks — 2026-10-01

Owner approved preserving five bypass profiles: Best bypass occupies slot 1.
Runtime commit f792ba4 is deployed on Poland; cdn_ordered_fallbacks_live=1.

## Published contract

- Auto, Best bypass, bypass 2/3: ordinary nodes -> CDN 4096 bytes / 1 ms.
- Bypass 4/5: ordinary nodes -> CDN 4096 bytes / 1 ms -> reserve CDN 24000 bytes / 10 ms.
- Fast: Estonia /api-ee-direct, GET/header X-Session-Token, padding 100-200, separate download through the same CDN.
- Reserve: Estonia /api-ee-reserve, GET/header X-Request-Trace, padding 100-1000, shared CDN download; serverMaxHeaderBytes 65536.
- Existing identities, subscription URLs, manual locations and YouTube profile preserved. LTE entitlement remains required. No extra profile 1 created.
- Availability probes drive fallback selection; this does not detect every video degradation or migrate established connections.

## Evidence

51 focused tests passed; Python compile and four local Xray configuration checks passed.
Real fast tunnel returned HTTP 204 in 2.397 seconds. With ordinary nodes and fast CDN deliberately disabled in a private local client, the actual reserve chain returned HTTP 204 in 0.773 seconds.
Standalone reserve connection failed once and its 64 KiB upload timed out. Large upload reliability and real restricted-mode operator/video acceptance remain open; chat-recommended parameters are not certified by these checks.
After deployment, the existing allowed owner device subscription returned HTTP 200 with 12 profiles, six fast CDN outbounds and two reserve outbounds. Both control-plane services are active.
Private test configurations/results stay outside Git in Temp/ArcVPN-ordered-cdn-check.

## Server changes and rollback

Estonia localhost inbound 10003 and nginx /api-ee-reserve added; scoped YouTube DIRECT precedes the existing YouTube bridge rule. Existing LTE squad is authorized for fast and reserve inbounds. Nginx syntax/reload and listener checks passed.
Private panel backup: /root/ArcVPN/.secrets/ordered-cdn-reserve-before.json.
Estonia nginx backup: /root/arcvpn-cdn-reserve-nginx-before.j50l5o_w.
First rollback: set cdn_ordered_fallbacks_live=0 and restart only arcvpn-subscription.service. Keep server inbounds until cached client configurations have aged out. Restore scoped backups only after checking subsequent changes.
Next acceptance: owner refreshes subscription and tests video and connectivity during actual mobile restrictions.
