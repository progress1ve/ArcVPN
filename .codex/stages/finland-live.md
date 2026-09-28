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

## Direct-route repair required

Owner explicitly rejected an additional Estonia relay. Only the accepted direct
Moscow/Finland route is in scope; do not propose or deploy the extra hop again.
After direct reachability is restored: verify real CDN and reciprocal bridges, generated configs,
download/upload, external decoy, comparable throughput; only then enable FI
automatic membership and bypass delivery.

Provisioning helpers intentionally refuse re-creation when FI profile exists.
Do not rerun bootstrap on the live node without first inspecting partial state.

## Direct-route diagnosis and benchmark follow-up

- Moscow tcpdump observed repeated outbound SYNs to Finland TCP80; timed
  Finland capture observed none. This places the failure before Finland's
  local INPUT filtering, without identifying which upstream provider causes it.
- Compared FI/EE: MTU1500, fq_codel, gateway10.0.0.1 onlink, rp_filter2,
  tcp_mtu_probing0; Finland chooses its correct public source address. No local
  setting difference demonstrated a cause; broad firewall/sysctl changes avoided.
- Installed official Ubuntu iperf3/jq on FI. Reviewed multitest and its Russian
  iperf helper; did not execute full multitest, public report uploads, or tuning.
- FI -> Petersburg ICMP 3/3, average16.253ms; EE same target 3/3,15.885ms.
  FI -> Nizhny Novgorod 2/3,28.556ms; sample too small for loss conclusions.
- Separate 5-second, four-stream TCP directions to Petersburg: first FI run
  upload24.1Mbps/download548.6Mbps. EE upload1082.9/download766.5Mbps.
  FI repeat on5202 reset; these short public-server measurements are not a
  guaranteed capacity estimate or sufficient evidence for priority promotion.
- Sequential FI repeat on the same5203 endpoint used by EE: upload129.6Mbps,
  download720.0Mbps. Public endpoint/short-run variation remains significant.
- FI -> Moscow TCP443 still times out, while Russian public iperf connections
  work. Failure is not a universal lack of Finland/Russia connectivity.

## Owner-requested upload retest

- No routing, firewall, service, or TCP tuning changes. Separate sequential
  8-second upload tests, four streams, to three Russian public iperf endpoints.
- FI Petersburg5203:15.0Mbps;5204 interrupted;5205:33.5Mbps.
  FI Nizhny Novgorod5203:15.0Mbps;5204:67.1Mbps;5205 interrupted.
  FI Moscow Hostkey5203/5204/5205 all interrupted (no successful result).
- EE same endpoints5205: Petersburg980.3Mbps, Nizhny Novgorod991.8Mbps,
  Moscow Hostkey904.7Mbps; all completed. FI5205 follow-up used the same
  endpoint, port, stream count, and duration, without overlapping EE tests.
- FI reported client CPU0.3-4.0%, not a demonstrated CPU bottleneck. Public
  test-server variability remains, but poor FI -> Russia upload repeated across
  ports/endpoints. This direction is relevant to delivery to Russian clients.
- Exact provider/root cause remains unproven. No refund/retirement performed;
  direct Moscow bridge failure remains open. Owner can use these results in a
  provider ticket or decide to replace FI; existing EE remains the safer primary.
