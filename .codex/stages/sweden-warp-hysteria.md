# Sweden WARP + Hysteria2 profiles — 2026-10-08

Owner-authorized scope: insert after Finland: 🇸🇪 Швеция (Для нейросетей), then 🇸🇪 Швеция (Для игр🎮). Existing profiles, subscription URLs, UUIDs, quotas, SE61/EE39 and CDN fallbacks unchanged. Manual profiles excluded from Auto/YouTube/bypass balancers.

| Visible profile | Client endpoint / SNI | Transport / server route | CDN | Multiplier | Failure | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| 🇸🇪 Швеция (Для нейросетей) | se.arccnet.space:8444 / existing SE Reality SNI | Separate VLESS Reality inbound -> localhost WARP SOCKS40000; private/bittorrent blocked, unsupported UDP blocked | none | 1 | fail closed if WARP unavailable; no ordinary exit fallback | hide new Host and restore private profile snapshot |
| 🇸🇪 Швеция (Для игр🎮) | se.arccnet.space:443 UDP / se.arccnet.space | Hysteria2 with own existing SE certificate -> Sweden DIRECT; private/bittorrent blocked | none | 1 | unavailable if UDP blocked, existing manual alternatives remain | hide new Host and restore profile snapshot |

Components: Sweden WARP package in proxy mode; RemnaNode certificate mount; existing profile/node/ordinary squad plus two new hidden Hosts; subscription_api.py naming/order/transport inclusion. Stage route follows owner's explicitly requested WARP/Hysteria choices and names. No invented destination or replacement of ordinary Sweden.
Acceptance before publish: WARP cloudflare trace says warp=on; server syntax/listeners/firewall and preserved existing inbound IDs; hidden canary authorized; real Reality/WARP HTTPS and real Hysteria HTTPS plus tunneled UDP; generated customer JSON syntax and native links names/order; canary cleanup. Physical owner Happ/game latency remains separately observable.
Rollback snapshots remain remote-only mode0600, no secrets in Git/output. No subagents authorized. Worktree sweden-node; primary owner changes untouched. Production Poland is authoritative.
Evidence: preparing.
