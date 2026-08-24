---
name: arcvpn-node-ops
description: Provision, repair, validate, or retire ArcVPN nodes, Remnawave bindings, Reality, Hysteria2, LTE/XHTTP, CDN, DNS, and certificates with credential-vault lookup and production gates.
---

# ArcVPN Node Operations

1. Read `AGENTS.md`, `.codex/handoff.md`, `.codex/server-inventory.toml`, and `.codex/references/node-config-contract.md`.
2. For server access, use the local DPAPI vault through `scripts/ops/server-vault.ps1`. Never print, log, commit, or paste a decrypted credential into a command line.
3. Identify the requested mode and read only its reference:
   - ordinary node provisioning/repair/retirement: [references/node-lifecycle.md](references/node-lifecycle.md)
   - LTE/XHTTP/CDN/DNS/certificates: [references/cdn-lte.md](references/cdn-lte.md)
4. Before mutation, record target alias, current state, desired state, affected subscriptions, acceptance gate, and rollback in `.codex/stages/current.md`.
5. Preserve subscription URLs, user UUIDs, and active authorization. Generate unique Reality material on the target and never store private keys locally.
6. A node is not accepted on ping or open port alone. Require Remnawave authorization/binding, generated client config, and real tunneled traffic.
7. Update the non-secret inventory and handoff after verified topology changes; finish with `$arcvpn-closeout`.
