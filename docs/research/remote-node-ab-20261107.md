# Remote Telegram A/B diagnostic — 2026-11-07

The owner saw no clear difference between A and B and authorized remote tests,
explicitly excluding their PC as a measurement source. Measurements ran on
Moscow95.182.120.237 from07:00:05 to07:01:56UTC. Windows was used only to control
SSH and collect the report; no Windows browser, VPN client or benchmark carried
measurement traffic. No account session or Telegram application was used.

## Method

- Same Linux Xray26.7.28 core for all four clients, exact published owner JSON
  configuration with only local inbounds replaced by127.0.0.1 SOCKS listeners.
  Kernel routes to NL, LT and Telegram used ens3/default gateway, not a pre-existing
  VPN. Trace requests confirmed A/B/ordinary NL exit45.141.202.248 and LT88.216.62.135.
- Six alternating-order rounds against five Telegram DC IPs,30 connections per
  route. Every connection used a newly generated random nonce and checked the
  returned resPQ constructor, nonce and envelope length. These are native
  unauthenticated MTProto connection checks, not downloads from an account.
- One public video from the official Telegram channel,7,385,426 bytes, served by
  cdn1.telesco.pe. Three3MiB ranges covered the beginning, middle and end. Each
  range was requested twice on each route, interleaved A/B/NL/LT and LT/NL/B/A.
  Each curl process made a new connection; bodies were read into transient memory
  and discarded, not read from a file/application cache. Successful requests had
  HTTP206, exact Content-Range/length and matching SHA256 across routes.
- Client-side target149.154.175.205 was fixed for HTTPS with the original Host/SNI.
  A's server-side sniffing is still allowed to resolve the hostname again; this
  is the intended configuration difference. No claim that it necessarily chose
  the same physical upstream server.
- Request headers asked for no-cache, but Telegram's upstream cache is outside
  our control. Response Cache-Control was max-age10800/must-revalidate, with no
  Age/X-Cache proof of a cold origin. Alternating order limits warm-up bias; this
  is not proof of a cold native Telegram media cache or a10-minute seek.

## Results

| Route | Fresh MTProto success | MTProto median |3MiB range success | Range first byte median | Complete range median |
|---|---:|---:|---:|---:|---:|
| A, routeOnly false |30/30|389.86ms|6/6|720.17ms|1480.22ms|
| B, routeOnly true |30/30|388.79ms|6/6|701.10ms|1479.91ms|
| Ordinary Netherlands |30/30|397.60ms|6/6|697.13ms|1425.26ms|
| Ordinary Lithuania |30/30|430.34ms|5/6|826.12ms|1824.36ms|

Success-only latency statistics do not hide the separate failure count. The
failed LT middle-range request received HTTP206 and3,063,135 of3,145,728 bytes,
then hit25s. The remaining LT complete-range maximum was3.364s. No corresponding
failure occurred on the three NL paths in this batch. This does not establish
that Lithuania is generally unreliable on the owner's network.

Matched B/A median ratios were1.002 for total range time and0.9766 for first byte.
Six matched pairs are a small sample; no practical download gain was established.
The owner's impression that A/B download similarly agrees with this result.

The sidecar CPU throttle count stayed6 and throttled time305231µs before/after,
so the25%CPU cap did not throttle this run. CPU usage increased447254µs. Memory
afterwards was10.7MB. Targeted TCP snapshots showed roughly40–47ms NL/Moscow RTT
and some packet reordering; these snapshots do not establish full-run packet
loss statistics. Main remnanode start/restart count remained unchanged. Web
nginx stayed active. Temporary clients, their directory and private profile
input were removed; no public configuration/service/firewall change was made.

## Interpretation and limits

routeOnly has no established advantage here and is not promoted to ordinary
production nodes. No60-second stall was reproduced on the NL sample. The next
useful hypothesis is transport/session behavior under sustained or interrupted
native media traffic, rather than treating this routeOnly comparison as a fix.
A Moscow datacenter is not the owner's home ISP or an LTE operator; these results
cannot certify that access path. Authenticated native playback/seek remains
unmeasured. Existing owner A/B expiry remains2026-11-08 09:43:30MSK.

Raw sanitized samples: [remote-node-ab-20261107.json](evidence/remote-node-ab-20261107.json).
Reproducible harness: scripts/ops/remote_node_ab.py, commit396d52d8. No signed
media URLs, subscriber IDs, UUIDs or keys are present in the report.

Protocol references: [Telegram authorization handshake](https://core.telegram.org/mtproto/auth_key),
[intermediate framing](https://core.telegram.org/mtproto/mtproto-transports#intermediate).
