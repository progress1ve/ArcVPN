# Subscription refresh through CDN — 2026-10-02

Owner authorized work in the signed-in Yandex console and asked to preserve its open session. Existing subscription URLs and device aliases must remain unchanged.

## Accepted route

| Client hostname | Resource | Origin | Protocol / Host / SNI | Cache | Identifier impact | Rollback |
|---|---|---|---|---|---|---|
| sub.arccnet.space | New dedicated Yandex CDN | 217.60.33.38 | HTTPS / sub.arccnet.space / sub.arccnet.space | Disabled, including browser cache; cookies forwarded | None | Restore sub A record 217.60.33.38 |

Existing VPN CDN cdn-de.arccnet.space stays unchanged. Keep GET/HEAD subscription delivery and the other existing web/API methods, request headers, cookies and query parameters working. No public redirect can rescue a blocked initial subscription hostname, so migration requires changing that hostname's DNS after validating the new edge.

## Preparation completed

- Existing sub DNS points directly to Poland. Existing allowed-device subscription returned HTTP 200 with 12 profiles.
- Public HTTPS origin and services verified. Subscription API already emits private/no-store/no-cache headers.
- Requested managed certificate arc-cert-sub, ID fpq8qr7engd81q141cfl, for sub.arccnet.space using HTTP validation. No existing certificate covers this hostname.
- Initial public validation file returns HTTP 200 with matching content from both Poland and the owner's computer.
- HTTPS ACME webroot added on the subscription origin, so CDN HTTPS origin requests can validate the domain. nginx syntax/reload passed; post-reload HTTPS challenge returned 200. Commit 942e4a9.
- Private rollback backup: /root/arcvpn-sub-cdn-origin-before.75au43en/arcvpn-control-plane.
- CDN creation draft: numeric Poland origin, HTTPS, manual SNI and Host, sub hostname; CDN/browser caching, cookie ignoring and large-file segmentation disabled. Do not submit with arc-cert-de: it covers only cdn-de and was used during initial form preparation. Select issued arc-cert-sub before creation.

## Pending gates

1. Certificate status Issued, with renewal configured. Static HTTP challenge files alone are not durable renewal; use the documented validation redirect or permanent DNS challenge delegation.
2. Owner cost confirmation: console estimates 150 RUB/month plus metered traffic. Do not create the paid resource before approval.
3. Access to Reg.ru DNS (ns1/ns2.reg.ru), requested from owner. Do not change sub DNS before CDN acceptance.
4. Validate edge certificate and exact existing allowed-device subscription parity without printing identifiers or profile credentials. Invalid identifiers must remain denied and personalized content must never be shared through cache.
5. Smoke test existing web/app/API behavior, including allowed methods and session cookies. Then change only sub A to the assigned CNAME, preserving every other record.
6. Owner confirms refresh during actual mobile restriction. Normal-network HTTPS evidence does not establish that gate.

Browser tabs and sign-in must remain open. CDN creation is incomplete and no DNS cutover has happened at this checkpoint.

Renewal reference: https://yandex.cloud/en/docs/certificate-manager/concepts/challenges
