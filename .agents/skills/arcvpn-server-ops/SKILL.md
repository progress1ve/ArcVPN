---
name: arcvpn-server-ops
description: Operate ArcVPN servers for deployments, service state, logs, health checks, diagnostics, file transfer, and repeatable maintenance. Use for general server work that is not a node topology or protocol change.
---

# ArcVPN Server Operations

1. Resolve the target from `.codex/server-inventory.toml`; never invent an
   address, alias, service, path, or authority.
2. Automatically prefer the private `arcvpn-ops` MCP whenever `arcvpn_*` tools
   are available. Do not wait for the user to name or invoke it.
3. Choose the smallest tool that proves the result:
   - inventory: `arcvpn_list_hosts`;
   - health: `arcvpn_node_health`;
   - services/logs: `arcvpn_service_status` and `arcvpn_journal`;
   - one bounded operation: `arcvpn_exec`;
   - stateful or interactive diagnosis: `arcvpn_shell_*`;
   - long operation: `arcvpn_job_*`;
   - approved repeatable workflow: `arcvpn_recipe_*`;
   - allowlisted transfer: `arcvpn_file_upload` or `arcvpn_file_download`.
4. If MCP tools are unavailable or the target is not yet enrolled, use
   `scripts/ops/server-vault.ps1` with `scripts/ops/ssh_exec.py`. Preserve strict
   host-key verification and never expose decrypted credentials.
5. Treat MCP as transport, not authorization. Read-only diagnosis is allowed
   when relevant; mutations must remain within the user's request. Confirm the
   exact target before destructive commands and use the repository production
   workflow for runtime changes.
6. Keep output bounded. Query focused journal windows and status fields instead
   of dumping configurations, databases, environments, or full logs. Never ask
   a server to print secrets, subscription identifiers, or private key material.
7. For code deployment follow: local checks, staged diff, commit, push,
   production fast-forward pull, restart only affected services, then verify
   service state and public behavior. MCP does not replace any gate.
8. Route Remnawave node, Reality, XHTTP, CDN, DNS, certificates, bridges, or
   client-tunnel changes to `$arcvpn-node-ops`.

When recurring work takes more than a few low-level calls, add a narrow recipe or
high-level tool to the private `arcvpn-ops-mcp` repository rather than repeatedly
spending context on shell orchestration. Keep generic recovery access available.
