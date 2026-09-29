# Node configuration contract

## Non-negotiable

- Preserve public subscription URLs, user UUIDs, and active-user authorization.
- Every Reality deployment gets its own keypair and short ID. Private keys never enter Git, chat, or documentation.
- Admission requires: node authorization, connected agent, correct profile/squad/host binding, public port reachability, and a real tunneled request.

## Client compatibility

- On affected Happ/mobile routes, `chrome` fingerprint is known to fail.
- Default fingerprint: `firefox`; fallback: `edge`. Do not change this without a real client gate.

## Product profiles

- Normal profiles: traffic multiplier 1.
- LTE/anti-block and CDN/XHTTP profiles: separate inbounds/hosts, traffic multiplier 1. Do not silently merge identities, quotas, or product presentation into normal profiles.
- Current CDN XHTTP baseline (2026-09-29): `packet-up`, `GET` uplink with `uplinkDataPlacement: header` and `uplinkDataKey: X-Session-Token` on both profile and Host. Estonia uses `/api-test`, Finland `/api-fin`; retain compatible padding and check rendered `extra`. The former `OPTIONS -> POST` route is historical, not a provisioning template. Verify live state; see `docs/operations/node-topology-current.md`.

## Gate

For TCP Reality, Hysteria2, UDP, or XHTTP, verify syntax, listening socket, firewall, Remnawave binding, generated client profile, and real traffic. Ping alone is not proof.

Before a topology mutation, the accepted stage contract must identify every client-visible path, hostname, CDN resource, origin/fallback order, Host/SNI, inbound/path, multiplier, public identifier impact, failure behavior, and rollback. A previously rejected draft is not an implementation option.
