# Subscription refresh: direct primary, automatic CDN fallback

Owner decision (2026-10-02): keep `sub.arccnet.space` as the direct primary and make CDN an **automatic fallback for the same client URL**. The earlier plan to permanently point this hostname at CDN is superseded. No DNS, certificate attachment, subscription URL, UUID, or VPN route has changed.

| State | Client URL | Resolution / route | Failure behavior |
| --- | --- | --- | --- |
| Normal | `https://sub.arccnet.space/sub/<existing-id>` | Direct A record to Poland `217.60.33.38` | Existing behavior |
| Fallback candidate | The **same** URL | DNS would need to resolve to the existing Yandex CDN; CDN → Estonia HTTP:80 with Host `origin.arccnet.space` → Poland HTTPS:443 with Host/SNI `sub.arccnet.space` | Automatic switch only after independently proven mobile-restriction failure and edge success |

The current authoritative Reg.ru A record has TTL **86400 seconds (24 hours)**. A DNS switch cannot reliably rescue clients that cached the direct address, even if a monitor changes the record immediately. Server redirects cannot help when the direct host is blocked before receiving a request. No automatic client-side fallback mechanism has been verified. Therefore **do not activate DNS failover or present it as working**. A same-host solution needs a separately accepted DNS/control design and a real restricted-network client test, including the behavior of cached resolvers.

Preparation under the superseded CDN-primary plan remains available: existing CDN resource `bc8r4rihi5cxxmbj3qgs` has caching disabled, forwards cookies, and uses Estonia origin. Estonia Nginx proxies `/sub/` and prepared import routes to Poland without cache; backup `/root/arcvpn-sub-cdn-routes-before.mkj4q0ui`. An additional dual-domain certificate `arc-cert-cdn-sub` (`fpqc3jcvh6utlo7apsju`) was issued but is not attached. Its DNS challenge CNAME records remain in Reg.ru; do not delete certificates or records without lifecycle review. The active VPN certificate, origin group, and XHTTP paths remain unchanged.

Evidence: direct allowed-device GET returned HTTP 200, 50,676 bytes, private/no-store. Invalid ID through the existing CDN hostname returned 404 and private/no-store. A valid request to `cdn-de.arccnet.space` from Poland timed out before reaching Estonia, so valid edge byte parity is still **open**. CDN currently allows only GET/HEAD/OPTIONS; device-import POST is not proven. Real restricted-network refresh and automatic client recovery are also **open**.

Next decision must be an exact route/monitor/rollback table before any DNS or CDN mutation. Preserve original URLs and IDs. Do not route app, billing or device-import POST through this CDN without a verified method contract.
