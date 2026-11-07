# Ordinary-node configuration review

2026-11-07. Economy. Research and inactive proposals. The owner has paused traffic tests. Production configuration has not been changed by this review.

## Current path

Ordinary Netherlands uses client → Royale TCP443 Reality → DIRECT. Ordinary Lithuania uses client → Lithuania TCP443 Reality → DIRECT for general traffic, with the existing client-side YouTube rule using Royale. Preserve the existing legacy Lithuania YouTube routing during any server-side change.

Both Reality targets are local nginx at `127.0.0.1:8443`. The installed REALITY implementation contacts that target during TLS establishment and closes it after successful authentication. Subsequent authenticated VPN payload uses Xray. Thus nginx TLS availability matters to opening a connection, while HTTP body buffering and static-file settings apply to the masking website or explicitly proxied HTTP transports.

The ordinary node profiles have no explicit policy override or socket options. Both use sniffing for HTTP/TLS/QUIC, with `routeOnly` absent. Nginx uses `worker_processes auto`, `worker_connections 768`, and systemd `LimitNOFILE=524288`. Those values alone do not establish a capacity bottleneck.

[Installed REALITY dependency](https://github.com/XTLS/REALITY/blob/9234c772ba8f/tls.go), [node contract](../../.codex/references/node-config-contract.md).

## First candidate — preserve the original destination

For a later isolated comparison, merge `routeOnly` into the existing sniffing block on the ordinary VLESS Reality inbound only. Preserve all existing fields and restrictions.

```json
"sniffing": {
  "enabled": true,
  "routeOnly": true,
  "destOverride": ["http", "tls", "quic"]
}
```

Without `routeOnly`, Xray may replace a requested IP with the sniffed hostname and perform DNS resolution again. With `routeOnly`, the original target IP remains available to IP rules and outbound dialing, while the sniffed hostname remains available to domain rules. This is relevant to HTTPS/CDN endpoints selected by an application. It does not establish a fix for native MTProto, which usually has no TLS SNI.

This candidate retains sniffing. Disabling sniffing globally would also affect private-domain/P2P restrictions and Lithuania's YouTube domain routing. `routeOnly` does not remove the sniffing stage or its potential initial-data wait. The installed dispatcher uses a 200 ms sniffing budget, which cannot by itself explain an observed minute-long stall.

Later acceptance should cover ordinary NL/LT HTTPS, native Telegram, private-address blocking, P2P policy, and current Lithuania YouTube rules with the same client profile and physical network. Only the ordinary inbound should change. Rollback removes the newly added field and restores the saved profile.

[Dispatcher](https://github.com/XTLS/Xray-core/blob/v26.7.28/app/dispatcher/default.go), [routing context](https://github.com/XTLS/Xray-core/blob/v26.7.28/features/routing/session/context.go), [Bedolaga Reality notes](https://github.com/Rxflex/BedolagaBD/blob/1b60387/docs/02-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D1%8B/reality.md).

## Second candidate — inbound keepalive

The previous hypothesis needs qualification. The server listener disables inbound keepalive by default, but the client dialer already enables keepalive with 45-second idle and interval values. There is already client-originated TCP keepalive when the default dialer is used. A matching explicit server configuration would add probes in the opposite direction.

An inactive candidate matching those client defaults is the following merge into the ordinary inbound's `streamSettings.sockopt`.

```json
"sockopt": {
  "tcpKeepAliveIdle": 45,
  "tcpKeepAliveInterval": 45
}
```

Its intended purpose is idle/NAT session maintenance. It does not increase transfer bandwidth. The deployed JSON schema exposes these two keepalive fields. Some community snippets also contain `tcpKeepAliveCount`, which is absent from that schema. Do not assume such snippets configure the probe count.

Application idle policy is a separate mechanism. Increasing kernel keepalive settings does not override an application's socket settings or prevent application-level idle closure. Candidate values remain unvalidated on the owner's network.

[Server listener](https://github.com/XTLS/Xray-core/blob/v26.7.28/transport/internet/system_listener.go), [installed client dialer](https://github.com/XTLS/Xray-core/blob/1b1647c/transport/internet/system_dialer.go), [socket schema](https://github.com/XTLS/Xray-core/blob/v26.7.28/infra/conf/transport_sockopt.go).

## Separate transport candidate — direct XHTTP TLS

Bedolaga and XTLS describe HTTP/2 streaming through nginx `grpc_pass`. The direct TLS transport can reuse the outer connection, unlike a separate cold Reality connection for each application socket. This gives a plausible explanation for lower startup delay in a warmed short comparison. It introduces separate connection-reuse, idle-timeout, and client-compatibility considerations.

An inactive nginx location for a future dedicated loopback Xray inbound would look like this. Replace the path and port after inventory verification, bind the inbound through Remnawave, and preserve the current masking location.

```nginx
location ^~ /PRIVATE_XHTTP_PATH/ {
    grpc_pass grpc://127.0.0.1:UNUSED_LOOPBACK_PORT;
    grpc_set_header Host nl.arccnet.space;
    grpc_read_timeout 3600s;
    grpc_send_timeout 3600s;
    client_max_body_size 0;
    access_log off;
}
```

These are proposal placeholders, not an installable configuration. An nginx gRPC read timeout is the gap between upstream reads, rather than the whole transfer duration. The default is 60 seconds. A future long-lived XHTTP transport should explicitly handle idle behavior instead of inheriting that default. A larger timeout does not generate application heartbeat data.

Start with stock XHTTP connection-reuse defaults. XTLS notes that setting one XMUX field can suppress defaults for other fields. An isolated `maxConnections=1` or an aggressive reuse setting can concentrate multiple application streams on one carrier connection. `maxConcurrency=1` is useful as a controlled comparison, rather than a proven general production setting.

Keep normal-main authorization, expiry, traffic factor 1, local exit, and subscription compatibility. An eventual owner-only profile should have proper panel binding and sync persistence before delivery. Changing the existing ordinary profiles for all customers requires compatibility evidence. The temporary transport from the earlier comparison has been removed.

[Bedolaga XHTTP notes](https://github.com/Rxflex/BedolagaBD/blob/1b60387/docs/02-%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D1%8B/xhttp.md), [XTLS XHTTP description](https://github.com/XTLS/Xray-core/discussions/4113), [nginx gRPC timeouts](https://nginx.org/en/docs/http/ngx_http_grpc_module.html#grpc_read_timeout).

## Method and decision boundaries

Earlier unbound workstation benchmarks may have traversed the active Windows Wintun route. They should not be interpreted as clean device-to-node baselines. The final pre-pause run pinned the physical interface. Short file and nonce results remain distinct from native Telegram playback and operator-specific acceptance.

The existing ArcVPN Bedolaga audit from August concerns the bot and cabinet upstreams. Its product and UI conclusions do not supply node-performance evidence. The community knowledge-base examples are individual observations, and some contradict one another. For example, TCP Fast Open is enabled in some snippets and discouraged for server/NAT paths in others.

For later work, evaluate `routeOnly` first, then explicit keepalive as a separate change. Compare a dedicated direct XHTTP profile independently. Keep the owner-requested study-only mode until traffic testing is explicitly resumed.
