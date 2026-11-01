# Auto CDN leastPing reserve — 2026-11-01

Economy,no subagents. Owner explicitly accepts LT+SE leastLoad primary, authorized CDN pool leastPing reserve. Candidate module monitoring/auto_cdn_reserve.py, one post-render hook. No infrastructure, identities, subscription URLs, billing, quotas or public profile names changed.

| Profile/path | Existing endpoints, CDN/origin, Host/SNI/inbound/path | Selection | Failure/rollback |
|---|---|---|---|
| Auto primary | Existing LT and SE Reality bindings, including existing LT fragment candidate | Existing leastLoad settings preserved | All unqualified -> loopback auto-cdn-stage |
| Auto authorized reserve | Copy existing Best bypass cdn-medium/fast/safe XHTTP authorizations and exact CDN host/origin/Host/SNI/paths | leastPing, candidates proactively observed | All unqualified -> existing cdn-safe, never direct |
| No CDN entitlement; manual/YouTube/Best bypass profiles | Unchanged | Unchanged | Unchanged |

Traffic multipliers unchanged. Prefix selectors preserve existing LT fragment observation. Reserve dispatch rule first, with distinct inbound tag auto-cdn-reserve, prevents recursion into primary selection. Shared burstObservatory covers both tiers, existing Best bypass HTTP204 endpoint, interval15s/sampling2/timeout5s. These values are not a guaranteed failover deadline. Existing connections are not migrated between proxies; failed requests during detection may need retry. One CDN domain with3 transport variants is not3 independent providers.

## Gates

Local18focused tests passed: source preservation, authorization copied from existing entitled bypass, no-entitlement behavior, primary strategy preserved, reserved routing priority and observation membership. Candidate Xray26.7.28 syntax passed on generated full Auto.

Poland direct CDN TCP unreachable during audit; same CDN TCP/TLS from current Moscow succeeds. This prevented valid Poland fallback acceptance and is not attributed to new routing. Existing primary source Poland still works. Tests moved to Moscow without changing ordinary nodes or firewall. All private configurations stored0700/0600 and disposed after tests.

Cold start with all primary addresses redirected to127.0.0.1:9 and one CDN similarly failed: real HTTPS204 through auto-cdn-1 passed; debug detour confirms primary fallback->loopback->CDN. Dynamic first run: normal204, one failed request at primary-down transition, recovery204. Repeating with40s observation wait, recording each attempt; improvement on actual owner's mobile network remains unverified.

Deployment and final dynamic gate pending. Do not deploy unless working reserve and recovery demonstrated. Rollback: revert scoped module/hook, fast-forward production and restart only subscription service; no database restore. No node restart.

## Final candidate gate passed
Final dynamic run on Moscow, current Xray26.7.28, same running process throughout:
- Normal: HTTPS204, detours se-primary and lt-primary.
- Both primary relays disabled and connections closed, auto-cdn-0 deliberately unavailable: HTTPS204 first attempt, detours auto-cdn-stage -> auto-cdn-1.
- Relays restored: HTTPS204 first attempt, detour lt-primary-fragment (existing ordinary LT member).
Waits10s/35s/65s used for observation settling, not measured minimum switching times. Earlier transition failure retained above, not hidden. Collector parser errors in intermediate attempts were harness errors, processes stopped in finally, not production failures. Private configs/test listeners disposed. No phone whitelist reproduction claim.
