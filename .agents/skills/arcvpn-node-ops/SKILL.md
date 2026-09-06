---
name: arcvpn-node-ops
description: Provision, repair, validate, or retire ArcVPN nodes, Remnawave bindings, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, and certificates with credential-vault lookup and production gates.
---

# ArcVPN Node Operations

1. Read `AGENTS.md`, `.codex/handoff.md`, `.codex/server-inventory.toml`, and `.codex/references/node-config-contract.md`.
2. For server access, automatically use the private `arcvpn-ops` MCP when its
   `arcvpn_*` tools are available. Prefer the narrowest high-level tool, then a
   bounded command, and use an interactive shell only when stateful diagnosis is
   genuinely useful. Do not ask the user to invoke the MCP. If it is unavailable,
   fall back to the local DPAPI vault through `scripts/ops/server-vault.ps1` and
   `scripts/ops/ssh_exec.py`. Never print, log, commit, or paste a decrypted
   credential into a command line.
3. Identify the requested mode and read only its reference:
   - ordinary node provisioning/repair/retirement: [references/node-lifecycle.md](references/node-lifecycle.md)
   - LTE/XHTTP/CDN/DNS/certificates: [references/cdn-lte.md](references/cdn-lte.md)
4. Before mutation, record target alias, current state, desired state, affected subscriptions, acceptance gate, and rollback in `.codex/stages/current.md`. Add one row per client path with: visible profile, client hostname, CDN resource, origin group, active/backup origin, Host/SNI, inbound/path, traffic multiplier, public URL impact, failure behavior, and rollback. Do not mutate until the owner explicitly accepts this table when topology or a public contract changes.
5. Preserve subscription URLs, user UUIDs, and active authorization. Generate unique Reality material on the target and never store private keys locally.
6. A node is not accepted on ping, open port, config syntax, or generated JSON alone. Require Remnawave authorization/binding, generated client config, and real tunneled traffic. If censorship failover cannot be reproduced, report that gate as open instead of weakening it.
7. Update the non-secret inventory and handoff after verified topology changes; finish with `$arcvpn-closeout`.

MCP access changes transport, not authority: preserve the accepted route table,
mutation scope, production gates, and real-tunnel acceptance requirements.
