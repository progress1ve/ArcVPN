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
- Working DHost XHTTP baseline: `packet-up`, path `/api-test`, upstream method `OPTIONS`, compatible padding, and origin rewrite `OPTIONS -> POST` where required by the CDN path.

## Gate

For TCP Reality, Hysteria2, UDP, or XHTTP, verify syntax, listening socket, firewall, Remnawave binding, generated client profile, and real traffic. Ping alone is not proof.

Before a topology mutation, the accepted stage contract must identify every client-visible path, hostname, CDN resource, origin/fallback order, Host/SNI, inbound/path, multiplier, public identifier impact, failure behavior, and rollback. A previously rejected draft is not an implementation option.
