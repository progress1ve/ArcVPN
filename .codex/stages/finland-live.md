# Finland rollout checkpoint — 2026-09-28

Owner accepted direct Finland, FI+EE routine peers with DE reserve, existing
CDN/Moscow /api-fin path, reciprocal RU YouTube egress and FI bridge membership.
Owner requested early production delivery for personal testing.

## Verified and deployed

- New node 92.42.102.139, fin.arccnet.space, Ubuntu 22.04, 1963 MB RAM.
- Root credential DPAPI-only; ED25519 fingerprint independently matched owner
  VNC evidence and pinned. No credential in Git or command literals.
- Docker/nginx active; RemnaNode 3.4.1 connected to Poland; Xray 26.7.28.
- Target-generated unique Reality key; local TLS decoy 127.0.0.1:8443 HTTP 200.
  Let's Encrypt expires 2026-12-27, automatic renewal enabled.
- Dedicated Reality 443, managed XHTTP localhost10001 /api-fin, service bridge
  2443. Existing ordinary/LTE/bridge squad authorization extended without user
  UUID or subscription URL changes. Traffic multiplier 1.
- Port guard enabled across reboot: control22600 Poland only; bridge2443
  Moscow only; corresponding IPv6 service ports denied. No SSH rule changed.
- Real direct tunnel HTTP204 and exit92.42.102.139 HTTP200. Direct managed
  XHTTP origin also exits92.42.102.139 HTTP200.
- Ordinary Host enabled. Three generated subscriptions show AutoSelect,
  YouTube, real Finland, Estonia in that order; old EE-backed Finland alias gone.
- Runtime90c8d98 then safety gate93c0433 pushed/pulled ff-only to Poland;
  only subscription service restarted, active; public website HTTP200.
- 232 local tests passed; existing datetime.utcnow warning unchanged.

## Open acceptance and safety rollback

- Moscow -> Finland TCP80/443 timeout; Finland -> Moscow HTTPS timeout.
  During timed Moscow HTTP probe19:01:26-19:01:32 UTC, target raw IPv4 capture
 19:01:17-19:01:48 saw zero Moscow TCP packets. Both local OUTPUT policies allow
  traffic; FI INPUT accepts these public ports. This identifies a path-level
  reachability failure, not its provider/root cause.
- Estonia -> Finland HTTP200, ping p50 around13.6 ms with0/3 loss.
- CDN /api-fin through Moscow times out from Poland and Moscow. LTE Host stays
  disabled; original /api-test DE/EE path untouched. New Moscow location has a
  backup /opt/arcvpn/staging/arc-guide-https.before-finland.conf.
- FI_BRIDGE outbound was added to Moscow then removed from active EU_BRIDGE
  selector after reachability failure; DE/EE preserved. Backup on Poland:
  backups/finland-moscow-before.json; squad backup finland-squads-before.json.
- Finland excluded from routine AutoSelect/YouTube until bridge verified.
  Manual FI still has YouTube->RU policy, currently unreachable. Explicitly tell
  owner YouTube on manual Finland is not accepted; do not claim full readiness.
- Benchmark endpoint failed TLS on FI and timed out on EE: no valid throughput
  comparison, no promotion of FI over EE.
- A temporary local credential-bearing canary transfer file was removed;
  restricted remote /opt/arcvpn/staging/fi-cdn-canary.json remains0600.

## Decision required

Ask owner to authorize additional hop: CDN -> Moscow -> Estonia -> Finland,
and reciprocal Finland -> Estonia -> Moscow YouTube relay, or obtain provider
repair of direct Moscow/Finland route. Do not silently deploy extra topology.
After decision: verify real CDN and reciprocal bridges, generated configs,
download/upload, external decoy, comparable throughput; only then enable FI
automatic membership and bypass delivery.

Provisioning helpers intentionally refuse re-creation when FI profile exists.
Do not rerun bootstrap on the live node without first inspecting partial state.
