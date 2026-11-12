# Shared M3T RU-Direct client routing

Economy. Owner authorized shared rollout on 2026-11-12. Use the routing object from M3T 98daeede14d5f88fc9c1c350ede83f9f1f0e9e75, previously checked through the owner-only Reality profile.

| Client path | Accepted behavior |
|---|---|
| Ordinary NL, LT, SE and other working profiles | Replace the common direct-split rules with M3T. Keep local networks direct, existing endpoints, DNS, transport, credentials and Telegram/TikTok rules. LT/SE YouTube still goes from client to NL. |
| Auto and YouTube profile | Same M3T split, existing balancers and precedence. Auto remains leastLoad with its authorized CDN fallback. |
| Best Bypass and manual CDN | Same M3T split, with existing dedicated CDN routes and authorization. |
| No-LTE and exhausted users | Same M3T split in working JSON profiles, no new LTE authorization. |
| Legacy plain/base64 and emergency access | Existing wire format, routing header and access policy. Share links and legacy Happ headers cannot represent the complete ordered M3T rule set. |

Components: subscription JSON renderer, protected pinned M3T data on Poland. No node, CDN, DNS, billing or control-plane topology changes. Remove the duplicate owner trial from shared rollout. Missing or invalid policy restores the existing split. Rollback remove the protected shared policy and restart subscription API.

Acceptance: confirm pinned policy equals audited upstream and owner trial, verify public owner/LTE/no-LTE output, exact non-routing equality and rule precedence, existing URLs and legacy wire output, Xray config and real traffic. Beeline/INCY Telegram seek remains an on-device performance check.

## Closeout

- Runtime 0a103473 fast-forward deployed on Poland. Restarted only the subscription API. Bot and subscription active, public health HTTP 200. The mode-0600 policy matches upstream and the owner trial digest.
- Public bound owner/LTE/no-LTE returned 18/18/10 working JSON profiles. The exact ordered M3T rules replaced the old common rules in each, with local exceptions ahead of M3T. Compared all remaining routing rules, balancers, endpoints, identities, DNS and observatory settings to the pre-release snapshot. Plain/base64 share links and routing headers matched.
- Local compile and 27 focused tests passed. One catalog-order test also failed on the parent commit with the local Finland configuration and was excluded from the focused rerun.
- Moscow loopback Xray validation passed for NL, SE, Auto with and without LTE, and manual CDN. NL kept Royale egress, Telegram MTProto and t.me in the tunnel, and VK/Yandex direct. SE MTProto passed. Paired CDN old/new both returned HTTP 204. Paired LT old/new both timed out through the same proxy outbound. No Moscow forwarding service was deployed.
- Rollback: move .secrets/m3t-ru-direct.json out of its active path and restart only the subscription API. Previous stage history remains in 931433d7. Next check is same-video seek in INCY on the owner's SIM after subscription refresh.
