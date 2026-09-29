---
name: arcvpn-add-node
description: Add a new ArcVPN VPS node from an owner-provided IP and credential, including ordinary Reality, Moscow bridges, YouTube and AutoSelect pools, and optional CDN bypass. Use for full new-node onboarding; use arcvpn-node-ops directly for a narrow repair or retirement.
---

# Add an ArcVPN node

1. Read the root `AGENTS.md`, `$arcvpn-node-ops`,
   `.codex/references/node-config-contract.md`, and
   `docs/operations/node-topology-current.md`. For a speed request also use
   `$arcvpn-benchmark-nodes`; for deployments use `$arcvpn-server-ops`. Treat
   the dated topology as a snapshot and confirm code, panel and live routes.
2. Resolve the proposed host, provider, intended country/role, domain and SSH
   trust. Store credentials only in the local DPAPI vault under a new alias;
   never copy passwords or Reality private material to Git, chat, commands or
   reports. Prefer private `arcvpn-ops` MCP for enrolled hosts; otherwise use
   strict host-key-checked vault/SSH tooling. Do not accept a changed fingerprint
   silently. Keep SSH access recoverable during bootstrap.
3. Inspect the existing machine and dependencies before touching it. Inventory
   panel/node/profile/host bindings, ports, firewall, TLS/DNS and route state.
   Check it is not an already active or owner-modified host. Capture scoped
   backups of affected configs with restricted permissions.
4. Draft one explicit client-path table as required by `$arcvpn-node-ops`:
   ordinary node, Moscow→new node, new node→Moscow YouTube, AutoSelect,
   YouTube balancer, manual catalog order, and CDN/XHTTP if requested. Include
   host/SNI, path, origin group, priority, public URL/UUID impact, multiplier,
   fallback and rollback. Use the existing FI/EE topology as a *candidate*
   default, not an instruction to insert every new node into every pool. Ask
   the owner once to accept or revise this concrete route table before any
   production topology change. An IP/password alone does not authorize buying
   resources or changing unrelated hosts.
5. Provision against the accepted table: unique Reality material generated
   on the target; Remnawave authorization and profile/squad/host binding;
   self-steal/decoy TLS when applicable; scoped Moscow bridge in both directions;
   optional XHTTP CDN route on the existing resource only if accepted. Keep
   the new host hidden/canary until all required paths pass. Preserve public
   subscription URLs, existing UUIDs, active access and multiplier 1.
6. Require a real client tunnel/exit check for each relevant route in addition
   to syntax, agent status, DNS, TLS, ports, firewall and rendered subscription.
   Test bridge/YouTube, AutoSelect selection/failure, and CDN edge/origin
   separately. Report mobile censorship as unverified unless tested on the
   affected network. Do not promote by ping or a single impressive benchmark.
7. Publish only after gates and owner-approved priority. Follow the production
   workflow, verify users' existing keys still work, update inventory and
   handoff, and provide a bounded rollback. Retire an old node only when the
   owner requests that separate change; never delete it as a cleanup shortcut.
