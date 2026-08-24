# Node lifecycle

## Discover

- Resolve the inventory alias and local credential-vault entry.
- Capture provider, location, public IP/hostname, OS, CPU/RAM/disk, network limits, expiry, and intended role.
- Baseline reachability, loss/jitter/latency, CPU steal, disk pressure, clock, firewall, listening sockets, and existing services.

## Provision or repair

- Patch the OS without changing the SSH access path mid-session.
- Install the supported Remnawave/wCloud node agent using the current upstream instructions, not a remembered command.
- Generate node-specific Reality key material on the node. Configure TCP Reality first; add Hysteria2/UDP only after its separate gate.
- Authorize the node in Remnawave, attach the intended config profile, hosts, and internal squad. Keep it hidden/canary until verified.

## Gate

- Agent connected and stable after restart.
- Expected ports listen and are reachable from outside.
- Remnawave shows the intended profile/inbounds and users are authorized.
- A fresh test subscription imports into Happ with the required fingerprint and completes real HTTP/UDP traffic as applicable.
- Record p50/p95 latency, loss, jitter, throughput, CPU steal, and evening behavior for canaries.

## Retire

- Remove the node from visible hosts/auto-selection before stopping it.
- Confirm no active catalog entry or squad depends on it.
- Preserve user UUIDs and URLs; verify public subscriptions after removal.
- Revoke node credentials and remove inventory/vault entries only after the rollback window.
