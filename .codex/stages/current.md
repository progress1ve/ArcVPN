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
