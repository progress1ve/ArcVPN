# Royale Netherlands production rollout

Economy. Scope and route contract authorized by owner on 2026-11-06. Poland remains control plane. Current Royale owner path works; current main squad lacks Royale, current CDN origin is Lithuania.

| Client path | Endpoint and route | Authorization and failure / rollback |
|---|---|---|
| Netherlands, after YouTube before Sweden | nl.arccnet.space:443 / Reality SNI nl.arccnet.space / NL_ROYALE_OWNER / local NL exit | Existing main UUID, factor 1; retire duplicate Swedish-backed NL alias in renderer. Disable global delivery to restore old catalog and owner-only path. |
| Sweden | Existing SE Reality and server routing | Existing main UUID and separate row. |
| Auto | Existing LT direct/fragment and NL Reality, leastPing; existing CDN pool only as reserve | No LTE entitlement added. Existing LT-fragment fallback for accounts without CDN. |
| Lithuania | Existing LT Reality for ordinary VPN traffic; client YouTube domains to NL Reality, fail closed on NL outage | Preserve existing local split routing for Russian/private services. JSON clients receive split rule; plain share links cannot encode multiple outbounds. |
| YouTube without ads | Replace Sweden with NL direct exit; retain LT and its existing server route | Existing main UUID, no added LTE fallback; retained LT fallback. |
| CDN/Auto reserve/legacy clients | cdn-de.arccnet.space:443 / existing Yandex resource bc8r4rihi5cxxmbj3qgs / group ee-origin 48160100662656097 / HTTP80 Host origin.arccnet.space -> Royale local XHTTP, preserving all current and legacy paths and subscription proxy | Existing LTE UUID and quota, factor 1, URLs/TLS unchanged. Keep LT origin operational for rollback. Confirm direct-origin tunnels and bound subscription delivery before switch, then repeat against public edge and verify NL egress before moving monitoring. |

Components: main/LTE Remnawave squads and node, persistent main-squad sync setting, subscription JSON/plain renderer, nginx, Yandex origin group, admin node inventory/operator worker. No billing, identity, DNS or public URL migrations. Risks: sync could undo a non-declarative change; cached clients require existing LT/SE listeners; CDN propagation can vary by edge; actual device restrictions and ads need device observation.

Acceptance: verify persistent membership and main identity through real non-owner LTE/no-LTE client traffic, order and exactly one NL in JSON/plain/base64, Auto failover with appropriate authorization, LT general vs NL YouTube route, direct NL YouTube without RU. Check all live origin paths, subscription proxy and rollback. Report independent completion if Cloud console access is blocked.
## Evidence and outstanding gate

- Passed shared profiles, order, no alias duplicate, expected main UUID and independent LTE entitlement. Public bound owner and other LTE subscriptions each 18 JSON profiles, no-LTE 10. JSON, plain and base64 all fetched with HTTP200. Xray passed ordinary LT and Royale exit checks on all three. YouTube returned HTTP204 via the Lithuania client's `youtube-nl` rule with the LT outbound deliberately disconnected. The YouTube profile's Royale candidate also passed direct NL exit and YouTube. Sweden remains separate.
- Passed Auto primary selection and authorized CDN failover. From Moscow, disabling all LT/NL transports and one CDN candidate still returned HTTP200 with the existing Lithuanian CDN exit. Four delivered public CDN variants returned HTTP200 and Lithuania egress. The 65536 variant timed out on the first isolated probe and passed on the rerun.
- Passed main squad readback and scheduled sync. Preserve the active 18 preexisting squad bindings plus Royale in the sync configuration. The prior config referenced two removed inbounds and a retired Albania inbound. The current owner-only squad and exception are retained. Main-only sample was denied by the Royale CDN even when explicitly supplying its main UUID.
- Passed direct origin preflight. Royale nginx responds on HTTP80 with Host origin.arccnet.space. All seven local XHTTP paths plus their seven legacy aliases tunneled to HTTPS with Royale egress. The bound subscription proxy returned HTTP200. LT origin and its config remain available. Private rollback snapshots on Poland under .secrets/royale-main-before-20261106.json and .secrets/royale-cdn-before-20261106.json. Royale nginx can disable only the arcvpn-royale-cdn vhost and reload.
- Passed RoyaleHosting admin data readback through the admin overview handler against live Remnawave and local DB. Admin browser rendering deferred because the browser connector could not establish the current URL.
- Deployment: 32 focused tests and py_compile passed, staged diff reviewed, runtime bd2f01ad pushed to main, Poland fast-forward pulled, subscription service restarted. Bot/API active and public health HTTP200. Global renderer is controlled by the existing private Royale state; clear only global_enabled to restore owner-only delivery. Cached NL profiles can continue using the inbound until the main binding is removed.
- Deferred CDN group switch and operator monitoring. At Moscow CDN edge, fresh LT marker HTTP200 and NL marker HTTP404. Browser cannot access Yandex Cloud because URL enforcement stopped the session. In Cloud CDN, edit ee-origin (48160100662656097), replace the active 88.216.62.135 source with 45.141.202.248, preserving HTTP and Host origin.arccnet.space. To roll back, restore 88.216.62.135. After propagation verify marker and fresh real tunnels across the public edge with Royale exit, then move operator worker and admin evidence to NL. Leave operator accounting on LT until public exit is verified.

## Cutover follow-up

Owner reports replacing the active Yandex origin with Royale. Prepare admin and scheduled operator changes during propagation. Keep the runtime origin label on Lithuania until a fresh public CDN marker and real Moscow-source tunnels confirm Royale. The existing origin group, transport, client labels, XHTTP URLs and credentials remain the contract. Verify the existing admin node data and operator panel binding on mobile/tablet/desktop/wide when browser access is available. No layout or interaction changes. After the gate, activate Royale attribution, check worker configuration and first operator batch, and record the rollback: restore LT in Yandex and clear the confirmed flag.

### Cutover verification

- Owner saved Yandex group update. Moscow public marker first reported Royale 15:02 MSK and six consecutive probes reached Royale without reaching LT by 15:08 MSK. Intermittent timeouts were observed during mixed-origin propagation. Seven canonical nginx XHTTP locations were aligned with the legacy aliases for upstream Host, streaming headers and no-store. `nginx -t` and reload passed. Pre-change nginx snapshot remains `/root/arcvpn-royale-cdn-canonical-before-20261106.conf` on Royale.
- Real public TLS XHTTP tests from Moscow produced HTTP200 and 45.141.202.248 on all seven canonical paths and seven aliases across the full run and targeted retries. The canonical reserve and legacy 4096 paths needed separate retries. Temporary status-only nginx diagnostic logs and config removed after the test. All four delivered variants passed again as one group. With LT/NL and one CDN candidate disabled, Auto fell back to an authorized CDN candidate with Royale exit. The bound subscription via the public CDN returned HTTP200; after cutover owner/LTE/no-LTE public JSON/plain/base64 and real Reality/YouTube passed again.
- Admin/operator runtime `bd8e545a`: 25 focused tests, py_compile, TypeScript/Vite build, staged review, push, Poland fast-forward pull and subscription-only restart. Public health, admin entry and new/previous entry assets HTTP200. New asset matched production SHA256. Browser reached the public login; authenticated admin rendering was not exercised. Admin handler data confirmed Royale and all four active XHTTP inbounds.
- Switched the protected confirmation flag and ran the existing 24000/10 operator job. The timer remains active. First NL batch recorded Beeline, MegaFon and T-Mobile OK; MTS and T2 failed with Yandex control reachable and Google control failing. Restriction state unconfirmed. Last LT batch also failed MTS and failed MegaFon instead of T2. One batch per origin is not comparative coverage evidence.
- Direct Reality from Moscow returned Royale egress and five YouTube HTTPS204 results in 252–331 ms. Ordinary HTTPS to the masking host nl.arccnet.space has a valid certificate and returns HTTP403 after TLS; masking site was not changed.
- Rollback if needed: restore 88.216.62.135 in ee-origin, verify public XHTTP egress to LT, clear only `cdn_origin_confirmed` so admin and operator attribution return to LT. Keep client URLs, identities and quota accounting.

## Telegram comparison and Remnawave Nodes repair

Acceptance: compare the same Telegram-hosted media bytes over published Royale and Sweden profiles from a single source, verify egress, and distinguish browser media transport from the native Telegram application. Repair the existing Nodes list so Royale is visible and opens the active CDN check, with current operator rows and manual action only on the active source. Keep LT history. Existing layout and interactions apart from the CDN link are retained. Browser acceptance on phone/tablet/desktop/wide, actual origin and operator payload, TypeScript/build, release assets and subscription health. No Telegram routing mutation is assumed. Roll back the scoped runtime commit if needed.

## HostUp Sweden exit migration

Owner approved moving Sweden-backed profiles to Royale before HostUp expiry and Dutch flags for Games and AI. Preserve the names of Sweden and Estonia as compatibility aliases. Routes:

| Client path | Royale ingress and exit | Compatibility |
|---|---|---|
| Sweden and Estonia aliases | nl.arccnet.space TCP443, SNI nl.arccnet.space, existing main Reality -> NL direct | Names and main identities retained. Old cached Sweden IP requires a refresh. |
| AI 🇳🇱 | nl.arccnet.space TCP8444, SNI nl.arccnet.space, dedicated Reality -> local WARP SOCKS | Existing behavior with separate WARP routing. Verify WARP trace and application HTTPS. |
| Games 🇳🇱 | nl.arccnet.space UDP443, SNI nl.arccnet.space, Hysteria2 -> NL direct | Existing authentication and TLS validation. Verify native Xray Hysteria2 traffic. |
| Auto, YouTube and LTE CDN | existing LT/NL and verified Yandex CDN routes | No Sweden endpoint in public config or fallback. Preserve URL, UUID and quota. |

Roll out new inbounds and check actual tunnels before switching rendered endpoints. Keep protected pre-change panel, authorization and overlay snapshots. Confirm public JSON, plain and Base64 with and without LTE, main/AI/Games, CDN and admin. Rollback while HostUp is available uses the original overlay and hosts. Existing CDN serves on Royale throughout.

### HostUp closeout

- Runtime f54ecd52. Official WARP runs in proxy mode on Royale, with local SOCKS40000 returning warp=on. Dedicated Remnawave Reality8444 and Hysteria2 UDP443 are authorized in the existing main squad and persisted in its sync environment. Pre-change panel, squad and env snapshot in .secrets/royale-special-before-20261106.json. Original Royale container retained stopped as remnanode-before-royale-special-20261106. Certificate mount limited to the NL live and archive directories.
- Activated the existing HostUp delivery overlay with the Royale endpoint. Protected original overlay hostup-return-before-royale-20261106.json remains on the controller. Public owner/LTE/no-LTE JSON/plain/base64 passed with Dutch AI/Games flags and no old IP/hostname. All four migrated profiles passed real traffic for each cohort. AI WARP trace and Google204 passed before release. Games also returned an application UDP DNS response through published Hysteria2. Old HostUp remains available for cached configs until expiry. Roll back the overlay only while that VPS is reachable.
- Public CDN operator path and current 24000 path each reached Royale from Moscow. Forced failure of both primary countries and one CDN candidate still reached Royale through the authorized CDN reserve. Bound subscription via public CDN HTTP200.
- Forty focused tests, TypeScript/Vite build and staged diff passed. Updated and prior admin JS assets, admin page and health HTTP200. Authenticated browser at 360/768/1280/1600px showed the Royale node, CDN link, existing operator rows and manual check button with no horizontal overflow or page errors. Lithuania retained historical CDN checks without the live run button. No operator batch launched during browser verification.
- Before switch, same 4 MiB public Telegram video range from Moscow, four measured samples per profile with alternating order. Median first byte NL 703 ms / SE 622 ms. Median total NL 1.470 s / SE 1.503 s. This measures HTTPS media delivery, while native Telegram app throughput remains unmeasured.

## Royale intermittent connection audit

Compare the published direct Netherlands profile, a literal-IP canary, Lithuania, historical HostUp and XHTTP GET. Verify egress and fresh Telegram MTProto nonce replies from Moscow and the owner workstation. Probe HTTPS through the public CDN and each origin with the same XHTTP settings. Treat the previous media timing as inconclusive because the test did not establish a cold cache.

Correct the Royale loopback TLS target on 127.0.0.1:8443 to serve an index and negotiate HTTP/2, matching the working Lithuania target. Preserve the Reality endpoint, SNI, certificate, routes, CDN group and client delivery. Snapshot the vhost and validate Nginx before reloading. Verify TLS 1.3/h2, HTTP 200 and fresh Reality/Telegram traffic. Restore the saved vhost and reload Nginx if validation fails.

### Audit closeout

- Live Remnawave and generated profiles confirm ordinary NL TCP443 Reality -> Royale DIRECT, same SNI via domain and literal-IP canary. The October Lithuania Moscow1443 ingress was retired on October 29. Historical HostUp and current LT have a server-side YouTube-specific RU rule, while ordinary traffic exits directly. Shared LT JSON sends YouTube via NL on the client. Royale has no RU outbound. Only the dedicated AI inbound uses WARP.
- Moscow fresh Telegram MTProto nonce replies before and after the mask change: 15/15 per run and per direct route (NL hostname, NL IP, LT, old HostUp). Across the first two tested DC endpoints after the change, medians were NL hostname 201 ms, NL IP 151 ms, LT 203 ms and HostUp 130 ms. On the owner's workstation with the installed INCY Xray, NL and LT each passed 9/9 before, and 15/15 after. The literal IP also passed before, with a slow outlier on both address forms. DNS-only failure was not established. Fresh connections do not measure cold media throughput, and the original media timing did not control application cache.
- Royale Nginx loopback mask corrected from HTTP403/1.1 to HTTP200/h2. Public TLS1.3, h2 and certificate verification passed from Moscow. Only Nginx reloaded; remnanode remained running with zero restarts. The public endpoint, SNI and routing are preserved. Rollback restores root-only /root/arcvpn-royale-mask-before-20261106.conf over /etc/nginx/sites-available/arcvpn-royale, runs nginx -t and reloads Nginx.
- XHTTP GET #4 with the same transport/auth completed 12/12 HTTP(S) tests through each origin directly. On Yandex public CDN, HTTP204 probe passed 4/4 but HTTPS passed 4/8. A second public run across four explicit CDN-only profiles found 18/48 HTTPS failures and 23/24 HTTP probe successes, routed via cdn-direct. The old LT origin canary also completed 12/12. This isolates a failure in the public CDN path but does not identify the edge setting or establish an intermittent failure on the direct Reality profile. No origin rollback or CDN settings change was applied. Record the affected profile and time on the owner's network if direct Reality fails again.

- Tested public XHTTP #4 with ALPN forced to h2 and HTTP/1.1 in isolated clients. Neither fixed it. Default reached 8/10 HTTPS responses, h2 reached 5/10, and HTTP/1.1 reached 0/10 in this batch. The direct Royale origin reached 10/10. Leave ALPN as published. A final paired run reached 14/14 HTTPS responses directly at Royale and 7/14 over the public edge, while HTTP checks passed 7/7 over each. No XHTTP error code was captured in that run.

## Alternate CDN edge

Add 188.72.110.52 as a fourth authorized Best Bypass candidate using the existing 24000/10 transport and as a candidate in Auto's LTE reserve. Keep the DNS candidates and DNS fallback. Test candidate identity, transport equality and no-LTE exclusion. Roll back the scoped commit if needed.

Latency Lab in Orel returned 5/5 for this IP versus 3/5 for the current DNS IP in one series. Royale and LT origin locations retain HTTP/1.1 upstream, disabled request/response buffering and no-store for the 24000 path. No nginx change is needed to select a different public edge.

## Royale transport and CDN probe acceptance

Economy. Owner authorized implementation after the BedolagaBD audit. Keep published endpoints, SNI, XHTTP paths, identities, traffic factors, CDN origin and the current candidate ordering. Correct the proxy health signal without changing the public topology.

| Scope | Current | Proposed and acceptance | Rollback |
|---|---|---|---|
| LTE Auto reserve and Best Bypass | HTTP on controller :18080 can pass through a candidate that times out on HTTPS | HTTPS 204 on dedicated controller :18443, healthy cert from every node, probe-only telemetry and real tunnel evidence. Keep HTTP for installed clients. Verify failed candidates are rejected and forced Auto fallback can use the remaining CDN path. | Revert renderer first, keep TLS listener available for cached profiles until refreshed. |
| Ordinary Royale and Lithuania | CUBIC, unchanged Reality | Isolated CUBIC/BBR A/B on Royale with fixed payload, same source and interleaved runs. Require measured improvement before changing live Reality or kernel defaults. | Remove the canary; retain current service settings. |
| CDN origin nginx | 24000 route streams to local Xray without buffering | Inspect status and timings on test requests; change production only for a demonstrated origin defect. | Restore the previous vhost and reload only nginx. |

Components: controller nginx and subscription renderer, observatory classifier, active CDN routes, isolated Linux socket canary. Keep Lithuania ordinary authorization and no-LTE behavior. Mobile user and Telegram playback acceptance remains the owner's test.

The public controller answered 204 on both old HTTP and new HTTPS listeners. Direct Moscow tunnels through Royale and Lithuania reached the new HTTPS probe and returned expected egress. XHTTP edge 188.72.110.52 passed HTTP 5/5 but HTTPS 2/5 in the paired series. DNS 24000 passed this probe 5/5 while still occasionally failing other external HTTPS. Forced primary and alternative CDN failure selected the only usable alternate IP in both Auto and Best, with intermittent HTTPS responses. The probe improves detection but does not prove stability for every destination. Direct origin completed 21/21 HTTPS checks. Public edge baseline 12/21, lowered per-request cap 11/21, shorter header chunk 12/21, forced frequent H2 connection rotation 10/21. No XHTTP transport or origin configuration change was promoted. Controller nginx backup /root/arcvpn-cdn-probe-before-https-20261106.conf.
