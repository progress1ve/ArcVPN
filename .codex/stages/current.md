# YouTube videoplayback routing — 2026-09-27

Goal: restore YouTube video playback on Windows through ArcVPN JSON subscriptions in INCY and the ArcVPN client.

Non-goals: no node, DNS, certificate, public URL, UUID, payment, or topology changes; no modification of owner-untracked Windows-client sources.

Components: `subscription_api.py` JSON-profile routing and focused routing tests. Russian-domain and private/reserved-address direct routes remain. Explicit YouTube/Googlevideo proxy domains precede direct rules; remove broad `geoip:ru` IP-only direct shortcut, because a Russian-hosted Googlevideo CDN IP cannot be distinguished from a Russian service when only an IP is supplied. Other IPs fall through to the existing proxy/balancer.

Acceptance: in every JSON profile, YouTube/Googlevideo domains use the existing proxy/balancer before Russian-domain direct rules; no `geoip:ru` appears in JSON direct-IP rule; private/reserved IP and Russian-domain rules remain; profile count/order/fallback unchanged; local tests pass; production service/public endpoint healthy. Real PC playback remains a user verification gate, not inferred from HTTP health.

Risk: Russian destinations addressed only by IP now use VPN. Domain-based Russian routing remains direct. Rollback: revert scoped runtime commit, pull fast-forward on Poland, restart only `arcvpn-subscription.service`.

Verification: focused routing assertions; Python suite; staged diff; production Git/service/public endpoint; user playback in INCY and ArcVPN client after profile refresh.

Closeout: `e80bd3e` pushed to `main` and pulled fast-forward on Poland. Only `arcvpn-subscription.service` restarted; it is active. Focused routing tests: 5 passed. Full suite: 228 passed, one existing datetime deprecation warning. Staged diff check passed. Public landing and panel endpoints return HTTP 200. No real browser/video playback was performed; owner should refresh the subscription in INCY and ArcVPN client and test one YouTube video. If playback still fails, capture only the request error/status and inspect client routing logs before another production change. Rollback not needed so far.
