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

### November 13 follow-up

Fresh published Reality profiles passed HTTP 200 and MTProto on NL, SE and LT from the same Moscow diagnostic client. The LT exit was the physical Cherry server. Tested 3 MiB ranges around the middle of one public Telegram video, at a fixed media IPv4. Fresh curl requests, alternating order on the same Royale connection profile, no local media cache. Validated HTTP 206, exact Content-Range, length and matching bytes across routes. The CDN cache remained uncontrolled.

| Route | Valid ranges | Median first byte | Median after first byte | Median total |
|---|---:|---:|---:|---:|
| NL with M3T | 8/8 | 0.730 s | 0.759 s | 1.510 s |
| NL with previous rules | 8/8 | 0.743 s | 0.784 s | 1.517 s |
| SE with M3T | 4/4 | 0.630 s | 0.843 s | 1.471 s |
| LT with M3T | 4/4 | 0.803 s | 0.945 s | 1.742 s |

The slowest NL range took 2.502 s, including 1.745 s after first byte. The same range with previous rules took 2.192 s, including 1.406 s after first byte. The paired NL data did not show a repeatable gain from routing alone in this series. This is a public HTTPS range proxy for seeking, with a separate MTProto handshake check. Native INCY/Beeline playback remains open. Keep the current runtime and collect TCP retransmission and RTT evidence in both directions during a slow native seek before choosing another transport parameter.

### Owner-only Reality fingerprint comparison

Economy. The owner requested new test candidates. Add two 24-hour JSON profiles cloned from ordinary Netherlands. Same Royale address, TCP443, Reality SNI and authorization, Vision, DNS and M3T routing. Only the client fingerprint differs from the Firefox control. Use Chrome for the community hypothesis and Safari as a second Xray-supported fingerprint. No topology, CDN or billing changes.

Acceptance: verify precisely two owner profiles on the bound public subscription, equivalent to ordinary NL after normalizing display name and fingerprint. Verify other cohorts and legacy links, then smoke-test a real tunnel with both candidates using a remote Xray client. Owner runs the INCY comparison. Rollback moves the protected expiry file out of its active path.

Closeout: runtime 03b98c84 deployed on Poland. Restarted the subscription API only. Owner JSON 20 profiles, LTE 18, no-LTE 10. Both clones differ only in name and fingerprint, and existing JSON profiles, plain/base64 links and routing headers match the baseline. Both published candidates passed Xray syntax, HTTPS 200 with Royale egress, and fresh Telegram MTProto from Moscow. Local checks covered owner scope, expiry, absent state and duplicate prevention. The protected `.secrets/owner-reality-fingerprints.json` expires November 14 at 14:51 MSK. INCY playback and fingerprint support on the owner's client build remain for the owner to compare.

### Royale node card and complete LTE operator checks

Economy. Owner requests Royale in the normal node list and checks for every delivered XHTTP variant. Remnawave lists Royale connected on 89.248.65.203; the admin filter uses its inventory and CDN origin address 45.141.202.248. Match the same node across both addresses, preserving the established detail URL and probe history. Show the live Remnawave card and its CDN shortcut.

| Delivered variant | Client endpoint | Current path |
|---|---|---|
| 4096/7 + XMUX | Existing CDN domain | /api-lt-test-4096 |
| 24000/10 | Existing CDN domain | /api-lt-test-24000 |
| 32768/10 | Existing CDN domain | /api-lt-32768 |
| 65536/60–75 | Existing CDN domain | /api-lt-65536 |
| 24000/10 · IP | Existing CDN edge IP | /api-lt-test-24000 |

Use the delivered TLS, Host, XHTTP extras and LTE identity. Keep the existing origin, authorization, cadence and cooldown. A batch records each operator and variant independently, with unknown for missing/offline provider results. In the existing responsive cards, show the number of successful variants and each result. Keep the latest complete batch and previous history. Verify real LatencyLab batch, live node card, CDN detail at mobile/tablet/desktop/wide, and unchanged user-facing subscription configuration. Rollback revert runtime and admin bundle. No Remnawave or CDN mutations.
