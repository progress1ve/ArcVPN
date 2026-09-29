# ArcVPN node and CDN topology — verified snapshot, 2026-09-29

This is a non-secret operational snapshot, not a substitute for checking current code, Remnawave, DNS and live tunnels before any change. Historical entries in `AI_CONTEXT.md` can describe retired routes. The production/control plane is Poland `pl-control` (`217.60.33.38`); Germany control plane and Germany exit are retired. Credentials live only in the encrypted local vault referenced by `.codex/server-inventory.toml`, never in Git.

## Active exits and routes

- Estonia: `ee.arccnet.space` (`87.251.19.197`), own TCP Reality :443 and own keys.
- Finland: `fin.arccnet.space` (`151.241.137.174`), real Finnish VPS, own TCP Reality :443 and own keys. This replaced the previous Finnish VPS; never restore that IP from old notes.
- Finland and Estonia are peers in AutoSelect and YouTube without ads. CDN is only an emergency AutoSelect fallback. The ordinary Finland profile follows YouTube without ads in the subscription order. Do not promote either exit on one ping or one speed test.
- Moscow `85.198.101.79`: scoped Shadowsocks :2443 bridge to each exit; return bridge :2444 from Finland/Estonia for YouTube without ads. A country-labelled profile is not necessarily a separate exit: Poland/Netherlands aliases may use Finland, Sweden may use Estonia. Verify current bindings and avoid counting aliases as extra balancer weight.
- Legacy Germany fallbacks may remain in code, but the VPS was returned. Do not re-enable a dead exit or remove active users' existing links without a migration plan.

## CDN bypass

The existing public CDN resource remains `cdn-de.arccnet.space:443` with TLS/SNI, despite its legacy name. Its `ee-origin` origin group routes via Moscow HTTPS `origin.arccnet.space`, then to the selected exit. Estonia uses `/api-test`; Finland uses `/api-fin`. Exit nginx :80 forwards to local Xray :10001. Confirm the actual origin-group, Host, SNI and certificate in the CDN panel before modifying it.

The current replacement for the broken OPTIONS scheme is XHTTP `packet-up` with `uplinkHTTPMethod: GET`, `uplinkDataPlacement: header`, and `uplinkDataKey: X-Session-Token`. The three fields must match in both Remnawave config profile `xhttpSettings` and Host `xhttpExtraParams`, and appear in the rendered VLESS `extra`. Preserve other working padding and transport parameters. Old `OPTIONS -> POST` guidance is superseded; do not silently restore it. Keep existing subscription URL, UUID, quota and traffic multiplier 1; clients refresh subscriptions after a change. The Firefox TLS fingerprint has been used as an edge compatibility fallback; Chrome failed in that particular test, not universally.

## Evidence and remaining gate

The release evidence is in `.codex/stages/finland-replacement.md` and the implementation in `scripts/repair_cdn_get.py` and `subscription_api.py`: Finland Reality exit and both directions of Moscow bridge were tested; public Estonia/Finland CDN GET/header returned HTTP 204 from Moscow; 288 tests and Poland service/public health passed at release. A Poland-source public CDN TLS probe failed with curl 35, and success on affected mobile operators was not established. Do not call the bypass universally working without fresh operator/client tests.

For a new node, write an explicit route/balancer/profile table and get owner approval for product topology, then canary the real tunnel and rendered subscription before production promotion. Follow `.codex/references/node-config-contract.md` and `$arcvpn-add-node`.
