# Real CDN tunnel comparison — 2026-10-01

Owner authorized network tests, superseding earlier no-test instruction. Source local Windows, Xray26.9.9, same owner-only EE /api-ee-direct identity; both directions via CDN, direct EE YouTube egress. No production config changes during measurements. Four variants, two sequential repetitions each. Test endpoints Google generate204, Cloudflare speed __down 10,000,000bytes / __up 1,048,576bytes. Single-connection HTTPS via SOCKS5 hostname DNS. No Multitest VPS figures substituted for tunnel measurements.

| Packet/interval | Download connections | Connect success | Complete download | Successful download Mbps | Upload success |
|---|---|---|---|---|---|
|2048/10ms|separate|0/2|1/2|15.27|0/2|
|4096/1ms|separate|2/2|2/2|17.42,19.22|0/2|
|8192/1ms|separate|1/2|1/2|19.09|0/2|
|4096/1ms|shared|1/2|0/2|not valid|0/2|

Shared second download returned200 but timed out at9,996,800/10,000,000bytes; not counted as complete. All upload tests failed curl56/28; curl size_upload only confirms handing bytes toward proxy, not successful remote reception. No valid upload throughput obtained. Direct controls same Windows source: download29.60Mbps (10MB/2.703s); upload endpoint accepted1MiB HTTP200/0.802s. Control single snapshot cannot certify source capacity. No claim that packet/interval alone causes failures. Some attempts failed TLS handshake; CDN/source/time effects remain possible.

Current best candidate4096/1ms split; eight downloads is too small a sample for reliability certification. Large-packet tuning not justified by these results. YouTube video/real mobile whitelist gate remains owner-tested only; initial FI direct-YouTube video worked, full-CDN EE video not yet confirmed. No global publication. Private raw numeric results/variant URIs/configs stored outsideGit Temp/ArcVPN-CDN-benchmark-20261001 (configs contain identity, do not print/commit). Local Xray child stopped in finally. Server Xray header limit16384, max payload5,000,000: unchanged.
