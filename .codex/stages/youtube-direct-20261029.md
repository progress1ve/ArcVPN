# YouTube route comparison — 2026-10-29

## Result and owner decision

Shortening the path did not improve measured performance. Owner explicitly rejected the slower trial: "если медленнее, то нам такое не нужно". The owner-only experimental profile is removed; existing Auto/YouTube leastLoad LT/SE and manual Lithuania routes remain. Zapret on Moscow remains enabled.

Runtime trial ca8b00cdb15f2b1adcafbe1264277d0dee878a85 was briefly published only to @progressive_dev, then reverted after the comparison and owner rejection. No UUID, URL, quota, binding, firewall, node config, or database changes.

## Compared paths

| Mode | YouTube path | Ordinary traffic | Scope |
| --- | --- | --- | --- |
| Existing | Client -> Lithuania -> Moscow zapret -> YouTube | Existing Lithuania rules | Existing production profiles |
| Trial, removed | Client -> Moscow Reality443 -> YouTube | Existing Lithuania rules | Separate owner-only JSON profile |

Existing Moscow public443/ru.arccnet.space -> HAProxy -> RU_VLESS_REALITY10443; existing owner main identity already authorized. Traffic multiplier1, noCDN/neworigin. Trial excluded global Auto/YouTube, plain share links unchanged. No private Reality key exported; protected state contained only public connection material.

## Measurement

Same public video aqz-KE-bpKQ, format298, same signed URL, same Poland test source, common Moscow egress, HTTP/1.1 over SOCKS, ABBA ordering. Zapret enabled for both. Hostname/object matched; CDN IP was not pinned. Results are server-source observations, not Beeline/owner WiFi measurements.

| Test (median) | Existing LT -> Moscow | Direct Moscow |
| --- | ---: | ---: |
| 4MiB complete range, 4 samples each | 37.26 Mbps | 14.41 Mbps |
| First byte, 4MiB samples | 301.8 ms | 467.8 ms |
| 12-second windows, 2 samples each | 3.62 Mbps | 3.29 Mbps |
| First byte, 12-second windows | 285.2 ms | 718.0 ms |

All12 requests HTTP206. All8 short ranges completed; all4 long ranges intentionally stopped at12 seconds before16MiB, not transport failures. Limited sample count, visible variation/CDN pacing prevent a universal performance claim. No measured reason to replace the existing route. Sanitized metrics: evidence/youtube-direct-20261029/final.public.json.

## Verification and cleanup

Candidate3 configurations passed Xray syntax; ordinary trace Lithuania88.216.62.135; YouTube regionRU; trial YouTube worked with Lithuania outbound deliberately disconnected. Homepage HTML sometimes remained open until bounded timeout; region content was present, so actual mediaHTTP206/bytes used for performance. Published INCY defaultJSON19, real published profile ordinaryLT and256KiBYouTubemedia206 passed. OtherLTE/noLTE JSON18/10 and plain17/9 unchanged; owner plain17 unchanged.21 focused local/production tests passed during rollout.

Removal restores ownerJSON18/plain17 and removes the experimental renderer/module/tests; other catalogs stay18/10 and17/9. Final live readback and deployment recorded in current.md. Trial disabled in protected state; rollback never requires DB restoration. Both signed media URL copies removed, all diagnostic processes/listeners stopped. Moscow zapret active+enabled. No remaining production topology mutation.
