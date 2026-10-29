# Restore direct Lithuania ingress — 2026-10-29

Owner explicitly orders direct Lithuania traffic after historical comparison. This supersedes the earlier Moscow-ingress choice. Apply globally after a real generated owner canary; no further approval required.

| Visible paths | Client hostname/port | CDN / origin | Host/SNI / inbound | Multiplier / URL impact | Failure / rollback |
| --- | --- | --- | --- | --- | --- |
| Auto and ordinary aliases, YouTube | 88.216.62.135:443 | none | lt.arccnet.space / existing LT Reality | 1; same subscription URLs and main UUIDs | Existing plain/fragment Auto, then authorized CDN24000; revert renderer only |
| AI | 88.216.62.135:8444 | none | lt.arccnet.space / existing LT WARP Reality | 1; UUID and name unchanged | Existing WARP behavior; revert renderer |
| Gaming | 88.216.62.135 UDP443 | none | lt.arccnet.space / existing LT Hysteria2 | 1; same auth/name | Existing manual profile; revert renderer |
| CDN / bypasses | cdn-de.arccnet.space:443 | existing Yandex resource / ee-origin sole LT88.216.62.135 HTTP80 | existing CDN TLS and origin Hostorigin.arccnet.space / existing LT XHTTP paths | 1; separate LTE identity and URLs unchanged | Existing behavior; no CDN mutation |

LT server-side YouTube -> Moscow95.182.120.237:2444 remains. Normal non-YouTube tunnel traffic leaves LT directly. Existing local routing DIRECT rules remain. Moscow website, return bridge and old cached ingress listeners remain running. Do not restart LT nodes or touch the friend's remnanode container.

Components: monitoring/lithuania_canary.py JSON and share-link rewrite; focused tests; topology evidence. Target controller pl-control217.60.33.38. LT node lt-cherry88.216.62.135. Current runtime before repair d6debd97 (344adf4c runtime). No DB, identity, quota, prices, flags, DNS, TLS certificate, balancing/probe/fragment parameter changes.

Acceptance: focused migration/routing tests; generated owner+nonowner+noLTE configs preserve identifiers and routing, no Moscow ingress in JSON or share links; real direct Reality tunnel, Telegram stateless response, YouTube RU egress, WARP and Hysteria traffic. Preserve CDN bytes/authorization. Then reviewed scoped commit/FFpush, Poland FFpull, subscription-only restart and fresh public/device readback.

Risk: client refresh/reconnect required; actual affected mobile/WiFi compatibility and media throughput need owner observation. CDN symptoms are separate. Rollback is a scoped renderer revert, no DB restore. Keep cached ingress available during migration.

Completed runtime `8a1b3debc653819e6ec34adea8fdc4a0fee01978`: reviewed two-file Git change, normal FFpush to main, Poland FFpull, subscription-only restart; bot and subscription active. No node/container restart or Remnawave/DB mutation.

Passed14 focused tests (Lithuania overlay and Russian-service routing). Candidate generated owner/other-LTE/no-LTE subscriptions17/17/9 profiles; exact comparison proves only ordinary endpoint addresses/ports changed. Main/LTE authorization, CDN configuration, routing, probe, fragmentation, names and flags unchanged. Both JSON and ordinary share links covered. Initial system Python lacked Flask; reran in the existing application venv successfully.

Real Xray canary on Poland using generated candidate subscription: Auto ordinary Cloudflare exitLT; YouTube homepageHTTP200/regionRU; Telegram stateless req_pq/resPQ with matching nonce0.150s; AI WARP=on and Google204; gaming Hysteria2 tunneled trace exitLT. Config files lived in protected temporary directories and were removed; temporary processes stopped. This proves protocol traffic, not real-device media throughput or ad playback.

Postpublication public HTTPS bound-device subscriptions: owner and otherLTE17profiles, noLTE9; JSON200 and v2RayTun plain200 for all, ordinary Reality/AI/Hysteria addresses88.216.62.135,8ordinary links per sample; appropriate CDN authorization retained. One initial noLTE sample used the legacy base quota column and actually had an active addon, so the check was corrected to use effective entitlements; the resulting noLTE verification passed. No entitlement changes were made. Public root/sub health and WebApp200.

Rollback remains a scoped source revert; keep Moscow cached-ingress listeners available. Owner must refresh subscriptions and reconnect; affected mobile/WiFi Telegram/media acceptance remains open. CDN path was unchanged. Documentation closeout requires FFpull only, no service restart.
