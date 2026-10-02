# Subscription refresh through CDN — 2026-10-02

Owner authorized work in the signed-in Yandex console and asked to preserve its open session. Existing subscription URLs and device aliases must remain unchanged.

## Accepted route

| Client hostname | Resource | Origin | Protocol / Host / SNI | Cache | Identifier impact | Rollback |
|---|---|---|---|---|---|---|
| sub.arccnet.space | Existing CDN `bc8r4rihi5cxxmbj3qgs`, additional domain | Estonia origin HTTP:80 → Poland HTTPS:443 | CDN and browser cache disabled; cookies forwarded | None | Restore sub A record 217.60.33.38 |

Existing VPN CDN `cdn-de.arccnet.space` shares the resource and origin. Its XHTTP paths must continue working. Keep GET/HEAD subscription delivery and the other existing web/API methods, request headers, cookies and query parameters working. No public redirect can rescue a blocked initial subscription hostname, so migration requires changing that hostname's DNS after validating the new edge.

## Preparation completed

- Existing sub DNS points directly to Poland. Existing allowed-device subscription returned HTTP 200 with 12 profiles.
- Public HTTPS origin and services verified. Subscription API already emits private/no-store/no-cache headers.
- Requested managed certificate arc-cert-sub, ID fpq8qr7engd81q141cfl, for sub.arccnet.space using HTTP validation. No existing certificate covers this hostname.
- Initial public validation file returns HTTP 200 with matching content from both Poland and the owner's computer.
- HTTPS ACME webroot added on the subscription origin, so CDN HTTPS origin requests can validate the domain. nginx syntax/reload passed; post-reload HTTPS challenge returned 200. Commit 942e4a9.
- Private rollback backup: /root/arcvpn-sub-cdn-origin-before.75au43en/arcvpn-control-plane.
- Owner chose to reuse the existing CDN resource rather than create a second paid resource. The unused resource draft was not submitted.
- The existing resource has CDN/browser caching disabled, cookies forwarded, and query parameters uncached. Its origin remains `ee-origin` (Estonia HTTP:80, Host `origin.arccnet.space`). Estonia `/sub/` proxies to Poland HTTPS with verified SNI `sub.arccnet.space` and no cache.
- New managed certificate `arc-cert-cdn-sub` (`fpqc3jcvh6utlo7apsju`) covers both `cdn-de.arccnet.space` and `sub.arccnet.space`. Reg.ru CNAME validation records `_acme-challenge.cdn-de` and `_acme-challenge.sub` point to `fpqc3jcvh6utlo7apsju.cm.yandexcloud.net.`; authoritative DNS and Google public DNS have confirmed them.
- The dual-domain certificate is now **Issued**, valid through 2026-12-31; both challenges show Valid in Certificate Manager.
- Estonia's origin now covers `/sub/`, `/import/`, `/api/device/import/`, and the clean single-token route. Nginx syntax and active state passed; backup `/root/arcvpn-sub-cdn-routes-before.mkj4q0ui`. An allowed device's `/sub/` response was identical byte-for-byte between direct Poland and Estonia, both 200 with no-store. Import HTML also matched; invalid subscription remains denied.
- Current CDN allowed methods are GET, HEAD, OPTIONS. Device import requires POST. Yandex's CDN documentation says enabling POST may require support permission. Confirm POST passes through the CDN before changing `sub` DNS; a 405 is a release blocker.

## Pending gates

1. Keep both DNS challenge CNAMEs for renewal. The old issued VPN certificate remains attached until the resource edit.
2. Add `sub.arccnet.space` to the current resource and select the new dual-domain certificate in one edit. Preserve `ee-origin`, HTTP origin protocol, fixed origin Host, and VPN routes.
3. Validate edge certificates for both hostnames, real VPN tunnel and exact allowed-device subscription parity without printing identifiers or profile credentials. Invalid identifiers must remain denied and personalized content must never be shared through cache.
4. Smoke test the existing import, clean subscription route, and app/API paths that use the subscription hostname. In particular, allow and verify POST `/api/device/import/<id>` through CDN; do not cut over while it returns 405.
5. Change only sub A to the assigned CDN CNAME, preserving every other DNS record. Then verify public TLS, subscriptions and VPN again. Roll back to the old A record on failure.
6. Owner confirms refresh during actual mobile restriction. Normal-network HTTPS evidence does not establish that gate.

Browser tabs and sign-in must remain open. The old single-domain `arc-cert-sub` request is unused; do not delete it during this migration. No subscription DNS cutover has happened at this checkpoint.

Renewal reference: https://yandex.cloud/en/docs/certificate-manager/concepts/challenges
